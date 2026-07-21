from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import FSInputFile, Message

from app.database.models import ChatSettings
from app.services.tts import TTSService

router = Router(name="voice")


@router.message(Command("voice"))
async def voice(
    message: Message, command: CommandObject, tts: TTSService, chat_settings: ChatSettings | None
) -> None:
    text = (command.args or "").strip()
    if not text:
        await message.answer("Напиши текст после команды: <code>/voice Ну что, погнали?</code>")
        return
    if len(text) > tts.max_length:
        await message.answer(
            f"Слишком длинно. Максимум {tts.max_length} символов — я не аудиокнига."
        )
        return
    path = await tts.synthesize(text, chat_settings.tts_voice if chat_settings else None)
    if path is None:
        await message.answer("Голосовые связки сегодня бастуют. Текстом я всё ещё великолепен.")
        return
    try:
        await message.answer_voice(FSInputFile(path))
    finally:
        await tts.cleanup(path)
