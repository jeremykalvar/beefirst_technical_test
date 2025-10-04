from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg

try:
    from app.settings import get_settings
except Exception:
    get_settings = None


MIGRATIONS_DIR = Path(os.environ.get("MIGRATIONS_DIR", "migrations"))
SCHEMA_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
  version    text PRIMARY KEY,
  applied_at timestamptz NOT NULL DEFAULT now()
);
"""


def log(msg: str) -> None:
    print(msg, flush=True)


def dsn() -> str:
    if get_settings:
        url = get_settings().database_url
    else:
        url = os.environ.get("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL is not set", file=sys.stderr)
        sys.exit(2)
    return url


def list_migrations() -> list[Path]:
    if not MIGRATIONS_DIR.exists():
        print(f"ERROR: migrations dir not found: {MIGRATIONS_DIR}", file=sys.stderr)
        sys.exit(2)
    return sorted([p for p in MIGRATIONS_DIR.glob("*.sql")])


def applied_versions(conn: psycopg.Connection) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(SCHEMA_TABLE_SQL)
        cur.execute("SELECT version FROM schema_migrations ORDER BY version;")
        rows = cur.fetchall()
    return {r[0] for r in rows}


def apply_one(conn: psycopg.Connection, path: Path) -> None:
    version = path.stem
    sql = path.read_text(encoding="utf-8")
    log(f"==> applying {version}")
    with conn.cursor() as cur:
        cur.execute(sql)
        cur.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (%s, now());",
            (version,),
        )
    conn.commit()
    log(f"✓ applied {version}")


def cmd_up() -> int:
    with psycopg.connect(dsn(), autocommit=False) as conn:
        done = applied_versions(conn)
        to_run = [p for p in list_migrations() if p.stem not in done]
        if not to_run:
            log("No pending migrations.")
            return 0
        for path in to_run:
            try:
                apply_one(conn, path)
            except Exception as e:
                conn.rollback()
                print(f"✗ failed {path.stem}: {e}", file=sys.stderr)
                return 1
    return 0


def cmd_status() -> int:
    with psycopg.connect(dsn()) as conn, conn.cursor() as cur:
        cur.execute(SCHEMA_TABLE_SQL)
        cur.execute(
            "SELECT version, applied_at FROM schema_migrations ORDER BY version;"
        )
        rows = cur.fetchall()
    all_versions = [p.stem for p in list_migrations()]
    print("=== Applied ===")
    seen = set()
    for v, at in rows:
        seen.add(v)
        print(f"{v} @ {at.isoformat() if isinstance(at, datetime) else at}")
    print("=== Pending ===")
    for v in all_versions:
        if v not in seen:
            print(v)
    return 0


def cmd_new(name: str) -> int:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    filename = f"{ts}_{name}.sql"
    path = MIGRATIONS_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    template = "-- write your SQL here\n"
    path.write_text(template, encoding="utf-8")
    print(str(path))
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(
            "usage: python -m app.infrastructure.db.migrate [up|status|new <name>]",
            file=sys.stderr,
        )
        return 2
    cmd = argv[1]
    if cmd == "up":
        return cmd_up()
    if cmd == "status":
        return cmd_status()
    if cmd == "new":
        if len(argv) < 3:
            print("usage: ... new <name>", file=sys.stderr)
            return 2
        return cmd_new(argv[2])
    print(f"unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
