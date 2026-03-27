"""Tests for Stage 4.25: required_skills filter in job_finder/orchestrator.py"""

import sys
import pytest
from unittest.mock import MagicMock, patch


def _make_job(title="Senior Salesforce Developer", description="", url="https://example.com/job/1"):
    return {
        "title": title,
        "description": description,
        "company": "Acme Corp",
        "url": url,
        "url_hash": "abc123",
        "ats_type": "generic",
        "score": 0,
        "location": "Remote",
        "posted_at": None,
    }


def _run_orchestrator_with_jobs(parsed_jobs, required_skills=None, bonus_skills=None):
    """
    Patch the pipeline so only Stage 4.25 (skills filter) executes.
    Returns the summary dict.
    """
    sys.modules.pop("job_finder.config", None)
    sys.modules.pop("job_finder.orchestrator", None)

    env_patch = {
        "SERPER_API_KEY": "x", "ANTHROPIC_API_KEY": "x",
        "SF_USERNAME": "x", "SF_PASSWORD": "x", "SF_SECURITY_TOKEN": "x",
        "PG_DBNAME": "x", "PG_USER": "x", "PG_PASSWORD": "x",
        "DEFAULT_KEYWORDS": "Salesforce Developer",
        "LOCATION_PREFERENCE": "Remote",
        "SENIORITY_TARGETS": "senior",
        "MIN_ANNUAL_SALARY": "0",
    }

    with patch.dict("os.environ", env_patch):
        # Patch external dependencies
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        with patch("job_finder.db.connect", return_value=mock_conn), \
             patch("job_finder.db.insert_job_lead", return_value=1), \
             patch("job_finder.db.mark_skipped"), \
             patch("job_finder.search.google_cse.search_all_ats", return_value=[
                 {"url": j["url"], "title": j["title"]} for j in parsed_jobs
             ]), \
             patch("job_finder.deduplicator.is_duplicate", return_value=False), \
             patch("job_finder.deduplicator.hash_url", side_effect=lambda u: u), \
             patch("job_finder.parser.generic.can_parse", return_value=True), \
             patch("job_finder.parser.generic.parse", side_effect=lambda raw: next(
                 ({**j, "url_hash": j["url"]} for j in parsed_jobs if j["url"] == raw["url"]), None
             )), \
             patch("job_finder.parser.greenhouse.can_parse", return_value=False), \
             patch("job_finder.parser.lever.can_parse", return_value=False):

            from job_finder import orchestrator
            return orchestrator.run(
                keywords="Salesforce Developer",
                limit=10,
                dry_run=True,
                required_skills=required_skills,
                bonus_skills=bonus_skills,
            )


class TestRequiredSkillsFilter:
    def test_no_required_skills_passes_all_jobs(self):
        jobs = [
            _make_job(description="Project Manager role", url="https://example.com/1"),
            _make_job(description="Apex developer role", url="https://example.com/2"),
        ]
        summary = _run_orchestrator_with_jobs(jobs, required_skills=None)
        assert summary["skills_filtered"] == 0
        assert summary["parsed"] == 2

    def test_empty_required_skills_passes_all_jobs(self):
        jobs = [
            _make_job(description="Project Manager role", url="https://example.com/1"),
            _make_job(description="Apex developer role", url="https://example.com/2"),
        ]
        summary = _run_orchestrator_with_jobs(jobs, required_skills=[])
        assert summary["skills_filtered"] == 0
        assert summary["parsed"] == 2

    def test_required_skill_drops_non_matching_jobs(self):
        jobs = [
            _make_job(description="Must know Apex and SOQL.", url="https://example.com/1"),
            _make_job(description="Project Manager role, no technical skills.", url="https://example.com/2"),
        ]
        summary = _run_orchestrator_with_jobs(jobs, required_skills=["Apex"])
        assert summary["skills_filtered"] == 1
        # qualified + skipped = passed jobs (1 passed the filter)
        assert summary["qualified"] + summary["skipped"] == 1

    def test_any_of_logic_passes_job_with_one_matching_skill(self):
        jobs = [
            _make_job(description="Experience with SOQL required.", url="https://example.com/1"),
        ]
        # required_skills is any-of — SOQL matches so job passes
        summary = _run_orchestrator_with_jobs(jobs, required_skills=["Apex", "SOQL", "LWC"])
        assert summary["skills_filtered"] == 0

    def test_job_with_none_of_required_skills_is_dropped(self):
        jobs = [
            _make_job(description="Salesforce Admin certification required.", url="https://example.com/1"),
        ]
        summary = _run_orchestrator_with_jobs(jobs, required_skills=["Apex", "SOQL", "LWC"])
        assert summary["skills_filtered"] == 1

    def test_skills_filter_is_case_insensitive(self):
        jobs = [
            _make_job(description="Must have APEX experience.", url="https://example.com/1"),
        ]
        # Token is lowercase in filter, uppercase in description
        summary = _run_orchestrator_with_jobs(jobs, required_skills=["apex"])
        assert summary["skills_filtered"] == 0

    def test_multiple_jobs_filtered_counts_correctly(self):
        jobs = [
            _make_job(description="Apex and LWC developer.", url="https://example.com/1"),
            _make_job(description="Salesforce Admin no code.", url="https://example.com/2"),
            _make_job(description="PM role, business analyst.", url="https://example.com/3"),
            _make_job(description="SOQL query optimization.", url="https://example.com/4"),
        ]
        summary = _run_orchestrator_with_jobs(jobs, required_skills=["Apex", "SOQL", "LWC"])
        # Jobs 1 (Apex, LWC) and 4 (SOQL) pass; jobs 2 and 3 are filtered
        assert summary["skills_filtered"] == 2
        assert summary["qualified"] + summary["skipped"] == 2
