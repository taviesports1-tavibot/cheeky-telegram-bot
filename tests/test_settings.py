import pytest

from app.config import Settings


def test_superadmin_ids_are_parsed() -> None:
    settings = Settings(superadmin_ids="123, 456")
    assert settings.superadmin_ids == frozenset({123, 456})


def test_invalid_telegram_id_is_rejected() -> None:
    with pytest.raises(ValueError):
        Settings(superadmin_ids="-1")


def test_postgres_url_is_normalized() -> None:
    settings = Settings(database_url="postgresql://user:pass@host/db")
    assert settings.database_url.startswith("postgresql+asyncpg://")
