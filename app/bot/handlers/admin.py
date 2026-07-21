from datetime import UTC, datetime, timedelta

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters import is_admin
from app.bot.keyboards import admin_menu
from app.config import Settings
from app.database import Database
from app.database.models import (
    ApiUsage,
    BotAction,
    Chat,
    ChatSettings,
    ConversationMessage,
    MediaItem,
    User,
    UserBotBan,
)
from app.services.cache import CacheService

router = Router(name="admin")


async def require_admin(message: Message, bot: Bot, settings: Settings) -> bool:
    user_id = message.from_user.id if message.from_user else 0
    allowed = await is_admin(bot, message.chat.id, user_id, settings.superadmin_ids)
    if not allowed:
        await message.answer("Эта кнопка для админов. Корона пока не твоя 👑")
    return allowed


@router.message(Command("admin"))
async def admin_panel(message: Message, bot: Bot, settings: Settings) -> None:
    if await require_admin(message, bot, settings):
        await message.answer("<b>Панель управления хаосом</b>", reply_markup=admin_menu())


@router.callback_query(F.data.startswith("admin:"))
async def admin_callback(callback: CallbackQuery, bot: Bot, settings: Settings) -> None:
    if not callback.message or not await is_admin(
        bot, callback.message.chat.id, callback.from_user.id, settings.superadmin_ids
    ):
        await callback.answer("Нет доступа", show_alert=True)
        return
    section = (callback.data or "").split(":", 1)[1]
    hints = {
        "personality": "/rudeness 1-4, /swearing on|off, /auto_reply 0-100",
        "voice": "/voice_settings ru-RU-DmitryNeural",
        "media": "/add_media категория, /delete_media ID, /media_stats",
        "reactions": "/reaction_settings 0-100",
        "schedule": "/schedule — список и формат создания",
        "stats": "/stats, /users, /health",
    }
    await callback.answer()
    await callback.message.answer(hints.get(section, "Раздел в отпуске."))


async def update_int_setting(
    message: Message,
    command: CommandObject,
    bot: Bot,
    settings: Settings,
    row: ChatSettings | None,
    field: str,
    low: int,
    high: int,
) -> None:
    if not await require_admin(message, bot, settings) or row is None:
        return
    try:
        value = int(command.args or "")
        if not low <= value <= high:
            raise ValueError
    except ValueError:
        await message.answer(f"Нужно число от {low} до {high}.")
        return
    setattr(row, field, value)
    await message.answer(f"Готово: {value}.")


@router.message(Command("rudeness", "personality"))
async def rudeness(
    message: Message,
    command: CommandObject,
    bot: Bot,
    settings: Settings,
    chat_settings: ChatSettings | None,
) -> None:
    await update_int_setting(message, command, bot, settings, chat_settings, "rudeness_level", 1, 4)


@router.message(Command("auto_reply"))
async def auto_reply(
    message: Message,
    command: CommandObject,
    bot: Bot,
    settings: Settings,
    chat_settings: ChatSettings | None,
) -> None:
    await update_int_setting(
        message, command, bot, settings, chat_settings, "random_reply_chance", 0, 100
    )


@router.message(Command("reaction_settings"))
async def reaction_settings(
    message: Message,
    command: CommandObject,
    bot: Bot,
    settings: Settings,
    chat_settings: ChatSettings | None,
) -> None:
    await update_int_setting(
        message, command, bot, settings, chat_settings, "reaction_chance", 0, 100
    )


@router.message(Command("swearing"))
async def swearing(
    message: Message,
    command: CommandObject,
    bot: Bot,
    settings: Settings,
    chat_settings: ChatSettings | None,
) -> None:
    if not await require_admin(message, bot, settings) or chat_settings is None:
        return
    value = (command.args or "").casefold()
    if value not in {"on", "off"}:
        await message.answer("Формат: <code>/swearing on</code> или <code>off</code>")
        return
    chat_settings.swearing_enabled = value == "on"
    await message.answer(
        "Мат включён. Держите меня семеро." if value == "on" else "Мат выключен. Надеваю галстук."
    )


@router.message(Command("voice_settings"))
async def voice_settings(
    message: Message,
    command: CommandObject,
    bot: Bot,
    settings: Settings,
    chat_settings: ChatSettings | None,
) -> None:
    from app.services.tts import ALLOWED_VOICES

    if not await require_admin(message, bot, settings) or chat_settings is None:
        return
    voice = (command.args or "").strip()
    if voice not in ALLOWED_VOICES:
        await message.answer("Доступные голоса:\n" + "\n".join(sorted(ALLOWED_VOICES)))
        return
    chat_settings.tts_voice = voice
    await message.answer("Голос сменил. Теперь официально звучим дороже.")


@router.message(Command("reset_context"))
async def reset_context(
    message: Message,
    bot: Bot,
    settings: Settings,
    db_session: AsyncSession | None,
    db_chat: Chat | None,
) -> None:
    if await require_admin(message, bot, settings) and db_session and db_chat:
        await db_session.execute(
            delete(ConversationMessage).where(ConversationMessage.chat_id == db_chat.id)
        )
        await message.answer("Контекст чата очищен. Никто ничего не видел.")


@router.message(Command("ban_bot", "unban_bot"))
async def bot_ban(
    message: Message,
    bot: Bot,
    settings: Settings,
    db_session: AsyncSession | None,
    db_chat: Chat | None,
) -> None:
    if not await require_admin(message, bot, settings) or not db_session or not db_chat:
        return
    target = message.reply_to_message.from_user if message.reply_to_message else None
    if target is None:
        await message.answer("Ответь командой на сообщение пользователя.")
        return
    user = await db_session.scalar(select(User).where(User.telegram_id == target.id))
    if user is None:
        await message.answer("Пользователь ещё не записан в базе.")
        return
    unban = (message.text or "").startswith("/unban_bot")
    await db_session.execute(
        delete(UserBotBan).where(UserBotBan.chat_id == db_chat.id, UserBotBan.user_id == user.id)
    )
    if not unban:
        db_session.add(UserBotBan(chat_id=db_chat.id, user_id=user.id, reason="admin command"))
    await message.answer(
        "Доступ к боту возвращён."
        if unban
        else "Пользователь больше не может взаимодействовать с ботом."
    )


@router.message(Command("stats", "users"))
async def stats(
    message: Message,
    bot: Bot,
    settings: Settings,
    db_session: AsyncSession | None,
    db_chat: Chat | None,
) -> None:
    if not await require_admin(message, bot, settings) or not db_session or not db_chat:
        return
    now = datetime.now(UTC)
    day = (
        await db_session.scalar(
            select(func.count(User.id)).where(User.last_active_at >= now - timedelta(days=1))
        )
        or 0
    )
    week = (
        await db_session.scalar(
            select(func.count(User.id)).where(User.last_active_at >= now - timedelta(days=7))
        )
        or 0
    )
    month = (
        await db_session.scalar(
            select(func.count(User.id)).where(User.last_active_at >= now - timedelta(days=30))
        )
        or 0
    )
    total = await db_session.scalar(select(func.count(User.id))) or 0
    messages = (
        await db_session.scalar(
            select(func.count(ConversationMessage.id)).where(
                ConversationMessage.chat_id == db_chat.id
            )
        )
        or 0
    )
    media = (
        await db_session.scalar(
            select(func.sum(MediaItem.use_count)).where(MediaItem.chat_id == db_chat.id)
        )
        or 0
    )
    usage = (
        await db_session.execute(
            select(
                func.coalesce(func.sum(ApiUsage.prompt_tokens + ApiUsage.completion_tokens), 0),
                func.coalesce(func.avg(ApiUsage.latency_ms), 0),
                func.coalesce(func.sum(ApiUsage.estimated_cost_usd), 0),
            ).where(ApiUsage.chat_id == db_chat.id)
        )
    ).one()
    await message.answer(
        f"<b>Статистика</b>\nПользователей: {total}\nАктивны 24ч/7д/30д: {day}/{week}/{month}\n"
        f"Сообщений в контексте: {messages}\nМедиа отправлено: {media}\n"
        f"AI-токенов: {usage[0]}\nСредний ответ: {float(usage[1]):.0f} мс\n"
        f"Оценка стоимости: ${float(usage[2]):.4f}"
    )


@router.message(Command("health"))
async def health(
    message: Message,
    bot: Bot,
    settings: Settings,
    database: Database,
    cache: CacheService,
) -> None:
    if not await require_admin(message, bot, settings):
        return
    db_ok = await database.health()
    redis_ok = bool(getattr(cache, "client", None))
    await message.answer(
        f"Bot: ✅\nPostgreSQL: {'✅' if db_ok else '❌'}\n"
        f"Redis: {'✅' if redis_ok else '⚠️ fallback'}"
    )


@router.message(Command("broadcast"))
async def broadcast(
    message: Message,
    command: CommandObject,
    bot: Bot,
    settings: Settings,
    db_session: AsyncSession | None,
) -> None:
    if not message.from_user or message.from_user.id not in settings.superadmin_ids:
        await message.answer("Рассылку может запускать только SUPERADMIN.")
        return
    text = (command.args or "").strip()
    if not text.startswith("--confirm "):
        await message.answer("Для подтверждения: <code>/broadcast --confirm текст</code>")
        return
    if not db_session:
        await message.answer("База недоступна.")
        return
    payload = text.removeprefix("--confirm ")[:4000]
    chats = list((await db_session.scalars(select(Chat).where(Chat.active.is_(True)))).all())
    sent = failed = 0
    for chat in chats:
        try:
            await bot.send_message(chat.telegram_id, payload)
            sent += 1
        except Exception:
            failed += 1
    db_session.add(BotAction(action="broadcast", details={"sent": sent, "failed": failed}))
    await message.answer(f"Рассылка завершена: {sent} успешно, {failed} ошибок.")


@router.message(Command("logs"))
async def logs(
    message: Message, bot: Bot, settings: Settings, db_session: AsyncSession | None
) -> None:
    if not await require_admin(message, bot, settings) or not db_session:
        return
    rows = list(
        (
            await db_session.scalars(
                select(BotAction).order_by(BotAction.created_at.desc()).limit(20)
            )
        ).all()
    )
    text = (
        "\n".join(f"#{row.id} {row.created_at:%d.%m %H:%M} — {row.action}" for row in rows)
        or "Действий пока нет."
    )
    await message.answer("<b>Последние действия</b>\n" + text)


@router.message(Command("media_settings"))
async def media_settings(message: Message, bot: Bot, settings: Settings) -> None:
    if await require_admin(message, bot, settings):
        await message.answer(
            f"Максимальный размер: {settings.max_media_size_mb} МБ. "
            "Разрешены JPEG, PNG, WebP, GIF, MP4 и OGG. Добавление: /add_media категория."
        )
