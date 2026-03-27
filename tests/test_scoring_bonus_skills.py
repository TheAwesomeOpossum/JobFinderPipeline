"""Tests for Signal 6: bonus_skills scoring in job_finder/scoring.py"""

import sys
import pytest


def _set_env(monkeypatch):
    for k, v in {
        "SERPER_API_KEY": "x", "ANTHROPIC_API_KEY": "x",
        "SF_USERNAME": "x", "SF_PASSWORD": "x", "SF_SECURITY_TOKEN": "x",
        "PG_DBNAME": "x", "PG_USER": "x", "PG_PASSWORD": "x",
        "DEFAULT_KEYWORDS": "Salesforce Developer",
        "LOCATION_PREFERENCE": "Remote",
        "SENIORITY_TARGETS": "senior",
    }.items():
        monkeypatch.setenv(k, v)


def _fresh_score(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    sys.modules.pop("job_finder.scoring", None)
    from job_finder.scoring import score
    return score


def _job(description=""):
    return {"title": "Senior Salesforce Developer", "description": description, "location": "Remote", "score": 0}


def test_no_bonus_skills_no_change(monkeypatch):
    score = _fresh_score(monkeypatch)
    job = _job("We need Apex and LWC skills.")
    base = score(job)
    job2 = _job("We need Apex and LWC skills.")
    boosted = score(job2, bonus_skills=None)
    assert base == boosted


def test_single_bonus_skill_match_adds_5(monkeypatch):
    score = _fresh_score(monkeypatch)
    base_job = _job("We need Apex skills.")
    bonus_job = _job("We need Apex skills.")
    base = score(base_job)
    boosted = score(bonus_job, bonus_skills=["Apex"])
    assert boosted == base + 5


def test_two_bonus_skill_matches_add_10(monkeypatch):
    score = _fresh_score(monkeypatch)
    base_job = _job("We need Apex and SOQL.")
    bonus_job = _job("We need Apex and SOQL.")
    base = score(base_job)
    boosted = score(bonus_job, bonus_skills=["Apex", "SOQL"])
    assert boosted == base + 10


def test_four_bonus_skill_matches_caps_at_20(monkeypatch):
    score = _fresh_score(monkeypatch)
    desc = "Experience with Apex, SOQL, LWC, and CPQ required."
    base_job = _job(desc)
    bonus_job = _job(desc)
    base = score(base_job)
    # 4 matches * 5 = 20 — exactly at cap; overall score still capped at 100
    boosted = score(bonus_job, bonus_skills=["Apex", "SOQL", "LWC", "CPQ"])
    assert boosted == min(base + 20, 100)


def test_five_bonus_skill_matches_still_capped_at_20(monkeypatch):
    score = _fresh_score(monkeypatch)
    desc = "Must know apex, soql, lwc, cpq, and aura frameworks."
    base_job = _job(desc)
    bonus_job = _job(desc)
    base = score(base_job)
    # 5 matches: still max +20; overall score still capped at 100
    boosted = score(bonus_job, bonus_skills=["Apex", "SOQL", "LWC", "CPQ", "Aura"])
    assert boosted == min(base + 20, 100)


def test_bonus_skill_match_is_case_insensitive(monkeypatch):
    score = _fresh_score(monkeypatch)
    base_job = _job("APEX experience required.")
    bonus_job = _job("APEX experience required.")
    base = score(base_job)
    boosted = score(bonus_job, bonus_skills=["apex"])
    assert boosted == base + 5


def test_bonus_skill_not_in_description_adds_nothing(monkeypatch):
    score = _fresh_score(monkeypatch)
    base_job = _job("Python and Django experience.")
    bonus_job = _job("Python and Django experience.")
    base = score(base_job)
    boosted = score(bonus_job, bonus_skills=["Apex", "SOQL"])
    assert boosted == base


def test_bonus_skills_empty_list_adds_nothing(monkeypatch):
    score = _fresh_score(monkeypatch)
    base_job = _job("Apex and SOQL required.")
    bonus_job = _job("Apex and SOQL required.")
    base = score(base_job)
    boosted = score(bonus_job, bonus_skills=[])
    assert boosted == base


def test_score_stays_within_100(monkeypatch):
    score = _fresh_score(monkeypatch)
    from datetime import date
    today = date.today().isoformat()
    job = {
        "title": "Senior Salesforce Developer",
        "description": "salesforce developer apex soql lwc cpq aura remote united states senior",
        "location": "Remote",
        "posted_at": today,
        "score": 0,
    }
    result = score(job, bonus_skills=["Apex", "SOQL", "LWC", "CPQ"])
    assert result <= 100
