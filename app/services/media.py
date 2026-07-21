from __future__ import annotations

from dataclasses import dataclass

from aiogram import Bot
from aiogram.types import FSInputFile

from app.database.models import MediaItem

ALLOWED_MIME = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "video/mp4",
    "audio/ogg",
}
ALLOWED_CATEGORIES = {
    "memes",
    "reactions",
    "welcome",
    "parties",
    "mood",
    "games",
    "animals",
    "relationships",
    "sarcasm",
    "motivation",
    "random",
    "gifs",
    "photos",
}


@dataclass(frozen=True, slots=True)
class MediaValidation:
    valid: bool
    reason: str = ""


def validate_media(mime_type: str | None, size: int | None, max_mb: int) -> MediaValidation:
    if mime_type not in ALLOWED_MIME:
        return MediaValidation(False, "Неподдерживаемый тип файла")
    if size is None or size <= 0 or size > max_mb * 1024 * 1024:
        return MediaValidation(False, f"Размер должен быть от 1 байта до {max_mb} МБ")
    return MediaValidation(True)


async def send_media(bot: Bot, chat_id: int, item: MediaItem, caption: str | None = None) -> None:
    source: str | FSInputFile
    if item.telegram_file_id:
        source = item.telegram_file_id
    elif item.local_path:
        source = FSInputFile(item.local_path)
    elif item.source_url:
        source = item.source_url
    else:
        raise ValueError("Media item has no source")
    if item.media_type == "photo":
        await bot.send_photo(chat_id, source, caption=caption)
    elif item.media_type in {"gif", "animation"}:
        await bot.send_animation(chat_id, source, caption=caption)
    elif item.media_type == "voice":
        await bot.send_voice(chat_id, source, caption=caption)
    else:
        await bot.send_document(chat_id, source, caption=caption)
