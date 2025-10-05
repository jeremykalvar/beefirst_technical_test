from typing import Callable

from app.domain.ports.activation_cache import ActivationCachePort
from app.domain.ports.unit_of_work import UnitOfWorkPort
from app.infrastructure.db.pool import get_pool
from app.infrastructure.db.uow import PgUnitOfWork
from app.infrastructure.redis_cache.activation_cache import RedisActivationCache
from app.infrastructure.redis_cache.pool import get_redis
from app.infrastructure.security.password import hash_password, verify_password


def get_uow() -> UnitOfWorkPort:
    return PgUnitOfWork(get_pool())


def get_activation_cache() -> ActivationCachePort:
    return RedisActivationCache(get_redis())


def get_hash_password() -> Callable[..., str]:
    return hash_password


def get_verify_password() -> Callable[[str, str], bool]:
    return verify_password


def get_code_ttl_seconds() -> int:
    return 60
