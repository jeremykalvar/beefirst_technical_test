from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.infrastructure.db.pool import get_pool, close_pool
from app.infrastructure.email.http_smtp_adapter import HttpSmtpEmailAdapter
from app.infrastructure.http.client import (
    close_http_client,
    open_http_client,
    get_http_client,
)
from app.infrastructure.redis_cache.pool import get_redis, close_redis
from app.logging import setup_logging
from app.presentation.api import api
from app.settings import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    pool = get_pool()
    if not getattr(pool, "is_open", False):
        await pool.open()

    await open_http_client()

    get_redis()

    # Create ONE shared Email adapter, using the shared HTTP client
    email_adapter = HttpSmtpEmailAdapter(
        base_url=settings.smtp_base_url,
        client=get_http_client(),
    )
    app.state.email_adapter = email_adapter  # expose to dependencies

    try:
        yield
    finally:
        # shutdown
        await email_adapter.aclose()  # it won't close the shared client
        await close_http_client()  # closes the shared client
        await close_redis()
        await close_pool()


def create_app() -> FastAPI:
    setup_logging(settings.log_level)
    app = FastAPI(title="Registration API", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.include_router(api)
    return app


app = create_app()
