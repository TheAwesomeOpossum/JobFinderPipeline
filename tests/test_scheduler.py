"""Tests for job_finder/scheduler.py"""

import sys


_FULL_SUMMARY = {
    "found": 5,
    "new": 3,
    "parsed": 3,
    "skills_filtered": 0,
    "salary_filtered": 0,
    "qualified": 2,
    "pushed": 2,
    "skipped": 1,
    "failed": 0,
}


def _set_env(monkeypatch):
    for k, v in {
        "SERPER_API_KEY": "x",
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

    scheduler._run_job({"keywords": "Salesforce Developer", "limit": 10}, "profiles/salesforce_dev.yaml")

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

    scheduler._run_job({}, "profiles/default.yaml")

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

    scheduler._run_job({"keywords": "Python", "limit": 5}, "profiles/default.yaml")

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
    scheduler._run_job({}, "profiles/default.yaml")


# ─── SF-driven flow tests ───────────────────────────────────────────────────

def test_run_job_passes_sf_search_config_id_to_orchestrator(monkeypatch):
    _reload_scheduler(monkeypatch)
    from job_finder import scheduler

    calls = []
    monkeypatch.setattr(
        scheduler.orchestrator,
        "run",
        lambda **kw: calls.append(kw) or dict(_FULL_SUMMARY),
    )
    monkeypatch.setattr(scheduler, "post_summary", lambda s: None)

    profile = {"keywords": "Apex Dev", "limit": 5, "sf_record_id": "a001x000000XXXXX"}
    scheduler._run_job(profile, "SF Config", sf=None)

    assert calls[0]["sf_search_config_id"] == "a001x000000XXXXX"


def test_run_job_passes_min_annual_salary_to_orchestrator(monkeypatch):
    _reload_scheduler(monkeypatch)
    from job_finder import scheduler

    calls = []
    monkeypatch.setattr(
        scheduler.orchestrator,
        "run",
        lambda **kw: calls.append(kw) or dict(_FULL_SUMMARY),
    )
    monkeypatch.setattr(scheduler, "post_summary", lambda s: None)

    profile = {"keywords": "Apex Dev", "limit": 5, "min_annual_salary": 150000.0}
    scheduler._run_job(profile, "SF Config", sf=None)

    assert calls[0]["min_annual_salary"] == 150000.0


def test_run_job_calls_writeback_when_sf_config_id_present(monkeypatch):
    _reload_scheduler(monkeypatch)
    from job_finder import scheduler

    monkeypatch.setattr(
        scheduler.orchestrator,
        "run",
        lambda **kw: dict(_FULL_SUMMARY),
    )
    monkeypatch.setattr(scheduler, "post_summary", lambda s: None)

    writeback_calls = []
    monkeypatch.setattr(
        scheduler.sf_config_reader,
        "writeback",
        lambda sf, config_id, summary: writeback_calls.append((sf, config_id, summary)),
    )

    mock_sf = object()
    profile = {"keywords": "Apex Dev", "limit": 5, "sf_record_id": "a001x000000XXXXX"}
    scheduler._run_job(profile, "SF Config", sf=mock_sf)

    assert len(writeback_calls) == 1
    assert writeback_calls[0][1] == "a001x000000XXXXX"


def test_run_job_skips_writeback_when_no_sf_config_id(monkeypatch):
    _reload_scheduler(monkeypatch)
    from job_finder import scheduler

    monkeypatch.setattr(
        scheduler.orchestrator,
        "run",
        lambda **kw: dict(_FULL_SUMMARY),
    )
    monkeypatch.setattr(scheduler, "post_summary", lambda s: None)

    writeback_calls = []
    monkeypatch.setattr(
        scheduler.sf_config_reader,
        "writeback",
        lambda *a, **kw: writeback_calls.append(True),
    )

    mock_sf = object()
    profile = {"keywords": "Apex Dev", "limit": 5}  # no sf_record_id
    scheduler._run_job(profile, "YAML Profile", sf=mock_sf)

    assert len(writeback_calls) == 0


def test_run_job_passes_days_from_profile(monkeypatch):
    _reload_scheduler(monkeypatch)
    from job_finder import scheduler

    calls = []
    monkeypatch.setattr(
        scheduler.orchestrator,
        "run",
        lambda **kw: calls.append(kw) or dict(_FULL_SUMMARY),
    )
    monkeypatch.setattr(scheduler, "post_summary", lambda s: None)

    scheduler._run_job({"keywords": "Apex", "limit": 5, "days": 3}, "Test Profile")

    assert calls[0]["days"] == 3
