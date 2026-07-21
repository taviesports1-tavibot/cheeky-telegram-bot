from aiogram import Dispatcher

from app.bot.handlers import admin, chat, common, games, media, schedule, voice


def register_handlers(dispatcher: Dispatcher) -> None:
    dispatcher.include_router(common.router)
    dispatcher.include_router(voice.router)
    dispatcher.include_router(media.router)
    dispatcher.include_router(games.router)
    dispatcher.include_router(schedule.router)
    dispatcher.include_router(admin.router)
    dispatcher.include_router(chat.router)


__all__ = ["register_handlers"]
