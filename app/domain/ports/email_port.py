from __future__ import annotations

from typing import Protocol


class EmailPort(Protocol):
    async def send(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        idempotency_key: str | None = None,
    ) -> None:
        """Send an email."""
