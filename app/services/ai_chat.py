from __future__ import annotations

import asyncio
import random

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import AIProvider, AIResponse
from app.ai.client import FALLBACKS
from app.ai.memory import approximate_tokens, trim_context
from app.ai.moderation import looks_like_prompt_injection, sanitize_user_text
from app.ai.prompts import Personality, build_system_prompt
from app.config import Settings
from app.database.models import ApiUsage, Chat, ConversationMessage, User
from app.database.repositories import MemoryRepository

log = structlog.get_logger()


class ChatAIService:
    def __init__(self, provider: AIProvider, settings: Settings) -> None:
        self.provider = provider
        self.settings = settings
        self._semaphore = asyncio.Semaphore(4)

    async def reply(
        self,
        session: AsyncSession | None,
        chat: Chat | None,
        user: User | None,
        text: str,
        rudeness: int,
        swearing: bool,
    ) -> str:
        clean = sanitize_user_text(text)
        if looks_like_prompt_injection(clean):
            return "Хитро. Но внутренние настройки я не раздаю — даже за красивые глаза 😈"
        memories: list[str] = []
        history: list[dict[str, str]] = []
        if session and chat and user:
            memories = [m.content for m in await MemoryRepository(session).list_for_user(user.id)]
            rows = list(
                (
                    await session.scalars(
                        select(ConversationMessage)
                        .where(ConversationMessage.chat_id == chat.id)
                        .order_by(ConversationMessage.created_at.desc())
                        .limit(30)
                    )
                ).all()
            )
            history = [{"role": row.role, "content": row.content} for row in reversed(rows)]
        system = build_system_prompt(Personality(rudeness, swearing), memories)
        display_name = user.preferred_name or user.display_name if user is not None else "участника"
        messages = [
            {"role": "system", "content": system},
            *history,
            {
                "role": "user",
                "content": f"Сообщение от {display_name}: {clean}",
            },
        ]
        messages = [messages[0], *trim_context(messages[1:], self.settings.ai_context_token_limit)]
        try:
            async with self._semaphore:
                response = await self.provider.generate(messages)
            answer = response.text or random.choice(FALLBACKS)
            await self._record(session, chat, user, clean, answer, response, True)
            return answer
        except Exception as exc:
            log.error("ai_request_failed", error=type(exc).__name__)
            await self._record(
                session, chat, user, clean, "", AIResponse(""), False, type(exc).__name__
            )
            return random.choice(FALLBACKS)

    async def _record(
        self,
        session: AsyncSession | None,
        chat: Chat | None,
        user: User | None,
        prompt: str,
        answer: str,
        response: AIResponse,
        success: bool,
        error: str | None = None,
    ) -> None:
        if not session or not chat or not user:
            return
        session.add_all(
            [
                ConversationMessage(
                    chat_id=chat.id,
                    user_id=user.id,
                    role="user",
                    content=prompt,
                    token_count=approximate_tokens(prompt),
                ),
                ConversationMessage(
                    chat_id=chat.id,
                    role="assistant",
                    content=answer,
                    token_count=approximate_tokens(answer),
                ),
                ApiUsage(
                    chat_id=chat.id,
                    user_id=user.id,
                    provider=self.settings.ai_provider,
                    model=response.model or self.settings.ai_model,
                    prompt_tokens=response.prompt_tokens,
                    completion_tokens=response.completion_tokens,
                    estimated_cost_usd=(
                        response.prompt_tokens * 0.15 / 1_000_000
                        + response.completion_tokens * 0.60 / 1_000_000
                    ),
                    latency_ms=response.latency_ms,
                    success=success,
                    error_code=error,
                ),
            ]
        )
