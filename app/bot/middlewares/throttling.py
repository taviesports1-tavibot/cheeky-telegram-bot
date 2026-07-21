from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from app.config import Settings
from app.services.cache import CacheService


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, cache: CacheService, settings: Settings) -> None:
        self.cache = cache
        self.settings = settings

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message) or event.from_user is None:
            return await handler(event, data)
        key = f"rate:{event.chat.id}:{event.from_user.id}"
        if not await self.cache.allowed(key, self.settings.rate_limit_per_minute, 60):
            await event.answer(
                "Притормози, чемпион. Я не успеваю разгребать этот пулемёт сообщений 😅"
            )
            return None
        return await handler(event, data)
