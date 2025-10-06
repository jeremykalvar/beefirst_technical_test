import pytest

from app.infrastructure.http import client as http_client_mod


@pytest.fixture(autouse=True)
async def reset_http_client():
    """
    Ensure each test starts with a clean module-level client
    and leaves it clean afterwards.
    """
    # hard reset before
    if getattr(http_client_mod, "_client", None) is not None:
        await http_client_mod.close_http_client()
    http_client_mod._client = None

    yield

    # hard reset after
    if getattr(http_client_mod, "_client", None) is not None:
        await http_client_mod.close_http_client()
    http_client_mod._client = None


@pytest.mark.asyncio
async def test_get_before_open_raises():
    with pytest.raises(RuntimeError):
        _ = http_client_mod.get_http_client()


@pytest.mark.asyncio
async def test_open_returns_singleton_and_has_default_timeout():
    c1 = await http_client_mod.open_http_client()
    assert c1 is not None
    assert not c1.is_closed

    # Singleton behavior
    c2 = await http_client_mod.open_http_client()
    assert c1 is c2

    # Default timeout should be 10.0 across the board
    t = c1.timeout
    assert float(t.connect) == pytest.approx(10.0)
    assert float(t.read) == pytest.approx(10.0)
    assert float(t.write) == pytest.approx(10.0)
    assert float(t.pool) == pytest.approx(10.0)


@pytest.mark.asyncio
async def test_close_http_client_is_idempotent_and_drops_singleton():
    # open once
    c1 = await http_client_mod.open_http_client()
    assert not c1.is_closed

    # close once
    await http_client_mod.close_http_client()
    assert c1.is_closed
    assert http_client_mod._client is None

    # close again (idempotent, should not raise)
    await http_client_mod.close_http_client()
    assert http_client_mod._client is None


@pytest.mark.asyncio
async def test_reopen_creates_new_instance():
    c1 = await http_client_mod.open_http_client()
    await http_client_mod.close_http_client()

    c2 = await http_client_mod.open_http_client()
    assert c2 is not c1
    assert not c2.is_closed
