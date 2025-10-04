from fastapi import APIRouter

from app.settings import get_settings


router = APIRouter()


@router.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}


# TODO: remove this route
@router.get("/settings")
async def settings() -> dict:
    return {"settings": get_settings().model_dump()}
