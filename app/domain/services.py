# app/domain/services.py
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets


def generate_4digit_code() -> str:
    """Zero-padded 4-digit numeric code."""
    return f"{secrets.randbelow(10_000):04d}"


def secure_compare(a: str, b: str) -> bool:
    """
    Constant-time comparison for secrets.
    Accepts strings; falls back to bytes if needed.
    """
    try:
        # hmac.compare_digest supports str if types match
        return hmac.compare_digest(a, b)
    except TypeError:
        return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def _sha256_salt_plus_code(salt: bytes, code: str) -> bytes:
    h = hashlib.sha256()
    h.update(salt)
    h.update(code.encode("utf-8"))
    return h.digest()


def make_code_digest(code: str) -> tuple[str, str]:
    """
    Return (salt_b64, digest_b64) where digest = SHA256(salt || code).
    """
    salt = os.urandom(16)
    digest = _sha256_salt_plus_code(salt, code)
    return (
        base64.b64encode(salt).decode("utf-8"),
        base64.b64encode(digest).decode("utf-8"),
    )


def verify_code_digest(code: str, salt_b64: str, digest_b64: str) -> bool:
    """
    Verify code against (salt_b64, digest_b64) from make_code_digest().
    """
    try:
        salt = base64.b64decode(salt_b64.encode("utf-8"))
        expected = base64.b64decode(digest_b64.encode("utf-8"))
    except Exception:
        return False

    calc = _sha256_salt_plus_code(salt, code)
    return hmac.compare_digest(calc, expected)
