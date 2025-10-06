import os
import asyncio
import base64
import hashlib
import secrets
from uuid import uuid4

import pytest
from redis.asyncio import Redis

from app.infrastructure.redis_cache.activation_cache import RedisActivationCache


def make_digest_b64(code: str, salt_b64: str) -> str:
    salt = base64.b64decode(salt_b64.encode("utf-8"))
    h = hashlib.sha256()
    h.update(salt)
    h.update(code.encode("utf-8"))
    return base64.b64encode(h.digest()).decode("utf-8")


def make_cache() -> tuple[RedisActivationCache, Redis]:
    url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    r = Redis.from_url(url, encoding="utf-8", decode_responses=True)
    return RedisActivationCache(r), r


@pytest.mark.asyncio
async def test_store_verify_consume_success_then_missing():
    cache, r = make_cache()
    user_id = str(uuid4())
    code = "1234"

    # prepare salt/digest
    salt_b64 = base64.b64encode(secrets.token_bytes(16)).decode()
    digest_b64 = make_digest_b64(code, salt_b64)

    await cache.store_hashed_code(user_id, salt_b64, digest_b64, ttl_seconds=60)

    # first verify succeeds and consumes the key
    ok1 = await cache.verify_and_consume(user_id, code)
    assert ok1 is True

    # second verify fails (single-use)
    ok2 = await cache.verify_and_consume(user_id, code)
    assert ok2 is False

    # key is gone
    exists = await r.exists(f"act:{user_id}")
    assert exists == 0


@pytest.mark.asyncio
async def test_wrong_code_does_not_consume():
    cache, r = make_cache()
    user_id = str(uuid4())
    good_code = "5678"
    bad_code = "9999"

    salt_b64 = base64.b64encode(secrets.token_bytes(16)).decode()
    digest_b64 = make_digest_b64(good_code, salt_b64)

    await cache.store_hashed_code(user_id, salt_b64, digest_b64, ttl_seconds=60)

    ok = await cache.verify_and_consume(user_id, bad_code)
    assert ok is False

    # key still present (not consumed on mismatch)
    h = await r.hgetall(f"act:{user_id}")
    assert h.get("digest") == digest_b64


@pytest.mark.asyncio
async def test_missing_key_returns_false():
    cache, _ = make_cache()
    ok = await cache.verify_and_consume(str(uuid4()), "1234")
    assert ok is False


@pytest.mark.asyncio
async def test_invalidate_deletes_key():
    cache, r = make_cache()
    user_id = str(uuid4())

    salt_b64 = base64.b64encode(secrets.token_bytes(16)).decode()
    digest_b64 = make_digest_b64("1234", salt_b64)

    await cache.store_hashed_code(user_id, salt_b64, digest_b64, ttl_seconds=60)
    await cache.invalidate(user_id)

    exists = await r.exists(f"act:{user_id}")
    assert exists == 0


@pytest.mark.asyncio
async def test_ttl_expiry_causes_failure():
    cache, _ = make_cache()
    user_id = str(uuid4())
    code = "0001"

    salt_b64 = base64.b64encode(secrets.token_bytes(16)).decode()
    digest_b64 = make_digest_b64(code, salt_b64)

    await cache.store_hashed_code(user_id, salt_b64, digest_b64, ttl_seconds=1)
    await asyncio.sleep(1.2)

    ok = await cache.verify_and_consume(user_id, code)
    assert ok is False


@pytest.mark.asyncio
async def test_atomic_single_use_under_race():
    cache, r = make_cache()
    user_id = str(uuid4())
    code = "4242"

    salt_b64 = base64.b64encode(secrets.token_bytes(16)).decode()
    digest_b64 = make_digest_b64(code, salt_b64)

    await cache.store_hashed_code(user_id, salt_b64, digest_b64, ttl_seconds=60)

    # Two concurrent attempts; only one should succeed.
    res1, res2 = await asyncio.gather(
        cache.verify_and_consume(user_id, code),
        cache.verify_and_consume(user_id, code),
    )
    assert sorted([res1, res2]) == [False, True]

    # key consumed
    exists = await r.exists(f"act:{user_id}")
    assert exists == 0
