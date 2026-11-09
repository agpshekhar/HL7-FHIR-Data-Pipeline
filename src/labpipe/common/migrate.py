"""Apply the SQL migrations in db/migrations/, each one exactly once."""

import os
from pathlib import Path

import psycopg

DEFAULT_DIR = Path("db/migrations")

LEDGER_DDL = """
CREATE TABLE IF NOT EXISTS public.schema_migrations (
    version    text        PRIMARY KEY,
    applied_at timestamptz NOT NULL DEFAULT now()
)
"""


def migrations_dir() -> Path:
    """Where the .sql files live: LABPIPE_MIGRATIONS_DIR, or db/migrations."""
    return Path(os.environ.get("LABPIPE_MIGRATIONS_DIR", DEFAULT_DIR))


def find_migrations(directory: Path) -> list[Path]:
    """Return the .sql files in run order (their names start with a number)."""
    return sorted(directory.glob("*.sql"))


def apply_migrations(conn: psycopg.Connection, directory: Path) -> list[str]:
    """Apply every migration not yet in the ledger. Return the names applied."""
    with conn.transaction():
        conn.execute(LEDGER_DDL)
        done = {row[0] for row in conn.execute("SELECT version FROM public.schema_migrations")}

    applied = []
    for path in find_migrations(directory):
        if path.name in done:
            continue
        with conn.transaction():
            conn.execute(path.read_text(encoding="utf-8"))
            conn.execute("INSERT INTO public.schema_migrations (version) VALUES (%s)", [path.name])
        applied.append(path.name)
    return applied
