from __future__ import annotations

from passlib.context import CryptContext

from app.settings import get_settings

# One global context; bcrypt is the only scheme we use.
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str, *, rounds: int | None = None) -> str:
    """
    Hash a password using bcrypt. If rounds is None, use settings.bcrypt_rounds.
    """
    if rounds is None:
        rounds = int(get_settings().bcrypt_rounds)
    return _pwd.hash(plain, rounds=rounds)


def verify_password(plain: str, password_hash: str) -> bool:
    """
    Verify a password against its bcrypt hash (safe timing).
    """
    return _pwd.verify(plain, password_hash)
