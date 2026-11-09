"""Database connection and query functions."""

import os

import psycopg


def database_url() -> str:
    """Return the Postgres URL from the DATABASE_URL environment variable"""
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL environment variable is not set.")
    return url


def connect(url: str | None = None) -> psycopg.Connection:
    """Open a connection to the Postgres database."""
    return psycopg.connect(url or database_url())
