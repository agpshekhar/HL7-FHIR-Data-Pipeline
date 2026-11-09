"""Shared pytest fixtures."""

import os
import uuid

import psycopg
import pytest
from psycopg import sql


@pytest.fixture
def fresh_db_url():
    """Create an empty throwaway database, hand its URL to the test, then drop it.

    Needs DATABASE_URL pointing at a Postgres server where the user may create
    databases. Tests that use this fixture are skipped when DATABASE_URL is not set.
    """
    base_url = os.environ.get("DATABASE_URL")
    if not base_url:
        pytest.skip("DATABASE_URL not set; start Postgres with: docker compose up -d db")

    name = f"labpipe_test_{uuid.uuid4().hex[:8]}"
    with psycopg.connect(base_url, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))

    yield psycopg.conninfo.make_conninfo(base_url, dbname=name)

    with psycopg.connect(base_url, autocommit=True) as admin:
        admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
