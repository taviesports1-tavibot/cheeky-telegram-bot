from __future__ import annotations

import asyncio
from contextlib import suppress

import structlog
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from app.ai import OpenAICompatibleProvider
from app.bot.handlers import register_handlers
from app.bot.middlewares import ContextMiddleware, ThrottlingMiddleware
from app.config import Settings, get_settings
from app.database import Database
from app.services import CacheService, ChatAIService, TTSService
from app.services.scheduler import SchedulerService
from app.utils.logging import configure_logging

log = structlog.get_logger()


def build_storage(settings: Settings, cache: CacheService) -> BaseStorage:
    if settings.redis_url and cache.client is not None:
        return RedisStorage.from_url(settings.redis_url)
    return MemoryStorage()


async def set_commands(bot: Bot) -> None:
    commands = [
        BotCommand(command="help", description="Все команды"),
        BotCommand(command="profile", description="Мой профиль"),
        BotCommand(command="memory", description="Что бот помнит"),
        BotCommand(command="voice", description="Озвучить текст"),
        BotCommand(command="meme", description="Случайный мем"),
        BotCommand(command="roulette", description="Рулетка ответов"),
        BotCommand(command="who_today", description="Кто сегодня"),
        BotCommand(command="truth_or_dare", description="Правда или действие"),
        BotCommand(command="prediction", description="Предсказание"),
        BotCommand(command="roast", description="Дружеская прожарка"),
    ]
    await bot.set_my_commands(commands)


async def create_app(
    settings: Settings,
) -> tuple[Bot, Dispatcher, Database, CacheService, SchedulerService]:
    bot = Bot(
        token=settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    database = Database(settings.database_url)
    cache = CacheService(settings.redis_url)
    await cache.connect()
    storage = build_storage(settings, cache)
    dispatcher = Dispatcher(storage=storage)
    ai_chat = ChatAIService(OpenAICompatibleProvider(settings), settings)
    tts = TTSService(settings.tts_voice)
    scheduler = SchedulerService(bot, database, settings.default_timezone)

    dispatcher["settings"] = settings
    dispatcher["database"] = database
    dispatcher["cache"] = cache
    dispatcher["ai_chat"] = ai_chat
    dispatcher["tts"] = tts
    dispatcher["scheduler"] = scheduler
    dispatcher.message.outer_middleware(ThrottlingMiddleware(cache, settings))
    dispatcher.message.outer_middleware(ContextMiddleware(database, settings))
    register_handlers(dispatcher)
    return bot, dispatcher, database, cache, scheduler


async def close_resources(
    bot: Bot,
    dispatcher: Dispatcher,
    database: Database,
    cache: CacheService,
    scheduler: SchedulerService,
) -> None:
    await scheduler.close()
    await dispatcher.storage.close()
    await cache.close()
    await database.close()
    await bot.session.close()
    log.info("bot_stopped")


async def run_polling(settings: Settings) -> None:
    bot, dispatcher, database, cache, scheduler = await create_app(settings)
    health_app = web.Application()

    async def health(_: web.Request) -> web.Response:
        return web.json_response(
            {"status": "ok", "database": await database.health(), "redis": cache.client is not None}
        )

    health_app.router.add_get("/health", health)
    runner = web.AppRunner(health_app)
    try:
        await runner.setup()
        await web.TCPSite(runner, "0.0.0.0", settings.port).start()
        await bot.delete_webhook(drop_pending_updates=False)
        await set_commands(bot)
        await scheduler.start()
        log.info("bot_started", mode="polling")
        await dispatcher.start_polling(bot, allowed_updates=dispatcher.resolve_used_update_types())
    finally:
        await runner.cleanup()
        await close_resources(bot, dispatcher, database, cache, scheduler)


async def run_webhook(settings: Settings) -> None:
    if not settings.webhook_url or not settings.webhook_secret.get_secret_value():
        raise RuntimeError("WEBHOOK_URL и WEBHOOK_SECRET обязательны для webhook")
    bot, dispatcher, database, cache, scheduler = await create_app(settings)
    app = web.Application()

    async def health(_: web.Request) -> web.Response:
        return web.json_response(
            {"status": "ok", "database": await database.health(), "redis": cache.client is not None}
        )

    app.router.add_get("/health", health)
    SimpleRequestHandler(
        dispatcher=dispatcher,
        bot=bot,
        secret_token=settings.webhook_secret.get_secret_value(),
    ).register(app, path=settings.webhook_path)
    setup_application(app, dispatcher, bot=bot)

    async def startup(_: web.Application) -> None:
        await set_commands(bot)
        await scheduler.start()
        url = settings.webhook_url.rstrip("/") + settings.webhook_path
        await bot.set_webhook(
            url,
            secret_token=settings.webhook_secret.get_secret_value(),
            allowed_updates=dispatcher.resolve_used_update_types(),
        )
        log.info("bot_started", mode="webhook")

    async def cleanup(_: web.Application) -> None:
        await close_resources(bot, dispatcher, database, cache, scheduler)

    app.on_startup.append(startup)
    app.on_cleanup.append(cleanup)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", settings.port)
    await site.start()
    try:
        await asyncio.Event().wait()
    finally:
        with suppress(Exception):
            await runner.cleanup()


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    if not settings.bot_token.get_secret_value():
        raise RuntimeError("BOT_TOKEN не задан. Скопируйте .env.example в .env и заполните токен.")
    asyncio.run(run_webhook(settings) if settings.bot_mode == "webhook" else run_polling(settings))


if __name__ == "__main__":
    main()
