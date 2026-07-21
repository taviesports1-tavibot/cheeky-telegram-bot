from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Chat
from app.database.repositories import UserRepository
from app.services import games
from app.services.cache import CacheService
from app.utils.html import safe

router = Router(name="games")


async def game_ready(message: Message, cache: CacheService) -> bool:
    if await cache.acquire_once(
        f"game:{message.chat.id}:{message.from_user.id if message.from_user else 0}", 8
    ):
        return True
    await message.answer("Игровой автомат ещё крутится. Подожди пару секунд, азартный ты человек.")
    return False


@router.message(Command("roulette"))
async def roulette(message: Message, cache: CacheService) -> None:
    if await game_ready(message, cache):
        await message.answer("🎰 " + games.roulette())


@router.message(Command("who_today"))
async def who_today(
    message: Message, cache: CacheService, db_session: AsyncSession | None, db_chat: Chat | None
) -> None:
    if not await game_ready(message, cache):
        return
    users = (
        await UserRepository(db_session).active_in_chat(db_chat.id)
        if db_session and db_chat
        else []
    )
    names = [safe("@" + user.username if user.username else user.display_name) for user in users]
    await message.answer(games.who_today(names))


@router.message(Command("duel"))
async def duel(message: Message, command: CommandObject, cache: CacheService) -> None:
    if not await game_ready(message, cache):
        return
    first = safe(message.from_user.full_name if message.from_user else "Аноним")
    second = ""
    if message.reply_to_message and message.reply_to_message.from_user:
        second = safe(message.reply_to_message.from_user.full_name)
    elif command.args:
        second = safe(command.args.strip()[:100])
    if not second:
        await message.answer(
            "Вызови соперника ответом на его сообщение или: <code>/duel @username</code>"
        )
        return
    await message.answer(games.duel(first, second))


@router.message(Command("truth_or_dare"))
async def truth_or_dare(message: Message, cache: CacheService) -> None:
    if await game_ready(message, cache):
        await message.answer(games.truth_or_dare())


@router.message(Command("prediction"))
async def prediction(message: Message, cache: CacheService) -> None:
    if await game_ready(message, cache):
        await message.answer(games.prediction())


@router.message(Command("rate"))
async def rate(message: Message, command: CommandObject, cache: CacheService) -> None:
    if not await game_ready(message, cache):
        return
    text = command.args or (message.reply_to_message.text if message.reply_to_message else "") or ""
    await message.answer(games.rate(text))


@router.message(Command("roast"))
async def roast(message: Message, command: CommandObject, cache: CacheService) -> None:
    if not await game_ready(message, cache):
        return
    target = command.args or (
        message.reply_to_message.from_user.full_name
        if message.reply_to_message and message.reply_to_message.from_user
        else ""
    )
    if not target:
        target = message.from_user.full_name if message.from_user else "герой"
    await message.answer(games.roast(safe(target[:100]), target))
