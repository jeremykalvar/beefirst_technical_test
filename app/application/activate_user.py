from typing import Callable

from app.domain.errors import InvalidActivationCode, InvalidCredentials
from app.domain.ports.activation_cache import ActivationCachePort
from app.domain.ports.unit_of_work import UnitOfWorkPort


async def activate_user(
    uow: UnitOfWorkPort,
    activation_cache: ActivationCachePort,
    email: str,
    password: str,
    code: str,
    verify_password: Callable[[str, str], bool],
) -> None:
    normalized_email = email.strip().lower()

    async with uow as transaction:
        record = await transaction.users.get_by_email_with_hash_for_update(
            normalized_email
        )
        if not record:
            raise InvalidCredentials()
        user, password_hash = record
        if not verify_password(password, password_hash):
            raise InvalidCredentials()
        if not await activation_cache.verify_and_consume(user.id, code):
            raise InvalidActivationCode()
        user.activate()
        await transaction.users.set_active(user.id)
        await transaction.commit()
