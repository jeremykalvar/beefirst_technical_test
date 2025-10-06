from typing import Callable

from fastapi import Request

from app.domain.ports.activation_cache import ActivationCachePort
from app.domain.ports.email_port import EmailPort
from app.domain.ports.unit_of_work import UnitOfWorkPort
from app.infrastructure.db.pool import get_pool
from app.infrastructure.db.uow import PgUnitOfWork
from app.infrastructure.email.http_smtp_adapter import HttpSmtpEmailAdapter
from app.infrastructure.http.client import get_http_client
from app.infrastructure.redis_cache.activation_cache import RedisActivationCache
from app.infrastructure.redis_cache.pool import get_redis
from app.infrastructure.redis_cache.sessions import RedisSessions
from app.infrastructure.security.password import hash_password, verify_password
from app.settings import get_settings


def get_uow() -> UnitOfWorkPort:
    return PgUnitOfWork(get_pool())


def get_activation_cache() -> ActivationCachePort:
    return RedisActivationCache(get_redis())


def get_hash_password() -> Callable[..., str]:
    return hash_password


def get_verify_password() -> Callable[[str, str], bool]:
    return verify_password


def get_code_ttl_seconds() -> int:
    return get_settings().code_ttl_seconds


def get_email_port(request: Request) -> EmailPort:
    # This is set in app.main lifespan()
    return request.app.state.email_adapter


def get_sessions() -> RedisSessions:
    return RedisSessions(get_redis(), ttl_seconds=get_settings().session_ttl_seconds)
