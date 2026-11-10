"""Tests for labpipe vocab load, against a throwaway Postgres database."""

import shutil
from pathlib import Path

import psycopg
import pytest

from labpipe.common.migrate import apply_migrations
from labpipe.common.vocab import DEFAULT_DIR, load_vocabulary
from tests.test_vocab_subset import build_into

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def cdm_db(fresh_db_url):
    with psycopg.connect(fresh_db_url) as conn:
        apply_migrations(conn, ROOT / "db" / "migrations")
        yield conn


@pytest.fixture
def mini_subset(tmp_path):
    build_into(tmp_path / "subset")
    return tmp_path / "subset"


def count(conn, table):
    return conn.execute(f"SELECT count(*) FROM cdm.{table}").fetchone()[0]


def test_load_fills_the_tables(cdm_db, mini_subset):
    counts = load_vocabulary(cdm_db, mini_subset)
    assert counts["concept"] == count(cdm_db, "concept") > 0
    assert counts["concept_relationship"] == count(cdm_db, "concept_relationship") > 0
    assert count(cdm_db, "vocabulary") > 0


def test_empty_fields_become_null(cdm_db, mini_subset):
    load_vocabulary(cdm_db, mini_subset)
    row = cdm_db.execute(
        "SELECT standard_concept, invalid_reason FROM cdm.concept WHERE concept_id = 0"
    ).fetchone()
    assert row == (None, None)


def test_rerun_gives_the_same_tables(cdm_db, mini_subset):
    first = load_vocabulary(cdm_db, mini_subset)
    assert load_vocabulary(cdm_db, mini_subset) == first
    assert count(cdm_db, "concept") == first["concept"]


def test_missing_concept_is_rejected_and_rolled_back(cdm_db, mini_subset, tmp_path):
    load_vocabulary(cdm_db, mini_subset)
    before = count(cdm_db, "concept")

    broken = tmp_path / "broken"
    shutil.copytree(mini_subset, broken)
    concept = broken / "CONCEPT.csv"
    lines = concept.read_text(encoding="utf-8").splitlines(keepends=True)
    # Drop the concept behind the LOINC vocabulary row: a foreign key now points nowhere.
    concept.write_text("".join(ln for ln in lines if not ln.startswith("44819102\t")))

    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        load_vocabulary(cdm_db, broken)
    assert count(cdm_db, "concept") == before


@pytest.mark.skipif(not (ROOT / DEFAULT_DIR).is_dir(), reason="db/vocab_subset not built yet")
def test_committed_subset_loads(cdm_db):
    counts = load_vocabulary(cdm_db, ROOT / DEFAULT_DIR)
    assert counts["concept"] > 0
