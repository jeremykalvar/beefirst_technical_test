from __future__ import annotations

import asyncio
import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import basic_auth
from tests.fakes import FakeSessions


def test_login_and_me_happy_path(client: TestClient, auth_overrides, active_user):
    email, password = active_user.email, "s3cret"

    r = client.post("/v1/users/login", headers=basic_auth(email, password))
    assert r.status_code == 200, r.text
    token = r.json()["token"]
    assert token.startswith("tok-")

    r2 = client.get("/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200, r2.text
    body = r2.json()
    assert body["id"] == active_user.id
    assert body["email"] == active_user.email
    assert body["status"] == "active"


def test_login_invalid_credentials(client: TestClient, auth_overrides, active_user):
    r = client.post("/v1/users/login", headers=basic_auth(active_user.email, "wrong"))
    assert r.status_code == 401
    assert r.json()["detail"] == "invalid credentials"


def test_me_missing_authorization_header(client: TestClient, auth_overrides):
    r = client.get("/v1/users/me")
    # HTTPBearer returns 403 when no auth header is provided
    assert r.status_code == 403
    assert r.json()["detail"] == "Not authenticated"


def test_me_invalid_token(client: TestClient, auth_overrides):
    r = client.get("/v1/users/me", headers={"Authorization": "Bearer nope"})
    assert r.status_code == 401
    assert r.json()["detail"] == "invalid or expired token"


def test_me_expired_token_after_login(
    client: TestClient, auth_overrides, active_user, request
):
    sessions: FakeSessions = auth_overrides["sessions"]  # provided by fixture
    r = client.post("/v1/users/login", headers=basic_auth(active_user.email, "s3cret"))
    token = r.json()["token"]

    # simulate expiration/revocation
    asyncio.get_event_loop().run_until_complete(sessions.revoke(token))

    r2 = client.get("/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 401
    assert r2.json()["detail"] == "invalid or expired token"
