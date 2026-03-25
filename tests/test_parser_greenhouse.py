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
    "pay_input_ranges": [
        {"min_cents": 8000000, "max_cents": 12000000, "currency_type": "USD",
         "title": "Base Salary"}
    ],
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


def test_parse_extracts_salary_from_pay_input_ranges(monkeypatch):
    """pay_input_ranges amounts are in cents — must divide by 100."""
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    from job_finder.parser import greenhouse

    monkeypatch.setattr("job_finder.parser.greenhouse.requests.get", lambda *a, **kw: type("R", (), {
        "raise_for_status": lambda self: None,
        "json": lambda self: GREENHOUSE_RESPONSE,
    })())

    raw = {"url": "https://boards.greenhouse.io/acme/jobs/12345",
           "title": "", "snippet": "", "ats_type": "greenhouse", "url_hash": ""}
    result = greenhouse.parse(raw)

    assert result["annual_salary_min"] == 80000.0
    assert result["annual_salary_max"] == 120000.0
    assert result["salary_range_text"] == "$80k-$120k/yr"
    assert result["salary_type"] == "annual"


def test_parse_salary_none_when_pay_ranges_absent(monkeypatch):
    """If pay_input_ranges is absent, all salary fields should be None."""
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    from job_finder.parser import greenhouse

    response_no_salary = {k: v for k, v in GREENHOUSE_RESPONSE.items() if k != "pay_input_ranges"}
    monkeypatch.setattr("job_finder.parser.greenhouse.requests.get", lambda *a, **kw: type("R", (), {
        "raise_for_status": lambda self: None,
        "json": lambda self: response_no_salary,
    })())

    raw = {"url": "https://boards.greenhouse.io/acme/jobs/12345",
           "title": "", "snippet": "", "ats_type": "greenhouse", "url_hash": ""}
    result = greenhouse.parse(raw)

    assert result["annual_salary_min"] is None
    assert result["annual_salary_max"] is None


def test_parse_recruiter_always_none_for_greenhouse(monkeypatch):
    """Greenhouse public API does not expose recruiter info — always None."""
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    from job_finder.parser import greenhouse

    monkeypatch.setattr("job_finder.parser.greenhouse.requests.get", lambda *a, **kw: type("R", (), {
        "raise_for_status": lambda self: None,
        "json": lambda self: GREENHOUSE_RESPONSE,
    })())

    raw = {"url": "https://boards.greenhouse.io/acme/jobs/12345",
           "title": "", "snippet": "", "ats_type": "greenhouse", "url_hash": ""}
    result = greenhouse.parse(raw)

    assert result["recruiter_name"] is None
    assert result["recruiter_email"] is None


def test_parse_appends_pay_transparency_param(monkeypatch):
    """API URL must include &pay_transparency=true to get salary data."""
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

    raw = {"url": "https://boards.greenhouse.io/acme/jobs/12345",
           "title": "", "snippet": "", "ats_type": "greenhouse", "url_hash": ""}
    greenhouse.parse(raw)

    assert len(captured_urls) == 1
    assert "pay_transparency=true" in captured_urls[0]
