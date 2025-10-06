from __future__ import annotations
from typing import Protocol, Any


class OutboxRepositoryPort(Protocol):
    async def enqueue(
        self, topic: str, payload: dict, idempotency_key: str | None = None
    ) -> str:
        """
        Enqueue a message into the outbox with status='pending'.
        """

    async def reserve_due(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Atomically pick a small batch that is due, mark as "processing",
        and bump attempts (to avoid duplicate work by multiple workers).
        """

    async def mark_succeeded(self, msg_id: str) -> None:
        """
        Mark a message as successfully dispatched
        """

    async def mark_failed(
        self, msg_id: str, error: str, retry_in_seconds: int | None
    ) -> None:
        """
        On failure, either schedule a retry (status back to 'pending' with next_attempt_at),
        or mark permanently 'failed' if retry_in_seconds is None.
        """
