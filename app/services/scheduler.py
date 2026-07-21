from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import structlog
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from app.database import Database
from app.database.models import Birthday, Chat, ScheduledPost, User

log = structlog.get_logger()


class SchedulerService:
    def __init__(self, bot: Bot, database: Database, timezone: str) -> None:
        self.bot = bot
        self.database = database
        self.scheduler = AsyncIOScheduler(timezone=timezone)
        self.timezone = timezone

    async def start(self) -> None:
        self.scheduler.start()
        if not await self.database.health():
            log.warning("scheduler_started_without_database")
            return
        async with self.database.session() as session:
            posts = list(
                (
                    await session.scalars(
                        select(ScheduledPost).where(ScheduledPost.enabled.is_(True))
                    )
                ).all()
            )
        for post in posts:
            self.register(post)
        self.scheduler.add_job(
            self.send_birthday_greetings,
            CronTrigger(hour=10, minute=0, timezone=ZoneInfo(self.timezone)),
            id="system:birthdays",
            replace_existing=True,
        )
        log.info("scheduler_started", jobs=len(posts))

    def register(self, post: ScheduledPost) -> None:
        run_at = post.next_run_at
        if run_at.tzinfo is None:
            run_at = run_at.replace(tzinfo=UTC)
        if post.cron in {"daily", "weekly"}:
            trigger = IntervalTrigger(
                days=1 if post.cron == "daily" else 7,
                start_date=run_at,
                timezone=ZoneInfo(post.timezone),
            )
        else:
            trigger = DateTrigger(run_date=max(run_at, datetime.now(UTC) + timedelta(seconds=1)))
        self.scheduler.add_job(
            self.publish,
            trigger=trigger,
            args=[post.id],
            id=f"post:{post.id}",
            replace_existing=True,
            misfire_grace_time=3600,
        )

    async def publish(self, post_id: int) -> None:
        try:
            async with self.database.session() as session:
                post = await session.get(ScheduledPost, post_id)
                if post is None or not post.enabled:
                    return
                chat = await session.get(Chat, post.chat_id)
                if chat is None:
                    return
                await self.bot.send_message(
                    chat.telegram_id, post.text or "😈 Запланированный привет из будущего."
                )
                if post.cron not in {"daily", "weekly"}:
                    post.enabled = False
            log.info("scheduled_post_sent", post_id=post_id)
        except Exception as exc:
            log.error("scheduled_post_failed", post_id=post_id, error=type(exc).__name__)

    async def send_birthday_greetings(self) -> None:
        today = datetime.now(ZoneInfo(self.timezone)).date()
        try:
            async with self.database.session() as session:
                rows = (
                    await session.execute(
                        select(Birthday, User, Chat)
                        .join(User, Birthday.user_id == User.id)
                        .join(Chat, Birthday.chat_id == Chat.id)
                        .where(Chat.active.is_(True))
                    )
                ).all()
            for birthday, user, chat in rows:
                if (birthday.birth_date.month, birthday.birth_date.day) != (
                    today.month,
                    today.day,
                ):
                    continue
                await self.bot.send_message(
                    chat.telegram_id,
                    f"🎂 Сегодня день рождения у {user.display_name}! "
                    "Поздравляем, легенда. Пусть проблемы стареют быстрее тебя 😈",
                )
        except Exception as exc:
            log.error("birthday_job_failed", error=type(exc).__name__)

    def remove(self, post_id: int) -> None:
        job = self.scheduler.get_job(f"post:{post_id}")
        if job:
            job.remove()

    async def close(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
