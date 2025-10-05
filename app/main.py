from fastapi import FastAPI

from app.logging import setup_logging
from app.presentation.api import api
from app.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.log_level)

    app = FastAPI(title="Registration API", version="0.1.0")
    app.state.settings = settings
    app.include_router(api)

    # TODO: Add custom exception handler

    return app


app = create_app()
