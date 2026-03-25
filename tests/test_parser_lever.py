"""Tests for job_finder/parser/lever.py"""

import sys
import pytest

LEVER_RESPONSE = {
    "id": "abc-123",
    "text": "Senior Software Engineer",
    "company": "Lever Inc",
    "categories": {
        "location": "Remote",
        "department": "Engineering",
    },
    "descriptionPlain": "We are looking for a senior software engineer.",
    "description": "<p>We are looking for a senior software engineer.</p>",
    "createdAt": 1742860800000,  # 2025-03-25 in ms epoch
    "hiring_managers": [
        {
            "id": "hm-001",
            "name": "Alice Johnson",
            "email": "alice@leverinc.com",
            "username": "alice.johnson",
            "accessRole": "team_member",
            "photo": "https://photos.example.com/alice.jpg",
        }
    ],
    "salary": {
        "min": 80000,
        "max": 120000,
        "currency": "USD",
        "interval": "per-year",
    },
}


def _set_env(monkeypatch):
    for k, v in {
        "GOOGLE_API_KEY": "x", "GOOGLE_CSE_ID": "x", "ANTHROPIC_API_KEY": "x",
        "SF_USERNAME": "x", "SF_PASSWORD": "x", "SF_SECURITY_TOKEN": "x",
        "PG_DBNAME": "x", "PG_USER": "x", "PG_PASSWORD": "x",
    }.items():
        monkeypatch.setenv(k, v)


def test_can_parse_lever_url(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    from job_finder.parser.lever import can_parse
    assert can_parse("https://jobs.lever.co/acme/abc-123") is True
    assert can_parse("https://boards.greenhouse.io/acme/jobs/123") is False


def test_parse_created_at_milliseconds(monkeypatch):
    """createdAt is ms epoch — must divide by 1000 to get correct date."""
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    from job_finder.parser import lever

    mock_response = type("R", (), {
        "raise_for_status": lambda self: None,
        "json": lambda self: LEVER_RESPONSE,
    })()

    monkeypatch.setattr("job_finder.parser.lever.requests.get", lambda *a, **kw: mock_response)

    raw = {
        "url": "https://jobs.lever.co/acme/abc-123",
        "title": "Senior SE", "snippet": "", "ats_type": "lever", "url_hash": "",
    }
    result = lever.parse(raw)

    assert result is not None
    # posted_at should be a valid date string (not year ~55000)
    year = int(result["posted_at"][:4])
    assert 2020 <= year <= 2030, f"Unexpected year in posted_at: {result['posted_at']}"


def test_parse_appends_mode_json(monkeypatch):
    """Must include ?mode=json — without it the endpoint returns HTML."""
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    from job_finder.parser import lever

    captured_urls = []

    def mock_get(url, **kwargs):
        captured_urls.append(url)
        return type("R", (), {
            "raise_for_status": lambda self: None,
            "json": lambda self: LEVER_RESPONSE,
        })()

    monkeypatch.setattr("job_finder.parser.lever.requests.get", mock_get)

    raw = {
        "url": "https://jobs.lever.co/acme/abc-123",
        "title": "", "snippet": "", "ats_type": "lever", "url_hash": "",
    }
    lever.parse(raw)

    assert len(captured_urls) == 1
    assert "mode=json" in captured_urls[0]


def test_parse_maps_fields(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    from job_finder.parser import lever

    mock_response = type("R", (), {
        "raise_for_status": lambda self: None,
        "json": lambda self: LEVER_RESPONSE,
    })()

    monkeypatch.setattr("job_finder.parser.lever.requests.get", lambda *a, **kw: mock_response)

    raw = {
        "url": "https://jobs.lever.co/acme/abc-123",
        "title": "Senior SE", "snippet": "", "ats_type": "lever", "url_hash": "",
    }
    result = lever.parse(raw)

    assert result["title"] == "Senior Software Engineer"
    assert result["location"] == "Remote"
    assert result["department"] == "Engineering"
    assert "senior software engineer" in result["description"].lower()


def test_parse_returns_none_on_api_error(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    from job_finder.parser import lever

    monkeypatch.setattr("job_finder.parser.lever.requests.get", lambda *a, **kw: (_ for _ in ()).throw(Exception("fail")))

    raw = {"url": "https://jobs.lever.co/acme/abc-123", "title": "", "snippet": "", "ats_type": "lever", "url_hash": ""}
    assert lever.parse(raw) is None


def test_parse_missing_created_at_gives_none_posted_at(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    from job_finder.parser import lever

    resp_no_date = dict(LEVER_RESPONSE)
    del resp_no_date["createdAt"]

    mock_response = type("R", (), {
        "raise_for_status": lambda self: None,
        "json": lambda self: resp_no_date,
    })()

    monkeypatch.setattr("job_finder.parser.lever.requests.get", lambda *a, **kw: mock_response)

    raw = {"url": "https://jobs.lever.co/acme/abc-123", "title": "", "snippet": "", "ats_type": "lever", "url_hash": ""}
    result = lever.parse(raw)
    assert result is not None
    assert result["posted_at"] is None


def test_parse_extracts_hiring_manager_as_recruiter(monkeypatch):
    """hiring_managers[0] should populate recruiter_name and recruiter_email."""
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    from job_finder.parser import lever

    mock_response = type("R", (), {
        "raise_for_status": lambda self: None,
        "json": lambda self: LEVER_RESPONSE,
    })()

    monkeypatch.setattr("job_finder.parser.lever.requests.get", lambda *a, **kw: mock_response)

    raw = {"url": "https://jobs.lever.co/acme/abc-123", "title": "", "snippet": "", "ats_type": "lever", "url_hash": ""}
    result = lever.parse(raw)

    assert result["recruiter_name"] == "Alice Johnson"
    assert result["recruiter_email"] == "alice@leverinc.com"
    assert result["recruiter_is_internal"] is None  # not yet determined by enrichment


def test_parse_recruiter_none_when_no_hiring_managers(monkeypatch):
    """When hiring_managers is absent or empty, recruiter fields are None."""
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    from job_finder.parser import lever

    resp_no_hm = {k: v for k, v in LEVER_RESPONSE.items() if k != "hiring_managers"}
    monkeypatch.setattr("job_finder.parser.lever.requests.get", lambda *a, **kw: type("R", (), {
        "raise_for_status": lambda self: None,
        "json": lambda self: resp_no_hm,
    })())

    raw = {"url": "https://jobs.lever.co/acme/abc-123", "title": "", "snippet": "", "ats_type": "lever", "url_hash": ""}
    result = lever.parse(raw)

    assert result["recruiter_name"] is None
    assert result["recruiter_email"] is None


def test_parse_extracts_annual_salary(monkeypatch):
    """salary object with per-year interval → annual_salary_min/max."""
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    from job_finder.parser import lever

    monkeypatch.setattr("job_finder.parser.lever.requests.get", lambda *a, **kw: type("R", (), {
        "raise_for_status": lambda self: None,
        "json": lambda self: LEVER_RESPONSE,
    })())

    raw = {"url": "https://jobs.lever.co/acme/abc-123", "title": "", "snippet": "", "ats_type": "lever", "url_hash": ""}
    result = lever.parse(raw)

    assert result["annual_salary_min"] == 80000.0
    assert result["annual_salary_max"] == 120000.0
    assert result["salary_type"] == "annual"
    assert result["salary_range_text"] == "$80k-$120k/yr"


def test_parse_salary_none_when_salary_absent(monkeypatch):
    """When salary field is missing, all salary dict values should be None."""
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    from job_finder.parser import lever

    resp_no_salary = {k: v for k, v in LEVER_RESPONSE.items() if k != "salary"}
    monkeypatch.setattr("job_finder.parser.lever.requests.get", lambda *a, **kw: type("R", (), {
        "raise_for_status": lambda self: None,
        "json": lambda self: resp_no_salary,
    })())

    raw = {"url": "https://jobs.lever.co/acme/abc-123", "title": "", "snippet": "", "ats_type": "lever", "url_hash": ""}
    result = lever.parse(raw)

    assert result["annual_salary_min"] is None
    assert result["annual_salary_max"] is None
    assert result["salary_type"] is None


def test_parse_extracts_hourly_salary(monkeypatch):
    """salary with per-hour interval → hourly_rate_min/max."""
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    from job_finder.parser import lever

    hourly_response = dict(LEVER_RESPONSE)
    hourly_response["salary"] = {"min": 40, "max": 60, "currency": "USD", "interval": "per-hour"}

    monkeypatch.setattr("job_finder.parser.lever.requests.get", lambda *a, **kw: type("R", (), {
        "raise_for_status": lambda self: None,
        "json": lambda self: hourly_response,
    })())

    raw = {"url": "https://jobs.lever.co/acme/abc-123", "title": "", "snippet": "", "ats_type": "lever", "url_hash": ""}
    result = lever.parse(raw)

    assert result["hourly_rate_min"] == 40.0
    assert result["hourly_rate_max"] == 60.0
    assert result["salary_type"] == "hourly"
