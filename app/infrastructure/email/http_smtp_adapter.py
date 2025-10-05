from __future__ import annotations

from typing import Optional, Dict

import httpx

from app.domain.ports.email_port import EmailPort


class HttpSmtpEmailAdapter(EmailPort):
    """
    Concrete EmailPort that talks to a simple SMTP-mock HTTP service.

    - POSTs JSON to /send on the SMTP mock (e.g. http://smtp-mock:8080/send).
    - Raises RuntimeError on any network error or non-2xx response.
    - Optionally attaches an Idempotency-Key header if provided.
    """

    def __init__(
        self,
        base_url: str,
        *,
        client: Optional[httpx.AsyncClient] = None,
        timeout: float = 5.0,
        send_path: str = "/send",
    ) -> None:
        self._owns_client: bool = client is None
        self._client: httpx.AsyncClient = client or httpx.AsyncClient(
            base_url=base_url, timeout=timeout
        )
        self._send_path: str = send_path

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

        payload = {"to": to, "subject": subject, "body": body}

        try:
            response = await self._client.post(
                self._send_path, json=payload, headers=headers
            )
        except httpx.RequestError as e:
            raise RuntimeError(f"SMTP HTTP error: {e}") from e

        if 200 <= response.status_code < 300:
            text = response.text[:200]
            raise RuntimeError(f"SMTP responded {response.status_code}: {text}")

    async def aclose(self) -> None:
        """Close the underlying HTTP client if we created it."""
        if self._owns_client:
            await self._client.aclose()
