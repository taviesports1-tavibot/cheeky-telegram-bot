from app.services.cache import CacheService


async def test_rate_limit_memory_fallback() -> None:
    cache = CacheService("")
    assert await cache.allowed("x", 2, 60)
    assert await cache.allowed("x", 2, 60)
    assert not await cache.allowed("x", 2, 60)


async def test_cooldown_memory_fallback() -> None:
    cache = CacheService("")
    assert await cache.acquire_once("cooldown", 30)
    assert not await cache.acquire_once("cooldown", 30)
