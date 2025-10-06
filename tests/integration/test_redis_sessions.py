import asyncio
import pytest

from app.infrastructure.redis_cache.sessions import RedisSessions


async def _flush_prefix(redis, prefix: str) -> None:
    keys = await redis.keys(f"{prefix}*")
    if keys:
        await redis.delete(*keys)


@pytest.mark.asyncio
async def test_create_get_revoke_session(redis_client):
    r = redis_client
    prefix = "sess:test:cgr:"
    await _flush_prefix(r, prefix)

    sessions = RedisSessions(r, key_prefix=prefix, ttl_seconds=30)

    token = await sessions.create("user-123")
    assert token and isinstance(token, str)

    user_id = await sessions.get(token)
    assert user_id == "user-123"

    await sessions.revoke(token)
    assert await sessions.get(token) is None


@pytest.mark.asyncio
async def test_session_expires_by_ttl(redis_client):
    r = redis_client
    prefix = "sess:test:exp:"
    await _flush_prefix(r, prefix)

    sessions = RedisSessions(r, key_prefix=prefix, ttl_seconds=1)

    token = await sessions.create("user-xyz")
    ttl = await r.ttl(f"{prefix}{token}")
    assert ttl in (1, 2)

    await asyncio.sleep(1.5)

    assert await sessions.get(token) is None
    ttl_after = await r.ttl(f"{prefix}{token}")
    assert ttl_after == -2  # key missing


@pytest.mark.asyncio
async def test_tokens_are_random_and_unique(redis_client):
    r = redis_client
    prefix = "sess:test:uniq:"
    await _flush_prefix(r, prefix)

    sessions = RedisSessions(r, key_prefix=prefix, ttl_seconds=10)

    tokens = {await sessions.create("user-1") for _ in range(8)}
    assert len(tokens) == 8

    resolved = [await sessions.get(t) for t in tokens]
    assert all(uid == "user-1" for uid in resolved)
