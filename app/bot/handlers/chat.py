from __future__ import annotations

import asyncio
import random

import structlog
from aiogram import Bot, F, Router
from aiogram.types import FSInputFile, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.moderation import sanitize_user_text
from app.bot.keyboards import welcome_buttons
from app.database.models import Chat, ChatSettings, User, UserBotBan
from app.database.repositories import MemoryRepository
from app.services.ai_chat import ChatAIService
from app.services.cache import CacheService
from app.services.reactions import choose_reaction, react
from app.services.tts import TTSService
from app.texts.ru import WELCOME_TEMPLATES
from app.utils.html import safe

log = structlog.get_logger()
router = Router(name="chat")
TRIGGERS = ("шальной", "бот скажи", "эй бот", "совет нужен", "рассуди нас")


def fallback_settings() -> ChatSettings:
    return ChatSettings(
        rudeness_level=3,
        swearing_enabled=True,
        random_reply_chance=0,
        voice_reply_chance=0,
        reaction_enabled=True,
        reaction_chance=0,
        reaction_emojis=["😂", "🔥", "👏"],
        tts_voice="ru-RU-DmitryNeural",
        welcome_delay_seconds=1,
        welcome_voice_chance=0,
    )


@router.message(F.new_chat_members)
async def welcome(message: Message, chat_settings: ChatSettings | None) -> None:
    settings = chat_settings or fallback_settings()
    if settings.welcome_delay_seconds:
        await asyncio.sleep(min(settings.welcome_delay_seconds, 10))
    for member in message.new_chat_members or []:
        if member.is_bot:
            continue
        text = random.choice(WELCOME_TEMPLATES).format(name=safe(member.full_name))
        if settings.rules_text:
            text += "\n\n📜 " + safe(settings.rules_text[:1000])
        await message.answer(text, reply_markup=welcome_buttons(settings.rules_url))


@router.message(F.text & ~F.text.startswith("/"))
async def conversational_reply(
    message: Message,
    bot: Bot,
    ai_chat: ChatAIService,
    tts: TTSService,
    cache: CacheService,
    db_session: AsyncSession | None,
    db_user: User | None,
    db_chat: Chat | None,
    chat_settings: ChatSettings | None,
) -> None:
    if message.from_user is None or message.from_user.is_bot:
        return
    if db_session and db_chat and db_user:
        banned = await db_session.scalar(
            select(UserBotBan.id).where(
                UserBotBan.chat_id == db_chat.id, UserBotBan.user_id == db_user.id
            )
        )
        if banned:
            return
    settings = chat_settings or fallback_settings()
    text = message.text or ""
    lowered = text.casefold()
    remember_prefix = "запомни, что"
    if lowered.startswith(remember_prefix) and db_session and db_user:
        fact = sanitize_user_text(text[len(remember_prefix) :].lstrip(" :,-"), max_length=500)
        if not fact:
            await message.reply(
                "А что именно запомнить? После фразы — пустота, как утром в голове."
            )
            return
        if "[СКРЫТО]" in fact:
            await message.reply(
                "Такое я не сохраняю. Платёжным и чувствительным данным тут не место."
            )
            return
        await MemoryRepository(db_session).add(db_user.id, fact)
        await message.reply("Запомнил. Теперь это официальная часть нашей странной истории 😈")
        return
    bot_user = await bot.me()
    username = (bot_user.username or "").casefold()
    mentioned = bool(username and f"@{username}" in lowered)
    replied = bool(
        message.reply_to_message
        and message.reply_to_message.from_user
        and message.reply_to_message.from_user.id == bot.id
    )
    triggered = any(trigger in lowered for trigger in TRIGGERS)
    private = message.chat.type == "private"
    random_reply = random.randrange(100) < settings.random_reply_chance
    should_reply = private or mentioned or replied or triggered or random_reply

    if settings.reaction_enabled and random.randrange(100) < settings.reaction_chance:
        if await cache.acquire_once(f"reaction:{message.chat.id}", 5):
            try:
                await react(
                    bot,
                    message.chat.id,
                    message.message_id,
                    choose_reaction(settings.reaction_emojis),
                )
            except Exception as exc:
                log.debug("reaction_failed", error=type(exc).__name__)
    if not should_reply:
        return
    if not await cache.acquire_once(f"reply:user:{message.chat.id}:{message.from_user.id}", 8):
        return
    if not await cache.acquire_once(f"reply:chat:{message.chat.id}", 3):
        return
    clean = text.replace(f"@{bot_user.username}", "").strip() if bot_user.username else text
    await bot.send_chat_action(message.chat.id, "typing")
    answer = await ai_chat.reply(
        db_session,
        db_chat,
        db_user,
        clean,
        settings.rudeness_level,
        settings.swearing_enabled,
    )
    if random.randrange(100) < settings.voice_reply_chance and len(answer) <= tts.max_length:
        path = await tts.synthesize(answer, settings.tts_voice)
        if path:
            try:
                await message.reply_voice(FSInputFile(path))
                return
            finally:
                await tts.cleanup(path)
    await message.reply(safe(answer))
