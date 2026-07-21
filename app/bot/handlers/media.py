from aiogram import Bot, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters import is_admin
from app.config import Settings
from app.database.models import Chat, MediaItem, User
from app.database.repositories import MediaRepository
from app.services.media import ALLOWED_CATEGORIES, send_media, validate_media

router = Router(name="media")

CATEGORY_MAP = {"meme": "memes", "gif": "gifs", "photo": "photos", "reaction": "reactions"}


async def send_random(
    message: Message,
    bot: Bot,
    category: str,
    db_session: AsyncSession | None,
    db_chat: Chat | None,
) -> None:
    if db_session is None:
        await message.answer("Медиатека временно закрыта на переучёт.")
        return
    item = await MediaRepository(db_session).random(category, db_chat.id if db_chat else None)
    if item is None:
        await message.answer("В этой категории пока пусто. Админ, заноси мемы через /add_media 😈")
        return
    try:
        await send_media(bot, message.chat.id, item)
    except Exception:
        await message.answer("Этот файл решил умереть молодым. Попробуй ещё раз.")


@router.message(Command(*CATEGORY_MAP.keys()))
async def media_command(
    message: Message, bot: Bot, db_session: AsyncSession | None, db_chat: Chat | None
) -> None:
    command = (message.text or "").split()[0].split("@")[0].lstrip("/")
    await send_random(message, bot, CATEGORY_MAP[command], db_session, db_chat)


@router.message(Command("add_media"))
async def add_media(
    message: Message,
    command: CommandObject,
    bot: Bot,
    settings: Settings,
    db_session: AsyncSession | None,
    db_chat: Chat | None,
    db_user: User | None,
) -> None:
    user_id = message.from_user.id if message.from_user else 0
    if not await is_admin(bot, message.chat.id, user_id, settings.superadmin_ids):
        await message.answer("Медиатекой заведуют админы. Не трогай экспонаты руками.")
        return
    if db_session is None or db_chat is None:
        await message.answer("База недоступна, файл не сохранён.")
        return
    category = (command.args or "random").strip().casefold()
    if category not in ALLOWED_CATEGORIES:
        await message.answer("Категория: " + ", ".join(sorted(ALLOWED_CATEGORIES)))
        return
    source = message.reply_to_message
    if source is None:
        await message.answer("Ответь этой командой на фото, GIF, голосовое или документ.")
        return
    file_id: str | None = None
    mime: str | None = None
    size: int | None = None
    media_type = "document"
    if source.photo:
        photo = source.photo[-1]
        file_id, size, mime, media_type = (
            photo.file_id,
            photo.file_size,
            "image/jpeg",
            "photo",
        )
    elif source.animation:
        animation = source.animation
        file_id, size, mime, media_type = (
            animation.file_id,
            animation.file_size,
            animation.mime_type or "image/gif",
            "animation",
        )
    elif source.voice:
        voice = source.voice
        file_id, size, mime, media_type = (
            voice.file_id,
            voice.file_size,
            voice.mime_type or "audio/ogg",
            "voice",
        )
    elif source.document:
        document = source.document
        file_id, size, mime = document.file_id, document.file_size, document.mime_type
    validation = validate_media(mime, size, settings.max_media_size_mb)
    if not file_id or not validation.valid:
        await message.answer(validation.reason or "Не нашёл подходящий файл.")
        return
    saved = await MediaRepository(db_session).add(
        chat_id=db_chat.id,
        category=category,
        media_type=media_type,
        telegram_file_id=file_id,
        mime_type=mime,
        file_size=size,
        added_by_id=db_user.id if db_user else None,
        safe=True,
    )
    await message.answer(
        f"Добавил в медиатеку. ID: <code>{saved.id}</code>, категория: {category}."
    )


@router.message(Command("delete_media"))
async def delete_media(
    message: Message,
    command: CommandObject,
    bot: Bot,
    settings: Settings,
    db_session: AsyncSession | None,
    db_chat: Chat | None,
) -> None:
    user_id = message.from_user.id if message.from_user else 0
    if not await is_admin(bot, message.chat.id, user_id, settings.superadmin_ids):
        return
    try:
        media_id = int(command.args or "")
    except ValueError:
        await message.answer("Формат: <code>/delete_media ID</code>")
        return
    deleted = bool(
        db_session and db_chat and await MediaRepository(db_session).delete(media_id, db_chat.id)
    )
    await message.answer("Удалено." if deleted else "Такого ID в этом чате нет.")


@router.message(Command("media_stats"))
async def media_stats(
    message: Message,
    bot: Bot,
    settings: Settings,
    db_session: AsyncSession | None,
    db_chat: Chat | None,
) -> None:
    user_id = message.from_user.id if message.from_user else 0
    if (
        not await is_admin(bot, message.chat.id, user_id, settings.superadmin_ids)
        or not db_session
        or not db_chat
    ):
        return
    rows = (
        await db_session.execute(
            select(MediaItem.category, func.count(MediaItem.id), func.sum(MediaItem.use_count))
            .where(MediaItem.chat_id == db_chat.id)
            .group_by(MediaItem.category)
        )
    ).all()
    text = (
        "\n".join(f"{cat}: {count} шт., отправлено {uses or 0}" for cat, count, uses in rows)
        or "Медиатека пуста."
    )
    await message.answer("<b>Медиа:</b>\n" + text)
