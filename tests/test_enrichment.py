"""Tests for job_finder/enrichment.py"""

import sys
import json
import pytest


def _set_env(monkeypatch):
    for k, v in {
        "SERPER_API_KEY": "x", "ANTHROPIC_API_KEY": "x",
        "SF_USERNAME": "x", "SF_PASSWORD": "x", "SF_SECURITY_TOKEN": "x",
        "PG_DBNAME": "x", "PG_USER": "x", "PG_PASSWORD": "x",
    }.items():
        monkeypatch.setenv(k, v)


ENRICHMENT_RESULT = {
    "mission": "To make software better.",
    "core_values": ["Quality", "Integrity"],
    "website_url": "https://acmecorp.com",
    "hq_address": {"street": "123 Main St", "city": "San Francisco", "state": "CA", "postal_code": "94105", "country": "US"},
}


def _make_mock_anthropic(result_dict):
    """Build a mock anthropic.Anthropic() client that returns result_dict via tool_use block."""
    class MockToolBlock:
        type = "tool_use"
        input = result_dict

    class MockResponse:
        content = [MockToolBlock()]

    class MockMessages:
        def create(self, **kwargs):
            return MockResponse()

    class MockClient:
        messages = MockMessages()

    return MockClient()


def test_enrich_jobs_one_call_per_company(monkeypatch):
    """enrich_jobs must call enrich_company once per unique company, not once per job."""
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    sys.modules.pop("job_finder.enrichment", None)
    from job_finder import enrichment

    call_count = {"n": 0}

    def mock_enrich_company(company_name):
        call_count["n"] += 1
        return dict(ENRICHMENT_RESULT)

    monkeypatch.setattr(enrichment, "enrich_company", mock_enrich_company)

    jobs = [
        {"company": "Acme Corp", "title": "SWE", "description": "", "url": "https://a.com", "url_hash": "h1", "score": 0,
         "location": "", "department": None, "posted_at": None, "ats_type": "greenhouse",
         "description_html": "", "snippet": "", "mission": None, "core_values": [], "hq_address": None, "website_url": None,
         "sf_job_app_id": None, "sf_account_id": None},
        {"company": "Acme Corp", "title": "PM", "description": "", "url": "https://b.com", "url_hash": "h2", "score": 0,
         "location": "", "department": None, "posted_at": None, "ats_type": "greenhouse",
         "description_html": "", "snippet": "", "mission": None, "core_values": [], "hq_address": None, "website_url": None,
         "sf_job_app_id": None, "sf_account_id": None},
        {"company": "Beta Inc", "title": "DevOps", "description": "", "url": "https://c.com", "url_hash": "h3", "score": 0,
         "location": "", "department": None, "posted_at": None, "ats_type": "lever",
         "description_html": "", "snippet": "", "mission": None, "core_values": [], "hq_address": None, "website_url": None,
         "sf_job_app_id": None, "sf_account_id": None},
    ]

    enrichment.enrich_jobs(jobs)

    # 2 unique companies → 2 calls, not 3
    assert call_count["n"] == 2


def test_enrich_jobs_merges_into_job(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    sys.modules.pop("job_finder.enrichment", None)
    from job_finder import enrichment

    monkeypatch.setattr(enrichment, "enrich_company", lambda name: dict(ENRICHMENT_RESULT))

    job = {
        "company": "Acme Corp", "title": "SWE", "description": "", "url": "https://a.com",
        "url_hash": "h1", "score": 0, "location": "", "department": None, "posted_at": None,
        "ats_type": "greenhouse", "description_html": "", "snippet": "",
        "mission": None, "core_values": [], "hq_address": None, "website_url": None,
        "sf_job_app_id": None, "sf_account_id": None,
    }
    enrichment.enrich_jobs([job])

    assert job["mission"] == "To make software better."
    assert job["website_url"] == "https://acmecorp.com"
    assert "Quality" in job["core_values"]


def test_enrich_company_returns_empty_on_exception(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    sys.modules.pop("job_finder.enrichment", None)
    from job_finder import enrichment

    class BrokenClient:
        class messages:
            @staticmethod
            def create(**kwargs):
                raise RuntimeError("API down")

    monkeypatch.setattr("job_finder.enrichment.anthropic.Anthropic", lambda **kw: BrokenClient())

    result = enrichment.enrich_company("SomeCo")
    assert result["mission"] is None
    assert result["core_values"] == []
    assert result["website_url"] is None
    assert result["hq_address"] is None


# ---------------------------------------------------------------------------
# determine_recruiter_context
# ---------------------------------------------------------------------------

RECRUITER_INTERNAL_RESULT = {
    "is_internal": True,
    "confidence": "high",
    "recruiter_firm_name": None,
}

RECRUITER_EXTERNAL_RESULT = {
    "is_internal": False,
    "confidence": "high",
    "recruiter_firm_name": "TEKsystems",
}


def _make_mock_anthropic_recruiter(result_dict):
    class MockToolBlock:
        type = "tool_use"
        input = result_dict
    class MockResponse:
        content = [MockToolBlock()]
    class MockMessages:
        def create(self, **kwargs):
            return MockResponse()
    class MockClient:
        messages = MockMessages()
    return MockClient()


def test_determine_recruiter_context_internal(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    sys.modules.pop("job_finder.enrichment", None)
    from job_finder import enrichment

    monkeypatch.setattr(
        "job_finder.enrichment.anthropic.Anthropic",
        lambda **kw: _make_mock_anthropic_recruiter(RECRUITER_INTERNAL_RESULT)
    )

    result = enrichment.determine_recruiter_context("Jane Smith", "jane@acme.com", "Acme Corp")

    assert result["is_internal"] is True
    assert result["recruiter_firm_name"] is None


def test_determine_recruiter_context_external(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    sys.modules.pop("job_finder.enrichment", None)
    from job_finder import enrichment

    monkeypatch.setattr(
        "job_finder.enrichment.anthropic.Anthropic",
        lambda **kw: _make_mock_anthropic_recruiter(RECRUITER_EXTERNAL_RESULT)
    )

    result = enrichment.determine_recruiter_context("Bob Recruiter", None, "Acme Corp")

    assert result["is_internal"] is False
    assert result["recruiter_firm_name"] == "TEKsystems"


def test_determine_recruiter_context_defaults_to_internal_on_failure(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    sys.modules.pop("job_finder.enrichment", None)
    from job_finder import enrichment

    class BrokenClient:
        class messages:
            @staticmethod
            def create(**kwargs):
                raise RuntimeError("API down")

    monkeypatch.setattr("job_finder.enrichment.anthropic.Anthropic", lambda **kw: BrokenClient())

    result = enrichment.determine_recruiter_context("Jane Smith", None, "Acme Corp")

    assert result["is_internal"] is True
    assert result["recruiter_firm_name"] is None


def test_enrich_recruiter_jobs_skips_jobs_without_recruiter(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    sys.modules.pop("job_finder.enrichment", None)
    from job_finder import enrichment

    call_count = {"n": 0}
    def mock_ctx(name, email, company):
        call_count["n"] += 1
        return RECRUITER_INTERNAL_RESULT

    monkeypatch.setattr(enrichment, "determine_recruiter_context", mock_ctx)

    jobs = [
        {"company": "Acme", "recruiter_name": None, "recruiter_email": None},
        {"company": "Acme", "recruiter_name": "Jane", "recruiter_email": None,
         "recruiter_is_internal": None, "recruiter_firm_name": None},
    ]
    enrichment.enrich_recruiter_jobs(jobs)

    assert call_count["n"] == 1  # only the job with recruiter_name


def test_enrich_recruiter_jobs_external_triggers_firm_enrichment(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    sys.modules.pop("job_finder.enrichment", None)
    from job_finder import enrichment

    monkeypatch.setattr(enrichment, "determine_recruiter_context",
                        lambda n, e, c: RECRUITER_EXTERNAL_RESULT)
    firm_calls = {"n": 0}
    def mock_enrich(firm_name):
        firm_calls["n"] += 1
        return dict(ENRICHMENT_RESULT)
    monkeypatch.setattr(enrichment, "enrich_company", mock_enrich)

    job = {"company": "Acme", "recruiter_name": "Bob", "recruiter_email": None,
           "recruiter_is_internal": None, "recruiter_firm_name": None,
           "recruiter_firm_mission": None, "recruiter_firm_values": [],
           "recruiter_firm_website": None, "recruiter_firm_hq": None}
    enrichment.enrich_recruiter_jobs([job])

    assert firm_calls["n"] == 1
    assert job["recruiter_firm_name"] == "TEKsystems"
    assert job["recruiter_is_internal"] is False
