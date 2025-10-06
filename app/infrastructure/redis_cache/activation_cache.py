from __future__ import annotations

import base64
import hashlib

from redis.asyncio import Redis

from app.domain.ports.activation_cache import ActivationCachePort


_LUA_CONSUME = """
-- KEYS[1]: activation key
-- ARGV[1]: expected digest (base64)
local key = KEYS[1]
local expected = ARGV[1]
local cur = redis.call('HGET', key, 'digest')
if not cur then
  return 0
end
if cur ~= expected then
  return 0
end
redis.call('DEL', key)
return 1
"""


def _digest_b64(code: str, salt_b64: str) -> str:
    """
    Must match app.domain.services: digest = SHA256(salt || code).
    """
    salt = base64.b64decode(salt_b64.encode("utf-8"))
    h = hashlib.sha256()
    h.update(salt)
    h.update(code.encode("utf-8"))
    return base64.b64encode(h.digest()).decode("utf-8")


class RedisActivationCache(ActivationCachePort):
    def __init__(self, redis: Redis, *, key_prefix: str = "act:") -> None:
        self._redis = redis
        self._prefix = key_prefix

    def _key(self, user_id: str) -> str:
        return f"{self._prefix}{user_id}"

    async def store_hashed_code(
        self, user_id: str, salt_b64: str, digest_b64: str, ttl_seconds: int
    ) -> None:
        key = self._key(user_id)
        pipe = self._redis.pipeline(transaction=True)
        pipe.hset(key, mapping={"salt": salt_b64, "digest": digest_b64})
        pipe.expire(key, ttl_seconds)
        await pipe.execute()

    async def verify_and_consume(self, user_id: str, code: str) -> bool:
        key = self._key(user_id)
        # read salt (to compute expected digest)
        stored = await self._redis.hgetall(key)
        if not stored or "salt" not in stored or "digest" not in stored:
            return False
        expected = _digest_b64(code, stored["salt"])
        # atomic compare-and-delete
        res = await self._redis.eval(_LUA_CONSUME, 1, key, expected)
        return int(res) == 1

    async def invalidate(self, user_id: str) -> None:
        await self._redis.delete(self._key(user_id))
