import pytest

from tests.fakes import FakeActivationCache, FakeErroredActivationCache, FakeUoW


@pytest.fixture()
def uow():
    return FakeUoW()


@pytest.fixture()
def cache():
    return FakeActivationCache(verify_result=True)


@pytest.fixture()
def cache_bad():
    return FakeActivationCache(verify_result=False)


@pytest.fixture()
def errored_cache():
    return FakeErroredActivationCache()


@pytest.fixture()
def hash_password_stub():
    return lambda p: "hashed-" + p


@pytest.fixture(autouse=True)
def patch_code(monkeypatch):
    """
    Make the 4-digit code deterministic in all tests.
    You can override in a specific test by re-monkeypatching.
    """
    from app.domain import services as domain_services

    monkeypatch.setattr(domain_services, "generate_4digit_code", lambda: "1234")
    yield
