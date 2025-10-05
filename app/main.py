from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.infrastructure.db.pool import get_pool, close_pool
from app.infrastructure.redis_cache.pool import get_redis, close_redis
from app.logging import setup_logging
from app.presentation.api import api
from app.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_pool()
    get_redis()
    try:
        yield
    finally:
        await close_redis()
        await close_pool()


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.log_level)
    app = FastAPI(title="Registration API", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.include_router(api)
    return app


app = create_app()
