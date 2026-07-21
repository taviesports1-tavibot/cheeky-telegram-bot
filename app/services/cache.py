from __future__ import annotations

import asyncio
import time
from collections import defaultdict

import redis.asyncio as redis
import structlog

log = structlog.get_logger()


class CacheService:
    """Redis cache with an in-process fallback for local/degraded operation."""

    def __init__(self, url: str) -> None:
        self.client: redis.Redis | None = (
            redis.from_url(url, decode_responses=True)  # type: ignore[no-untyped-call]
            if url
            else None
        )
        self._values: dict[str, tuple[str, float]] = {}
        self._counters: defaultdict[str, tuple[int, float]] = defaultdict(lambda: (0, 0.0))
        self._locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def connect(self) -> bool:
        if self.client is None:
            return False
        try:
            await self.client.ping()
            log.info("redis_connected")
            return True
        except Exception as exc:
            log.warning("redis_unavailable_using_memory", error=type(exc).__name__)
            await self.client.aclose()
            self.client = None
            return False

    async def set(self, key: str, value: str, ttl: int) -> None:
        if self.client:
            await self.client.set(key, value, ex=ttl)
            return
        self._values[key] = (value, time.monotonic() + ttl)

    async def get(self, key: str) -> str | None:
        if self.client:
            value = await self.client.get(key)
            return str(value) if value is not None else None
        item = self._values.get(key)
        if item is None or item[1] < time.monotonic():
            self._values.pop(key, None)
            return None
        return item[0]

    async def allowed(self, key: str, limit: int, window: int) -> bool:
        if self.client:
            async with self.client.pipeline(transaction=True) as pipe:
                pipe.incr(key)
                pipe.expire(key, window, nx=True)
                count, _ = await pipe.execute()
            return int(count) <= limit
        count, expiry = self._counters[key]
        now = time.monotonic()
        if expiry < now:
            count, expiry = 0, now + window
        count += 1
        self._counters[key] = (count, expiry)
        return count <= limit

    async def acquire_once(self, key: str, ttl: int) -> bool:
        if self.client:
            return bool(await self.client.set(key, "1", ex=ttl, nx=True))
        async with self._locks[key]:
            if await self.get(key):
                return False
            await self.set(key, "1", ttl)
            return True

    async def close(self) -> None:
        if self.client:
            await self.client.aclose()
