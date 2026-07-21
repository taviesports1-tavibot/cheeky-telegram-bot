from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters import is_admin
from app.config import Settings
from app.database.models import Chat, ScheduledPost, User
from app.services.scheduler import SchedulerService
from app.utils.html import safe

router = Router(name="schedule")


@router.message(Command("schedule"))
async def schedule_command(
    message: Message,
    command: CommandObject,
    bot: Bot,
    settings: Settings,
    db_session: AsyncSession | None,
    db_chat: Chat | None,
    db_user: User | None,
    scheduler: SchedulerService,
) -> None:
    user_id = message.from_user.id if message.from_user else 0
    if not await is_admin(bot, message.chat.id, user_id, settings.superadmin_ids):
        return
    if not db_session or not db_chat:
        await message.answer("База недоступна — расписание не изменить.")
        return
    args = (command.args or "").strip()
    if not args:
        rows = list(
            (
                await db_session.scalars(
                    select(ScheduledPost)
                    .where(ScheduledPost.chat_id == db_chat.id, ScheduledPost.enabled.is_(True))
                    .order_by(ScheduledPost.next_run_at)
                )
            ).all()
        )
        listing = "\n".join(
            f"#{row.id} — {row.next_run_at:%d.%m.%Y %H:%M} "
            f"({row.cron or 'один раз'}): {safe((row.text or '')[:50])}"
            for row in rows
        )
        await message.answer(
            "<b>Расписание</b>\n"
            + (listing or "Пусто.")
            + "\n\nСоздать: <code>/schedule 25.07.2026 09:00 | once | Доброе утро!</code>\n"
            "Повтор: <code>daily</code> или <code>weekly</code>. Удалить: /schedule_delete ID"
        )
        return
    try:
        date_part, repeat, text = (part.strip() for part in args.split("|", 2))
        if repeat not in {"once", "daily", "weekly"} or not text:
            raise ValueError
        local_time = datetime.strptime(date_part, "%d.%m.%Y %H:%M").replace(
            tzinfo=ZoneInfo(settings.default_timezone)
        )
        if local_time <= datetime.now(ZoneInfo(settings.default_timezone)):
            raise ValueError
    except (ValueError, KeyError):
        await message.answer(
            "Формат: <code>/schedule ДД.ММ.ГГГГ ЧЧ:ММ | once|daily|weekly | текст</code>"
        )
        return
    post = ScheduledPost(
        chat_id=db_chat.id,
        created_by_id=db_user.id if db_user else None,
        text=text[:4000],
        next_run_at=local_time,
        timezone=settings.default_timezone,
        cron=None if repeat == "once" else repeat,
    )
    db_session.add(post)
    await db_session.flush()
    scheduler.register(post)
    await message.answer(f"Запланировано. ID: <code>{post.id}</code>.")


@router.message(Command("schedule_delete"))
async def schedule_delete(
    message: Message,
    command: CommandObject,
    bot: Bot,
    settings: Settings,
    db_session: AsyncSession | None,
    db_chat: Chat | None,
    scheduler: SchedulerService,
) -> None:
    user_id = message.from_user.id if message.from_user else 0
    if (
        not await is_admin(bot, message.chat.id, user_id, settings.superadmin_ids)
        or not db_session
        or not db_chat
    ):
        return
    try:
        post_id = int(command.args or "")
    except ValueError:
        await message.answer("Формат: <code>/schedule_delete ID</code>")
        return
    post = await db_session.get(ScheduledPost, post_id)
    if post is None or post.chat_id != db_chat.id:
        await message.answer("Такой публикации в этом чате нет.")
        return
    post.enabled = False
    scheduler.remove(post_id)
    await message.answer("Публикация удалена из расписания.")
