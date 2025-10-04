from __future__ import annotations

from typing import Any, Mapping, Protocol


class OutboxRepositoryPort(Protocol):
    async def enqueue(
        self,
        *,
        topic: str,
        payload: Mapping[str, Any],
        idempotency_key: str | None = None,
    ) -> str:
        """
        Enqueue a message into the outbox with status='pending'.

        - `topic`: short name (e.g., "user.verification_code").
        - `payload`: JSON-serializable mapping (will be stored as JSON).
        - `idempotency_key` (optional): if provided and already present,
          the implementation may return the existing message id instead of inserting again.

        Returns:
            The outbox message id (UUID string).
        """
