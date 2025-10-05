import pytest

from app.application.activate_user import activate_user
from app.domain.errors import InvalidActivationCode, InvalidCredentials


@pytest.mark.asyncio
async def test_activate_user_happy_path(uow, cache, hash_password_stub):
    uow.db_users.password_hash_by_email["jeremy@example.com"] = "hashed-s3cret"

    def verify_password(password: str, password_hash: str) -> bool:
        return password_hash == "hashed-s3cret" and password == "s3cret"

    await activate_user(
        uow=uow,
        activation_cache=cache,
        email=" Jeremy@Example.COM ",
        password="s3cret",
        code="1234",
        verify_password=verify_password,
    )

    assert uow.db_users.set_active_calls == ["u1"]
    assert uow.committed is True
    assert uow.rolled_back is False


@pytest.mark.asyncio
async def test_activate_user_invalid_credentials(uow, cache):
    uow.db_users.password_hash_by_email["jeremy@example.com"] = "hashed-s3cret"

    with pytest.raises(InvalidCredentials):
        await activate_user(
            uow=uow,
            activation_cache=cache,
            email="jeremy@example.com",
            password="s3cret",
            code="1234",
            verify_password=lambda password, password_hash: False,
        )

    assert uow.db_users.set_active_calls == []
    assert uow.committed is False
    assert uow.rolled_back is True
    assert getattr(cache, "calls", []) == []


@pytest.mark.asyncio
async def test_activate_user_invalid_activation_code(uow, cache_bad):
    uow.db_users.password_hash_by_email["jeremy@example.com"] = "hashed-s3cret"

    with pytest.raises(InvalidActivationCode):
        await activate_user(
            uow=uow,
            activation_cache=cache_bad,
            email=" Jeremy@Example.COM ",
            password="s3cret",
            code="1234",
            verify_password=lambda password, password_hash: True,
        )

    assert uow.db_users.set_active_calls == []
    assert uow.committed is False
    assert uow.rolled_back is True
    assert getattr(cache_bad, "calls", []) == [("u1", "1234")]


@pytest.mark.asyncio
async def test_activate_user_no_user_found(uow, cache):

    with pytest.raises(InvalidCredentials):
        await activate_user(
            uow=uow,
            activation_cache=cache,
            email="jeremy@example.com",
            password="s3cret",
            code="1234",
            verify_password=lambda password, password_hash: False,
        )

    assert uow.db_users.set_active_calls == []
    assert uow.committed is False
    assert uow.rolled_back is True
    assert getattr(cache, "calls", []) == []
