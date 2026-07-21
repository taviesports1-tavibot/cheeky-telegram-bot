from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from app.config import Settings
from app.database import Database
from app.database.models import CommandUsage
from app.database.repositories import SettingsRepository, UserRepository

log = structlog.get_logger()


class ContextMiddleware(BaseMiddleware):
    def __init__(self, database: Database, settings: Settings) -> None:
        self.database = database
        self.settings = settings

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message) or event.from_user is None:
            return await handler(event, data)
        try:
            async with self.database.session() as session:
                user = await UserRepository(session).upsert(
                    event.from_user.id,
                    event.from_user.username,
                    event.from_user.full_name,
                )
                chat = await SettingsRepository(session).get_or_create_chat(
                    event.chat.id,
                    event.chat.title,
                    event.chat.type,
                )
                defaults = {
                    "rudeness_level": self.settings.default_rudeness_level,
                    "swearing_enabled": self.settings.default_swearing_enabled,
                    "random_reply_chance": self.settings.default_random_reply_chance,
                    "voice_reply_chance": self.settings.default_voice_reply_chance,
                    "reaction_chance": self.settings.default_reaction_chance,
                    "timezone": self.settings.default_timezone,
                    "tts_voice": self.settings.tts_voice,
                }
                chat_settings = await SettingsRepository(session).get_or_create_settings(
                    chat, defaults
                )
                if event.text and event.text.startswith("/"):
                    command = event.text.split(maxsplit=1)[0].split("@")[0].lstrip("/")[:64]
                    session.add(CommandUsage(command=command, chat_id=chat.id, user_id=user.id))
                data.update(
                    db_session=session, db_user=user, db_chat=chat, chat_settings=chat_settings
                )
                return await handler(event, data)
        except Exception as exc:
            log.error("context_database_error", error=type(exc).__name__)
            data.update(db_session=None, db_user=None, db_chat=None, chat_settings=None)
            return await handler(event, data)
