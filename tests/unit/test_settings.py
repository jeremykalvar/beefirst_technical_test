from app.settings import get_settings


def test_get_settings_is_cached():
    get_settings.cache_clear()
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2  # lru_cache returns the same instance


def test_env_overrides_and_cache_clear(monkeypatch):
    # override via env and ensure cache is respected
    monkeypatch.setenv("CODE_TTL_SECONDS", "123")
    get_settings.cache_clear()
    s = get_settings()
    assert s.code_ttl_seconds == 123

    # cleanup: remove env and reset cache
    monkeypatch.delenv("CODE_TTL_SECONDS", raising=False)
    get_settings.cache_clear()
    s2 = get_settings()
    assert s2.code_ttl_seconds != 123  # back to default or another env value
