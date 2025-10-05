from __future__ import annotations

from dataclasses import dataclass
from types import TracebackType
from typing import Protocol, Type

from app.domain.ports.outbox_repository import OutboxRepositoryPort
from app.domain.ports.user_repository import UserRepositoryPort


@dataclass
class UnitOfWorkPort(Protocol):
    """
    Transaction boundary.

    Usage:
        async with uow as tx:
            user = await tx.users.create_or_update_pending(email, pwd_hash)
            msg_id = await tx.outbox.enqueue(topic="user.verification_code", payload={...})
            await tx.commit()
    """

    db_users: UserRepositoryPort
    outbox: OutboxRepositoryPort

    async def __aenter__(self) -> "UnitOfWorkPort":
        """Begin a new transaction. Code here runs before code in the context manager."""

    async def __aexit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """End the transaction. Code here runs after code in the context manager."""

    async def commit(self) -> None:
        """Commit the transaction."""

    async def rollback(self) -> None:
        """Rollback the transaction."""
