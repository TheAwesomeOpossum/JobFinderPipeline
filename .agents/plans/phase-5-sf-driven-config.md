# Phase 5 — SF-Driven Config (`Job_Search_Config__c` Integration)

**Status: PLANNED**
**Branch:** JobFinderPipeline

The following plan should be complete, but validate documentation and codebase patterns before starting. Pay special attention to the semicolon-delimited MultiselectPicklist fields in Salesforce — split on `;`, not `,`.

---

## Feature Description

Wire the JobFinder scheduler to read active `Job_Search_Config__c` records from Salesforce as the primary config source. YAML profiles remain as a local fallback when SF is unreachable or has no active records. After each run, the config record is updated with `Last_Run_At__c` (timestamp) and `Last_Run_Summary__c` (JSON run stats). Each `JobApplication__c` record produced by a SF-driven run gets its `Search_Config__c` lookup populated.

The `Job_Search_Config__c` SF object is **already deployed** in the org with all fields, validation rules, page layout, and the `Anthropic_Claude` permission set granting Read+Edit. This phase only touches the Python pipeline — zero Salesforce metadata changes required.

## User Story

As a job seeker,
I want to manage my nightly search configurations from Salesforce,
So that I can adjust keywords, required skills, salary thresholds, and schedule without editing files or restarting the container.

## Problem Statement

Currently the scheduler is driven exclusively by YAML profile files on disk. Changing keywords or schedule requires editing YAML and restarting the Docker container. `Job_Search_Config__c` is deployed in Salesforce but the pipeline ignores it.

## Solution Statement

Add `sf_config_reader.py` that queries active `Job_Search_Config__c` records and maps them to profile dicts. Update `scheduler.py` to prefer SF configs over YAML, with graceful fallback. Pipe `sf_search_config_id` through `orchestrator.run()` so it lands on `JobApplication__c.Search_Config__c`. Write `Last_Run_At__c` / `Last_Run_Summary__c` back after each run.

## Feature Metadata

**Feature Type**: Enhancement
**Estimated Complexity**: Medium
**Primary Systems Affected**: `scheduler.py`, `orchestrator.py`, `db.py`, new `sf_config_reader.py`
**Dependencies**: `simple_salesforce` (already installed), `Job_Search_Config__c` (already deployed)

---

## CONTEXT REFERENCES

### Relevant Codebase Files — YOU MUST READ THESE BEFORE IMPLEMENTING

- `job_finder/scheduler.py` (full file) — The `main()` function adds APScheduler jobs from YAML; `_run_job()` calls `orchestrator.run()`. Both need surgery for SF-driven flow.
- `job_finder/orchestrator.py` (lines 20–50, 130–180) — `run()` signature; where `profile_name` is stamped onto jobs. Need to add `sf_search_config_id` + `min_annual_salary` params.
- `job_finder/sf_writer.py` (lines 130–165) — `create_job_application()` already reads `job.get("sf_search_config_id")` for `Search_Config__c`. **No changes needed here.**
- `job_finder/profiles.py` (full file) — `get_skills()`, `get_schedule()`, `load_profile()` — mirror these patterns in `sf_config_reader.py`.
- `job_finder/db.py` (lines 40–100) — `mark_pushed()` signature — add `sf_search_config_id` param.
- `job_finder/config.py` (full file) — `_require()` pattern and `MIN_ANNUAL_SALARY` env var fallback.
- `tests/test_scheduler.py` (full file) — existing test patterns: `_set_env`, `_reload_scheduler`, `monkeypatch.setattr`.
- `tests/test_orchestrator_skills_filter.py` (lines 1–70) — shows how to test orchestrator with mocked pipeline stages.
- `docs/sf_job_search_config_requirements.md` (full file) — **the spec for this phase**: SOQL query, field→Python mapping, write-back contract, semicolon-split note.

### New Files to Create

- `job_finder/sf_config_reader.py` — SOQL read, field mapping, write-back
- `sql/04_job_lead_sf_config.sql` — add `sf_search_config_id VARCHAR(18)` to `job_lead`
- `tests/test_sf_config_reader.py` — unit tests for the new module

### Relevant Documentation — READ BEFORE IMPLEMENTING

- `docs/sf_job_search_config_requirements.md` — canonical field definitions, SOQL query, Python mapping table, write-back contract, example records
- `simple_salesforce` docs: `sf.query(soql)` returns `{"totalSize": N, "records": [...]}` — records include an `attributes` key that should be ignored when mapping fields

### Patterns to Follow

**`_require()` pattern** (`config.py`):
```python
def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(f"Required environment variable '{key}' is not set.")
    return value
```

**`_with_backoff()` pattern** (`sf_writer.py`):
```python
def _with_backoff(fn, max_retries: int = 5):
    for attempt in range(max_retries):
        try:
            return fn()
        except SalesforceExpiredSession:
            raise
        except Exception as exc:
            if attempt == max_retries - 1:
                raise
            wait = 2 ** attempt
            time.sleep(wait)
```

**Scheduler profile loading** (`scheduler.py`):
```python
profile = load_profile(profile_path)
hour, minute = get_schedule(profile)
scheduler.add_job(_run_job, CronTrigger(...), args=[profile, profile_path], ...)
```

**Orchestrator profile stamping** (`orchestrator.py`):
```python
for job in qualified + skipped:
    job["search_profile"] = profile_name or "default"
```

**MultiselectPicklist split** (critical — `;` delimiter, NOT `,`):
```python
skills = record["Required_Skills__c"] or ""
skill_list = [s.strip() for s in skills.split(";") if s.strip()]
```

**Test module reload pattern** (`tests/test_scheduler.py`):
```python
def _reload_scheduler(monkeypatch):
    _set_env(monkeypatch)
    for mod in ["job_finder.config", "job_finder.scheduler", "job_finder.notifications"]:
        sys.modules.pop(mod, None)
```

**Orchestrator test patching pattern** (`tests/test_orchestrator_skills_filter.py`):
Uses `patch.dict("os.environ", env_patch)` + individual `patch(...)` context managers for all external dependencies.

**Naming convention**: snake_case for Python; `sf_search_config_id` for the SF record ID carried through the pipeline.

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation — new module + SQL migration

Create `sf_config_reader.py` and the SQL migration. These have no dependencies on other Phase 5 changes.

### Phase 2: Core — orchestrator + db plumbing

Thread `sf_search_config_id` and per-profile `min_annual_salary` through `orchestrator.run()` and `db.mark_pushed()`. These are backward-compatible additions (all new params are optional with sensible defaults).

### Phase 3: Integration — scheduler SF-driven flow

Update `scheduler.py` to call `sf_config_reader.load_sf_profiles()` at startup with fallback to YAML, pass `sf_search_config_id` to `_run_job()`, and call `sf_config_reader.writeback()` after each run.

### Phase 4: Testing & Validation

New test file for `sf_config_reader.py`, updated scheduler tests for SF-driven flow, and a regression check against all 141 existing tests.

---

## STEP-BY-STEP TASKS

### CREATE `sql/04_job_lead_sf_config.sql`

- **IMPLEMENT**: Single `ALTER TABLE` adding `sf_search_config_id VARCHAR(18)` to `job_lead`
- **PATTERN**: Mirror `sql/03_job_lead_search_profile.sql` — single column addition with `ADD COLUMN IF NOT EXISTS`
- **GOTCHA**: Column is nullable — jobs from YAML fallback have no config record
- **VALIDATE**: `psql $DATABASE_URL -f sql/04_job_lead_sf_config.sql`

```sql
-- sql/04_job_lead_sf_config.sql
-- Phase 5: link job_lead rows to the SF config record that produced them.
-- Nullable — jobs from YAML-fallback runs have no config ID.
ALTER TABLE job_lead
    ADD COLUMN IF NOT EXISTS sf_search_config_id VARCHAR(18);
```

---

### CREATE `job_finder/sf_config_reader.py`

- **IMPLEMENT**: Three public functions: `load_sf_profiles(sf)`, `_map_record(record)`, `writeback(sf, config_id, summary)`
- **PATTERN**: `_with_backoff` pattern from `sf_writer.py` — wrap SF calls
- **IMPORTS**: `import json, logging, time; from datetime import datetime, timezone; from simple_salesforce import Salesforce, SalesforceExpiredSession; from job_finder.sf_writer import _with_backoff`
- **GOTCHA**: SF MultiselectPicklist fields use `;` as delimiter (e.g. `"Apex;LWC;SOQL"`). `Keywords__c` is a plain text field — comma-separated, passed as-is.
- **GOTCHA**: `sf.query()` returns records with an `attributes` key (e.g. `{"attributes": {"type": "Job_Search_Config__c"}, "Id": "...", "Name": "..."}`). Ignore `attributes` when mapping.
- **GOTCHA**: Numeric fields from SF come back as `float` (e.g. `Daily_Limit__c = 10.0`). Cast with `int()` and `float()`.
- **GOTCHA**: If all fields are null (e.g. newly created record), provide safe defaults.
- **VALIDATE**: `python3 -c "import sys; sys.modules.pop('job_finder.config', None); from job_finder import sf_config_reader; print('import OK')"`

```python
"""Read Job_Search_Config__c records from Salesforce and map to profile dicts."""

import json
import logging
import time
from datetime import datetime, timezone

from simple_salesforce import Salesforce, SalesforceExpiredSession

logger = logging.getLogger(__name__)

_SOQL = """
SELECT Id, Name, Keywords__c, Required_Skills__c, Bonus_Skills__c,
       Daily_Limit__c, Min_Annual_Salary__c, Schedule_Hour__c,
       Schedule_Minute__c, Days_Back__c
FROM Job_Search_Config__c
WHERE Is_Active__c = true
ORDER BY Schedule_Hour__c ASC, Schedule_Minute__c ASC
"""


def load_sf_profiles(sf: Salesforce) -> list[dict]:
    """
    Query active Job_Search_Config__c records and return as profile dicts.
    Returns empty list if the query fails (caller should fall back to YAML).
    """
    try:
        result = sf.query(_SOQL)
    except SalesforceExpiredSession:
        raise
    except Exception as exc:
        logger.warning("Could not query Job_Search_Config__c: %s — falling back to YAML", exc)
        return []

    records = result.get("records", [])
    if not records:
        logger.info("No active Job_Search_Config__c records found — falling back to YAML")
        return []

    profiles = [_map_record(r) for r in records]
    logger.info("Loaded %d profile(s) from Salesforce", len(profiles))
    return profiles


def _map_record(record: dict) -> dict:
    """Map a Job_Search_Config__c record to a profile dict."""
    def _split_multiselect(value) -> list[str]:
        if not value:
            return []
        return [s.strip() for s in str(value).split(";") if s.strip()]

    return {
        "profile_name":      record["Name"],
        "keywords":          record.get("Keywords__c") or "",
        "required_skills":   _split_multiselect(record.get("Required_Skills__c")),
        "bonus_skills":      _split_multiselect(record.get("Bonus_Skills__c")),
        "limit":             int(record.get("Daily_Limit__c") or 10),
        "min_annual_salary": float(record.get("Min_Annual_Salary__c") or 0),
        "schedule_hour":     int(record.get("Schedule_Hour__c") or 2),
        "schedule_minute":   int(record.get("Schedule_Minute__c") or 0),
        "days":              int(record.get("Days_Back__c") or 1),
        "sf_record_id":      record["Id"],  # stored separately from profile keys
    }


def writeback(sf: Salesforce, config_id: str, summary: dict) -> None:
    """
    Write Last_Run_At__c and Last_Run_Summary__c back to the config record.
    Non-fatal — logs a warning on failure.
    """
    payload = {
        "Last_Run_At__c":      datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "Last_Run_Summary__c": json.dumps(summary),
    }
    try:
        from job_finder.sf_writer import _with_backoff
        _with_backoff(lambda: sf.Job_Search_Config__c.update(config_id, payload))
        logger.info("Wrote back run summary to Job_Search_Config__c/%s", config_id)
    except SalesforceExpiredSession:
        raise
    except Exception as exc:
        logger.warning("Could not write back to Job_Search_Config__c/%s: %s", config_id, exc)
```

---

### UPDATE `job_finder/orchestrator.py` — add `sf_search_config_id` + `min_annual_salary`

- **IMPLEMENT**: Add two optional params to `run()`: `sf_search_config_id: str | None = None` and `min_annual_salary: float | None = None`. Stamp `sf_search_config_id` on each job dict. Use `min_annual_salary` (if not None) instead of `config.MIN_ANNUAL_SALARY` in the salary filter stage.
- **PATTERN**: `orchestrator.py` lines 130–145 — where `search_profile` is stamped; add `sf_search_config_id` to the same loop
- **GOTCHA**: The `min_annual_salary` param must fall back to `config.MIN_ANNUAL_SALARY` when `None` — don't break existing YAML-profile behavior
- **GOTCHA**: `sf_writer.create_job_application()` already reads `job.get("sf_search_config_id")` — just stamp it on the job dict and the writer picks it up automatically
- **VALIDATE**: `python3 -m pytest tests/test_orchestrator_skills_filter.py -q`

Changes to `orchestrator.py`:

1. **Update `run()` signature** — add two optional keyword params:
```python
def run(
    keywords: str,
    limit: int,
    dry_run: bool,
    days: int = 1,
    verbose: bool = False,
    required_skills: list[str] | None = None,
    bonus_skills: list[str] | None = None,
    profile_name: str | None = None,
    sf_search_config_id: str | None = None,   # NEW
    min_annual_salary: float | None = None,    # NEW — None → use config.MIN_ANNUAL_SALARY
) -> dict:
```

2. **Update salary threshold resolution** — replace the hardcoded `config.MIN_ANNUAL_SALARY` check in Stage 4.5 with:
```python
_salary_threshold = min_annual_salary if min_annual_salary is not None else config.MIN_ANNUAL_SALARY
if _salary_threshold > 0:
    before = len(parsed_jobs)
    parsed_jobs = [j for j in parsed_jobs if _above_salary_threshold(j, _salary_threshold)]
    summary["salary_filtered"] = before - len(parsed_jobs)
    ...
```

Also update `_above_salary_threshold()` to accept threshold as a parameter:
```python
def _above_salary_threshold(job: dict, threshold: float) -> bool:
    if threshold <= 0:
        return True
    ...
    return max(ceilings) >= threshold
```

3. **Stamp `sf_search_config_id` on jobs** — in the profile-stamping loop (Stage 5):
```python
for job in qualified + skipped:
    job["search_profile"] = profile_name or "default"
    job["sf_search_config_id"] = sf_search_config_id  # NEW
```

---

### UPDATE `job_finder/db.py` — add `sf_search_config_id` to `mark_pushed()`

- **IMPLEMENT**: Add `sf_search_config_id: str | None = None` parameter to `mark_pushed()` and include it in the UPDATE SQL
- **PATTERN**: `db.py` `mark_pushed()` — mirror how `sf_recruiter_contact_id` was added (Phase 3)
- **GOTCHA**: Column must be added to `job_lead` via `sql/04_job_lead_sf_config.sql` before this runs
- **VALIDATE**: `python3 -m pytest tests/test_db.py -q`

Changes to `db.py`:

1. **Update `mark_pushed()` signature**:
```python
def mark_pushed(
    conn,
    url_hash: str,
    sf_job_app_id: str,
    sf_account_id: str,
    sf_recruiter_contact_id: str | None = None,
    annual_salary: float | None = None,
    salary_range_text: str | None = None,
    search_profile: str | None = None,
    sf_search_config_id: str | None = None,   # NEW
) -> None:
```

2. **Update SQL**:
```python
sql = """
    UPDATE job_lead
    SET status = 'pushed',
        sf_job_app_id = %(sf_job_app_id)s,
        sf_account_id = %(sf_account_id)s,
        sf_recruiter_contact_id = %(sf_recruiter_contact_id)s,
        annual_salary = %(annual_salary)s,
        salary_range_text = %(salary_range_text)s,
        search_profile = %(search_profile)s,
        sf_search_config_id = %(sf_search_config_id)s
    WHERE url_hash = %(url_hash)s
"""
```

3. **Update dict**:
```python
cur.execute(sql, {
    ...
    "sf_search_config_id": sf_search_config_id,
})
```

---

### UPDATE `job_finder/orchestrator.py` — pass `sf_search_config_id` to `db.mark_pushed()`

- **IMPLEMENT**: In Stage 8's `db.mark_pushed()` call, add `sf_search_config_id=job.get("sf_search_config_id")`
- **PATTERN**: `orchestrator.py` Stage 8 — the `db.mark_pushed()` call — add keyword arg
- **VALIDATE**: `python3 -m pytest tests/test_orchestrator_skills_filter.py -q`

```python
db.mark_pushed(
    pg_conn,
    job["url_hash"],
    sf_job_app_id,
    sf_account_id,
    sf_recruiter_contact_id=sf_recruiter_contact_id,
    annual_salary=annual_midpoint(job),
    salary_range_text=(job.get("salary_range_text") or "")[:20] or None,
    search_profile=job.get("search_profile"),
    sf_search_config_id=job.get("sf_search_config_id"),  # NEW
)
```

---

### UPDATE `job_finder/scheduler.py` — SF-driven config loading

This is the largest change. The scheduler must:
1. Try to connect to SF and query `Job_Search_Config__c` at startup
2. Fall back to `--profiles` YAML list if SF fails or has no active records
3. Pass `sf_search_config_id` and `min_annual_salary` through `_run_job()` to `orchestrator.run()`
4. Call `sf_config_reader.writeback()` after each successful run
5. Pass `days` from the profile (new — currently hard-defaults to 1)

- **IMPORTS**: Add `from job_finder import sf_config_reader, sf_writer` and `from job_finder.profiles import get_schedule, get_skills, get_location, get_seniority, load_profile`
- **GOTCHA**: SF connection at startup must not crash the scheduler if SF is down — wrap in try/except and fall back to YAML
- **GOTCHA**: When using SF-sourced profiles, `profile_path` (used for `Path(profile_path).stem`) doesn't exist. Use `profile["profile_name"]` directly instead.
- **GOTCHA**: `post_summary` still called after every run regardless of SF/YAML source
- **GOTCHA**: `writeback()` is only called for SF-sourced profiles that have `sf_record_id` set — skip for YAML-sourced profiles
- **VALIDATE**: `python3 -m pytest tests/test_scheduler.py -q`

Full rewrite of `scheduler.py`:

```python
"""Nightly scheduler daemon — runs the JobFinder pipeline on a cron schedule."""

import argparse
import logging
import signal
import sys
from pathlib import Path

from pytz import utc
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from job_finder import config, orchestrator, sf_config_reader, sf_writer
from job_finder.notifications import post_summary
from job_finder.profiles import get_schedule, get_skills, load_profile

logger = logging.getLogger(__name__)


def _run_job(profile: dict, profile_name: str, sf: object = None) -> None:
    """Scheduled job: run the discovery pipeline using profile config."""
    keywords          = profile.get("keywords", config.DEFAULT_KEYWORDS)
    limit             = int(profile.get("limit", config.DAILY_LIMIT))
    days              = int(profile.get("days", 1))
    sf_config_id      = profile.get("sf_record_id")            # None for YAML-sourced
    min_annual_salary = profile.get("min_annual_salary")       # None for YAML-sourced
    required_skills, bonus_skills = get_skills(profile)

    logger.info(
        "Scheduled run starting — profile=%r keywords=%r limit=%d required_skills=%r",
        profile_name, keywords, limit, required_skills,
    )
    try:
        summary = orchestrator.run(
            keywords=keywords,
            limit=limit,
            dry_run=False,
            days=days,
            required_skills=required_skills or None,
            bonus_skills=bonus_skills or None,
            profile_name=profile_name,
            sf_search_config_id=sf_config_id,
            min_annual_salary=min_annual_salary,
        )
        logger.info(
            "Run complete: found=%d new=%d pushed=%d skills_filtered=%d skipped=%d failed=%d",
            summary["found"], summary["new"], summary["pushed"],
            summary["skills_filtered"], summary["skipped"], summary["failed"],
        )
        post_summary(summary)

        # Write-back to SF config record (only for SF-sourced profiles)
        if sf_config_id and sf:
            sf_config_reader.writeback(sf, sf_config_id, summary)

    except Exception as exc:
        logger.error("Scheduled run failed: %s", exc, exc_info=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="JobFinder — nightly scheduler daemon")
    parser.add_argument(
        "--profiles",
        nargs="+",
        default=["profiles/default.yaml"],
        metavar="PROFILE",
        help="YAML profile paths used as fallback when Salesforce has no active configs",
    )
    args = parser.parse_args()

    scheduler = BlockingScheduler(
        timezone=utc,
        job_defaults={
            "coalesce": True,
            "max_instances": 1,
            "misfire_grace_time": 3600,
        },
    )

    def _shutdown(signum, frame):
        logger.info("Received signal %s — shutting down scheduler gracefully", signum)
        scheduler.shutdown(wait=True)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    # ── Attempt SF-driven config loading ──────────────────────────────────
    sf = None
    sf_profiles = []
    try:
        sf = sf_writer.connect()
        sf_profiles = sf_config_reader.load_sf_profiles(sf)
    except Exception as exc:
        logger.warning(
            "Could not load Salesforce configs (will use YAML fallback): %s", exc
        )

    if sf_profiles:
        logger.info("Using %d Salesforce-driven profile(s)", len(sf_profiles))
        profiles_to_schedule = [(p["profile_name"], p) for p in sf_profiles]
    else:
        logger.info("Using %d YAML profile(s) as fallback", len(args.profiles))
        profiles_to_schedule = []
        for profile_path in args.profiles:
            profile = load_profile(profile_path)
            profiles_to_schedule.append((Path(profile_path).stem, profile))
    # ──────────────────────────────────────────────────────────────────────

    for profile_name, profile in profiles_to_schedule:
        hour, minute = get_schedule(profile)
        scheduler.add_job(
            _run_job,
            CronTrigger(hour=hour, minute=minute, timezone=utc),
            args=[profile, profile_name, sf],
            id=f"job_finder_{profile_name}",
            name=f"JobFinder — {profile_name}",
            replace_existing=True,
        )
        logger.info(
            "Scheduled profile=%r at %02d:%02d UTC (id=job_finder_%s)",
            profile_name, hour, minute, profile_name,
        )

    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logger.info("Scheduler started with %d profile(s)", len(profiles_to_schedule))
    scheduler.start()


if __name__ == "__main__":
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    main()
```

---

### CREATE `tests/test_sf_config_reader.py`

- **IMPLEMENT**: Tests for `load_sf_profiles()`, `_map_record()`, and `writeback()`
- **PATTERN**: `tests/test_sf_writer.py` — `_set_env` + `sys.modules.pop` + `MockSF` class
- **IMPORTS**: `import sys, json, pytest; from unittest.mock import MagicMock`
- **GOTCHA**: Import `sf_config_reader` AFTER popping `job_finder.config` from `sys.modules` (config runs at import time)
- **VALIDATE**: `python3 -m pytest tests/test_sf_config_reader.py -v`

Tests to implement:

1. `test_load_sf_profiles_returns_mapped_list` — mock SF with 2 active records; assert 2 profile dicts returned with `sf_record_id` set
2. `test_load_sf_profiles_returns_empty_on_exception` — mock SF.query raising generic Exception; assert returns `[]`, doesn't crash
3. `test_load_sf_profiles_returns_empty_when_no_active_records` — mock SF.query returning `{"totalSize": 0, "records": []}`; assert `[]`
4. `test_map_record_splits_semicolon_skills` — `Required_Skills__c = "Apex;Lightning Web Components;SOQL"` → list of 3 items
5. `test_map_record_handles_null_fields` — all optional fields are `None` → safe defaults (limit=10, etc.)
6. `test_map_record_casts_float_numerics` — SF returns `Daily_Limit__c = 10.0`; assert `profile["limit"] == 10` (int)
7. `test_writeback_calls_sf_update_with_correct_payload` — mock SF object; assert `sf.Job_Search_Config__c.update(config_id, payload)` called with `Last_Run_At__c` and `Last_Run_Summary__c` JSON
8. `test_writeback_does_not_raise_on_failure` — mock SF.update raising Exception; assert writeback returns without raising

---

### UPDATE `tests/test_scheduler.py` — SF-driven flow tests

- **IMPLEMENT**: 4 new tests for the SF-driven scheduler flow
- **PATTERN**: Existing test pattern — `_reload_scheduler` + `monkeypatch.setattr`
- **VALIDATE**: `python3 -m pytest tests/test_scheduler.py -v`

New tests to add:

1. `test_run_job_passes_sf_search_config_id_to_orchestrator` — call `_run_job` with `profile = {"keywords": "Apex Dev", "limit": 5, "sf_record_id": "a001x000000XXXXX"}`, assert `orchestrator.run()` called with `sf_search_config_id="a001x000000XXXXX"`

2. `test_run_job_passes_min_annual_salary_to_orchestrator` — profile with `min_annual_salary=150000.0`; assert `orchestrator.run()` called with `min_annual_salary=150000.0`

3. `test_run_job_calls_writeback_when_sf_config_id_present` — mock `sf_config_reader.writeback`; profile has `sf_record_id`; assert writeback called with correct config_id

4. `test_run_job_skips_writeback_when_no_sf_config_id` — profile has no `sf_record_id`; assert `sf_config_reader.writeback` NOT called

5. `test_run_job_passes_days_from_profile` — profile has `days: 3`; assert `orchestrator.run()` called with `days=3`

---

## TESTING STRATEGY

### Unit Tests

All new/modified functions have unit tests. Mocking follows the existing pattern of `sys.modules.pop()` + `monkeypatch.setenv()` for config isolation. MockSF classes simulate SF responses without network calls.

### Integration (not required for this phase)

Manual smoke test against real SF org verifies end-to-end.

### Edge Cases

- SF has 0 active configs → scheduler uses YAML fallback
- SF connection times out at startup → scheduler uses YAML fallback
- `Required_Skills__c` is `None` (blank in SF) → empty list, no filter applied
- `Min_Annual_Salary__c` is `0.0` → salary filter disabled (same as `config.MIN_ANNUAL_SALARY = 0`)
- `Days_Back__c` is `None` → defaults to `1`
- `writeback()` fails after successful run → logged as warning, run considered successful

---

## VALIDATION COMMANDS

### Level 1: SQL migration

```bash
psql $DATABASE_URL -f sql/04_job_lead_sf_config.sql
```

### Level 2: Import check

```bash
python3 -c "
import sys
for m in list(sys.modules):
    if 'job_finder' in m:
        del sys.modules[m]
import os; os.environ.update({'SERPER_API_KEY':'x','ANTHROPIC_API_KEY':'x','SF_USERNAME':'x','SF_PASSWORD':'x','SF_SECURITY_TOKEN':'x','PG_DBNAME':'x','PG_USER':'x','PG_PASSWORD':'x'})
from job_finder import sf_config_reader
print('sf_config_reader import OK')
"
```

### Level 3: Unit tests — new module

```bash
python3 -m pytest tests/test_sf_config_reader.py -v
```

### Level 4: Full test suite — zero regressions

```bash
python3 -m pytest tests/ -q
```

Expected: all existing tests pass + new sf_config_reader tests pass.

### Level 5: CLI dry-run regression (YAML path still works)

```bash
python3 -m job_finder --dry-run --profile profiles/salesforce_dev.yaml --limit 3
```

Expected: runs without error, YAML profile loads normally.

---

## ACCEPTANCE CRITERIA

- [ ] `sql/04_job_lead_sf_config.sql` applies without error
- [ ] `sf_config_reader.py` imports cleanly
- [ ] `load_sf_profiles()` returns mapped profile list from SF query
- [ ] `load_sf_profiles()` returns `[]` and logs warning when SF unreachable
- [ ] `_map_record()` correctly splits `;`-delimited MultiselectPicklist values
- [ ] `writeback()` updates `Last_Run_At__c` and `Last_Run_Summary__c` on config record
- [ ] `orchestrator.run()` accepts `sf_search_config_id` and stamps it on each job
- [ ] `orchestrator.run()` accepts `min_annual_salary` and uses it in salary filter
- [ ] `db.mark_pushed()` stores `sf_search_config_id` in `job_lead`
- [ ] Scheduler loads SF configs when available; falls back to YAML when not
- [ ] `JobApplication__c.Search_Config__c` populated for SF-driven runs
- [ ] All 141 existing tests continue passing
- [ ] New tests for `sf_config_reader.py` all pass
- [ ] `python -m job_finder --dry-run --profile profiles/salesforce_dev.yaml` still works

---

## COMPLETION CHECKLIST

- [ ] `sql/04_job_lead_sf_config.sql` — created and applied
- [ ] `job_finder/sf_config_reader.py` — created with 3 functions
- [ ] `job_finder/orchestrator.py` — `sf_search_config_id` + `min_annual_salary` params added
- [ ] `job_finder/db.py` — `sf_search_config_id` added to `mark_pushed()`
- [ ] `job_finder/scheduler.py` — SF-driven loading + writeback
- [ ] `tests/test_sf_config_reader.py` — 8 tests, all passing
- [ ] `tests/test_scheduler.py` — 5 new tests, all passing
- [ ] `python3 -m pytest tests/ -q` — zero failures
- [ ] `python3 -m job_finder --dry-run --profile profiles/salesforce_dev.yaml` — works
- [ ] PRD.md Section 12 updated with Phase 5

---

## NOTES

**No Salesforce metadata changes needed.** `Job_Search_Config__c` is already deployed with all fields, validation rules, page layout, list view, and `Anthropic_Claude` permission set. The `Search_Config__c` lookup on `JobApplication__c` is also deployed. This phase is Python-only.

**`sf_writer.create_job_application()` is already wired.** It already has `"Search_Config__c": job.get("sf_search_config_id") or None` (added as a forward-compat stub in Phase 4/SF track). No changes needed to `sf_writer.py`.

**YAML profiles remain valid forever.** The fallback path is not a temporary shim — it's a permanent safety net for local development and for runs when SF is unreachable.

**SF connection reuse.** The `sf` object created in `scheduler.main()` is passed into each `_run_job()` call and stored in the APScheduler job args. This reuses the same session rather than re-authenticating per run, which is consistent with how other long-running SF integrations work. If the session expires mid-run, `SalesforceExpiredSession` propagates to `_run_job()`'s `except Exception` handler and logs an error.

**`profile_name` vs `sf_record_id`.** The `profile_name` (string label stored in `job_lead.search_profile`) is the SF record's `Name` field for SF-sourced configs (e.g. "Salesforce Developer Nightly"). The `sf_record_id` is the 18-char SF ID used for `Search_Config__c` lookup and writeback. These are distinct and both carried on the profile dict.

**`days` param was previously never passed from scheduler.** The current scheduler always uses `days=1` (the `orchestrator.run()` default). Phase 5 passes `profile.get("days", 1)` through, enabling per-profile `Days_Back__c` values. This also benefits YAML profiles if a user adds a `days` key (previously silently ignored).
