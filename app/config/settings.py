from collections.abc import Iterable
from functools import lru_cache
from typing import Literal, cast

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: SecretStr = SecretStr("")
    bot_username: str = ""
    superadmin_ids: frozenset[int] = Field(default_factory=frozenset)
    database_url: str = "sqlite+aiosqlite:///./cheeky_bot.db"
    redis_url: str = ""
    ai_provider: Literal["openai", "openrouter", "compatible", "ollama"] = "openai"
    ai_api_key: SecretStr = SecretStr("")
    ai_base_url: str = ""
    ai_model: str = "gpt-4.1-mini"
    ai_temperature: float = Field(0.85, ge=0, le=2)
    ai_max_tokens: int = Field(500, ge=32, le=4096)
    ai_timeout_seconds: float = Field(30, ge=1, le=120)
    ai_context_token_limit: int = Field(6000, ge=500, le=100_000)
    default_timezone: str = "Europe/Berlin"
    bot_mode: Literal["polling", "webhook"] = "polling"
    webhook_url: str = ""
    webhook_secret: SecretStr = SecretStr("")
    port: int = Field(8080, ge=1, le=65535)
    log_level: str = "INFO"
    tts_provider: Literal["edge", "elevenlabs"] = "edge"
    tts_voice: str = "ru-RU-DmitryNeural"
    default_rudeness_level: int = Field(3, ge=1, le=4)
    default_swearing_enabled: bool = True
    default_random_reply_chance: int = Field(5, ge=0, le=100)
    default_voice_reply_chance: int = Field(10, ge=0, le=100)
    default_reaction_chance: int = Field(15, ge=0, le=100)
    user_cooldown_seconds: int = Field(8, ge=0, le=3600)
    chat_cooldown_seconds: int = Field(3, ge=0, le=3600)
    rate_limit_per_minute: int = Field(12, ge=1, le=1000)
    max_media_size_mb: int = Field(10, ge=1, le=50)

    @field_validator("superadmin_ids", mode="before")
    @classmethod
    def parse_ids(cls, value: object) -> frozenset[int]:
        if value in (None, ""):
            return frozenset()
        if isinstance(value, str):
            try:
                ids = frozenset(int(item.strip()) for item in value.split(",") if item.strip())
            except ValueError as exc:
                raise ValueError(
                    "SUPERADMIN_IDS должен содержать Telegram ID через запятую"
                ) from exc
            if any(item <= 0 for item in ids):
                raise ValueError("Telegram ID должен быть положительным")
            return ids
        return frozenset(int(item) for item in cast(Iterable[int | str], value))

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+asyncpg://", 1)
        if value.startswith("postgresql://") and "+asyncpg" not in value:
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value

    @property
    def webhook_path(self) -> str:
        return "/telegram/webhook"


@lru_cache
def get_settings() -> Settings:
    return Settings()
