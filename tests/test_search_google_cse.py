"""Tests for job_finder/search/google_cse.py"""

import sys
import pytest


def _set_env(monkeypatch):
    for k, v in {
        "SERPER_API_KEY": "test_key", "ANTHROPIC_API_KEY": "x",
        "SF_USERNAME": "x", "SF_PASSWORD": "x", "SF_SECURITY_TOKEN": "x",
        "PG_DBNAME": "x", "PG_USER": "x", "PG_PASSWORD": "x",
    }.items():
        monkeypatch.setenv(k, v)


def test_search_one_site_returns_results(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    sys.modules.pop("job_finder.search.google_cse", None)
    from job_finder.search import google_cse

    mock_data = {
        "organic": [
            {"link": "https://boards.greenhouse.io/acme/jobs/1", "title": "SWE", "snippet": "Hiring..."},
            {"link": "https://boards.greenhouse.io/acme/jobs/2", "title": "PM", "snippet": "Seeking..."},
        ]
    }

    class MockResponse:
        ok = True
        def raise_for_status(self): pass
        def json(self): return mock_data

    monkeypatch.setattr("job_finder.search.google_cse.requests.post", lambda *a, **kw: MockResponse())

    results = google_cse.search_one_site("boards.greenhouse.io", "greenhouse", "Software Engineer", max_results=10)

    assert len(results) == 2
    assert results[0]["url"] == "https://boards.greenhouse.io/acme/jobs/1"
    assert results[0]["ats_type"] == "greenhouse"


def test_search_one_site_stops_on_empty_items(monkeypatch):
    """If 'items' absent from response, stop pagination."""
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    sys.modules.pop("job_finder.search.google_cse", None)
    from job_finder.search import google_cse

    call_count = {"n": 0}

    def mock_post(*a, **kw):
        call_count["n"] += 1
        return type("R", (), {
            "raise_for_status": lambda self: None,
            "json": lambda self: {},  # no 'organic'
        })()

    monkeypatch.setattr("job_finder.search.google_cse.requests.post", mock_post)

    results = google_cse.search_one_site("boards.greenhouse.io", "greenhouse", "Software Engineer", max_results=30)

    assert results == []
    assert call_count["n"] == 1  # stopped after first empty page


def test_search_one_site_handles_http_error_gracefully(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    sys.modules.pop("job_finder.search.google_cse", None)
    from job_finder.search import google_cse

    monkeypatch.setattr(
        "job_finder.search.google_cse.requests.post",
        lambda *a, **kw: (_ for _ in ()).throw(Exception("HTTP error"))
    )

    results = google_cse.search_one_site("boards.greenhouse.io", "greenhouse", "Software Engineer")
    assert results == []


def test_search_all_ats_combines_results(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    sys.modules.pop("job_finder.search.google_cse", None)
    from job_finder.search import google_cse

    call_domains = []

    def mock_search_one(domain, ats_type, keywords, max_results=10):
        call_domains.append(domain)
        return [{"url": f"https://{domain}/job/1", "title": "Job", "snippet": "", "ats_type": ats_type}]

    monkeypatch.setattr(google_cse, "search_one_site", mock_search_one)

    results = google_cse.search_all_ats("Software Engineer")

    assert len(results) == 5  # one result per ATS site
    assert len(call_domains) == 5
