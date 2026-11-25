"""Tests for orchestrator.push_url() — single-URL push mode."""

import sys
import pytest
from unittest.mock import MagicMock, patch


_FAKE_JOB = {
    "url": "https://www.linkedin.com/jobs/view/12345",
    "url_hash": "abc123",
    "title": "Senior Salesforce Developer",
    "company": "Acme Corp",
    "description": "Build cool stuff with Apex and LWC.",
    "description_html": "<p>Build cool stuff</p>",
    "location": "Remote",
    "department": None,
    "posted_at": "2026-04-01",
    "ats_type": "linkedin",
    "score": 0,
    "mission": None,
    "core_values": [],
    "hq_address": None,
    "website_url": None,
    "annual_salary_min": None,
    "annual_salary_max": None,
    "hourly_rate_min": None,
    "hourly_rate_max": None,
    "salary_range_text": None,
    "salary_type": None,
    "sf_job_app_id": None,
    "sf_account_id": None,
    "recruiter_name": None,
    "recruiter_email": None,
    "recruiter_is_internal": None,
    "recruiter_firm_name": None,
    "recruiter_firm_mission": None,
    "recruiter_firm_values": [],
    "recruiter_firm_website": None,
    "recruiter_firm_hq": None,
    "sf_recruiter_account_id": None,
    "sf_recruiter_contact_id": None,
}

_ENV = {
    "SERPER_API_KEY": "x", "ANTHROPIC_API_KEY": "x",
    "SF_USERNAME": "x", "SF_PASSWORD": "x", "SF_SECURITY_TOKEN": "x",
    "PG_DBNAME": "x", "PG_USER": "x", "PG_PASSWORD": "x",
    "DEFAULT_KEYWORDS": "Salesforce Developer",
    "LOCATION_PREFERENCE": "Remote",
    "SENIORITY_TARGETS": "senior",
    "MIN_ANNUAL_SALARY": "0",
}


def _push_url(url, dry_run=False, parse_return=None, write_job_return=("JA001", "ACC001", None),
              write_job_side_effect=None):
    """Run push_url with all external deps mocked. Returns (result, mocks_dict)."""
    # Clear cached modules so patches take effect on fresh imports
    for mod in list(sys.modules):
        if mod.startswith("job_finder"):
            sys.modules.pop(mod, None)

    mock_conn = MagicMock()

    with patch.dict("os.environ", _ENV), \
         patch("job_finder.db.connect", return_value=mock_conn), \
         patch("job_finder.db.insert_job_lead", return_value=1) as mock_insert, \
         patch("job_finder.db.mark_pushed") as mock_pushed, \
         patch("job_finder.db.mark_failed") as mock_failed, \
         patch("job_finder.sf_writer.connect", return_value=MagicMock()) as mock_sf_connect, \
         patch("job_finder.sf_writer.write_job",
               return_value=write_job_return,
               side_effect=write_job_side_effect) as mock_write, \
         patch("job_finder.enrichment.enrich_jobs", side_effect=lambda jobs: jobs) as mock_enrich, \
         patch("job_finder.enrichment.enrich_recruiter_jobs", side_effect=lambda jobs: jobs), \
         patch("job_finder.parser.linkedin.can_parse", return_value=True), \
         patch("job_finder.parser.linkedin.parse", return_value=parse_return), \
         patch("job_finder.parser.greenhouse.can_parse", return_value=False), \
         patch("job_finder.parser.lever.can_parse", return_value=False), \
         patch("job_finder.deduplicator.hash_url", return_value="abc123"):

        from job_finder import orchestrator
        result = orchestrator.push_url(url, dry_run=dry_run)
        return result, {
            "insert": mock_insert,
            "pushed": mock_pushed,
            "failed": mock_failed,
            "sf_connect": mock_sf_connect,
            "write": mock_write,
            "enrich": mock_enrich,
        }


class TestPushUrl:

    def test_success(self):
        result, mocks = _push_url(
            "https://www.linkedin.com/jobs/view/12345",
            parse_return=dict(_FAKE_JOB),
        )
        assert result["success"] is True
        assert result["sf_job_app_id"] == "JA001"
        assert result["sf_account_id"] == "ACC001"
        mocks["insert"].assert_called_once()
        mocks["pushed"].assert_called_once()
        mocks["enrich"].assert_called_once()
        mocks["write"].assert_called_once()

    def test_dry_run_skips_sf(self):
        result, mocks = _push_url(
            "https://www.linkedin.com/jobs/view/12345",
            parse_return=dict(_FAKE_JOB),
            dry_run=True,
        )
        assert result["success"] is True
        assert result["dry_run"] is True
        mocks["sf_connect"].assert_not_called()
        mocks["enrich"].assert_not_called()
        mocks["write"].assert_not_called()
        mocks["insert"].assert_called_once()

    def test_parse_failure(self):
        result, mocks = _push_url(
            "https://www.linkedin.com/jobs/view/99999",
            parse_return=None,
        )
        assert result["success"] is False
        assert "parse" in result["error"].lower()
        mocks["write"].assert_not_called()

    def test_sf_failure_marks_failed(self):
        result, mocks = _push_url(
            "https://www.linkedin.com/jobs/view/12345",
            parse_return=dict(_FAKE_JOB),
            write_job_side_effect=Exception("SF API error"),
        )
        assert result["success"] is False
        assert "SF API error" in result["error"]
        mocks["failed"].assert_called_once()

    def test_sets_manual_profile(self):
        result, mocks = _push_url(
            "https://www.linkedin.com/jobs/view/12345",
            parse_return=dict(_FAKE_JOB),
        )
        # Verify mark_pushed was called with search_profile="manual"
        kwargs = mocks["pushed"].call_args[1] if mocks["pushed"].call_args[1] else {}
        positional = mocks["pushed"].call_args[0] if mocks["pushed"].call_args[0] else ()
        assert kwargs.get("search_profile") == "manual" or "manual" in str(positional)
