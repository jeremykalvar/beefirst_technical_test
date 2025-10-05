import pytest

from app.infrastructure.db.pool import open_pool, get_pool, close_pool
from app.infrastructure.db.users_repo import PgUserRepository


@pytest.mark.asyncio
async def test_users_repo_create_or_update_and_get_with_hash():
    """
    Integration test against the real Postgres:
    - insert a pending user (or update if already pending)
    - confirm fields
    - flip to active and ensure upsert doesn't change it
    - fetch with FOR UPDATE and get the stored hash
    """
    await open_pool()
    pool = get_pool()

    # include leading & trailing spaces to be sure trimming is handled
    raw_email = " Jeremy@Example.COM "
    norm_email = raw_email.strip().lower()

    try:
        async with pool.connection() as conn:
            # Clean slate for this email regardless of how it might have been stored
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM users WHERE lower(trim(email)) = lower(trim(%s));",
                    (raw_email,),
                )

            repo = PgUserRepository(conn)

            # 1) Insert new pending user (repo should normalize internally)
            u1 = await repo.create_or_update_pending(raw_email, "hash-1")
            assert u1.email == "jeremy@example.com"
            assert u1.status == "pending"
            assert u1.id is not None

            # Verify the stored hash in DB is "hash-1"
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT password_hash FROM users WHERE lower(trim(email)) = lower(trim(%s));",
                    (raw_email,),
                )
                row = await cur.fetchone()
                assert row and row[0] == "hash-1"

            # 2) Now flip row to active and try upsert again with a new hash: it must NOT change
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE users SET status = 'active' WHERE id = %s;", (u1.id,)
                )

            u2 = await repo.create_or_update_pending("JEREMY@EXAMPLE.COM", "hash-2")
            assert u2.id == u1.id
            assert u2.status == "active"  # unchanged

            # Hash should still be "hash-1" because we don't update non-pending users
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT password_hash FROM users WHERE lower(trim(email)) = lower(trim(%s));",
                    (norm_email,),
                )
                row = await cur.fetchone()
                assert row and row[0] == "hash-1"

            # 3) Fetch row with hash & row lock
            got = await repo.get_by_email_with_hash_for_update(raw_email)
            assert got is not None
            user3, pwd_hash = got
            assert user3.id == u1.id
            assert user3.email == "jeremy@example.com"
            assert pwd_hash == "hash-1"
    finally:
        await close_pool()
