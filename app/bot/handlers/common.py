from datetime import date, datetime

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters import is_admin
from app.bot.keyboards import confirm_forget
from app.config import Settings
from app.database.models import Birthday, Chat, User
from app.database.repositories import MemoryRepository
from app.texts.ru import ADMIN_HELP, USER_HELP
from app.utils.html import safe

router = Router(name="common")


@router.message(Command("start"))
async def start(message: Message) -> None:
    await message.answer(
        "Привет. Я Шальной — местный поставщик шуток, мемов и сомнительно мудрых советов 😈\n"
        "Жми /help, если хочешь посмотреть весь арсенал."
    )


@router.message(Command("help"))
async def help_command(message: Message, bot: Bot, settings: Settings) -> None:
    user_id = message.from_user.id if message.from_user else 0
    admin = await is_admin(bot, message.chat.id, user_id, settings.superadmin_ids)
    await message.answer(USER_HELP + (ADMIN_HELP if admin else ""))


@router.message(Command("profile"))
async def profile(message: Message, db_user: User | None) -> None:
    if db_user is None:
        await message.answer("База сейчас отдыхает. Профиль покажу, когда она вернётся с перекура.")
        return
    level = max(0, db_user.relationship_level)
    await message.answer(
        f"<b>Профиль {safe(db_user.preferred_name or db_user.display_name)}</b>\n"
        f"Сообщений: {db_user.message_count}\n"
        f"Уровень отношений со мной: {level} 😈\n"
        f"Язык: {safe(db_user.language)}"
    )


@router.message(Command("memory"))
async def memory(message: Message, db_session: AsyncSession | None, db_user: User | None) -> None:
    if db_session is None or db_user is None:
        await message.answer("Память временно недоступна. Я не забыл тебя, просто БД прилегла.")
        return
    items = await MemoryRepository(db_session).list_for_user(db_user.id)
    facts = (
        "\n".join(f"• {safe(item.content)}" for item in items)
        or "Пока ничего важного. Загадочный ты человек."
    )
    await message.answer(
        f"<b>Что я помню о тебе:</b>\n{facts}\n\nЧувствительные данные я намеренно не храню."
    )


@router.message(Command("forget_me"))
async def forget_me(message: Message) -> None:
    if message.from_user:
        await message.answer(
            "Удалить факты и историю диалогов о тебе? Назад дороги не будет.",
            reply_markup=confirm_forget(message.from_user.id),
        )


@router.callback_query(F.data.startswith("forget:"))
async def confirm_forget_callback(
    callback: CallbackQuery, db_session: AsyncSession | None, db_user: User | None
) -> None:
    parts = (callback.data or "").split(":")
    if len(parts) != 3 or callback.from_user.id != int(parts[2]):
        await callback.answer("Это не твоя кнопка, шпион.", show_alert=True)
        return
    if parts[1] == "no":
        if isinstance(callback.message, Message):
            await callback.message.edit_text("Отмена. Воспоминания остаются при мне.")
        await callback.answer()
        return
    if db_session is None or db_user is None:
        await callback.answer("База недоступна, удаление не выполнено.", show_alert=True)
        return
    await MemoryRepository(db_session).delete_user_data(db_user.id)
    if isinstance(callback.message, Message):
        await callback.message.edit_text("Готово. Начинаем знакомство с чистого листа 🧹")
    await callback.answer()


@router.message(Command("birthday"))
async def birthday(
    message: Message,
    command: CommandObject,
    db_session: AsyncSession | None,
    db_user: User | None,
    db_chat: Chat | None,
) -> None:
    if db_session is None or db_user is None or db_chat is None:
        await message.answer("Не могу сохранить дату: база недоступна.")
        return
    if not command.args:
        await message.answer("Формат: <code>/birthday ДД.ММ.ГГГГ</code>")
        return
    try:
        parsed = datetime.strptime(command.args.strip(), "%d.%m.%Y").date()
        if parsed >= date.today():
            raise ValueError
    except ValueError:
        await message.answer(
            "Дата выглядит подозрительно. Нужен формат ДД.ММ.ГГГГ и дата из прошлого."
        )
        return
    row = await db_session.scalar(
        select(Birthday).where(Birthday.user_id == db_user.id, Birthday.chat_id == db_chat.id)
    )
    if row:
        row.birth_date = parsed
    else:
        db_session.add(Birthday(user_id=db_user.id, chat_id=db_chat.id, birth_date=parsed))
    await message.answer("Запомнил. Торт не обещаю, но шума устроим 🎂")


@router.message(Command("settings"))
async def user_settings(message: Message) -> None:
    await message.answer(
        "Личные настройки: язык — русский; память — включена. "
        "/forget_me удаляет память. Админам доступно /admin."
    )
