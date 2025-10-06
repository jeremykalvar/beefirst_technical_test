from __future__ import annotations

from typing import Optional, Dict
import httpx

from app.domain.ports.email_port import EmailPort


class HttpSmtpEmailAdapter(EmailPort):
    def __init__(
        self,
        base_url: str,
        *,
        client: Optional[httpx.AsyncClient] = None,
        timeout: float = 5.0,
        send_path: str = "/send",
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._send_path = send_path if send_path.startswith("/") else f"/{send_path}"
        self._owns_client: bool = client is None
        self._client: httpx.AsyncClient = client or httpx.AsyncClient(timeout=timeout)

    async def send(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        idempotency_key: str | None = None,
    ) -> None:
        headers: Dict[str, str] = {}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        url = f"{self._base_url}{self._send_path}"
        payload = {"to": to, "subject": subject, "body": body}

        try:
            resp = await self._client.post(url, json=payload, headers=headers)
            if not (200 <= resp.status_code < 300):
                text = resp.text[:200]
                raise RuntimeError(f"SMTP responded {resp.status_code}: {text}")
        except httpx.HTTPError as e:
            raise RuntimeError(f"SMTP HTTP error: {e}") from e

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
