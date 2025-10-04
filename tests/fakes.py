from app.domain.entities import User


class FakeUserRepo:
    def __init__(self):
        self.created_email = None
        self.created_hash = None
        self.set_last_code_calls = []

    async def create_or_update_pending(self, email: str, password_hash: str) -> User:
        self.created_email = email
        self.created_hash = password_hash
        return User(id="u1", email=email, status="pending")

    async def get_by_email_for_update(self, email: str):
        raise NotImplementedError

    async def set_active(self, user_id: str) -> None:
        raise NotImplementedError

    async def set_last_code_sent_at(self, user_id: str, when) -> None:
        self.set_last_code_calls.append((user_id, when))


class FakeOutboxRepo:
    def __init__(self):
        self.enqueues = []

    async def enqueue(
        self, *, topic: str, payload, idempotency_key: str | None = None
    ) -> str:
        self.enqueues.append((topic, payload, idempotency_key))
        return "m1"


class FakeActivationCache:
    def __init__(self):
        self.calls = []

    async def store_hashed_code(
        self, user_id: str, salt_b64: str, digest_b64: str, ttl_seconds: int
    ) -> None:
        self.calls.append((user_id, salt_b64, digest_b64, ttl_seconds))

    async def verify_and_consume(
        self, user_id: str, code: str
    ) -> bool:  # pragma: no cover
        return False

    async def invalidate(self, user_id: str) -> None:  # pragma: no cover
        pass


class FakeErroredActivationCache(FakeActivationCache):
    async def store_hashed_code(
        self, user_id: str, salt_b64: str, digest_b64: str, ttl_seconds: int
    ) -> None:
        raise RuntimeError("Redis down")


class FakeUoW:
    def __init__(self):
        self.users = FakeUserRepo()
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
