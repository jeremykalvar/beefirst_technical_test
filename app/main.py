from fastapi import FastAPI

from app.presentation.routes.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(title="Registration API", version="0.1.0")
    app.include_router(health_router)
    return app


# Allow "uvicorn app.main:app" too
app = create_app()
