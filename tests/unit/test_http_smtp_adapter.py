import json
import pytest
import httpx

from app.infrastructure.email.http_smtp_adapter import HttpSmtpEmailAdapter


@pytest.mark.asyncio
async def test_send_success_no_idempotency():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["json"] = json.loads(request.content.decode("utf-8"))
        seen["idem"] = request.headers.get("Idempotency-Key")
        return httpx.Response(202, text="Accepted")

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)

    adapter = HttpSmtpEmailAdapter(
        base_url="http://smtp-mock:8025",
        client=client,
        send_path="/send",
    )

    await adapter.send(to="a@a.com", subject="Hi", body="Hello")
    assert seen["url"].endswith("/send")
    assert seen["json"] == {"to": "a@a.com", "subject": "Hi", "body": "Hello"}
    assert seen["idem"] is None

    await client.aclose()


@pytest.mark.asyncio
async def test_send_success_with_idempotency():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["idem"] = request.headers.get("Idempotency-Key")
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)

    adapter = HttpSmtpEmailAdapter(
        base_url="http://smtp-mock:8025",
        client=client,
        send_path="/send",
    )

    await adapter.send(
        to="b@a.com", subject="Hi", body="Hello", idempotency_key="abc-123"
    )
    assert seen["idem"] == "abc-123"

    await client.aclose()


@pytest.mark.asyncio
async def test_send_non_2xx_raises_runtimeerror():
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(422, text="nope")

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)

    adapter = HttpSmtpEmailAdapter(
        base_url="http://smtp-mock:8025",
        client=client,
        send_path="/send",
    )

    with pytest.raises(RuntimeError) as ei:
        await adapter.send(to="x@y.com", subject="S", body="B")

    msg = str(ei.value)
    assert "SMTP responded 422" in msg
    assert "nope" in msg

    await client.aclose()


@pytest.mark.asyncio
async def test_network_error_is_wrapped_as_runtimeerror():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)

    adapter = HttpSmtpEmailAdapter(
        base_url="http://smtp-mock:8025",
        client=client,
        send_path="/send",
    )

    with pytest.raises(RuntimeError) as ei:
        await adapter.send(to="x@y.com", subject="S", body="B")

    assert "SMTP HTTP error:" in str(ei.value)

    await client.aclose()


@pytest.mark.asyncio
async def test_aclose_closes_owned_client_only():
    owned = HttpSmtpEmailAdapter(base_url="http://smtp-mock:8025")
    await owned.aclose()
    assert owned._client.is_closed  # type: ignore[attr-defined]

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    transport = httpx.MockTransport(handler)
    shared_client = httpx.AsyncClient(transport=transport)
    not_owned = HttpSmtpEmailAdapter(
        base_url="http://smtp-mock:8025", client=shared_client
    )

    await not_owned.aclose()
    assert shared_client.is_closed is False

    await shared_client.aclose()
