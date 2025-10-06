from typing import Any

import pytest
from psycopg.types.json import Json

from app.infrastructure.outbox.dispatcher import OutboxDispatcher, RetryPolicy
from tests.fakes import FakeEmailFlaky, FakeEmailOK

pytest_plugins = ["tests.integration.db_fixtures"]
pytestmark = pytest.mark.usefixtures("truncate_outbox")


async def _insert_outbox(
    pool,
    *,
    topic: str,
    payload: dict[str, Any],
    status: str = "pending",
    attempts: int = 0,
    due_now: bool = True,
) -> int:
    """
    Insert a row into outbox. If due_now=True, make it eligible immediately.
    """
    async with pool.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                if due_now:
                    sql = """
                        INSERT INTO outbox (topic, payload, status, attempts, next_attempt_at)
                        VALUES (%s, %s, %s, %s, NOW())
                        RETURNING id;
                    """
                    await cur.execute(sql, (topic, Json(payload), status, attempts))
                else:
                    sql = """
                        INSERT INTO outbox (topic, payload, status, attempts)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id;
                    """
                    await cur.execute(sql, (topic, Json(payload), status, attempts))
                row = await cur.fetchone()
                return int(row[0])


async def _row_by_id(pool, msg_id: int) -> dict[str, Any]:
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, topic, status, attempts, next_attempt_at FROM outbox WHERE id=%s",
                (msg_id,),
            )
            r = await cur.fetchone()
    if not r:
        return {}
    return {
        "id": r[0],
        "topic": r[1],
        "status": r[2],
        "attempts": r[3],
        "next_attempt_at": r[4],
    }


@pytest.mark.asyncio
async def test_dispatch_success_marks_dispatched(pool):
    email = FakeEmailOK()
    dispatcher = OutboxDispatcher(
        pool=pool,
        email_adapter=email,
        batch_size=10,
        poll_interval=0.1,
        retry_policy=RetryPolicy(base=1, max_delay=10),
    )

    msg_id = await _insert_outbox(
        pool,
        topic="user.verification_code",
        payload={"to": "u@example.com", "subject": "s", "body": "b"},
        due_now=True,
    )

    processed = await dispatcher._process_once()
    assert processed == 1

    row = await _row_by_id(pool, msg_id)
    assert row["status"] == "dispatched"
    assert email.calls and email.calls[0]["to"] == "u@example.com"


@pytest.mark.asyncio
async def test_dispatch_failure_is_retried_then_succeeds(pool):
    flaky = FakeEmailFlaky(fail_first=True)
    dispatcher = OutboxDispatcher(
        pool=pool,
        email_adapter=flaky,
        batch_size=10,
        poll_interval=0.1,
        retry_policy=RetryPolicy(base=2, max_delay=60),
    )

    msg_id = await _insert_outbox(
        pool,
        topic="user.verification_code",
        payload={"to": "u2@example.com", "subject": "s", "body": "b"},
        due_now=True,
    )

    processed1 = await dispatcher._process_once()
    assert processed1 == 1

    row1 = await _row_by_id(pool, msg_id)
    assert row1["status"] == "pending"
    assert row1["attempts"] == 1
    assert row1["next_attempt_at"] is not None

    async with pool.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE outbox SET next_attempt_at = NOW() WHERE id=%s",
                    (msg_id,),
                )

    processed2 = await dispatcher._process_once()
    assert processed2 == 1

    row2 = await _row_by_id(pool, msg_id)
    assert row2["status"] == "dispatched"
    assert flaky.calls >= 2


@pytest.mark.asyncio
async def test_unknown_topic_is_rescheduled(pool):
    email = FakeEmailOK()
    dispatcher = OutboxDispatcher(
        pool=pool,
        email_adapter=email,
        batch_size=5,
        poll_interval=0.1,
        retry_policy=RetryPolicy(base=1, max_delay=10),
    )

    msg_id = await _insert_outbox(
        pool,
        topic="weird.topic",
        payload={"foo": "bar"},
        due_now=True,
    )

    processed = await dispatcher._process_once()
    assert processed == 1

    row = await _row_by_id(pool, msg_id)
    assert row["status"] == "pending"
    assert row["attempts"] == 1
    assert row["next_attempt_at"] is not None
