"""Tests for job_finder/deduplicator.py"""

import sys
import os
import pytest


# Patch config before importing deduplicator
def _set_env(monkeypatch):
    for k, v in {
        "SERPER_API_KEY": "x", "ANTHROPIC_API_KEY": "x",
        "SF_USERNAME": "x", "SF_PASSWORD": "x", "SF_SECURITY_TOKEN": "x",
        "PG_DBNAME": "x", "PG_USER": "x", "PG_PASSWORD": "x",
    }.items():
        monkeypatch.setenv(k, v)


def test_normalize_url_strips_utm(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    from job_finder.deduplicator import normalize_url
    url = "https://boards.greenhouse.io/acme/jobs/123?utm_source=foo&utm_medium=bar"
    result = normalize_url(url)
    assert "utm_source" not in result
    assert "utm_medium" not in result
    assert "acme/jobs/123" in result


def test_normalize_url_lowercase_scheme_host(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    from job_finder.deduplicator import normalize_url
    result = normalize_url("HTTPS://BOARDS.GREENHOUSE.IO/acme/jobs/123")
    assert result.startswith("https://boards.greenhouse.io")


def test_normalize_url_strips_trailing_slash(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    from job_finder.deduplicator import normalize_url
    assert normalize_url("https://jobs.lever.co/acme/abc/") == normalize_url("https://jobs.lever.co/acme/abc")


def test_hash_url_is_deterministic(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    from job_finder.deduplicator import hash_url
    url = "https://boards.greenhouse.io/acme/jobs/123?utm_source=foo"
    assert hash_url(url) == hash_url(url)
    assert len(hash_url(url)) == 64


def test_hash_url_utm_stripped_produces_same_hash(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    from job_finder.deduplicator import hash_url
    url_with_utm = "https://boards.greenhouse.io/acme/jobs/123?utm_source=foo"
    url_clean = "https://boards.greenhouse.io/acme/jobs/123"
    assert hash_url(url_with_utm) == hash_url(url_clean)


def test_is_duplicate_returns_true_on_pg_hit(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    from job_finder.deduplicator import is_duplicate

    mock_conn = object()
    mock_sf = object()

    monkeypatch.setattr("job_finder.deduplicator.db.url_hash_exists", lambda conn, h: True)

    assert is_duplicate(mock_conn, mock_sf, "https://boards.greenhouse.io/acme/jobs/123") is True


def test_is_duplicate_returns_false_when_not_found(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    from job_finder.deduplicator import is_duplicate

    mock_conn = object()

    class MockSF:
        def query(self, soql):
            return {"totalSize": 0, "records": []}

    monkeypatch.setattr("job_finder.deduplicator.db.url_hash_exists", lambda conn, h: False)

    assert is_duplicate(mock_conn, MockSF(), "https://boards.greenhouse.io/acme/jobs/999") is False


def test_is_duplicate_returns_true_on_sf_hit(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    from job_finder.deduplicator import is_duplicate

    mock_conn = object()

    class MockSF:
        def query(self, soql):
            return {"totalSize": 1, "records": [{"Id": "abc"}]}

    monkeypatch.setattr("job_finder.deduplicator.db.url_hash_exists", lambda conn, h: False)

    assert is_duplicate(mock_conn, MockSF(), "https://boards.greenhouse.io/acme/jobs/999") is True
