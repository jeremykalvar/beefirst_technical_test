import pytest

from app.presentation.dependencies import get_activation_cache
from tests.fakes import FakeErroredActivationCache


@pytest.mark.asyncio
async def test_register_route_happy_path(client, app_and_deps):
    _, uow, cache = app_and_deps
    uow.db_users.password_hash_by_email["jeremy@example.com"] = "hashed-s3cret"

    response = client.post(
        "/v1/users",
        json={"email": "jeremy@example.com", "password": "s3cret"},
    )

    assert response.status_code == 202
    assert response.json() == {"status": "accepted"}
    assert uow.db_users.created_email == "jeremy@example.com"
    assert uow.db_users.created_hash == "hashed-s3cret"
    assert len(cache.calls) == 1
    user_id, salt_b64, digest_b64, ttl = cache.calls[0]
    assert user_id == "u1"
    assert isinstance(salt_b64, str)
    assert isinstance(digest_b64, str)
    assert ttl == 60


@pytest.mark.asyncio
async def test_register_route_error_in_activation_cache(
    client,
    app_and_deps,
):
    app, uow, cache = app_and_deps
    app.dependency_overrides[get_activation_cache] = (
        lambda: FakeErroredActivationCache()
    )

    response = client.post(
        "/v1/users",
        json={"email": "jeremy@example.com", "password": "s3cret"},
    )

    assert response.status_code == 500
    assert uow.committed is False
    assert uow.rolled_back is True
    assert len(uow.outbox.enqueues) == 0
    assert len(cache.calls) == 0
