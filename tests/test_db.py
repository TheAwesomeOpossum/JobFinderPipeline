"""Tests for job_finder/db.py — mocks psycopg2 entirely."""

import sys
import pytest
from unittest.mock import MagicMock, patch, call


def _set_env(monkeypatch):
    for k, v in {
        "GOOGLE_API_KEY": "x", "GOOGLE_CSE_ID": "x", "ANTHROPIC_API_KEY": "x",
        "SF_USERNAME": "x", "SF_PASSWORD": "x", "SF_SECURITY_TOKEN": "x",
        "PG_DBNAME": "testdb", "PG_USER": "testuser", "PG_PASSWORD": "testpass",
    }.items():
        monkeypatch.setenv(k, v)


def _make_conn(fetchone_return=None):
    """Build a mock psycopg2 connection."""
    conn = MagicMock()
    cursor = MagicMock()
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.__exit__ = MagicMock(return_value=False)
    cursor.fetchone.return_value = fetchone_return
    conn.cursor.return_value = cursor
    return conn, cursor


def test_insert_job_lead_executes_insert(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    sys.modules.pop("job_finder.db", None)
    from job_finder import db

    conn, cursor = _make_conn(fetchone_return=(42,))

    job = {
        "url_hash": "abc123", "url": "https://example.com", "title": "SWE",
        "company": "Acme", "ats_type": "greenhouse", "score": 75,
    }
    row_id = db.insert_job_lead(conn, job)

    assert row_id == 42
    conn.commit.assert_called_once()
    assert cursor.execute.call_count == 1
    sql_called = cursor.execute.call_args[0][0]
    assert "INSERT INTO job_lead" in sql_called
    assert "ON CONFLICT" in sql_called


def test_url_hash_exists_returns_true(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    sys.modules.pop("job_finder.db", None)
    from job_finder import db

    conn, cursor = _make_conn(fetchone_return=(1,))
    assert db.url_hash_exists(conn, "abc123") is True


def test_url_hash_exists_returns_false(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    sys.modules.pop("job_finder.db", None)
    from job_finder import db

    conn, cursor = _make_conn(fetchone_return=None)
    assert db.url_hash_exists(conn, "abc123") is False


def test_mark_pushed_updates_status(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    sys.modules.pop("job_finder.db", None)
    from job_finder import db

    conn, cursor = _make_conn()
    db.mark_pushed(conn, "abc123", "sf_app_id", "sf_acc_id")

    conn.commit.assert_called_once()
    sql_called = cursor.execute.call_args[0][0]
    assert "pushed" in sql_called


def test_mark_skipped_updates_status(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    sys.modules.pop("job_finder.db", None)
    from job_finder import db

    conn, cursor = _make_conn()
    db.mark_skipped(conn, "abc123")

    conn.commit.assert_called_once()
    sql_called = cursor.execute.call_args[0][0]
    assert "skipped" in sql_called


def test_mark_failed_updates_status_with_error(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    sys.modules.pop("job_finder.db", None)
    from job_finder import db

    conn, cursor = _make_conn()
    db.mark_failed(conn, "abc123", "Something went wrong")

    conn.commit.assert_called_once()
    sql_called = cursor.execute.call_args[0][0]
    assert "failed" in sql_called
