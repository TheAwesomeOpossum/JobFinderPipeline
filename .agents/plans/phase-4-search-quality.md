# Phase 4 — Search Quality + Multi-Profile Scheduler

**Status: PLANNED**
**Branch:** JobFinderPipeline

---

## Goals

1. **Eliminate non-technical jobs** — Salesforce Admin, PM, and Consultant roles are currently passing the scorer because the only technical signal is title-based. A required-skills hard filter drops any job whose full description contains none of the specified technical tokens.

2. **Run multiple search profiles simultaneously** — The scheduler currently supports one `--profile` at a time. Phase 4 makes the scheduler accept multiple profiles, each running on its own cron schedule.

3. **Fix silent profile key bug** — `location_preference` and `seniority_targets` in YAML profiles are read but never passed downstream. This is corrected as part of the profile system overhaul.

4. **SF requirements handoff** — The Salesforce-driven config layer (`Job_Search_Config__c`) is designed but deferred. See `docs/sf_job_search_config_requirements.md`.

---

## New Concepts

**`required_skills`** — list of skill tokens. After parsing, a job must contain **at least one** token (any-of) in its full description. Jobs that fail are hard-dropped before scoring — never reach SF or `job_lead`. Leave empty to disable.

**`bonus_skills`** — list of skill tokens that boost the relevance score (+5 each, max +20 total). Not a gate — never excludes a job.

Skill tokens use the exact `fullName` values from the existing `Skills` Global Value Set (used on `Job__c` and `Experience__c`) for vocabulary consistency with the future SF config layer.

---

## What Will Be Built

### `job_finder/profiles.py` — new helpers

```python
def get_skills(profile: dict) -> tuple[list[str], list[str]]:
    """Return (required_skills, bonus_skills). Handles list or comma-string."""

def get_location(profile: dict) -> str | None:
    """Return location_preference from profile (fixes silent-ignore bug)."""

def get_seniority(profile: dict) -> list[str] | None:
    """Return seniority_targets as a list (fixes silent-ignore bug)."""
```

### `job_finder/scoring.py` — Signal 6

New parameter: `bonus_skills: list[str] | None = None`

```python
# Signal 6: bonus skill match (+5 per skill in description, max 20)
if bonus_skills:
    matches = sum(1 for s in bonus_skills if s.lower() in description)
    total += min(matches * 5, 20)
```

### `job_finder/orchestrator.py` — Stage 4.25 + new params

New signature params: `required_skills`, `bonus_skills`, `profile_name`

New summary key: `"skills_filtered": 0`

Stage 4.25 (between parse and salary filter):
```python
def _has_required_skill(job: dict) -> bool:
    if not required_skills:
        return True
    desc = (job.get("description") or "").lower()
    return any(s.lower() in desc for s in required_skills)

parsed_jobs = [j for j in parsed_jobs if _has_required_skill(j)]
```

Profile stamping: `job["search_profile"] = profile_name or "default"` on each job before DB insert.

### `job_finder/__main__.py`

- Read `required_skills`, `bonus_skills` via `get_skills()`
- Read `location_preference` via `get_location()` — overrides `config.LOCATION_PREFERENCE`
- Read `seniority_targets` via `get_seniority()` — overrides `config.SENIORITY_TARGETS`
- Add `--required-skills` and `--bonus-skills` CLI flags (profile values are defaults; flags override)
- `skills_filtered` added to summary print

### `job_finder/scheduler.py` — multi-profile

`--profile` → `--profiles` (accepts multiple paths via `nargs="+"`)

Loops over profiles; creates one APScheduler job per profile with unique ID `job_finder_{stem}`:

```python
for profile_path in args.profiles:
    profile = load_profile(profile_path)
    scheduler.add_job(
        _run_job,
        CronTrigger(hour=hour, minute=minute, timezone=utc),
        args=[profile, profile_path],
        id=f"job_finder_{Path(profile_path).stem}",
        replace_existing=True,
    )
```

### `job_finder/db.py`

Add `search_profile: str | None = None` to `insert_job_lead()` and `mark_pushed()`.

### `job_finder/sf_writer.py`

Add to `create_job_application()` payload:
```python
"Search_Profile__c": (job.get("search_profile") or "")[:100] or None,
```

---

## Files Changed

| File | Change |
|------|--------|
| `job_finder/profiles.py` | Add `get_skills()`, `get_location()`, `get_seniority()` |
| `job_finder/scoring.py` | Add Signal 6 bonus skill scoring; new `bonus_skills` param |
| `job_finder/orchestrator.py` | Stage 4.25 skills filter; `required_skills`, `bonus_skills`, `profile_name` params; profile stamping |
| `job_finder/__main__.py` | `--required-skills`, `--bonus-skills` flags; fix profile key consumption; `skills_filtered` in summary |
| `job_finder/scheduler.py` | `--profiles` (multi); loop over profiles; forward skills/location/seniority |
| `job_finder/db.py` | `search_profile` column in insert/mark_pushed |
| `job_finder/sf_writer.py` | `Search_Profile__c` in `create_job_application()` |
| `profiles/salesforce_dev.yaml` | Add `required_skills`, `bonus_skills` |
| `profiles/salesforce_architect.yaml` | NEW |
| `sql/03_job_lead_search_profile.sql` | NEW — `ADD COLUMN search_profile VARCHAR(100)` |
| `tests/test_scoring_bonus_skills.py` | NEW — Signal 6 unit tests |
| `tests/test_orchestrator_skills_filter.py` | NEW — Stage 4.25 unit tests |

---

## Profile Definitions

### `profiles/salesforce_dev.yaml`

```yaml
keywords: "Salesforce Developer,Salesforce Engineer,SFDC Developer"
required_skills:
  - Apex
  - "Lightning Web Components"
  - "Flow Builder"
  - SOQL
  - "Screen Flows"
bonus_skills:
  - "Batch Apex"
  - "Queueable Apex"
  - "Invocable Apex"
  - "Integration Cloud"
  - CPQ
  - "Experience Cloud"
  - Aura
limit: 10
location_preference: "Remote"
seniority_targets: "mid,senior,staff,principal,lead"
schedule_hour: 2
schedule_minute: 30
```

### `profiles/salesforce_architect.yaml` (new)

```yaml
keywords: "Salesforce Architect,Salesforce Solutions Architect,SFDC Architect,Salesforce Technical Architect"
required_skills:
  - Apex
  - "Lightning Web Components"
  - "Integration Cloud"
bonus_skills:
  - CPQ
  - "Marketing Cloud"
  - "Analytics Cloud"
  - "Experience Cloud"
  - "Field Service Lightning"
limit: 8
location_preference: "Remote"
seniority_targets: "senior,staff,principal,lead,architect"
schedule_hour: 3
schedule_minute: 0
```

---

## Salesforce Prerequisite

Add `Search_Profile__c` as a **Text(100)** field to `JobApplication__c` in Object Manager.
No formula, no trigger — populated by the pipeline at insert time.
Enables list view filters by search profile name.

---

## To Deploy

```bash
# 1. Syntax check
python3 -m py_compile job_finder/profiles.py job_finder/scoring.py \
    job_finder/orchestrator.py job_finder/scheduler.py

# 2. Full test suite
python3 -m pytest tests/ -v

# 3. Dry run — confirm skills_filtered > 0
python3 -m job_finder --profile profiles/salesforce_dev.yaml --dry-run --verbose --limit 10

# 4. Verify multi-profile scheduler starts
python3 -m job_finder.scheduler \
    --profiles profiles/salesforce_dev.yaml profiles/salesforce_architect.yaml &
# Confirm two scheduled jobs logged, then kill

# 5. DB migration
PGPASSWORD=<your_pg_password> psql -h localhost -p 5432 -U sfuser -d salesforce_backup \
    -f sql/03_job_lead_search_profile.sql

# 6. Live run
python3 -m job_finder --profile profiles/salesforce_dev.yaml --limit 1
```

---

## Prerequisite (Salesforce Setup)

- Add `Search_Profile__c` Text(100) to `JobApplication__c` in Object Manager (no deployment tooling needed)
- Future: see `docs/sf_job_search_config_requirements.md` for the full `Job_Search_Config__c` design
