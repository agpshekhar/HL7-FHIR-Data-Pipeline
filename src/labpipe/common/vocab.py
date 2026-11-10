"""Load OMOP vocabulary tables from Athena-format files into cdm.*.

The same loader reads the committed subset in db/vocab_subset/ (the default) or a
full Athena download (set LABPIPE_VOCAB_DIR, or pass --dir). Both use Athena's
format: tab-separated, a header row, dates as YYYYMMDD, no quoting.

Each load replaces the six tables in one transaction. The foreign keys are
DEFERRABLE INITIALLY DEFERRED, so rows can arrive in any order; every key is checked
once, after the last file is copied. A broken subset rolls back and leaves the old rows.
"""

import os
from pathlib import Path

import psycopg
from psycopg import sql

DEFAULT_DIR = Path("db/vocab_subset")

# Table name -> Athena file name.
TABLES = {
    "concept": "CONCEPT.csv",
    "concept_relationship": "CONCEPT_RELATIONSHIP.csv",
    "domain": "DOMAIN.csv",
    "vocabulary": "VOCABULARY.csv",
    "concept_class": "CONCEPT_CLASS.csv",
    "relationship": "RELATIONSHIP.csv",
}

# CSV mode turns an empty field into NULL (invalid_reason, standard_concept, ...).
# Athena never quotes, but its names can contain a double quote, so the quote
# character is set to a byte that never appears in the files.
COPY_SQL = (
    "COPY cdm.{table} ({columns}) FROM STDIN "
    "WITH (FORMAT csv, DELIMITER E'\\t', HEADER true, QUOTE E'\\x01')"
)


def vocab_dir() -> Path:
    """Where the vocabulary files live: LABPIPE_VOCAB_DIR, or db/vocab_subset."""
    return Path(os.environ.get("LABPIPE_VOCAB_DIR", DEFAULT_DIR))


def missing_files(directory: Path) -> list[str]:
    """The Athena files the loader needs that are not in directory."""
    return [name for name in TABLES.values() if not (directory / name).is_file()]


def load_vocabulary(conn: psycopg.Connection, directory: Path) -> dict[str, int]:
    """Replace the cdm vocabulary tables with the files in directory. Return row counts."""
    missing = missing_files(directory)
    if missing:
        raise FileNotFoundError(f"missing in {directory}: {', '.join(missing)}")

    counts = {}
    with conn.transaction():
        for table in TABLES:
            conn.execute(sql.SQL("DELETE FROM cdm.{}").format(sql.Identifier(table)))
        for table, filename in TABLES.items():
            path = directory / filename
            with path.open(encoding="utf-8") as f:
                header = f.readline().rstrip("\r\n").split("\t")
            query = sql.SQL(COPY_SQL).format(
                table=sql.Identifier(table),
                columns=sql.SQL(", ").join(sql.Identifier(c.lower()) for c in header),
            )
            with conn.cursor() as cur:
                with cur.copy(query) as copy, path.open("rb") as f:
                    while chunk := f.read(1 << 20):
                        copy.write(chunk)
                counts[table] = cur.rowcount
        # Check every deferred foreign key now, inside this block. If the caller had
        # already opened a transaction, this block is only a savepoint, and the
        # check would otherwise wait for the caller's commit.
        conn.execute("SET CONSTRAINTS ALL IMMEDIATE")
    return counts
