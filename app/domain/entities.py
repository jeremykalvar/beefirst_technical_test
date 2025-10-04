from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from app.domain.errors import InvalidStatusTransition, UserLocked


@dataclass
class User:
    id: str | None = None
    email: str | None = None
    status: Literal["pending", "active", "locked"] = "pending"
    failed_attempts: int = 0
    last_code_sent_at: datetime | None = None

    def __post_init__(self):
        if self.email:
            self.email = self.email.strip().lower()
            if not self.email:
                raise ValueError("email cannot be empty")
        else:
            raise ValueError("email is required")

    def activate(self):
        if self.status == "locked":
            raise UserLocked()
        if self.status != "pending":
            raise InvalidStatusTransition()
        self.status = "active"

    def lock(self):
        self.status = "locked"
