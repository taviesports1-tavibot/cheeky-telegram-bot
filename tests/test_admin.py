from unittest.mock import AsyncMock, Mock

from app.bot.filters.admin import is_admin


async def test_superadmin_does_not_call_telegram() -> None:
    bot = Mock()
    bot.get_chat_member = AsyncMock()
    assert await is_admin(bot, -100, 42, frozenset({42}))
    bot.get_chat_member.assert_not_called()


async def test_group_admin_is_allowed() -> None:
    bot = Mock()
    bot.get_chat_member = AsyncMock(return_value=Mock(status="administrator"))
    assert await is_admin(bot, -100, 7, frozenset())
