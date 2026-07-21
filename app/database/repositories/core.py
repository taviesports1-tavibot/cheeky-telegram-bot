from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Chat, ChatSettings, ConversationMessage, MediaItem, User, UserMemory


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(self, telegram_id: int, username: str | None, display_name: str) -> User:
        user = await self.session.scalar(select(User).where(User.telegram_id == telegram_id))
        now = datetime.now(UTC)
        if user is None:
            user = User(
                telegram_id=telegram_id,
                username=username,
                display_name=display_name,
                last_active_at=now,
                message_count=1,
            )
            self.session.add(user)
            await self.session.flush()
            return user
        user.username = username
        user.display_name = display_name
        user.last_active_at = now
        user.message_count += 1
        return user

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        user: User | None = await self.session.scalar(
            select(User).where(User.telegram_id == telegram_id)
        )
        return user

    async def active_in_chat(self, chat_id: int, limit: int = 100) -> list[User]:
        stmt = (
            select(User)
            .join(ConversationMessage, ConversationMessage.user_id == User.id)
            .where(ConversationMessage.chat_id == chat_id)
            .group_by(User.id)
            .order_by(func.max(ConversationMessage.created_at).desc())
            .limit(limit)
        )
        return list((await self.session.scalars(stmt)).all())


class SettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create_chat(self, telegram_id: int, title: str | None, chat_type: str) -> Chat:
        chat = await self.session.scalar(select(Chat).where(Chat.telegram_id == telegram_id))
        if chat is None:
            chat = Chat(telegram_id=telegram_id, title=title, chat_type=chat_type)
            self.session.add(chat)
            await self.session.flush()
        else:
            chat.title = title
        return chat

    async def get_or_create_settings(
        self, chat: Chat, defaults: dict[str, object] | None = None
    ) -> ChatSettings:
        row = await self.session.scalar(select(ChatSettings).where(ChatSettings.chat_id == chat.id))
        if row is None:
            row = ChatSettings(chat_id=chat.id, **(defaults or {}))
            self.session.add(row)
            await self.session.flush()
        return row


class MemoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_user(self, user_id: int, limit: int = 30) -> list[UserMemory]:
        stmt = (
            select(UserMemory)
            .where(UserMemory.user_id == user_id)
            .order_by(UserMemory.created_at.desc())
            .limit(limit)
        )
        return list((await self.session.scalars(stmt)).all())

    async def add(self, user_id: int, content: str, kind: str = "fact") -> UserMemory:
        item = UserMemory(user_id=user_id, content=content[:1000], kind=kind)
        self.session.add(item)
        await self.session.flush()
        return item

    async def delete_user_data(self, user_id: int) -> None:
        await self.session.execute(delete(UserMemory).where(UserMemory.user_id == user_id))
        await self.session.execute(
            delete(ConversationMessage).where(ConversationMessage.user_id == user_id)
        )


class MediaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, **values: object) -> MediaItem:
        item = MediaItem(**values)
        self.session.add(item)
        await self.session.flush()
        return item

    async def random(self, category: str, chat_id: int | None = None) -> MediaItem | None:
        stmt = select(MediaItem).where(MediaItem.category == category, MediaItem.safe.is_(True))
        if chat_id is not None:
            stmt = stmt.where((MediaItem.chat_id == chat_id) | (MediaItem.chat_id.is_(None)))
        item = await self.session.scalar(stmt.order_by(func.random()).limit(1))
        if item:
            item.use_count += 1
        return item

    async def delete(self, media_id: int, chat_id: int) -> bool:
        deleted_id = await self.session.scalar(
            delete(MediaItem)
            .where(MediaItem.id == media_id, MediaItem.chat_id == chat_id)
            .returning(MediaItem.id)
        )
        return deleted_id is not None
