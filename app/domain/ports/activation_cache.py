from typing import Protocol


class ActivationCachePort(Protocol):
    async def store_hashed_code(
        self, user_id: str, salt_b64: str, digest_b64: str, ttl_seconds: int
    ) -> None:
        """Store/replace the hashed code with TTL=ttl_seconds."""

    async def verify_and_consume(self, user_id: str, code: str) -> bool:
        """True if matches (and then delete it for single-use), else False."""

    async def invalidate(self, user_id: str) -> None:
        """Delete any existing code (used before a resend)."""
