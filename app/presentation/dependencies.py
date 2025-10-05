from typing import Callable

from app.domain.ports.activation_cache import ActivationCachePort
from app.domain.ports.unit_of_work import UnitOfWorkPort
from app.infrastructure.security.password import hash_password, verify_password


def get_uow() -> UnitOfWorkPort:
    raise NotImplementedError("Not implemented")


def get_activation_cache() -> ActivationCachePort:
    raise NotImplementedError("Not implemented")


def get_hash_password() -> Callable[..., str]:
    return hash_password


def get_code_ttl_seconds() -> int:
    return 60


def get_verify_password() -> Callable[[str, str], bool]:
    return verify_password
