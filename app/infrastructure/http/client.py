from __future__ import annotations

from typing import Optional
import httpx

_client: Optional[httpx.AsyncClient] = None


async def open_http_client() -> httpx.AsyncClient:
    """Create a single shared AsyncClient (if not already created)."""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=10.0)
    return _client


def get_http_client() -> httpx.AsyncClient:
    """Return the shared client. Must have been opened at startup."""
    if _client is None:
        raise RuntimeError(
            "HTTP client not opened yet. Call open_http_client() at startup."
        )
    return _client


async def close_http_client() -> None:
    """Close and drop the shared client."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
