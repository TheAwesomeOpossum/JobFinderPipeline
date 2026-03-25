"""Tests for job_finder/parser/greenhouse.py"""

import sys
import pytest

GREENHOUSE_RESPONSE = {
    "id": 12345,
    "title": "Senior Software Engineer",
    "company_name": "Acme Corp",
    "location": {"name": "Remote"},
    "content": "<p>We are hiring a <b>Senior Software Engineer</b>.</p>",
    "first_published": "2026-03-25T06:00:00Z",
    "departments": [{"name": "Engineering"}],
    "absolute_url": "https://boards.greenhouse.io/acme/jobs/12345",
}


def _set_env(monkeypatch):
    for k, v in {
        "GOOGLE_API_KEY": "x", "GOOGLE_CSE_ID": "x", "ANTHROPIC_API_KEY": "x",
        "SF_USERNAME": "x", "SF_PASSWORD": "x", "SF_SECURITY_TOKEN": "x",
        "PG_DBNAME": "x", "PG_USER": "x", "PG_PASSWORD": "x",
    }.items():
        monkeypatch.setenv(k, v)


def test_can_parse_greenhouse_url(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    from job_finder.parser.greenhouse import can_parse
    assert can_parse("https://boards.greenhouse.io/acme/jobs/12345") is True
    assert can_parse("https://job-boards.greenhouse.io/acme/jobs/12345") is True
    assert can_parse("https://jobs.lever.co/acme/abc") is False


def test_parse_maps_fields_correctly(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    from job_finder.parser import greenhouse

    mock_response = type("R", (), {
        "raise_for_status": lambda self: None,
        "json": lambda self: GREENHOUSE_RESPONSE,
    })()

    monkeypatch.setattr("job_finder.parser.greenhouse.requests.get", lambda *a, **kw: mock_response)

    raw = {
        "url": "https://boards.greenhouse.io/acme/jobs/12345",
        "title": "Senior Software Engineer",
        "snippet": "We are hiring...",
        "ats_type": "greenhouse",
        "url_hash": "",
    }
    result = greenhouse.parse(raw)

    assert result is not None
    assert result["title"] == "Senior Software Engineer"
    assert result["company"] == "Acme Corp"
    assert result["location"] == "Remote"
    assert result["department"] == "Engineering"
    assert result["posted_at"] == "2026-03-25"
    assert "Senior Software Engineer" in result["description"]  # HTML stripped


def test_parse_appends_content_true_to_api_url(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    from job_finder.parser import greenhouse

    captured_urls = []

    def mock_get(url, **kwargs):
        captured_urls.append(url)
        return type("R", (), {
            "raise_for_status": lambda self: None,
            "json": lambda self: GREENHOUSE_RESPONSE,
        })()

    monkeypatch.setattr("job_finder.parser.greenhouse.requests.get", mock_get)

    raw = {
        "url": "https://boards.greenhouse.io/acme/jobs/12345",
        "title": "Senior SE", "snippet": "", "ats_type": "greenhouse", "url_hash": "",
    }
    greenhouse.parse(raw)

    assert len(captured_urls) == 1
    assert "content=true" in captured_urls[0]


def test_parse_returns_none_on_api_error(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    from job_finder.parser import greenhouse

    def mock_get(url, **kwargs):
        raise Exception("Connection error")

    monkeypatch.setattr("job_finder.parser.greenhouse.requests.get", mock_get)

    raw = {
        "url": "https://boards.greenhouse.io/acme/jobs/12345",
        "title": "", "snippet": "", "ats_type": "greenhouse", "url_hash": "",
    }
    assert greenhouse.parse(raw) is None


def test_parse_returns_none_for_non_matching_url(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    from job_finder.parser import greenhouse

    raw = {"url": "https://example.com/job/123", "title": "", "snippet": "", "ats_type": "greenhouse", "url_hash": ""}
    assert greenhouse.parse(raw) is None
