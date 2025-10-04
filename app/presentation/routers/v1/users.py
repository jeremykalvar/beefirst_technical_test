from typing import Annotated, Callable

from fastapi import APIRouter, Depends

from app.application.register_user import register_user
from app.domain.ports.activation_cache import ActivationCachePort
from app.domain.ports.unit_of_work import UnitOfWorkPort
from app.presentation.dependencies import (
    get_activation_cache,
    get_code_ttl_seconds,
    get_hash_password,
    get_uow,
)
from app.schemas.requests import UserCreateIn
from app.schemas.responses import AcceptedOut

router = APIRouter(prefix="/users", tags=["Users"])


@router.post(
    "/",
    status_code=202,
    response_model=AcceptedOut,
)
async def create_user(
    body: UserCreateIn,
    uow: Annotated[UnitOfWorkPort, Depends(get_uow)],
    activation_cache: Annotated[ActivationCachePort, Depends(get_activation_cache)],
    hash_password: Annotated[Callable[..., str], Depends(get_hash_password)],
    code_ttl_seconds: Annotated[int, Depends(get_code_ttl_seconds)],
):
    await register_user(
        uow=uow,
        activation_cache=activation_cache,
        email=body.email,
        password=body.password,
        hash_password=hash_password,
        code_ttl_seconds=code_ttl_seconds,
    )
    return AcceptedOut()
