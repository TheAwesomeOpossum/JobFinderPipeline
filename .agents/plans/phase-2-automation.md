# Feature: Phase 2 — Nightly Automation (APScheduler + Docker + YAML Profiles)

The following plan should be complete, but it is important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils, types, and models. Import from the right files.

---

## Feature Description

Phase 2 evolves the manual CLI tool into an unattended nightly automation daemon. It adds:
1. **YAML keyword profiles** — declarative per-role configs (keywords, limit, location, seniority, schedule time)
2. **APScheduler nightly runner** — a blocking Python scheduler that fires `orchestrator.run()` on a cron schedule (default 2 AM)
3. **Docker packaging** — Dockerfile + docker-compose.yml for containerized deployment, mirroring the `Salesforce_Backup` pattern
4. **Run summary log** — structured completion log at the end of each scheduled run
5. **Optional Slack webhook** — one-line POST of run stats to a Slack incoming webhook URL

Phase 1 (CLI pipeline) is fully implemented. This plan adds automation around it **without modifying any existing Phase 1 logic**.

---

## User Story

As a job seeker
I want to deploy JobFinder as a Docker container
So that the pipeline runs automatically every night without manual intervention, and I wake up to a triage inbox of freshly posted jobs

---

## Problem Statement

Phase 1 requires the user to manually run `python -m job_finder` each morning. The tool is stateless and ready for automation, but lacks: a configurable schedule runner, a profile system for different search strategies, and a container to run unattended.

## Solution Statement

Add a `job_finder/scheduler.py` module using APScheduler 3.x `BlockingScheduler` + `CronTrigger` that loads a YAML profile and fires the pipeline on schedule. Add a `profiles/` directory for named keyword configs. Containerize with `Dockerfile` + `docker-compose.yml` mirroring the existing `Salesforce_Backup` Docker pattern. Optionally POST a run summary to a Slack webhook.

---

## Feature Metadata

**Feature Type**: Enhancement
**Estimated Complexity**: Medium
**Primary Systems Affected**: `__main__.py`, `orchestrator.py` (read-only), new `scheduler.py`, new `profiles.py`, new `notifications.py`
**Dependencies**: `apscheduler>=3.11,<4.0`, `pyyaml>=6.0`, `pytz>=2024.1`

---

## CONTEXT REFERENCES

### Relevant Codebase Files — MUST READ BEFORE IMPLEMENTING

- `job_finder/__main__.py` (lines 1–55) — Why: `--profile` flag and two-pass argparse pattern must integrate here; understand existing flag names and defaults
- `job_finder/orchestrator.py` (lines 25–124) — Why: `run(keywords, limit, dry_run)` signature is the only interface the scheduler calls; don't change it
- `job_finder/config.py` (lines 1–43) — Why: `_require()` and `load_dotenv()` patterns; understand module-level loading; new env vars (`SCHEDULE_HOUR`, `SCHEDULE_MINUTE`, `SLACK_WEBHOOK_URL`) are optional and should NOT use `_require()`
- `job_finder/enrichment.py` (lines 44–64) — Why: Pattern for optional/graceful failure (`try/except`, return empty dict); mirror for `notifications.py`
- `tests/test_scoring.py` (lines 1–30) — Why: Gold standard for test structure: `_set_env(monkeypatch)`, `sys.modules.pop()`, module reload, then import
- `/home/your-username/Docker_Projects/Salesforce_Backup/Dockerfile` — Why: MIRROR this exactly for JobFinder Dockerfile (same `python:3.12-slim`, `useradd -m -u 1001`, WORKDIR, layer order)
- `/home/your-username/Docker_Projects/Salesforce_Backup/docker-compose.yml` — Why: MIRROR service structure (`env_file: .env`, `restart: unless-stopped`, `volumes: ./logs`)

### New Files to Create

- `profiles/default.yaml` — Default profile (Software Developer/Engineer, Remote, mid/senior, limit 20, 2 AM)
- `profiles/salesforce_dev.yaml` — Salesforce Developer profile (Salesforce keywords, limit 10, 2:30 AM)
- `job_finder/profiles.py` — YAML profile loader with validation and defaults
- `job_finder/scheduler.py` — APScheduler daemon (`python -m job_finder.scheduler`)
- `job_finder/notifications.py` — Optional Slack webhook POST (fire-and-forget)
- `Dockerfile` — Mirror of Salesforce_Backup Dockerfile
- `docker-compose.yml` — Scheduler service (no bundled Postgres — connects to external)
- `tests/test_profiles.py` — Unit tests for profile loading
- `tests/test_scheduler.py` — Unit tests for scheduler job invocation
- `tests/test_notifications.py` — Unit tests for Slack webhook notification

### Updated Files

- `requirements.txt` — Add `apscheduler>=3.11,<4.0`, `pyyaml>=6.0`, `pytz>=2024.1`
- `job_finder/__main__.py` — Add `--profile` flag with two-pass argparse pattern
- `.env.example` — Add `SCHEDULE_HOUR`, `SCHEDULE_MINUTE`, `SLACK_WEBHOOK_URL`
- `.gitignore` — Add `logs/` entry for Docker log volume directory

### Relevant Documentation — READ BEFORE IMPLEMENTING

- [APScheduler 3.x Docs — BlockingScheduler](https://apscheduler.readthedocs.io/en/3.x/userguide.html#starting-the-scheduler)
  - Specific section: Starting the Scheduler, CronTrigger
  - Why: `BlockingScheduler` is the correct class for a Docker daemon (blocks main thread); `BackgroundScheduler` requires a separate keepalive loop
- [APScheduler 3.x — CronTrigger](https://apscheduler.readthedocs.io/en/3.x/modules/triggers/cron.html)
  - Why: `hour` and `minute` parameters for scheduling at 2 AM
- [PyYAML safe_load](https://pyyaml.org/wiki/PyYAMLDocumentation#loading-yaml)
  - Why: Always use `yaml.safe_load()` not `yaml.load()` — never load untrusted YAML with full loader
- [Docker python:3.12-slim](https://hub.docker.com/_/python)
  - Why: Slim variant keeps image small; matches Salesforce_Backup pattern

---

## Patterns to Follow

### Two-Pass argparse Pattern for `--profile` Support

Pre-parse `--profile` before setting argparse defaults, so explicit CLI flags always win:

```python
# In __main__.py — add BEFORE existing parser setup:
import sys
from job_finder.profiles import load_profile

pre = argparse.ArgumentParser(add_help=False)
pre.add_argument("--profile")
pre_args, _ = pre.parse_known_args()

profile_data = {}
if pre_args.profile:
    profile_data = load_profile(pre_args.profile)

# Then use profile_data as defaults:
parser.add_argument("--keywords", default=profile_data.get("keywords", config.DEFAULT_KEYWORDS), ...)
parser.add_argument("--limit", type=int, default=profile_data.get("limit", config.DAILY_LIMIT), ...)
```

This means `python -m job_finder --profile profiles/salesforce_dev.yaml --limit 5` uses the profile's keywords but the explicit `--limit 5`.

### Profile YAML Schema

```yaml
# profiles/default.yaml
keywords: "Software Developer,Software Engineer"
limit: 20
location_preference: "Remote"
seniority_targets: "mid,senior"
schedule_hour: 2
schedule_minute: 0
```

All keys are optional — `profiles.py` fills in env-var defaults for missing keys.

### Graceful Failure Pattern (from `enrichment.py:54-64`)

```python
# Mirror in notifications.py:
try:
    requests.post(url, json={"text": text}, timeout=5)
except Exception as exc:
    logger.warning("Slack notification failed: %s", exc)
    # Never crash the pipeline over notification failure
```

### Scheduler Entrypoint Pattern

```python
# job_finder/scheduler.py
if __name__ == "__main__" or True:  # runnable via python -m job_finder.scheduler
    scheduler.start()
```

Allow `python -m job_finder.scheduler` by naming it with `__main__` behavior inside `scheduler.py` — OR create `job_finder/scheduler/__main__.py`. Simpler: just add a `main()` function and call it when run directly.

### Non-Root Docker User (from Salesforce_Backup/Dockerfile:4)

```dockerfile
RUN useradd -m -u 1001 appuser
# ...
USER appuser
```

Use `appuser` consistently (not `syncuser` which is Salesforce_Backup-specific).

### `sys.modules.pop()` Test Isolation (from `tests/test_scoring.py:22-23`)

```python
def test_...(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    sys.modules.pop("job_finder.profiles", None)
    from job_finder.profiles import load_profile
```

### Naming Conventions

- Module names: `snake_case` (`profiles.py`, `scheduler.py`, `notifications.py`)
- Profile file names: `kebab-case.yaml` (`default.yaml`, `salesforce-dev.yaml`)
  - **Note:** PRD specifies `salesforce_dev.yaml` — use underscore to match PRD
- Dict keys: `snake_case` (`schedule_hour`, `location_preference`)
- Log messages: `logger.info("...")` not `print()`

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation

Install new dependencies, create YAML profile files and loader, no changes to existing pipeline.

**Tasks:**
- Update `requirements.txt` with `apscheduler` and `pyyaml`
- Create `profiles/default.yaml` and `profiles/salesforce_dev.yaml`
- Implement `job_finder/profiles.py` with `load_profile()` and `get_schedule()` helpers
- Write `tests/test_profiles.py`

### Phase 2: Core Implementation

Add scheduler daemon and optional notifications module.

**Tasks:**
- Implement `job_finder/notifications.py` (Slack webhook, fire-and-forget)
- Implement `job_finder/scheduler.py` (APScheduler BlockingScheduler + CronTrigger)
- Write `tests/test_scheduler.py` and `tests/test_notifications.py`

### Phase 3: Integration

Wire `--profile` into `__main__.py` and create Docker artifacts.

**Tasks:**
- Update `job_finder/__main__.py` with two-pass `--profile` arg
- Create `Dockerfile`
- Create `docker-compose.yml`
- Update `.env.example` with new vars

### Phase 4: Testing & Validation

Run full test suite, build Docker image, validate CLI and scheduler paths.

---

## STEP-BY-STEP TASKS

### TASK 1: UPDATE `requirements.txt`

- **IMPLEMENT**: Append `apscheduler>=3.11,<4.0`, `pyyaml>=6.0`, and `pytz>=2024.1` to the file
- **GOTCHA**: Use `<4.0` upper bound — APScheduler 4.x has a completely different API (async-first, no `BlockingScheduler`). Pin to 3.x. Current latest 3.x is `3.11.2`.
- **GOTCHA**: `pytz` is a **required** transitive dependency of APScheduler 3.x for timezone objects (`from pytz import utc`). Without it, APScheduler raises `ImportError` at runtime when a timezone is specified. Add it explicitly.
- **GOTCHA**: `pyyaml` package installs as `yaml` in Python — the import is `import yaml`, not `import pyyaml`
- **VALIDATE**: `pip install -r requirements.txt` (no errors)

### TASK 2: CREATE `profiles/default.yaml`

- **IMPLEMENT**: Create `profiles/` directory and write default profile YAML matching env defaults
- **PATTERN**: Match field names to config.py env var semantics exactly (`keywords` → `DEFAULT_KEYWORDS`, `limit` → `DAILY_LIMIT`, etc.)
- **CONTENT**:
  ```yaml
  # Default profile: broad software engineering search
  keywords: "Software Developer,Software Engineer"
  limit: 20
  location_preference: "Remote"
  seniority_targets: "mid,senior"
  schedule_hour: 2
  schedule_minute: 0
  ```
- **VALIDATE**: `python -c "import yaml; print(yaml.safe_load(open('profiles/default.yaml')))"`

### TASK 3: CREATE `profiles/salesforce_dev.yaml`

- **IMPLEMENT**: Salesforce Developer targeted profile
- **CONTENT**:
  ```yaml
  # Salesforce Developer profile
  keywords: "Salesforce Developer,Salesforce Engineer,SFDC Developer"
  limit: 10
  location_preference: "Remote"
  seniority_targets: "mid,senior"
  schedule_hour: 2
  schedule_minute: 30
  ```
- **VALIDATE**: `python -c "import yaml; print(yaml.safe_load(open('profiles/salesforce_dev.yaml')))"`

### TASK 4: CREATE `job_finder/profiles.py`

- **IMPLEMENT**: Profile loader with `load_profile(path: str) -> dict` and `get_schedule(profile: dict) -> tuple[int, int]` helper
- **PATTERN**: Module-level `logger = logging.getLogger(__name__)` — mirror `enrichment.py:10`
- **IMPORTS**: `import yaml`, `import logging`, `from pathlib import Path`
- **LOGIC**:
  ```python
  def load_profile(path: str) -> dict:
      """Load a YAML profile file. Raises FileNotFoundError if path doesn't exist."""
      p = Path(path)
      if not p.exists():
          raise FileNotFoundError(f"Profile file not found: {path}")
      with p.open() as f:
          data = yaml.safe_load(f) or {}
      return data

  def get_schedule(profile: dict) -> tuple[int, int]:
      """Return (hour, minute) from profile, defaulting to 2:00 AM."""
      hour = int(profile.get("schedule_hour", 2))
      minute = int(profile.get("schedule_minute", 0))
      return hour, minute
  ```
- **GOTCHA**: `yaml.safe_load()` returns `None` for empty files — handle with `or {}`
- **GOTCHA**: YAML auto-converts unquoted `2` to `int` — explicit `int()` cast is still correct for safety
- **VALIDATE**: `python -c "from job_finder.profiles import load_profile; print(load_profile('profiles/default.yaml'))"`

### TASK 5: CREATE `tests/test_profiles.py`

- **IMPLEMENT**: Unit tests for `load_profile()` and `get_schedule()`
- **PATTERN**: Use `tmp_path` pytest fixture for temp YAML files (NOT `monkeypatch` for file I/O)
- **PATTERN**: DO NOT use `sys.modules.pop("job_finder.config")` here — `profiles.py` does NOT import `config.py`, so no env setup needed
- **TESTS**:
  1. `test_load_profile_returns_dict`: Write valid YAML to `tmp_path`, assert returns dict with expected keys
  2. `test_load_profile_missing_file_raises_file_not_found`: Assert `FileNotFoundError` for nonexistent path
  3. `test_load_profile_empty_file_returns_empty_dict`: Empty file → returns `{}`
  4. `test_get_schedule_uses_profile_values`: `{"schedule_hour": 3, "schedule_minute": 15}` → `(3, 15)`
  5. `test_get_schedule_defaults_to_2am`: Empty profile `{}` → `(2, 0)`
- **VALIDATE**: `pytest tests/test_profiles.py -v` (all pass)

### TASK 6: CREATE `job_finder/notifications.py`

- **IMPLEMENT**: Optional Slack webhook notification; fire-and-forget; never crashes pipeline
- **PATTERN**: Mirror `enrichment.py:54-64` graceful-failure pattern
- **IMPORTS**: `import os`, `import logging`, `import requests`
- **LOGIC**:
  ```python
  logger = logging.getLogger(__name__)

  def post_summary(summary: dict) -> None:
      """POST a run summary to SLACK_WEBHOOK_URL if configured. Silent on failure."""
      url = os.getenv("SLACK_WEBHOOK_URL")
      if not url:
          return
      text = (
          f":robot_face: *JobFinder* — run complete\n"
          f"found={summary['found']} new={summary['new']} "
          f"pushed={summary['pushed']} skipped={summary['skipped']} failed={summary['failed']}"
      )
      try:
          resp = requests.post(url, json={"text": text}, timeout=5)
          resp.raise_for_status()
          logger.info("Slack notification sent")
      except Exception as exc:
          logger.warning("Slack notification failed: %s", exc)
  ```
- **GOTCHA**: `requests` is already in `requirements.txt` — no new dependency
- **GOTCHA**: `os.getenv()` not `config.SLACK_WEBHOOK_URL` — this is optional, don't add it to `config.py`
- **VALIDATE**: `python -c "from job_finder.notifications import post_summary; post_summary({'found':5,'new':3,'pushed':2,'skipped':1,'failed':0})"` (no crash when env var absent)

### TASK 7: CREATE `tests/test_notifications.py`

- **IMPLEMENT**: Unit tests for `post_summary()`
- **PATTERN**: `_set_env(monkeypatch)` + `sys.modules.pop("job_finder.notifications", None)` before import
- **TESTS**:
  1. `test_post_summary_skips_when_no_webhook`: No `SLACK_WEBHOOK_URL` → `requests.post` never called (mock it, assert not called)
  2. `test_post_summary_posts_when_webhook_set`: Set `SLACK_WEBHOOK_URL=http://example.com/webhook` → `requests.post` called with correct JSON
  3. `test_post_summary_handles_request_exception_silently`: `requests.post` raises `Exception` → no crash, warning logged
- **VALIDATE**: `pytest tests/test_notifications.py -v`

### TASK 8: CREATE `job_finder/scheduler.py`

- **IMPLEMENT**: APScheduler daemon that loads a profile and fires `orchestrator.run()` on a cron schedule, with explicit SIGTERM/SIGINT signal handlers for graceful Docker shutdown
- **IMPORTS**:
  ```python
  import argparse
  import logging
  import signal
  import sys
  from pytz import utc
  from apscheduler.schedulers.blocking import BlockingScheduler
  from apscheduler.triggers.cron import CronTrigger
  from job_finder import config, orchestrator
  from job_finder.profiles import load_profile, get_schedule
  from job_finder.notifications import post_summary
  ```
- **PATTERN**: `logging.basicConfig(...)` mirrors `__main__.py:12-16` exactly
- **LOGIC**:
  ```python
  logger = logging.getLogger(__name__)

  def _run_job(profile: dict) -> None:
      """Scheduled job: run pipeline from profile config."""
      keywords = profile.get("keywords", config.DEFAULT_KEYWORDS)
      limit = int(profile.get("limit", config.DAILY_LIMIT))
      logger.info("Scheduled run starting — keywords=%r limit=%d", keywords, limit)
      try:
          summary = orchestrator.run(keywords=keywords, limit=limit, dry_run=False)
          logger.info(
              "Run complete: found=%d new=%d pushed=%d skipped=%d failed=%d",
              summary["found"], summary["new"],
              summary["pushed"], summary["skipped"], summary["failed"],
          )
          post_summary(summary)
      except Exception as exc:
          logger.error("Scheduled run failed: %s", exc, exc_info=True)


  def main() -> None:
      parser = argparse.ArgumentParser(description="JobFinder — nightly scheduler daemon")
      parser.add_argument(
          "--profile",
          default="profiles/default.yaml",
          help="Path to YAML profile file (default: profiles/default.yaml)",
      )
      args = parser.parse_args()

      profile = load_profile(args.profile)
      hour, minute = get_schedule(profile)
      logger.info("Scheduler loaded profile=%r, schedule=%02d:%02d", args.profile, hour, minute)

      scheduler = BlockingScheduler(
          timezone=utc,
          job_defaults={
              "coalesce": True,          # If missed multiple runs, fire once on resume
              "max_instances": 1,        # Never run overlapping copies
              "misfire_grace_time": 3600,  # Fire if up to 1h late (container restart)
          },
      )

      # Explicit signal handlers — do NOT rely on try/except KeyboardInterrupt alone.
      # docker stop sends SIGTERM; KeyboardInterrupt is only raised by SIGINT (Ctrl+C).
      # Without explicit SIGTERM handler, docker stop waits 10s then sends SIGKILL.
      def _shutdown(signum, frame):
          logger.info("Received signal %s — shutting down scheduler gracefully", signum)
          scheduler.shutdown(wait=True)  # wait=True: finish any running job before exiting
          sys.exit(0)

      signal.signal(signal.SIGTERM, _shutdown)
      signal.signal(signal.SIGINT, _shutdown)

      scheduler.add_job(
          _run_job,
          CronTrigger(hour=hour, minute=minute, timezone=utc),
          args=[profile],
          id="nightly_job_finder",
          name="JobFinder nightly run",
          replace_existing=True,  # Idempotent on restart — do not accumulate duplicate jobs
      )
      logger.info("Scheduler started — next run at %02d:%02d UTC", hour, minute)
      # Suppress verbose APScheduler internal logs; our _run_job logs what matters
      logging.getLogger("apscheduler").setLevel(logging.WARNING)
      scheduler.start()  # Blocks here until _shutdown() calls scheduler.shutdown()


  if __name__ == "__main__":
      logging.basicConfig(
          level=getattr(logging, config.LOG_LEVEL, logging.INFO),
          format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
          handlers=[logging.StreamHandler(sys.stdout)],
      )
      main()
  ```
- **GOTCHA**: `BlockingScheduler` blocks the main thread — correct for a Docker daemon. Do NOT use `BackgroundScheduler` (requires a `while True: time.sleep(1)` keepalive loop).
- **GOTCHA**: **SIGTERM vs SIGINT** — `docker stop` sends SIGTERM. `KeyboardInterrupt` is only raised by SIGINT (Ctrl+C). `try/except KeyboardInterrupt` alone silently ignores `docker stop` in Docker. Always register `signal.signal(signal.SIGTERM, ...)` explicitly.
- **GOTCHA**: `replace_existing=True` is required when the scheduler restarts — without it, a new job entry is added to the in-memory jobstore on every container restart, accumulating duplicates.
- **GOTCHA**: `coalesce=True` prevents the scheduler from firing missed runs in a catch-up loop after a container restart. Without it, if the container was down for 3 missed scheduled times, all 3 fire in rapid succession.
- **GOTCHA**: Always pass `timezone=utc` to both `BlockingScheduler()` and `CronTrigger()`. DST-sensitive timezones (e.g., `America/New_York`) can cause jobs to fire twice or be skipped during daylight saving transitions.
- **GOTCHA**: `logging.basicConfig` is called only inside `if __name__ == "__main__"` — when imported in tests, we don't want basicConfig to fire.
- **VALIDATE**: `python -c "from job_finder.scheduler import _run_job, main; print('import OK')"` (no crash with valid env)

### TASK 9: CREATE `tests/test_scheduler.py`

- **IMPLEMENT**: Unit tests for `_run_job()` and scheduler setup
- **PATTERN**: `_set_env(monkeypatch)` + `sys.modules.pop()` before import
- **TESTS**:
  1. `test_run_job_calls_orchestrator_with_profile_values`: Mock `orchestrator.run` returning `{"found":5,"new":3,"parsed":3,"qualified":2,"pushed":2,"skipped":1,"failed":0}`. Call `_run_job({"keywords": "Salesforce Developer", "limit": 10})`. Assert `orchestrator.run` called with `keywords="Salesforce Developer"`, `limit=10`, `dry_run=False`.
  2. `test_run_job_uses_config_defaults_when_profile_empty`: Mock `orchestrator.run`. Call `_run_job({})`. Assert `orchestrator.run` called with `config.DEFAULT_KEYWORDS` and `config.DAILY_LIMIT`.
  3. `test_run_job_calls_post_summary_after_success`: Mock both `orchestrator.run` and `post_summary`. Assert `post_summary` called with the summary dict.
  4. `test_run_job_does_not_crash_on_orchestrator_exception`: Mock `orchestrator.run` to raise `Exception("DB down")`. Assert `_run_job({})` does not raise (exception caught, logged).
- **GOTCHA**: Do NOT actually start `BlockingScheduler` in tests (it blocks forever). Only test `_run_job()` directly.
- **VALIDATE**: `pytest tests/test_scheduler.py -v`

### TASK 10: UPDATE `job_finder/__main__.py`

- **IMPLEMENT**: Add `--profile` flag using two-pass argparse pattern so profile is a default that explicit flags override
- **PATTERN**: Two-pass pre-parse described in "Patterns to Follow" section above
- **IMPORTS TO ADD**: `from job_finder.profiles import load_profile` (inside the function, after pre-parse check, to avoid circular import)
- **CHANGES** (patch only the `main()` function):
  ```python
  def main():
      logging.basicConfig(
          level=getattr(logging, config.LOG_LEVEL, logging.INFO),
          format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
          handlers=[logging.StreamHandler(sys.stdout)],
      )

      # ── Two-pass: pre-parse --profile before setting argparse defaults ──
      pre = argparse.ArgumentParser(add_help=False)
      pre.add_argument("--profile")
      pre_args, _ = pre.parse_known_args()

      profile_data: dict = {}
      if pre_args.profile:
          from job_finder.profiles import load_profile
          profile_data = load_profile(pre_args.profile)
      # ── End profile pre-parse ──

      parser = argparse.ArgumentParser(
          description="JobFinder — discover freshly posted engineering jobs"
      )
      parser.add_argument(
          "--profile",
          help="Path to YAML profile file (overrides env defaults, overridden by explicit flags)",
      )
      parser.add_argument(
          "--dry-run",
          action="store_true",
          help="Run full pipeline without writing to Salesforce",
      )
      parser.add_argument(
          "--keywords",
          default=profile_data.get("keywords", config.DEFAULT_KEYWORDS),
          help="Comma-separated search keywords (default: %(default)s)",
      )
      parser.add_argument(
          "--limit",
          type=int,
          default=profile_data.get("limit", config.DAILY_LIMIT),
          help="Max jobs to push to Salesforce (default: %(default)s)",
      )
      args = parser.parse_args()

      summary = orchestrator.run(
          keywords=args.keywords,
          limit=args.limit,
          dry_run=args.dry_run,
      )

      print(
          f"\nSummary: found={summary['found']} new={summary['new']} parsed={summary['parsed']} "
          f"qualified={summary['qualified']} pushed={summary['pushed']} "
          f"skipped={summary['skipped']} failed={summary['failed']}"
      )

      sys.exit(1 if summary.get("failed", 0) > 0 else 0)
  ```
- **GOTCHA**: The `from job_finder.profiles import load_profile` is inside the `if pre_args.profile:` block intentionally — avoids importing `yaml` (and requiring PyYAML) on every CLI invocation when `--profile` isn't used. Move to top-level import if you prefer consistency.
- **VALIDATE**: `python -m job_finder --help` (shows `--profile` flag); `python -m job_finder --profile profiles/default.yaml --dry-run --limit 3` (loads profile, dry-run completes)

### TASK 11: UPDATE `.env.example`

- **IMPLEMENT**: Add three new optional vars with comments
- **ADD** to end of file:
  ```bash
  # Scheduler (Phase 2)
  SCHEDULE_HOUR=2         # Hour for nightly run (0-23, default 2)
  SCHEDULE_MINUTE=0       # Minute for nightly run (0-59, default 0)

  # Notifications (Phase 2 — optional)
  # SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXX/YYY/ZZZ
  ```
- **GOTCHA**: `SCHEDULE_HOUR` and `SCHEDULE_MINUTE` are read in `profiles.py` `get_schedule()` only as a fallback if no profile key is set — they are NOT registered in `config.py` (no `_require()` for them)
- **VALIDATE**: `cat .env.example | grep SCHEDULE` (shows both vars)

### TASK 12: CREATE `Dockerfile`

- **IMPLEMENT**: Mirror `Salesforce_Backup/Dockerfile` exactly, with additions: copy `profiles/` directory, `-u` flag on Python CMD for unbuffered output
- **PATTERN**: `FROM python:3.12-slim` → `useradd -m -u 1001 appuser` → install deps → copy code → `USER appuser`
- **CONTENT**:
  ```dockerfile
  FROM python:3.12-slim

  # Create non-root user
  RUN useradd -m -u 1001 appuser

  WORKDIR /app

  # Install dependencies first (layer cache)
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt

  # Copy application code and profiles
  COPY job_finder/ ./job_finder/
  COPY profiles/ ./profiles/

  # Create logs directory owned by appuser
  RUN mkdir -p /app/logs && chown -R appuser:appuser /app

  USER appuser

  # -u: unbuffered stdout/stderr — required so logs appear immediately in docker logs
  CMD ["python", "-u", "-m", "job_finder.scheduler", "--profile", "profiles/default.yaml"]
  ```
- **GOTCHA**: Use **exec form** `CMD ["python", ...]` not shell form `CMD python ...`. Shell form spawns `/bin/sh` as PID 1; Python becomes PID 2+ and never receives SIGTERM from `docker stop`. Exec form makes Python PID 1 directly.
- **GOTCHA**: The `-u` flag forces unbuffered stdout/stderr. Without it, Python buffers output until its buffer fills — `docker logs scheduler` shows nothing for long periods.
- **GOTCHA**: Do NOT `COPY . .` — this picks up `.env` into the image. Copy only `job_finder/` and `profiles/`. Secrets come in via `env_file` in docker-compose.
- **GOTCHA**: `profiles/` volume mount in docker-compose overrides the `COPY profiles/` in the image — this is intentional so the user can edit profiles without rebuilding.
- **VALIDATE**: `docker build -t job-finder .` (no errors, image builds)

### TASK 13: CREATE `docker-compose.yml`

- **IMPLEMENT**: Single `scheduler` service; no bundled Postgres (user points `PG_HOST` to existing Postgres); mirror Salesforce_Backup service structure with critical Docker daemon additions
- **PATTERN**: `name: job-finder` → service `scheduler` → `build: .` → `restart: unless-stopped` → `env_file: .env` → volumes for `profiles/` and `logs/`
- **CONTENT**:
  ```yaml
  name: job-finder

  services:
    scheduler:
      build: .
      container_name: jf_scheduler
      restart: unless-stopped
      init: true          # Injects tini as PID 1 — ensures SIGTERM reaches Python
      stop_grace_period: 120s  # Give running pipeline jobs 2 min to finish before SIGKILL
      env_file: .env
      environment:
        - TZ=UTC          # Container OS timezone — keep consistent with APScheduler UTC
      volumes:
        - ./profiles:/app/profiles:ro
        - ./logs:/app/logs
      logging:
        driver: json-file
        options:
          max-size: "20m"
          max-file: "5"
          compress: "true"
  ```
- **GOTCHA**: `init: true` injects Docker's built-in `tini` as PID 1. Without it, Python runs as PID 1 and Linux suppresses default signal handlers — `docker stop` hangs 10 seconds then sends SIGKILL. `init: true` is the zero-Dockerfile-change fix; our explicit `signal.signal(SIGTERM, ...)` in `scheduler.py` provides additional defense-in-depth.
- **GOTCHA**: `stop_grace_period: 120s` — the nightly pipeline can take 1–3 minutes. Default Docker grace period is 10 seconds; the pipeline would be SIGKILL'd mid-Salesforce-write without this.
- **GOTCHA**: No `postgres` service — JobFinder shares the existing `sf_postgres` container. User sets `PG_HOST=sf_postgres` in `.env` and connects to the Salesforce_Backup network via: `docker network connect salesforce-backup_default jf_scheduler` after `docker compose up -d`. OR sets `PG_HOST` to host IP with `PG_SSLMODE=disable`.
- **GOTCHA**: `profiles` is mounted `:ro` (read-only) — the scheduler only reads profiles, never writes them.
- **GOTCHA**: `logging.driver=json-file` with `max-size/max-file` is essential — without rotation, a nightly daemon running for months fills disk with Docker logs.
- **GOTCHA**: `./logs:/app/logs` creates a `logs/` directory on the host — add `logs/` to `.gitignore`
- **VALIDATE**: `docker compose config` (validates YAML syntax without starting); `docker compose build` (builds image)

### TASK 14: UPDATE `.gitignore`

- **IMPLEMENT**: Add `logs/` to `.gitignore` so the Docker log volume mount directory is never committed
- **ADD** to `.gitignore`:
  ```
  # Docker log volume
  logs/
  ```
- **GOTCHA**: `docker-compose.yml` mounts `./logs:/app/logs` which creates the `logs/` directory on the host automatically on `docker compose up`. Without this entry it would show up as an untracked directory in `git status` after the first run.
- **VALIDATE**: `grep logs .gitignore` (shows the entry)

---

## TESTING STRATEGY

### Unit Tests

Follow existing pattern: `_set_env(monkeypatch)` + `sys.modules.pop()` for any module that transitively imports `job_finder.config`. Modules that do NOT import config (`profiles.py`) need no env setup.

**`test_profiles.py`**: Use `tmp_path` for file I/O; no monkeypatching needed.

**`test_notifications.py`**: Monkeypatch `requests.post` (not `requests.Session`); test both absent-webhook and present-webhook paths.

**`test_scheduler.py`**: Mock `orchestrator.run` with `pytest-mock`; never start actual `BlockingScheduler`.

### Integration Tests

Not applicable for Phase 2 unit tests. Integration is validated via Docker dry-run (Task 14 validation).

### Edge Cases

1. `--profile` points to nonexistent file → `FileNotFoundError` with clear message
2. Profile YAML is empty → `load_profile` returns `{}`, scheduler uses config defaults
3. Profile `schedule_hour: 25` → value passed as-is to CronTrigger which raises `ValueError` — acceptable (fail-fast at startup)
4. `SLACK_WEBHOOK_URL` not set → `post_summary` silently returns
5. Slack webhook returns 4xx/5xx → logged as warning, pipeline not affected
6. Scheduler started at 2:05 AM (1 minute past schedule) with `misfire_grace_time=3600` → job fires immediately (within grace period)

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style

```bash
# Verify new dependencies install cleanly
pip install -r requirements.txt

# Verify all new modules import without error (with valid env)
python -c "from job_finder.profiles import load_profile, get_schedule; print('profiles OK')"
python -c "from job_finder.notifications import post_summary; print('notifications OK')"
python -c "from job_finder.scheduler import _run_job, main; print('scheduler OK')"
```

### Level 2: Unit Tests

```bash
# New tests only
pytest tests/test_profiles.py -v
pytest tests/test_notifications.py -v
pytest tests/test_scheduler.py -v

# Full regression suite (zero failures expected)
pytest tests/ -v
```

### Level 3: Integration Tests

```bash
# CLI with profile flag (dry-run, no SF writes)
python -m job_finder --profile profiles/default.yaml --dry-run --limit 3

# CLI with profile + explicit override (limit overrides profile's limit)
python -m job_finder --profile profiles/salesforce_dev.yaml --dry-run --limit 2 --keywords "Python Developer"

# Verify --help shows --profile flag
python -m job_finder --help | grep profile
```

### Level 4: Docker Validation

```bash
# Build Docker image
docker build -t job-finder .

# Verify image doesn't contain .env file
docker run --rm job-finder ls -la /app/  # should NOT show .env

# Dry run inside container (pass env vars explicitly or via --env-file)
docker run --rm --env-file .env job-finder \
  python -m job_finder --profile profiles/default.yaml --dry-run --limit 3

# Validate docker-compose YAML syntax
docker compose config

# Start scheduler (detached) — verify it starts without crashing
docker compose up -d
docker compose logs scheduler  # should show "Scheduler started — next run at 02:00"
docker compose down
```

### Level 5: Profile Validation

```bash
# Verify both profiles parse correctly
python -c "
import yaml
for f in ['profiles/default.yaml', 'profiles/salesforce_dev.yaml']:
    data = yaml.safe_load(open(f))
    print(f, data)
"

# Verify get_schedule returns expected values
python -c "
from job_finder.profiles import load_profile, get_schedule
p = load_profile('profiles/default.yaml')
print('default schedule:', get_schedule(p))  # (2, 0)
p2 = load_profile('profiles/salesforce_dev.yaml')
print('sf_dev schedule:', get_schedule(p2))  # (2, 30)
"
```

---

## ACCEPTANCE CRITERIA

- [ ] `python -m job_finder --profile profiles/default.yaml --dry-run --limit 3` runs without error, loads profile keywords as defaults
- [ ] `python -m job_finder --profile profiles/salesforce_dev.yaml --keywords "Python" --dry-run` uses "Python" (explicit flag wins over profile keywords)
- [ ] `pytest tests/test_profiles.py tests/test_notifications.py tests/test_scheduler.py -v` — all pass
- [ ] `pytest tests/ -v` — zero regressions (all existing Phase 1 tests still pass)
- [ ] `docker build -t job-finder .` completes without error
- [ ] Docker image does not contain `.env` (secrets not baked in)
- [ ] `docker compose config` validates without error
- [ ] `docker run --env-file .env job-finder python -m job_finder --dry-run --limit 3` exits 0
- [ ] `from job_finder.scheduler import _run_job` — mock `orchestrator.run` → `_run_job(profile)` calls `orchestrator.run(keywords=..., limit=..., dry_run=False)`
- [ ] `post_summary({})` when `SLACK_WEBHOOK_URL` unset → no HTTP call, no exception
- [ ] `profiles/default.yaml` and `profiles/salesforce_dev.yaml` both parse with `yaml.safe_load` without error
- [ ] `.env.example` documents `SCHEDULE_HOUR`, `SCHEDULE_MINUTE`, `SLACK_WEBHOOK_URL`
- [ ] `requirements.txt` includes `apscheduler>=3.11,<4.0`, `pyyaml>=6.0`, and `pytz>=2024.1`
- [ ] `logs/` is in `.gitignore`

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed immediately after implementation
- [ ] `pytest tests/ -v` passes with zero failures
- [ ] Docker image builds and dry-run succeeds in container
- [ ] `docker compose config` validates
- [ ] `.env.example` updated
- [ ] Acceptance criteria all met

---

## NOTES

### Why BlockingScheduler vs BackgroundScheduler

`BlockingScheduler` is the correct choice for a Docker daemon. It blocks the main thread (making the container's PID 1 the scheduler process) and handles SIGTERM/SIGINT gracefully. `BackgroundScheduler` requires a `while True: time.sleep(1)` keepalive loop and more complex shutdown handling — unnecessary complexity.

### Why No Postgres in docker-compose.yml

JobFinder is a tenant of the existing `sf_postgres` container defined in `Salesforce_Backup/docker-compose.yml`. Including a second Postgres would risk data divergence. The user sets `PG_HOST` to point at the existing container. If they want standalone, they can add a Postgres service themselves.

### Why misfire_grace_time=3600

APScheduler raises a "misfire" warning if a scheduled job is missed (e.g., container was down at 2 AM). With `misfire_grace_time=3600` (1 hour), if the container starts at 2:05 AM, the job fires immediately rather than being skipped. This is desirable for a nightly pipeline.

### Profile Priority Resolution

`config.py env defaults` → `profile YAML values` → `explicit CLI flags`

This means:
- Running without `--profile`: uses env var defaults
- Running with `--profile profiles/default.yaml`: profile values replace env defaults
- Running with `--profile profiles/default.yaml --keywords "Rust Developer"`: profile sets limit, explicit `--keywords` wins for keywords

### Slack Notification

`SLACK_WEBHOOK_URL` is intentionally NOT added to `config.py` because it is purely optional and should not fail startup if absent. Reading it via `os.getenv()` in `notifications.py` keeps it decoupled from the required-var validation.

### APScheduler Version

`apscheduler>=3.11,<4.0` (latest 3.x is 3.11.2 as of Dec 2025) — Do NOT upgrade to 4.x. APScheduler 4.0 has a completely redesigned async-first API with no `BlockingScheduler` or `CronTrigger` classes at the same import paths. The `<4.0` upper bound prevents accidental upgrade. `pytz` is a required runtime dep of APScheduler 3.x — pin it explicitly.

### Docker PID 1 Signal Problem

In Docker, the process started by `CMD` must be PID 1 to receive signals. Shell-form `CMD python ...` spawns `/bin/sh` as PID 1; Python is PID 2+ and never receives SIGTERM from `docker stop`. Use exec-form `CMD ["python", ...]`. Additionally, even with Python as PID 1, Linux suppresses default signal behavior for PID 1 processes. The solution is `init: true` in docker-compose (injects Docker's built-in `tini` as PID 1 signal forwarder) plus explicit `signal.signal(SIGTERM, ...)` in Python as defense-in-depth.

### `coalesce=True` + `misfire_grace_time=3600`

These two job_defaults work together: `misfire_grace_time=3600` means "still fire the job if we're up to 1 hour late" (container restart at 2:05 AM fires immediately). `coalesce=True` means "if we missed N runs, fire exactly once" (container down for 3 days fires once, not 3 times). Both are essential for a nightly daemon.

### Python `-u` Flag in Dockerfile CMD

Without `-u`, Python buffers stdout/stderr output. In Docker, this means `docker logs jf_scheduler` shows nothing for potentially minutes. Always use `python -u` in container CMD entries.
