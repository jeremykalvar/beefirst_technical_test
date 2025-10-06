from __future__ import annotations

import secrets
from typing import Optional
from redis.asyncio import Redis


class RedisSessions:
    def __init__(
        self, redis: Redis, *, key_prefix: str = "sess:", ttl_seconds: int = 86400
    ) -> None:
        self._redis = redis
        self._prefix = key_prefix
        self._ttl = ttl_seconds

    def _key(self, token: str) -> str:
        return f"{self._prefix}{token}"

    async def create(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        await self._redis.set(self._key(token), user_id, ex=self._ttl)
        return token

    async def get(self, token: str) -> Optional[str]:
        return await self._redis.get(self._key(token))

    async def revoke(self, token: str) -> None:
        await self._redis.delete(self._key(token))
