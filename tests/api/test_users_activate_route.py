import pytest

from tests.api.conftest import basic_auth


@pytest.mark.asyncio
def test_activate_route_happy_path(client, app_and_deps):
    _, uow, _ = app_and_deps
    uow.db_users.password_hash_by_email["jeremy@example.com"] = "hashed-s3cret"

    response = client.post(
        "/v1/users/activate",
        json={"code": "1234"},
        headers=basic_auth("jeremy@example.com", "s3cret"),
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert uow.db_users.set_active_calls == ["u1"]
    assert uow.committed is True
