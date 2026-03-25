"""Tests for job_finder/enrichment.py"""

import sys
import json
import pytest


def _set_env(monkeypatch):
    for k, v in {
        "GOOGLE_API_KEY": "x", "GOOGLE_CSE_ID": "x", "ANTHROPIC_API_KEY": "x",
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
    """Build a mock anthropic.Anthropic() client that returns result_dict as JSON text."""
    class MockContent:
        text = json.dumps(result_dict)

    class MockResponse:
        content = [MockContent()]

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
