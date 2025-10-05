from __future__ import annotations

from datetime import datetime
from typing import Optional

import psycopg

from app.domain.entities import User
from app.domain.ports.user_repository import UserRepositoryPort


class PgUserRepository(UserRepositoryPort):
    """
    Postgres implementation of UserRepositoryPort.

    NOTE:
    - This repo is constructed with an *active async connection* supplied by the UoW.
    - It does not commit; the UnitOfWork controls the transaction boundary.
    """

    def __init__(self, conn: psycopg.AsyncConnection) -> None:
        self._conn = conn

    async def create_or_update_pending(self, email: str, password_hash: str) -> User:
        sql = """
        WITH upsert AS (
        INSERT INTO users (email, password_hash, status)
        VALUES (LOWER(TRIM(%s)), %s, 'pending')
        ON CONFLICT (email) DO UPDATE
            SET password_hash = EXCLUDED.password_hash
            WHERE users.status = 'pending'
        RETURNING id, email, status, failed_attempts, last_code_sent_at
        )
        SELECT id, email, status, failed_attempts, last_code_sent_at
        FROM upsert
        UNION ALL
        SELECT id, email, status, failed_attempts, last_code_sent_at
        FROM users
        WHERE email = LOWER(TRIM(%s)) AND NOT EXISTS (SELECT 1 FROM upsert)
        LIMIT 1;
        """
        async with self._conn.cursor() as cur:
            await cur.execute(sql, (email, password_hash, email))
            row = await cur.fetchone()

        if not row:
            raise RuntimeError("create_or_update_pending returned no row")

        uid, eml, status, failed_attempts, last_code_sent_at = row
        return User(
            id=str(uid),
            email=str(eml),
            status=status,
            failed_attempts=failed_attempts or 0,
            last_code_sent_at=last_code_sent_at,
        )

    async def get_by_email_with_hash_for_update(
        self, email: str
    ) -> Optional[tuple[User, str]]:
        sql = """
        SELECT id, email, password_hash, status, failed_attempts, last_code_sent_at
        FROM users
        WHERE email = LOWER(TRIM(%s))
        FOR UPDATE
        """
        async with self._conn.cursor() as cur:
            await cur.execute(sql, (email,))
            row = await cur.fetchone()
            if not row:
                return None

            (
                id_,
                db_email,
                db_password_hash,
                db_status,
                db_failed_attempts,
                db_last_code_sent_at,
            ) = row

            return (
                User(
                    id=str(id_),
                    email=str(db_email),
                    status=str(db_status),
                    failed_attempts=db_failed_attempts or 0,
                    last_code_sent_at=db_last_code_sent_at,
                ),
                db_password_hash,  # return as-is (should be a str)
            )

    async def get_by_email_for_update(self, email: str) -> Optional[User]:
        raise NotImplementedError

    async def set_active(self, user_id: str) -> None:
        raise NotImplementedError

    async def set_last_code_sent_at(self, user_id: str, when: datetime) -> None:
        raise NotImplementedError
