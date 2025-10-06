import base64

import pytest
from fastapi.testclient import TestClient

from app.domain.entities import User
from app.main import create_app
from app.presentation.dependencies import (
    get_activation_cache,
    get_code_ttl_seconds,
    get_hash_password,
    get_sessions,
    get_uow,
    get_verify_password,
)
from tests.fakes import (
    FakeActivationCache,
    FakeAuthUsersRepo,
    FakeSessions,
    FakeUoW,
    FakeUoWAuth,
)


@pytest.fixture()
def app_and_deps():
    app = create_app()
    uow = FakeUoW()
    cache = FakeActivationCache(verify_result=True)

    def _get_uow():
        return uow

    def _get_cache():
        return cache

    def _get_verify():
        return lambda plain, hashed: (plain == "s3cret" and hashed == "hashed-s3cret")

    def _get_hash_password():
        return lambda plain: "hashed-" + plain

    def _get_code_ttl_seconds():
        return 60

    app.dependency_overrides[get_uow] = _get_uow
    app.dependency_overrides[get_activation_cache] = _get_cache
    app.dependency_overrides[get_verify_password] = _get_verify
    app.dependency_overrides[get_hash_password] = _get_hash_password
    app.dependency_overrides[get_code_ttl_seconds] = _get_code_ttl_seconds

    try:
        yield app, uow, cache
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def client(app_and_deps):
    app, _, _ = app_and_deps
    return TestClient(app, raise_server_exceptions=False)


def basic_auth(email: str, password: str) -> dict[str, str]:
    token = base64.b64encode(f"{email}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


@pytest.fixture
def active_user() -> User:
    return User(id="auth-1", email="login@test.local", status="active")


@pytest.fixture
def auth_overrides(client: TestClient, active_user: User):
    """
    Temporarily override deps for login/me route tests:
      - use a seeded UoW with an active user
      - accept password == 's3cret' for the test user
      - use in-memory sessions
    """
    app = client.app
    original = dict(app.dependency_overrides)

    repo = FakeAuthUsersRepo(
        by_email={active_user.email: (active_user, "irrelevant-hash")},
        by_id={active_user.id: active_user},
    )
    sessions = FakeSessions()

    app.dependency_overrides[get_uow] = lambda: FakeUoWAuth(repo)
    app.dependency_overrides[get_verify_password] = lambda: (
        lambda plain, _hash: plain == "s3cret"
    )
    app.dependency_overrides[get_sessions] = lambda: sessions

    try:
        yield {"sessions": sessions}
    finally:
        app.dependency_overrides = original
