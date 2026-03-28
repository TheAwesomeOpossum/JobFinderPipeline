# Feature: Phase 6 — Finalization & Production Validation

The following plan should be complete, but it's important that you validate codebase patterns and task sanity before you start implementing.

Pay special attention to the SQL migration column name (`sf_search_config_id`) and its exact usage in `db.py` — the migration and the Python code must stay in sync.

---

## Feature Description

All five implementation phases of the JobFinder pipeline are complete in code and have 154 passing unit/mock tests. This plan validates that the live environment is fully operational: applies the one pending SQL migration, confirms all tests pass, and runs a dry-run end-to-end check against the real Salesforce org and PostgreSQL database. It also closes the stale Phase 4 checkboxes in the PRD, bringing documentation into sync with reality.

## User Story

As a job seeker running the JobFinder pipeline in production,
I want the database schema to match the application code and all validation checks to pass,
So that nightly runs succeed end-to-end without schema errors or silent failures.

## Problem Statement

`sql/04_job_lead_sf_config.sql` adds `sf_search_config_id VARCHAR(18)` to `job_lead`, which `db.mark_pushed()` references in its UPDATE statement (`db.py:70`). If the column is absent in the live database, every `mark_pushed` call on a real run will raise a `psycopg2.errors.UndefinedColumn` exception. The unit tests mock the DB connection and therefore cannot catch this gap.

Separately, PRD Phase 4 checkboxes remain ☐ despite the code being fully implemented — misleading anyone reading the PRD.

## Solution Statement

Apply the one-line SQL migration idempotently (`ADD COLUMN IF NOT EXISTS`), run the full test suite to confirm 154/154 pass, execute a real dry-run against the live environment, and update the PRD Phase 4 checkboxes to ✅.

## Feature Metadata

**Feature Type**: Enhancement / Production Readiness
**Estimated Complexity**: Low
**Primary Systems Affected**: PostgreSQL `job_lead` table, PRD documentation
**Dependencies**: Live PostgreSQL connection (`PG_*` env vars), Salesforce connection (`SF_*` env vars), `.env` populated

---

## CONTEXT REFERENCES

### Relevant Codebase Files — MUST READ BEFORE IMPLEMENTING

- `job_finder/db.py` (lines 49–84) — `mark_pushed()` contains `sf_search_config_id = %(sf_search_config_id)s`; the SQL migration must add this column or every real run fails
- `sql/04_job_lead_sf_config.sql` (lines 1–4) — single `ALTER TABLE … ADD COLUMN IF NOT EXISTS sf_search_config_id VARCHAR(18)` — idempotent and safe to re-run
- `sql/01_job_lead_schema.sql` — baseline schema; confirms `job_lead` table name and existing columns
- `sql/02_job_lead_recruiter_salary.sql` — pattern for previous migrations (column additions)
- `sql/03_job_lead_search_profile.sql` — immediate predecessor migration; same `ADD COLUMN IF NOT EXISTS` pattern
- `job_finder/orchestrator.py` (lines 157–160) — stamps `sf_search_config_id` on each job before DB insert
- `job_finder/sf_config_reader.py` (lines 22–43) — `load_sf_profiles()` reads `Job_Search_Config__c.Id` → `sf_record_id`; this ID flows through orchestrator → `mark_pushed` → `job_lead.sf_search_config_id`
- `.agents/plans/PRD.md` (Phase 4, lines ~486–494) — the six ☐ items to update to ✅

### New Files to Create

None. This is a validation-only phase — no new Python files.

### Files to Update

- `.agents/plans/PRD.md` — change Phase 4 ☐ items to ✅ after confirming implementation

### Relevant Documentation

- [psycopg2 ALTER TABLE docs](https://www.psycopg2.org/docs/cursor.html) — standard cursor.execute() pattern for DDL
- [pytest docs — running tests](https://docs.pytest.org/en/stable/how-to/usage.html) — `python3 -m pytest tests/ -v`

---

## Patterns to Follow

**Migration pattern** (from `sql/03_job_lead_search_profile.sql`):
```sql
ALTER TABLE job_lead
    ADD COLUMN IF NOT EXISTS search_profile VARCHAR(100);
```
Migration 04 follows the exact same pattern — already written correctly.

**DB connection pattern** (`job_finder/db.py:11–22`):
```python
def connect():
    conn = psycopg2.connect(
        host=config.PG_HOST, port=config.PG_PORT,
        dbname=config.PG_DBNAME, user=config.PG_USER,
        password=config.PG_PASSWORD, sslmode=config.PG_SSLMODE,
    )
    conn.autocommit = False
    return conn
```

**PRD checkbox format** — replace `☐` with `✅` for completed items in Phase 4.

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation — Verify Prerequisites

Confirm `.env` is populated and the DB is reachable before touching anything.

**Tasks:**
- Verify all required env vars are set
- Confirm PostgreSQL connection is live
- Confirm current `job_lead` schema (does `sf_search_config_id` column already exist?)

### Phase 2: Core — Apply SQL Migration

Apply `sql/04_job_lead_sf_config.sql` to the live database. The `IF NOT EXISTS` guard makes this idempotent.

**Tasks:**
- Run migration via `psql` CLI
- Confirm column exists post-migration

### Phase 3: Integration — Run Test Suite

Run all 154 tests to confirm nothing is broken.

**Tasks:**
- `python3 -m pytest tests/ -v`
- Confirm 154/154 pass, 0 failures

### Phase 4: Validation — End-to-End Dry Run

Run the CLI in `--dry-run` mode to exercise the full pipeline (search → parse → score → enrich skipped → log) without writing to Salesforce.

**Tasks:**
- CLI dry-run with default keywords
- CLI dry-run with custom keywords and profile
- Confirm logs show expected stages

### Phase 5: Documentation — Update PRD

Mark Phase 4 checkboxes as complete.

---

## STEP-BY-STEP TASKS

### TASK 1 — Verify .env and DB connectivity

- **VALIDATE**: `python3 -c "from job_finder import config, db; conn = db.connect(); conn.close(); print('DB OK')"`
- **GOTCHA**: If this raises `EnvironmentError`, a required env var is missing from `.env`. Populate `.env` from `.env.example` first.
- **GOTCHA**: If `psycopg2.OperationalError`, check `PG_HOST`, `PG_PORT`, `PG_SSLMODE` values.

### TASK 2 — Check if migration 04 is already applied

- **IMPLEMENT**: Query the `information_schema` to see if `sf_search_config_id` exists
- **VALIDATE**: `python3 -c "from job_finder import config, db; conn = db.connect(); cur = conn.cursor(); cur.execute(\"SELECT column_name FROM information_schema.columns WHERE table_name='job_lead' AND column_name='sf_search_config_id'\"); print('EXISTS' if cur.fetchone() else 'MISSING'); conn.close()"`
- If output is `EXISTS` → skip Task 3, migration already applied.
- If output is `MISSING` → proceed to Task 3.

### TASK 3 — Apply SQL migration 04 (only if column is MISSING)

- **IMPLEMENT**: Apply `sql/04_job_lead_sf_config.sql` to the live database
- **PATTERN**: Same as migrations 02 and 03 — `ALTER TABLE … ADD COLUMN IF NOT EXISTS`
- **VALIDATE**: `psql "$DATABASE_URL" -f sql/04_job_lead_sf_config.sql`
  - Or: `python3 -c "from job_finder import config, db; conn = db.connect(); conn.autocommit=True; conn.cursor().execute(\"ALTER TABLE job_lead ADD COLUMN IF NOT EXISTS sf_search_config_id VARCHAR(18)\"); conn.close(); print('Migration applied')"`
- **GOTCHA**: `conn.autocommit` must be `True` for DDL statements when using psycopg2, or use a separate transaction block. The `IF NOT EXISTS` guard means safe to run multiple times.
- **VALIDATE POST**: Re-run Task 2 check and confirm output is `EXISTS`.

### TASK 4 — Run full test suite

- **IMPLEMENT**: Run pytest against all 154 tests
- **VALIDATE**: `cd /home/your-username/Full_Stack_Applications/JobFinder && python3 -m pytest tests/ -v 2>&1 | tail -20`
- **EXPECTED**: `154 passed` with no failures or errors
- **GOTCHA**: Tests use mocks for DB and SF — they do NOT test against the live database. A passing test suite does not confirm the migration is applied; that was confirmed in Tasks 2–3.

### TASK 5 — CLI dry-run: default keywords

- **IMPLEMENT**: Run the pipeline in dry-run mode to confirm all stages (search → deduplicate → parse → score → filter → log) work against real APIs
- **VALIDATE**: `cd /home/your-username/Full_Stack_Applications/JobFinder && python3 -m job_finder --dry-run --limit 5 2>&1`
- **EXPECTED LOG LINES** (in order):
  1. `Found N raw results from Google CSE`
  2. `N new (non-duplicate) results`
  3. `N jobs parsed successfully`
  4. `Dry run complete. Would push N jobs to Salesforce.`
  5. `--- Qualified jobs (would be pushed) ---` with job listings
- **GOTCHA**: `config.py` runs `_require()` at import time, so any missing env var will raise before the pipeline starts.
- **GOTCHA**: Serper API has a daily free-tier quota. A `--limit 5` run consumes ~5 queries per ATS site × 5 sites = ~25 Serper calls.

### TASK 6 — CLI dry-run: Salesforce Developer profile

- **IMPLEMENT**: Dry-run using the Salesforce Developer YAML profile to confirm profile-based configuration works
- **VALIDATE**: `python3 -m job_finder --dry-run --profile profiles/salesforce_dev.yaml --limit 5 --verbose 2>&1`
- **EXPECTED**: Same log structure as Task 5, plus `skills_filtered=N` in the summary if any jobs were dropped by `required_skills` filter.
- **EXPECTED SUMMARY LINE**: `Summary: found=X new=Y parsed=Z skills_filtered=A salary_filtered=B qualified=C pushed=0 skipped=E failed=0`
- **GOTCHA**: The `--dry-run` flag skips Stage 7 (Claude enrichment) and Stage 8 (SF write), so no Anthropic or SF API calls are made.

### TASK 7 — Verify Salesforce connection (non-destructive)

- **IMPLEMENT**: Confirm SF credentials are valid and `Job_Search_Config__c` is queryable
- **VALIDATE**: `python3 -c "from job_finder import sf_writer, sf_config_reader; sf = sf_writer.connect(); profiles = sf_config_reader.load_sf_profiles(sf); print(f'SF OK — {len(profiles)} active config(s) found')"`
- **EXPECTED**: `SF OK — N active config(s) found` (N ≥ 0; if 0, scheduler will fall back to YAML)
- **GOTCHA**: If this raises `SalesforceAuthenticationFailed`, check `SF_USERNAME`, `SF_PASSWORD`, `SF_SECURITY_TOKEN`, `SF_DOMAIN` in `.env`.

### TASK 8 — Update PRD Phase 4 checkboxes

- **UPDATE**: `.agents/plans/PRD.md`
- **IMPLEMENT**: Change the 8 Phase 4 `☐` lines to `✅`:
  - `☐ required_skills hard filter` → `✅ required_skills hard filter`
  - `☐ bonus_skills scoring signal` → `✅ bonus_skills scoring signal`
  - `☐ profiles.py helpers` → `✅ profiles.py helpers`
  - `☐ Multi-profile scheduler` → `✅ Multi-profile scheduler`
  - `☐ profiles/salesforce_architect.yaml` → `✅ profiles/salesforce_architect.yaml`
  - `☐ profiles/salesforce_dev.yaml updated` → `✅ profiles/salesforce_dev.yaml updated`
  - `☐ search_profile stamped on each job` → `✅ search_profile stamped on each job`
  - `☐ sql/03_job_lead_search_profile.sql migration` → `✅ sql/03_job_lead_search_profile.sql migration`
  - `☐ SF requirements handoff: docs/sf_job_search_config_requirements.md` → `✅ SF requirements handoff: docs/sf_job_search_config_requirements.md`
- **VALIDATE**: `grep '☐' .agents/plans/PRD.md | wc -l` → should output `0`

---

## TESTING STRATEGY

### Unit Tests

154 tests across 19 test files. All use `unittest.mock.patch` to mock DB and SF connections. Do not modify existing tests.

Run: `python3 -m pytest tests/ -v`

Expected: 154/154 pass.

### Integration Tests (Manual)

There are no automated integration tests — the pipeline is validated manually via `--dry-run`. See Tasks 5–7.

### Edge Cases Already Covered by Existing Tests

- `test_db.py` — confirms `mark_pushed` SQL includes `sf_search_config_id` in the UPDATE (uses mock cursor)
- `test_sf_config_reader.py` — confirms `load_sf_profiles` and `writeback` map fields correctly
- `test_scheduler.py` — confirms SF-driven flow vs YAML fallback

---

## VALIDATION COMMANDS

### Level 1: Environment Check

```bash
# Verify .env loaded and DB reachable
python3 -c "from job_finder import config, db; conn = db.connect(); conn.close(); print('DB OK')"

# Check if migration 04 already applied
python3 -c "
from job_finder import config, db
conn = db.connect()
cur = conn.cursor()
cur.execute(\"SELECT column_name FROM information_schema.columns WHERE table_name='job_lead' AND column_name='sf_search_config_id'\")
print('EXISTS' if cur.fetchone() else 'MISSING')
conn.close()
"
```

### Level 2: SQL Migration

```bash
# Apply migration (idempotent — safe to run even if already applied)
python3 -c "
from job_finder import config, db
conn = db.connect()
conn.autocommit = True
conn.cursor().execute('ALTER TABLE job_lead ADD COLUMN IF NOT EXISTS sf_search_config_id VARCHAR(18)')
conn.close()
print('Migration 04 applied (or already present)')
"
```

### Level 3: Unit Tests

```bash
cd /home/your-username/Full_Stack_Applications/JobFinder
python3 -m pytest tests/ -v 2>&1 | tail -20
# Expected: 154 passed
```

### Level 4: Manual / CLI Validation

```bash
# Dry-run default keywords (no SF writes, no Claude calls)
python3 -m job_finder --dry-run --limit 5

# Dry-run Salesforce Developer profile with verbose skipped output
python3 -m job_finder --dry-run --profile profiles/salesforce_dev.yaml --limit 5 --verbose

# Verify SF connection and active configs
python3 -c "
from job_finder import sf_writer, sf_config_reader
sf = sf_writer.connect()
profiles = sf_config_reader.load_sf_profiles(sf)
print(f'SF OK — {len(profiles)} active config(s) found')
for p in profiles:
    print(f'  {p[\"profile_name\"]} @ {p[\"schedule_hour\"]:02d}:{p[\"schedule_minute\"]:02d} UTC | limit={p[\"limit\"]}')
"
```

### Level 5: Post-Migration Schema Verification

```bash
python3 -c "
from job_finder import config, db
conn = db.connect()
cur = conn.cursor()
cur.execute(\"\"\"
    SELECT column_name, data_type, character_maximum_length
    FROM information_schema.columns
    WHERE table_name = 'job_lead'
    ORDER BY ordinal_position
\"\"\")
for row in cur.fetchall():
    print(row)
conn.close()
"
# Verify sf_search_config_id VARCHAR(18) appears in the output
```

---

## ACCEPTANCE CRITERIA

- [ ] `python3 -m pytest tests/` → `154 passed, 0 failed`
- [ ] `information_schema.columns` confirms `sf_search_config_id VARCHAR(18)` exists in `job_lead`
- [ ] `python3 -m job_finder --dry-run --limit 5` completes without exception; logs show `Found`, `Dry run complete`
- [ ] `python3 -m job_finder --dry-run --profile profiles/salesforce_dev.yaml --limit 5 --verbose` logs `skills_filtered` count in summary
- [ ] Salesforce connection check returns `SF OK` with ≥ 0 configs
- [ ] PRD Phase 4 contains zero `☐` items (`grep '☐' .agents/plans/PRD.md | wc -l` → `0`)
- [ ] No `psycopg2.errors.UndefinedColumn` exceptions in log output on any task

---

## COMPLETION CHECKLIST

- [ ] Task 1: DB connectivity confirmed
- [ ] Task 2: Migration 04 presence checked
- [ ] Task 3: Migration 04 applied (or confirmed already applied)
- [ ] Task 4: 154/154 tests passing
- [ ] Task 5: Default dry-run produces expected log output
- [ ] Task 6: salesforce_dev profile dry-run shows `skills_filtered` in summary
- [ ] Task 7: Salesforce connection check returns `SF OK`
- [ ] Task 8: PRD Phase 4 checkboxes all changed to ✅
- [ ] All acceptance criteria met

---

## NOTES

### Why only one SQL migration?

Migrations 01–03 were applied during earlier phases. The PRD Phase 5 validation note explicitly states "SQL migration ready to apply" for `04_job_lead_sf_config.sql`. Migrations 01–03 are assumed applied since prior phases ran against the live DB.

### Why are Phase 4 PRD items still ☐?

The code for all Phase 4 items was written during the Phase 4 implementation cycle but the PRD document was not updated. The code evidence:
- `required_skills` filter → `orchestrator.py:122–136` (Stage 4.25)
- `bonus_skills` scoring → `scoring.py` (Signal 6)
- `profiles.py` helpers → `profiles.py:get_skills()`, `get_location()`, `get_seniority()`
- Multi-profile scheduler → `scheduler.py:99–123`
- YAML profiles → `profiles/salesforce_dev.yaml`, `profiles/salesforce_architect.yaml`
- `search_profile` stamp → `orchestrator.py:158–160`
- SQL migration → `sql/03_job_lead_search_profile.sql`
- SF requirements doc → `docs/sf_job_search_config_requirements.md`

### Dry-run vs full run

A `--dry-run` run skips Stage 7 (Claude enrichment) and Stage 8 (SF write), so it does NOT test the Anthropic API or SF write path. To do a full end-to-end test with real SF writes, use a dedicated sandbox org or run `--limit 1` with a `--dry-run=false` and monitor the SF record created. This is intentionally out of scope for this validation plan to avoid creating test noise in the production SF org.

### Scheduler smoke test (optional)

To confirm the scheduler starts without crashing:
```bash
timeout 5 python3 -m job_finder.scheduler --profiles profiles/salesforce_dev.yaml 2>&1 || true
# Expected: sees "Scheduler started with N profile(s)" before timeout kills it
```
