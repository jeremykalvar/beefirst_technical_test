from __future__ import annotations

from datetime import datetime
from typing import Optional, Protocol

from app.domain.entities import User


class UserRepositoryPort(Protocol):
    async def create_or_update_pending(self, email: str, password_hash: str) -> User:
        """
        Create user as 'pending' if not exists.
        If exists and status == 'pending', update password_hash.
        If exists and status == 'active', leave unchanged.
        Return the current User record in all cases.
        """

    async def get_by_email_for_update(self, email: str) -> Optional[User]:
        """
        Fetch user by email and lock the row for update (transaction-scoped).
        Return None if not found.
        """

    async def set_active(self, user_id: str) -> None:
        """Mark user as active."""

    async def set_last_code_sent_at(self, user_id: str, when: datetime) -> None:
        """Update last_code_sent_at for observability."""

    async def get_by_email_with_hash_for_update(
        self, email: str
    ) -> tuple[User, str] | None:
        """
        Fetch user by email and lock the row for update.
        Return None if not found.
        """
