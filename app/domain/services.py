from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from typing import Tuple

DIGEST_ALGO = "sha256"
SALT_BYTES = 16  # 128-bit random salt for code hashing


def generate_4digit_code() -> str:
    """
    Generate a zero-padded 4-digit code '0000'..'9999'.
    """
    return f"{secrets.randbelow(10000):04d}"


def secure_compare(a: str, b: str) -> bool:
    """
    Constant-time string comparison.
    """
    return hmac.compare_digest(a, b)


def _digest_with_salt(code: str, salt: bytes) -> bytes:
    """
    Compute digest = sha256(salt || code_utf8).
    """
    h = hashlib.new(DIGEST_ALGO)
    h.update(salt)
    h.update(code.encode("utf-8"))
    return h.digest()


def make_code_digest(code: str) -> Tuple[str, str]:
    """
    Returns (salt_b64, digest_b64) for the 4-digit code.
    """
    salt = secrets.token_bytes(SALT_BYTES)
    digest = _digest_with_salt(code, salt)
    return base64.b64encode(salt).decode(), base64.b64encode(digest).decode()


def verify_code_digest(code: str, salt_b64: str, digest_b64: str) -> bool:
    """
    Recompute digest and compare in constant time.
    """
    try:
        salt = base64.b64decode(salt_b64, validate=True)
        expected = base64.b64decode(digest_b64, validate=True)
    except Exception:
        return False
    actual = _digest_with_salt(code, salt)
    return hmac.compare_digest(actual, expected)
