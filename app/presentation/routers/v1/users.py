from typing import Annotated, Callable

from fastapi import APIRouter, Body, Depends, HTTPException, Header, Security, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBasic,
    HTTPBasicCredentials,
    HTTPBearer,
)

from app.application.activate_user import activate_user
from app.application.register_user import register_user
from app.domain.errors import (
    InvalidActivationCode,
    InvalidCredentials,
    InvalidStatusTransition,
)
from app.domain.ports.activation_cache import ActivationCachePort
from app.domain.ports.unit_of_work import UnitOfWorkPort
from app.infrastructure.db.uow import PgUnitOfWork
from app.infrastructure.redis_cache.sessions import RedisSessions
from app.presentation.dependencies import (
    get_activation_cache,
    get_code_ttl_seconds,
    get_hash_password,
    get_sessions,
    get_uow,
    get_verify_password,
)
from app.schemas.requests import UserActivateIn, UserCreateIn
from app.schemas.responses import AcceptedOut, OkOut

router = APIRouter(prefix="/users", tags=["Users"])
security = HTTPBasic()
bearer_scheme = HTTPBearer()


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


@router.post("/activate")
async def post_activate_user(
    creds: HTTPBasicCredentials = Depends(security),
    payload: UserActivateIn = Body(...),
    uow: UnitOfWorkPort = Depends(get_uow),
    activation_cache: ActivationCachePort = Depends(get_activation_cache),
    verify_password: Callable[[str, str], bool] = Depends(get_verify_password),
):
    try:
        await activate_user(
            uow=uow,
            activation_cache=activation_cache,
            email=creds.username,
            password=creds.password,
            code=payload.code,
            verify_password=verify_password,
        )
    except InvalidActivationCode:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="invalid activation code"
        )
    except InvalidStatusTransition:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="user already active"
        )

    return {"status": "ok"}


@router.post("/login")
async def post_login(
    creds: HTTPBasicCredentials = Depends(security),
    uow: PgUnitOfWork = Depends(get_uow),
    verify_password=Depends(get_verify_password),
    sessions: RedisSessions = Depends(get_sessions),
):
    email = creds.username.strip().lower()
    password = creds.password

    async with uow as transaction:
        user_and_hash = await transaction.db_users.get_by_email_with_hash(email)
        if not user_and_hash:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials"
            )
        user, pwd_hash = user_and_hash
        if user.status != "active" or not verify_password(password, pwd_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials"
            )
        token = await sessions.create(user.id)
        await transaction.commit()
    return {"token": token}


@router.get("/me")
async def get_me(
    auth: HTTPAuthorizationCredentials = Security(bearer_scheme),
    uow: PgUnitOfWork = Depends(get_uow),
    sessions: RedisSessions = Depends(get_sessions),
):
    token = auth.credentials
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token"
        )

    user_id = await sessions.get(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or expired token"
        )

    async with uow as tx:
        user = await tx.db_users.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="unknown user"
            )
        # no state change; no commit needed
    return {"id": user.id, "email": user.email, "status": user.status}
