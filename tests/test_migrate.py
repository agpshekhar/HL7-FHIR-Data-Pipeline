"""Tests for labpipe migrate."""

import psycopg
import pytest

from labpipe.common.migrate import DEFAULT_DIR, apply_migrations, find_migrations


def test_find_migrations_sorts_by_name(tmp_path):
    for name in ["0100_b.sql", "0001_a.sql", "notes.txt"]:
        (tmp_path / name).write_text("SELECT 1;")
    assert [p.name for p in find_migrations(tmp_path)] == ["0001_a.sql", "0100_b.sql"]


def test_first_run_applies_everything_second_run_nothing(fresh_db_url):
    expected = [p.name for p in find_migrations(DEFAULT_DIR)]
    with psycopg.connect(fresh_db_url) as conn:
        assert apply_migrations(conn, DEFAULT_DIR) == expected
        assert apply_migrations(conn, DEFAULT_DIR) == []


def test_expected_tables_exist(fresh_db_url):
    with psycopg.connect(fresh_db_url) as conn:
        apply_migrations(conn, DEFAULT_DIR)
        rows = conn.execute(
            "SELECT table_schema || '.' || table_name FROM information_schema.tables"
        ).fetchall()
    tables = {row[0] for row in rows}
    for table in [
        "staging.raw_message",
        "staging.error_queue",
        "staging.fhir_resource",
        "staging.crosswalk",
        "cdm.person",
        "cdm.measurement",
        "cdm.concept",
    ]:
        assert table in tables


def test_every_foreign_key_is_deferrable(fresh_db_url):
    with psycopg.connect(fresh_db_url) as conn:
        apply_migrations(conn, DEFAULT_DIR)
        total, deferrable = conn.execute(
            "SELECT count(*), count(*) FILTER (WHERE condeferrable AND condeferred) "
            "FROM pg_constraint WHERE contype = 'f'"
        ).fetchone()
    assert total > 0
    assert deferrable == total


def test_raw_message_rejects_a_duplicate_msh10(fresh_db_url):
    insert = "INSERT INTO staging.raw_message (msh10, message_type, raw) VALUES (%s, %s, %s)"
    with psycopg.connect(fresh_db_url) as conn:
        apply_migrations(conn, DEFAULT_DIR)
        conn.execute(insert, ["MSG0001", "ORU^R01", "MSH|..."])
        with pytest.raises(psycopg.errors.UniqueViolation):
            conn.execute(insert, ["MSG0001", "ORU^R01", "MSH|..."])


def test_a_failed_migration_is_not_recorded(fresh_db_url, tmp_path):
    (tmp_path / "0001_ok.sql").write_text("CREATE TABLE ok (id int);")
    (tmp_path / "0002_broken.sql").write_text("CREATE TABLE broken (id int); SELECT nonsense;")
    with psycopg.connect(fresh_db_url) as conn:
        with pytest.raises(psycopg.errors.UndefinedColumn):
            apply_migrations(conn, tmp_path)
        conn.rollback()
        versions = [r[0] for r in conn.execute("SELECT version FROM public.schema_migrations")]
        broken = conn.execute("SELECT to_regclass('public.broken')").fetchone()[0]
    assert versions == ["0001_ok.sql"]
    assert broken is None
