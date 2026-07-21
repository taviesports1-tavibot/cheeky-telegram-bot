from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64))
    display_name: Mapped[str] = mapped_column(String(255))
    preferred_name: Mapped[str | None] = mapped_column(String(100))
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    message_count: Mapped[int] = mapped_column(default=0)
    relationship_level: Mapped[int] = mapped_column(default=0)
    language: Mapped[str] = mapped_column(String(8), default="ru")
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    memories: Mapped[list[UserMemory]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Chat(TimestampMixin, Base):
    __tablename__ = "chats"
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    title: Mapped[str | None] = mapped_column(String(255))
    chat_type: Mapped[str] = mapped_column(String(32), default="group")
    active: Mapped[bool] = mapped_column(default=True)
    settings_row: Mapped[ChatSettings | None] = relationship(
        back_populates="chat", uselist=False, cascade="all, delete-orphan"
    )


class ChatSettings(TimestampMixin, Base):
    __tablename__ = "chat_settings"
    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"), unique=True)
    rudeness_level: Mapped[int] = mapped_column(default=3)
    swearing_enabled: Mapped[bool] = mapped_column(default=True)
    random_reply_chance: Mapped[int] = mapped_column(default=5)
    voice_reply_chance: Mapped[int] = mapped_column(default=10)
    reaction_enabled: Mapped[bool] = mapped_column(default=True)
    reaction_chance: Mapped[int] = mapped_column(default=15)
    reaction_emojis: Mapped[list[str]] = mapped_column(
        JSON, default=lambda: ["😂", "🔥", "🤡", "❤️", "🤔", "👏", "😁", "😈"]
    )
    exclude_admin_reactions: Mapped[bool] = mapped_column(default=True)
    tts_voice: Mapped[str] = mapped_column(String(100), default="ru-RU-DmitryNeural")
    rules_text: Mapped[str | None] = mapped_column(Text)
    rules_url: Mapped[str | None] = mapped_column(String(500))
    welcome_media_id: Mapped[int | None] = mapped_column(
        ForeignKey("media_items.id", ondelete="SET NULL")
    )
    welcome_voice_chance: Mapped[int] = mapped_column(default=10)
    welcome_delay_seconds: Mapped[int] = mapped_column(default=1)
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Berlin")
    quiet_minutes: Mapped[int] = mapped_column(default=180)
    custom: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    chat: Mapped[Chat] = relationship(back_populates="settings_row")


class UserMemory(TimestampMixin, Base):
    __tablename__ = "user_memories"
    __table_args__ = (Index("ix_user_memory_user_kind", "user_id", "kind"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(32), default="fact")
    content: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    user: Mapped[User] = relationship(back_populates="memories")


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"
    __table_args__ = (Index("ix_conversation_chat_created", "chat_id", "created_at"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    telegram_message_id: Mapped[int | None] = mapped_column(BigInteger)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MediaItem(TimestampMixin, Base):
    __tablename__ = "media_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int | None] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"), index=True
    )
    category: Mapped[str] = mapped_column(String(32), index=True)
    media_type: Mapped[str] = mapped_column(String(16))
    telegram_file_id: Mapped[str | None] = mapped_column(String(512))
    local_path: Mapped[str | None] = mapped_column(String(500))
    source_url: Mapped[str | None] = mapped_column(String(1000))
    mime_type: Mapped[str | None] = mapped_column(String(100))
    file_size: Mapped[int | None] = mapped_column(BigInteger)
    safe: Mapped[bool] = mapped_column(default=True, index=True)
    added_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    use_count: Mapped[int] = mapped_column(default=0)


class ScheduledPost(TimestampMixin, Base):
    __tablename__ = "scheduled_posts"
    __table_args__ = (Index("ix_schedule_due", "enabled", "next_run_at"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"))
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    kind: Mapped[str] = mapped_column(String(32), default="custom")
    text: Mapped[str | None] = mapped_column(Text)
    media_id: Mapped[int | None] = mapped_column(ForeignKey("media_items.id", ondelete="SET NULL"))
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Berlin")
    cron: Mapped[str | None] = mapped_column(String(100))
    enabled: Mapped[bool] = mapped_column(default=True)


class BotAction(Base):
    __tablename__ = "bot_actions"
    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int | None] = mapped_column(
        ForeignKey("chats.id", ondelete="SET NULL"), index=True
    )
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(64), index=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    duration_ms: Mapped[int | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class CommandUsage(Base):
    __tablename__ = "command_usage"
    id: Mapped[int] = mapped_column(primary_key=True)
    command: Mapped[str] = mapped_column(String(64), index=True)
    chat_id: Mapped[int | None] = mapped_column(ForeignKey("chats.id", ondelete="SET NULL"))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class Warning(TimestampMixin, Base):
    __tablename__ = "warnings"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"))
    reason: Mapped[str] = mapped_column(Text)
    issued_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class UserBotBan(TimestampMixin, Base):
    __tablename__ = "user_bot_bans"
    __table_args__ = (UniqueConstraint("chat_id", "user_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"))
    reason: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Birthday(TimestampMixin, Base):
    __tablename__ = "birthdays"
    __table_args__ = (UniqueConstraint("chat_id", "user_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"))
    birth_date: Mapped[date] = mapped_column(Date)


class ApiUsage(Base):
    __tablename__ = "api_usage"
    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int | None] = mapped_column(
        ForeignKey("chats.id", ondelete="SET NULL"), index=True
    )
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    provider: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(100))
    prompt_tokens: Mapped[int] = mapped_column(default=0)
    completion_tokens: Mapped[int] = mapped_column(default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
