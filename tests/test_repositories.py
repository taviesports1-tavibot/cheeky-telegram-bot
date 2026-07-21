from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Chat, ConversationMessage, UserMemory
from app.database.repositories import MediaRepository, MemoryRepository, UserRepository


async def test_user_repository_upserts(session: AsyncSession) -> None:
    repo = UserRepository(session)
    first = await repo.upsert(100, "anton", "Anton")
    second = await repo.upsert(100, "anton2", "Anton B")
    assert first.id == second.id
    assert second.username == "anton2"


async def test_media_add_and_random(session: AsyncSession) -> None:
    chat = Chat(telegram_id=-100, title="Test", chat_type="group")
    session.add(chat)
    await session.flush()
    repo = MediaRepository(session)
    item = await repo.add(
        chat_id=chat.id, category="memes", media_type="photo", telegram_file_id="abc", safe=True
    )
    selected = await repo.random("memes", chat.id)
    assert selected and selected.id == item.id


async def test_delete_memory_and_conversation(session: AsyncSession) -> None:
    user = await UserRepository(session).upsert(101, None, "User")
    chat = Chat(telegram_id=-101, title="Test", chat_type="group")
    session.add(chat)
    await session.flush()
    await MemoryRepository(session).add(user.id, "Любит кофе")
    session.add(ConversationMessage(chat_id=chat.id, user_id=user.id, role="user", content="hello"))
    await session.flush()
    await MemoryRepository(session).delete_user_data(user.id)
    assert not list(
        (await session.scalars(select(UserMemory).where(UserMemory.user_id == user.id))).all()
    )
    assert not list(
        (
            await session.scalars(
                select(ConversationMessage).where(ConversationMessage.user_id == user.id)
            )
        ).all()
    )
