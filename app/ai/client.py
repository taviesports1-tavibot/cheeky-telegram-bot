from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import structlog
from openai import AsyncOpenAI, RateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from app.config import Settings

log = structlog.get_logger()


@dataclass(frozen=True, slots=True)
class AIResponse:
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    model: str = ""


class AIProvider(ABC):
    @abstractmethod
    async def generate(self, messages: list[dict[str, str]]) -> AIResponse:
        raise NotImplementedError


class OpenAICompatibleProvider(AIProvider):
    def __init__(self, settings: Settings) -> None:
        api_key = settings.ai_api_key.get_secret_value() or (
            "ollama" if settings.ai_provider == "ollama" else "missing"
        )
        base_url = settings.ai_base_url or (
            "http://localhost:11434/v1" if settings.ai_provider == "ollama" else None
        )
        self.client = AsyncOpenAI(
            api_key=api_key, base_url=base_url, timeout=settings.ai_timeout_seconds
        )
        self.model = settings.ai_model
        self.temperature = settings.ai_temperature
        self.max_tokens = settings.ai_max_tokens

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=8),
        retry=retry_if_exception_type((RateLimitError, TimeoutError)),
        reraise=True,
    )
    async def generate(self, messages: list[dict[str, str]]) -> AIResponse:
        started = time.monotonic()
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore[arg-type]
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        usage: Any = response.usage
        text = response.choices[0].message.content or ""
        return AIResponse(
            text=text.strip(),
            prompt_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
            completion_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
            latency_ms=int((time.monotonic() - started) * 1000),
            model=response.model,
        )


FALLBACKS = (
    "У меня сейчас нейроны пошли покурить. Повтори через минутку 😈",
    "ИИ-шная кухня временно в дыму. Я жив, но ответ пока сгорел 🔥",
    "Сервер задумался о смысле жизни. Дай ему секунду и спроси ещё раз.",
)
