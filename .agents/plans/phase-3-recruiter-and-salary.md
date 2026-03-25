# Phase 3 — Recruiter Extraction + Salary Tracking

**Status: COMPLETE**
**Branch:** JobFinderPipeline

---

## What Was Built

### Recruiter Extraction
- **Greenhouse**: public Job Board API does NOT expose hiring_team. Recruiter fields always `None`.
- **Lever**: extracts `hiring_managers[0]` → `recruiter_name` + `recruiter_email`.
- `enrichment.determine_recruiter_context()` calls Claude to determine internal vs. external.
  - Internal → Contact linked to existing `Job Application` Account.
  - External → `enrich_company(recruiter_firm_name)` called; `Recruiter Account` (Type='Recruiter Account') created with full enrichment (website, address, company research).
- `sf_writer.upsert_recruiter_account()` + `upsert_recruiter_contact()` added.
- `Job_Application__c.Recruiter__c` set after Contact creation.
- Recruiter errors are non-fatal; `SalesforceExpiredSession` re-raised.

### Salary Tracking
- **`job_finder/salary_extractor.py`** — shared utilities:
  - `extract_greenhouse_salary()` — `pay_input_ranges` (cents → dollars), requires `?pay_transparency=true`
  - `extract_lever_salary()` — `salary` object (`per-year` / `per-hour` interval)
  - `extract_salary_from_text()` — regex fallback for Generic parser
  - `format_salary_range_text()` — ≤20 chars for `Salary_Range__c`
  - `annual_midpoint()` / `hourly_midpoint()` — midpoint for Currency fields
- `Annual_Salary__c` = midpoint of annual range (confirmed by user).
- `Hourly_Rate__c` = midpoint of hourly range.
- `Salary_Range__c` = formatted text string (truncated to 20 chars).
- SF trigger auto-converts between Annual and Hourly.

### Salary Threshold Filter
- `MIN_ANNUAL_SALARY` env var (default 0 = disabled).
- Stage 4.5 in orchestrator: hard filter — job dropped if max known salary < threshold.
- Jobs with no salary data pass through (never filtered on missing info).
- Filter confirmed: keep if `max(ceilings) >= threshold` (user confirmed max logic).

### DB Migration
- `sql/02_job_lead_recruiter_salary.sql` — adds `sf_recruiter_account_id`, `sf_recruiter_contact_id`, `annual_salary`, `salary_range_text` to `job_lead`.

---

## Files Changed

| File | Change |
|------|--------|
| `sql/02_job_lead_recruiter_salary.sql` | NEW — migration |
| `job_finder/salary_extractor.py` | NEW — all salary utilities |
| `job_finder/config.py` | Added `MIN_ANNUAL_SALARY` |
| `.env.example` | Added `MIN_ANNUAL_SALARY=0` |
| `job_finder/parser/greenhouse.py` | `pay_transparency=true` param; `pay_input_ranges` extraction; recruiter/salary fields |
| `job_finder/parser/lever.py` | `hiring_managers[0]` for recruiter; `salary` extraction |
| `job_finder/parser/generic.py` | `extract_salary_from_text()` call; recruiter None defaults |
| `job_finder/enrichment.py` | `determine_recruiter_context()` + `enrich_recruiter_jobs()` |
| `job_finder/sf_writer.py` | `upsert_recruiter_account()`, `upsert_recruiter_contact()`, salary fields in `create_job_application()`, `write_job()` → 3-tuple |
| `job_finder/db.py` | `mark_pushed()` extended with recruiter + salary params |
| `job_finder/orchestrator.py` | Stage 4.5 salary filter; Stage 7.5 recruiter enrichment; updated Stage 8/9 |
| `job_finder/__main__.py` | Summary print includes `salary_filtered` |
| `tests/test_salary_extractor.py` | NEW — 26 tests |
| `tests/test_sf_writer_recruiter.py` | NEW — 13 tests |
| `tests/test_parser_greenhouse.py` | +4 tests (salary, recruiter, pay_transparency) |
| `tests/test_parser_lever.py` | +5 tests (recruiter, salary annual/hourly) |
| `tests/test_enrichment.py` | +5 tests (recruiter context, enrich_recruiter_jobs) |
| `tests/test_sf_writer.py` | 3-tuple update + Contact property on MockSF |
| `tests/test_db.py` | +2 tests for updated mark_pushed() |

**Test result: 125/125 passed**

---

## To Deploy

```bash
# Run DB migration against PostgreSQL
psql "$DATABASE_URL" -f sql/02_job_lead_recruiter_salary.sql

# Verify new columns exist
psql "$DATABASE_URL" -c "\d job_lead" | grep -E "recruiter|salary"

# Dry run
python3 -m job_finder --dry-run --limit 3 --keywords "Software Engineer"

# Live run
python3 -m job_finder --limit 3 --keywords "Software Engineer"
```

## Prerequisite (Salesforce Setup)
- `Recruiter__c` lookup field on `Job_Application__c` → Contact (confirmed existing)
- `Account.Type` picklist value `'Recruiter Account'` must exist in Salesforce Setup UI
