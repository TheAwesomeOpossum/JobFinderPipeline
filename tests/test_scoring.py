"""Tests for job_finder/scoring.py"""

import sys
from datetime import date, timedelta
import pytest


def _set_env(monkeypatch):
    for k, v in {
        "GOOGLE_API_KEY": "x", "GOOGLE_CSE_ID": "x", "ANTHROPIC_API_KEY": "x",
        "SF_USERNAME": "x", "SF_PASSWORD": "x", "SF_SECURITY_TOKEN": "x",
        "PG_DBNAME": "x", "PG_USER": "x", "PG_PASSWORD": "x",
        "DEFAULT_KEYWORDS": "Software Developer,Software Engineer",
        "LOCATION_PREFERENCE": "Remote",
        "SENIORITY_TARGETS": "mid,senior",
    }.items():
        monkeypatch.setenv(k, v)


def test_senior_remote_scores_higher_than_junior_onsite(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    sys.modules.pop("job_finder.scoring", None)
    from job_finder.scoring import score

    today = date.today().isoformat()

    senior = {
        "title": "Senior Software Engineer",
        "description": "We are looking for a senior software engineer.",
        "location": "Remote",
        "posted_at": today,
        "score": 0,
    }
    junior = {
        "title": "Junior Software Developer",
        "description": "Entry level position on-site.",
        "location": "San Francisco, CA",
        "posted_at": None,
        "score": 0,
    }

    senior_score = score(senior)
    junior_score = score(junior)
    assert senior_score > junior_score


def test_score_missing_posted_at_does_not_crash(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    sys.modules.pop("job_finder.scoring", None)
    from job_finder.scoring import score

    job = {
        "title": "Software Engineer",
        "description": "remote python",
        "location": "Remote",
        "posted_at": None,
        "score": 0,
    }
    result = score(job)
    assert 0 <= result <= 100


def test_score_clamped_to_0_100(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    sys.modules.pop("job_finder.scoring", None)
    from job_finder.scoring import score

    today = date.today().isoformat()
    job = {
        "title": "Senior Software Engineer",
        "description": "senior software engineer remote",
        "location": "Remote",
        "posted_at": today,
        "score": 0,
    }
    result = score(job)
    assert 0 <= result <= 100


def test_score_sets_job_score_field(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    sys.modules.pop("job_finder.scoring", None)
    from job_finder.scoring import score

    job = {"title": "Engineer", "description": "", "location": "", "posted_at": None, "score": 0}
    result = score(job)
    assert job["score"] == result


def test_score_recent_posting_adds_points(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    sys.modules.pop("job_finder.scoring", None)
    from job_finder.scoring import score

    today = date.today().isoformat()
    old_date = (date.today() - timedelta(days=10)).isoformat()

    job_recent = {
        "title": "Software Engineer", "description": "software engineer",
        "location": "Remote", "posted_at": today, "score": 0,
    }
    job_old = {
        "title": "Software Engineer", "description": "software engineer",
        "location": "Remote", "posted_at": old_date, "score": 0,
    }

    assert score(job_recent) > score(job_old)
