import pytest

from app.application.register_user import register_user


@pytest.mark.asyncio
async def test_register_user_happy_path(uow, cache, hash_password_stub):
    await register_user(
        uow=uow,
        activation_cache=cache,
        email=" Jeremy@Example.COM ",
        password="s3cret",
        hash_password=hash_password_stub,
        code_ttl_seconds=60,
    )

    assert uow.db_users.created_email == "jeremy@example.com"
    assert uow.db_users.created_hash == "hashed-s3cret"

    assert len(cache.calls) == 1
    user_id, salt_b64, digest_b64, ttl = cache.calls[0]
    assert (
        user_id == "u1"
        and isinstance(salt_b64, str)
        and isinstance(digest_b64, str)
        and ttl == 60
    )

    assert len(uow.outbox.enqueues) == 1
    topic, payload, idem = uow.outbox.enqueues[0]
    assert topic == "user.verification_code"
    assert payload["to"] == "jeremy@example.com"
    assert "1234" in payload["body"]

    assert (
        uow.db_users.set_last_code_calls
        and uow.db_users.set_last_code_calls[0][0] == "u1"
    )
    assert uow.committed is True


@pytest.mark.asyncio
async def test_register_user_error_in_activation_cache(
    uow, errored_cache, hash_password_stub
):
    with pytest.raises(RuntimeError, match="Redis down"):
        await register_user(
            uow=uow,
            activation_cache=errored_cache,
            email=" Jeremy@Example.COM ",
            password="s3cret",
            hash_password=hash_password_stub,
            code_ttl_seconds=60,
        )

    assert len(uow.outbox.enqueues) == 0
    assert uow.committed is False
    assert uow.rolled_back is True
