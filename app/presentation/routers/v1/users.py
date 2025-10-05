from typing import Annotated, Callable

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.application.activate_user import activate_user
from app.application.register_user import register_user
from app.domain.errors import InvalidActivationCode, InvalidCredentials
from app.domain.ports.activation_cache import ActivationCachePort
from app.domain.ports.unit_of_work import UnitOfWorkPort
from app.presentation.dependencies import (
    get_activation_cache,
    get_code_ttl_seconds,
    get_hash_password,
    get_uow,
    get_verify_password,
)
from app.schemas.requests import UserActivateIn, UserCreateIn
from app.schemas.responses import AcceptedOut, OkOut

router = APIRouter(prefix="/users", tags=["Users"])


@router.post(
    "/",
    status_code=202,
    response_model=AcceptedOut,
)
async def post_create_user(
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


@router.post("/activate", status_code=200, response_model=OkOut)
async def post_activate_user(
    body: UserActivateIn,  # ideally rename to ActivationIn with only `code: str`
    uow: Annotated[UnitOfWorkPort, Depends(get_uow)],
    activation_cache: Annotated[ActivationCachePort, Depends(get_activation_cache)],
    verify_password: Annotated[
        Callable[[str, str], bool], Depends(get_verify_password)
    ],
    credentials: Annotated[HTTPBasicCredentials, Depends(HTTPBasic())],
):
    try:
        await activate_user(
            uow=uow,
            activation_cache=activation_cache,
            email=credentials.username,
            password=credentials.password,
            code=body.code,
            verify_password=verify_password,
        )
        return OkOut()

    except InvalidCredentials:
        raise HTTPException(status_code=401, detail="invalid credentials")
    except InvalidActivationCode:
        raise HTTPException(status_code=400, detail="invalid code")
