from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

from app.database.models import ScheduledPost
from app.services.scheduler import SchedulerService


async def test_scheduler_registers_post() -> None:
    bot = Mock()
    database = Mock()
    service = SchedulerService(bot, database, "Europe/Berlin")
    service.scheduler.start(paused=True)
    post = ScheduledPost(
        id=77,
        chat_id=1,
        text="test",
        next_run_at=datetime.now(UTC) + timedelta(hours=1),
        timezone="Europe/Berlin",
        enabled=True,
    )
    service.register(post)
    assert service.scheduler.get_job("post:77") is not None
    service.scheduler.shutdown(wait=False)
