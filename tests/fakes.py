from dataclasses import dataclass
from typing import Any
from app.domain.entities import User


class FakeUserRepo:
    def __init__(self):
        self.created_email = None
        self.created_hash = None
        self.set_last_code_calls = []
        self.password_hash_by_email: dict[str, str] = {}
        self.set_active_calls: list[str] = []

    async def create_or_update_pending(self, email: str, password_hash: str) -> User:
        self.created_email = email
        self.created_hash = password_hash
        return User(id="u1", email=email, status="pending")

    async def get_by_email_for_update(self, email: str):
        raise NotImplementedError

    async def set_active(self, user_id: str) -> None:
        self.set_active_calls.append(user_id)

    async def set_last_code_sent_at(self, user_id: str, when) -> None:
        self.set_last_code_calls.append((user_id, when))

    async def get_by_email_with_hash_for_update(
        self, email: str
    ) -> tuple[User, str] | None:
        normalized_email = email.strip().lower()
        if normalized_email not in self.password_hash_by_email:
            return None
        return (
            User(id="u1", email=normalized_email, status="pending"),
            self.password_hash_by_email[normalized_email],
        )


class FakeOutboxRepo:
    def __init__(self):
        self.enqueues = []

    async def enqueue(
        self, *, topic: str, payload, idempotency_key: str | None = None
    ) -> str:
        self.enqueues.append((topic, payload, idempotency_key))
        return "m1"


class FakeActivationCache:
    def __init__(self, verify_result: bool = True):
        self.verify_result = verify_result
        self.calls: list[tuple[str, str]] = []

    async def store_hashed_code(
        self, user_id: str, salt_b64: str, digest_b64: str, ttl_seconds: int
    ) -> None:
        self.calls.append((user_id, salt_b64, digest_b64, ttl_seconds))

    async def verify_and_consume(self, user_id: str, code: str) -> bool:
        self.calls.append((user_id, code))
        return self.verify_result

    async def invalidate(self, user_id: str) -> None:
        pass


class FakeErroredActivationCache(FakeActivationCache):
    async def store_hashed_code(
        self, user_id: str, salt_b64: str, digest_b64: str, ttl_seconds: int
    ) -> None:
        raise RuntimeError("Redis down")


class FakeUoW:
    def __init__(self):
        self.db_users = FakeUserRepo()
        self.outbox = FakeOutboxRepo()
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if exc:
            self.rolled_back = True

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class FakeEmailOK:
    def __init__(self):
        self.calls: list[dict[str, Any]] = []

    async def send(
        self, *, to: str, subject: str, body: str, idempotency_key=None
    ) -> None:
        self.calls.append(
            {
                "to": to,
                "subject": subject,
                "body": body,
                "idempotency_key": idempotency_key,
            }
        )


class FakeEmailFlaky:
    def __init__(self, fail_first: bool = True):
        self.calls: int = 0
        self.fail_first = fail_first

    async def send(
        self, *, to: str, subject: str, body: str, idempotency_key=None
    ) -> None:
        self.calls += 1
        if self.fail_first and self.calls == 1:
            raise RuntimeError("boom once")


class FakeSessions:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self._next = 0

    async def create(self, user_id: str) -> str:
        self._next += 1
        token = f"tok-{self._next}"
        self._store[token] = user_id
        return token

    async def get(self, token: str) -> str | None:
        return self._store.get(token)

    async def revoke(self, token: str) -> None:
        self._store.pop(token, None)


@dataclass
class FakeAuthUsersRepo:
    by_email: dict[str, tuple[User, str]]
    by_id: dict[str, User]

    async def get_by_email_with_hash(self, email: str) -> tuple[User, str] | None:
        return self.by_email.get(email)

    async def get_by_id(self, user_id: str) -> User | None:
        return self.by_id.get(user_id)


class FakeUoWAuth:
    def __init__(self, repo: FakeAuthUsersRepo) -> None:
        self.db_users = repo

    async def __aenter__(self) -> "FakeUoWAuth":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def commit(self) -> None:
        return None
