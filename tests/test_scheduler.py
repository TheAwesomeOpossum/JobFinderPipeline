"""Tests for job_finder/scheduler.py"""

import sys


_FULL_SUMMARY = {
    "found": 5,
    "new": 3,
    "parsed": 3,
    "qualified": 2,
    "pushed": 2,
    "skipped": 1,
    "failed": 0,
}


def _set_env(monkeypatch):
    for k, v in {
        "GOOGLE_API_KEY": "x",
        "GOOGLE_CSE_ID": "x",
        "ANTHROPIC_API_KEY": "x",
        "SF_USERNAME": "x",
        "SF_PASSWORD": "x",
        "SF_SECURITY_TOKEN": "x",
        "PG_DBNAME": "x",
        "PG_USER": "x",
        "PG_PASSWORD": "x",
        "DEFAULT_KEYWORDS": "Software Developer,Software Engineer",
        "DAILY_LIMIT": "20",
    }.items():
        monkeypatch.setenv(k, v)


def _reload_scheduler(monkeypatch):
    _set_env(monkeypatch)
    for mod in ["job_finder.config", "job_finder.scheduler", "job_finder.notifications"]:
        sys.modules.pop(mod, None)


def test_run_job_calls_orchestrator_with_profile_values(monkeypatch):
    _reload_scheduler(monkeypatch)
    from job_finder import scheduler

    calls = []
    monkeypatch.setattr(
        scheduler.orchestrator,
        "run",
        lambda **kw: calls.append(kw) or dict(_FULL_SUMMARY),
    )
    monkeypatch.setattr(scheduler, "post_summary", lambda s: None)

    scheduler._run_job({"keywords": "Salesforce Developer", "limit": 10})

    assert len(calls) == 1
    assert calls[0]["keywords"] == "Salesforce Developer"
    assert calls[0]["limit"] == 10
    assert calls[0]["dry_run"] is False


def test_run_job_uses_config_defaults_when_profile_empty(monkeypatch):
    _reload_scheduler(monkeypatch)
    from job_finder import scheduler, config

    calls = []
    monkeypatch.setattr(
        scheduler.orchestrator,
        "run",
        lambda **kw: calls.append(kw) or dict(_FULL_SUMMARY),
    )
    monkeypatch.setattr(scheduler, "post_summary", lambda s: None)

    scheduler._run_job({})

    assert calls[0]["keywords"] == config.DEFAULT_KEYWORDS
    assert calls[0]["limit"] == config.DAILY_LIMIT
    assert calls[0]["dry_run"] is False


def test_run_job_calls_post_summary_after_success(monkeypatch):
    _reload_scheduler(monkeypatch)
    from job_finder import scheduler

    monkeypatch.setattr(
        scheduler.orchestrator,
        "run",
        lambda **kw: dict(_FULL_SUMMARY),
    )
    summaries = []
    monkeypatch.setattr(scheduler, "post_summary", lambda s: summaries.append(s))

    scheduler._run_job({"keywords": "Python", "limit": 5})

    assert len(summaries) == 1
    assert summaries[0]["pushed"] == 2
    assert summaries[0]["failed"] == 0


def test_run_job_does_not_crash_on_orchestrator_exception(monkeypatch):
    _reload_scheduler(monkeypatch)
    from job_finder import scheduler

    monkeypatch.setattr(
        scheduler.orchestrator,
        "run",
        lambda **kw: (_ for _ in ()).throw(Exception("DB down")),
    )
    monkeypatch.setattr(scheduler, "post_summary", lambda s: None)

    # Must not raise
    scheduler._run_job({})
