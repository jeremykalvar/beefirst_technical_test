from datetime import datetime, timezone
from typing import Callable

import app.domain.services as domain_services
from app.domain.ports.activation_cache import ActivationCachePort
from app.domain.ports.unit_of_work import UnitOfWorkPort


async def register_user(
    uow: UnitOfWorkPort,
    activation_cache: ActivationCachePort,
    email: str,
    password: str,
    hash_password: Callable[..., str],
    code_ttl_seconds: int = 60,
) -> None:
    normalized_email = email.strip().lower()
    hashed_password = hash_password(password)
    generated_code = domain_services.generate_4digit_code()
    salt_b64, digest_b64 = domain_services.make_code_digest(generated_code)

    async with uow as transaction:
        user = await transaction.db_users.create_or_update_pending(
            normalized_email, hashed_password
        )
        await activation_cache.store_hashed_code(
            user.id, salt_b64, digest_b64, code_ttl_seconds
        )
        await transaction.outbox.enqueue(
            topic="user.verification_code",
            payload={
                "to": normalized_email,
                "subject": "Your verification code",
                "body": "Your code is " + generated_code,
            },
        )
        await transaction.db_users.set_last_code_sent_at(
            user.id, datetime.now(timezone.utc)
        )
        await transaction.commit()
