# app/main.py
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.infrastructure.db.pool import close_pool, open_pool
from app.logging import setup_logging
from app.presentation.api import api
from app.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # on startup
    await open_pool()
    try:
        yield
    finally:
        # on shutdown
        await close_pool()


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.log_level)

    app = FastAPI(title="Registration API", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.include_router(api)

    # TODO: add custom exception handlers

    return app


app = create_app()
