from dataclasses import dataclass

from aiogram import Bot
from aiogram.fsm.storage.base import BaseStorage

from app.ai import AIProvider
from app.config import Settings
from app.database import Database
from app.services.cache import CacheService


@dataclass(slots=True)
class AppContext:
    bot: Bot
    settings: Settings
    database: Database
    cache: CacheService
    ai: AIProvider
    storage: BaseStorage
