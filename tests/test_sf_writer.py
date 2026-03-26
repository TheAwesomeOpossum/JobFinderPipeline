"""Tests for job_finder/sf_writer.py"""

import sys
import pytest


def _set_env(monkeypatch):
    for k, v in {
        "SERPER_API_KEY": "x", "ANTHROPIC_API_KEY": "x",
        "SF_USERNAME": "x", "SF_PASSWORD": "x", "SF_SECURITY_TOKEN": "x",
        "PG_DBNAME": "x", "PG_USER": "x", "PG_PASSWORD": "x",
    }.items():
        monkeypatch.setenv(k, v)


def _make_job(**overrides):
    base = {
        "title": "Senior Software Engineer",
        "company": "Acme Corp",
        "description": "We are looking for a senior software engineer.",
        "description_html": "<p>We are looking for...</p>",
        "url": "https://boards.greenhouse.io/acme/jobs/12345",
        "url_hash": "abc123",
        "ats_type": "greenhouse",
        "location": "Remote",
        "department": "Engineering",
        "posted_at": "2026-03-25",
        "score": 80,
        "mission": "To do great things.",
        "core_values": ["Quality", "Integrity"],
        "hq_address": {"street": "123 Main", "city": "SF", "state": "CA", "postal_code": "94105", "country": "US"},
        "website_url": "https://acmecorp.com",
        "sf_job_app_id": None,
        "sf_account_id": None,
        # Recruiter
        "recruiter_name": None,
        "recruiter_email": None,
        "recruiter_is_internal": True,
        "recruiter_firm_name": None,
        "recruiter_firm_mission": None,
        "recruiter_firm_values": [],
        "recruiter_firm_website": None,
        "recruiter_firm_hq": None,
        "sf_recruiter_account_id": None,
        "sf_recruiter_contact_id": None,
        # Salary
        "annual_salary_min": None,
        "annual_salary_max": None,
        "hourly_rate_min": None,
        "hourly_rate_max": None,
        "salary_range_text": None,
        "salary_type": None,
    }
    base.update(overrides)
    return base


class MockSF:
    """Mock Salesforce client tracking calls."""

    def __init__(self, existing_account_id=None):
        self._existing_id = existing_account_id
        self.account_created = []
        self.account_updated = []
        self.job_app_created = []

    def query(self, soql):
        if self._existing_id:
            return {"totalSize": 1, "records": [{"Id": self._existing_id}]}
        return {"totalSize": 0, "records": []}

    class _Object:
        def __init__(self, created_id, tracker):
            self._id = created_id
            self._tracker = tracker

        def create(self, payload):
            self._tracker.append(payload)
            return {"id": self._id, "success": True, "errors": []}

        def update(self, record_id, payload):
            self._tracker.append((record_id, payload))
            return None

    @property
    def Account(self):
        return self._Object("new_account_id_001", self.account_created)

    @property
    def Job_Application__c(self):
        return self._Object("new_job_app_id_001", self.job_app_created)

    @property
    def Contact(self):
        return self._Object("new_contact_id_001", [])


def test_upsert_account_creates_new_when_not_found(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    sys.modules.pop("job_finder.sf_writer", None)
    from job_finder import sf_writer

    sf = MockSF(existing_account_id=None)
    job = _make_job()

    account_id = sf_writer.upsert_account(sf, job)

    assert account_id == "new_account_id_001"
    assert len(sf.account_created) == 1


def test_upsert_account_updates_existing(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    sys.modules.pop("job_finder.sf_writer", None)
    from job_finder import sf_writer

    sf = MockSF(existing_account_id="existing_account_001")
    job = _make_job()

    account_id = sf_writer.upsert_account(sf, job)

    assert account_id == "existing_account_001"
    # update was called (not create)
    assert len(sf.account_created) == 1  # MockSF._Object.update appends to tracker too
    # Confirm the update payload has the account id
    assert sf.account_created[0][0] == "existing_account_001"


def test_create_job_application_does_not_set_name(monkeypatch):
    """Name field must NOT be set — Salesforce trigger populates it."""
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    sys.modules.pop("job_finder.sf_writer", None)
    from job_finder import sf_writer

    sf = MockSF()
    job = _make_job()

    sf_writer.create_job_application(sf, job, "account_id_001")

    assert len(sf.job_app_created) == 1
    payload = sf.job_app_created[0]
    assert "Name" not in payload


def test_create_job_application_truncates_description(monkeypatch):
    """Job_Description__c must be ≤ 32768 chars."""
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    sys.modules.pop("job_finder.sf_writer", None)
    from job_finder import sf_writer

    sf = MockSF()
    job = _make_job(description="x" * 50000)

    sf_writer.create_job_application(sf, job, "account_id_001")

    payload = sf.job_app_created[0]
    assert len(payload["Job_Description__c"]) <= 32768


def test_write_job_returns_three_tuple(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    sys.modules.pop("job_finder.sf_writer", None)
    from job_finder import sf_writer

    sf = MockSF(existing_account_id=None)
    job = _make_job()

    result = sf_writer.write_job(sf, job)

    assert len(result) == 3
    job_app_id, account_id, _ = result
    assert job_app_id == "new_job_app_id_001"
    assert account_id == "new_account_id_001"


def test_upsert_account_escapes_single_quote_in_name(monkeypatch):
    """Company name with single quote must not break SOQL."""
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    sys.modules.pop("job_finder.sf_writer", None)
    from job_finder import sf_writer

    queries = []

    class QuoteTrackingSF(MockSF):
        def query(self, soql):
            queries.append(soql)
            return {"totalSize": 0, "records": []}

    sf = QuoteTrackingSF()
    job = _make_job(company="O'Reilly", website_url=None)

    sf_writer.upsert_account(sf, job)

    assert len(queries) == 1
    # Single quote escaped in the SOQL
    assert "O\\'Reilly" in queries[0]
