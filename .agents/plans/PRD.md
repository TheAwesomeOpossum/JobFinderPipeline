# JobFinder — Product Requirements Document

**Version:** 1.0
**Date:** 2026-03-25
**Status:** Draft

---

## 1. Executive Summary

JobFinder is a Python-based CLI tool and nightly automation daemon that discovers freshly posted software engineering jobs by querying ATS (Applicant Tracking System) platforms directly via Google Custom Search API. By targeting ATS board domains (Greenhouse, Lever, Workday, Ashby, SmartRecruiters) and restricting results to the last 24 hours, users are among the first applicants to any given posting — a materially higher-response-rate strategy than browsing aggregators like LinkedIn or Indeed.

Each discovered job is parsed, scored for relevance (0–100), deduplicated against a local PostgreSQL cache and Salesforce, enriched with company mission/values/HQ address via the Claude API, and then pushed as a `Job_Application__c` record in Salesforce with `Status = 'Draft'`. A daily cap (default 20) ensures only the most relevant postings make it through.

The MVP goal is a working end-to-end pipeline: Google CSE → parse → score → Claude enrichment → Salesforce `Account` + `Job_Application__c` records — runnable manually via CLI and automated nightly.

---

## 2. Mission

**Automate the discovery of freshly posted, high-relevance software engineering jobs and route them into a structured Salesforce triage queue — so no viable opportunity is missed within the first 24 hours of posting.**

### Core Principles

1. **Freshness first** — only postings from the last 24 hours qualify; early applicants win.
2. **Quality over quantity** — a daily cap and relevance scorer prevent inbox flood.
3. **Salesforce as system of record** — every qualified job becomes a `Job_Application__c`; PostgreSQL is a cache and audit log, not the truth.
4. **Reuse existing patterns** — leverage proven code from `Salesforce_Backup` (retry logic, SF connection, PG connection).
5. **Minimal blast radius** — `--dry-run` mode never writes to SF; all destructive operations require explicit flags.

---

## 3. Target Users

### Primary Persona: Active Job Seeker (Technical)

- Software developer or Salesforce developer conducting an active job search
- Comfortable with CLI tools and Python environments
- Uses Salesforce as a CRM to track job applications
- Pain point: manually searching job boards daily is time-consuming, and most viable postings are days old by the time they're discovered
- Goal: be among the first 20–50 applicants to any given role

### Technical Comfort Level

- Can set environment variables, run Docker Compose, and run a Python module via CLI
- Familiar with PostgreSQL and Salesforce object model at a basic level
- Does not need to modify source code for normal operation

---

## 4. MVP Scope

### Core Functionality

- ✅ Google Custom Search API integration with `dateRestrict=d1` (last 24 hours)
- ✅ Multi-ATS domain search: Greenhouse, Lever, Workday, Ashby, SmartRecruiters
- ✅ Job detail parsing: Greenhouse and Lever public APIs (structured); BeautifulSoup fallback for others
- ✅ Relevance scorer 0–100 (keyword matching + location + seniority signals)
- ✅ URL deduplication via SHA-256 hash in `job_lead` PG table (SOQL fallback)
- ✅ Daily cap (default 20, configurable)
- ✅ Claude API enrichment: company mission, core values, HQ address
- ✅ Salesforce `Account` upsert (`Type = 'Job Application'`, billing address, `Company_Research__c`)
- ✅ Salesforce `Job_Application__c` creation (`Status = 'Draft'`)
- ✅ PostgreSQL `job_lead` table updated with SF IDs post-push
- ✅ CLI: `--dry-run`, `--keywords`, `--limit` flags
- ✅ `--dry-run` mode — full pipeline without writing to SF

### Technical

- ✅ `job_lead` PostgreSQL schema (`sql/01_job_lead_schema.sql`)
- ✅ Environment-variable-based configuration (no secrets in code)
- ✅ Retry/backoff on SF and Google API calls
- ✅ Structured logging to stdout

### Out of Scope (MVP)

- ❌ Docker service / APScheduler nightly automation (Phase 2)
- ❌ Multi-keyword YAML profiles (Phase 2)
- ❌ Recruiter Contact extraction (Phase 3)
- ❌ `Account.Type = 'Recruiter Account'` picklist (Phase 3 prerequisite)
- ❌ Email/Slack notifications on run completion
- ❌ Web UI or dashboard
- ❌ Cover letter generation
- ❌ Indeed/LinkedIn scraping

---

## 5. User Stories

### US-1: Daily Discovery Run
**As a job seeker**, I want to run `python -m job_finder` each morning, so that I see a batch of freshly posted, relevant software jobs without manually searching.

*Example:* Running at 7 AM finds 8 Greenhouse-hosted roles posted overnight, scores them, and creates 8 `Job_Application__c` records in Salesforce with `Status = 'Draft'` for my morning triage.

### US-2: Dry Run Preview
**As a job seeker**, I want to run `python -m job_finder --dry-run`, so that I can see what jobs would be discovered and how they score without touching Salesforce.

*Example:* Before trusting the scorer, I run `--dry-run --limit 50` and inspect the JSON output to verify scoring makes sense.

### US-3: Custom Keyword Search
**As a job seeker**, I want to pass `--keywords "Salesforce Developer"`, so that I can target a specific role type without changing config files.

*Example:* `python -m job_finder --keywords "Salesforce Developer" --limit 5` returns the top 5 Salesforce Developer postings from the last 24 hours.

### US-4: Deduplication
**As a job seeker**, I want already-seen job URLs skipped automatically, so that Salesforce isn't polluted with duplicate records.

*Example:* A Greenhouse posting that was discovered yesterday is identified by its URL hash in `job_lead` and skipped — no duplicate `Job_Application__c` is created.

### US-5: Company Enrichment
**As a job seeker**, I want each new company Account pre-populated with mission, core values, and billing address, so that I have context for cover letters and interview prep without manual research.

*Example:* When Acme Corp is discovered for the first time, Claude returns its mission statement, 3 core values, and HQ address — all written to `Account.Company_Research__c` and billing fields.

### US-6: Salesforce Triage Queue
**As a job seeker**, I want all newly discovered jobs to land in `Status = 'Draft'`, so that I have a clear triage inbox each morning.

*Example:* I open the "Draft Applications" list view in Salesforce and see 6 new records — I then manually promote or discard each one.

### US-7: Daily Limit Cap
**As a job seeker**, I want to cap new records at 20 per run (configurable), so that my triage queue doesn't become unmanageable.

*Example:* The search returns 47 results; only the top 20 by score are pushed to Salesforce; the rest are marked `status = 'skipped'` in `job_lead`.

### US-8 (Technical): PostgreSQL Audit Log
**As a developer**, I want every discovered URL logged in `job_lead` with its status and SF IDs, so that I can audit what was found, pushed, skipped, or failed on any given day.

---

## 6. Core Architecture & Patterns

### High-Level Flow

```
Google Custom Search API (dateRestrict=d1)
        ↓
    Deduplicator ← job_lead PG table (url_hash cache)
        ↓              ↑ fallback: SOQL query
   Job Parser
   (Greenhouse/Lever public APIs → BeautifulSoup fallback)
        ↓
    Scorer (0–100)
        ↓
   Filter + Daily Limit (top N by score)
        ↓
   Claude Enrichment (mission + values + HQ address)
        ↓
   SF Writer
   ├─ upsert Account (Type='Job Application')
   └─ create Job_Application__c (Status='Draft')
        ↓
   job_lead table updated with sf_job_app_id + sf_account_id
        ↓
   Existing CDC listener syncs SF → jobapplication PG table (unchanged)
```

### Directory Structure

```
~/Full_Stack_Applications/JobFinder/
├── job_finder/
│   ├── __init__.py
│   ├── __main__.py          # CLI entry point
│   ├── orchestrator.py      # Top-level pipeline coordinator
│   ├── config.py            # Env-var config (_require() pattern)
│   ├── db.py                # psycopg2 connection + job_lead CRUD
│   ├── deduplicator.py      # URL hash check (PG → SOQL fallback)
│   ├── scoring.py           # 0–100 relevance scorer
│   ├── enrichment.py        # Claude API: mission + values + address
│   ├── sf_writer.py         # SF Account upsert + Job_Application__c create
│   ├── search/
│   │   ├── google_cse.py    # Google Custom Search API client
│   │   └── ats_sites.py     # ATS domain list + query builder
│   └── parser/
│       ├── greenhouse.py    # Greenhouse public API parser
│       ├── lever.py         # Lever public API parser
│       └── generic.py       # BeautifulSoup fallback parser
├── sql/
│   └── 01_job_lead_schema.sql
├── tests/
├── .env.example
├── requirements.txt
├── PRD.md
└── README.md
```

### Design Patterns

- **`_require(key)` config pattern** — raise at startup if env var missing (from `Salesforce_Backup/src/config.py`)
- **`_with_backoff()` retry** — exponential backoff for transient SF/API failures (from `Salesforce_Backup/src/salesforce.py:103`)
- **SF-first, PG-mirror** — write to Salesforce first; update `job_lead` with returned SF ID; CDC handles `jobapplication` table separately
- **Stateless pipeline stages** — each stage (search → parse → score → enrich → write) takes a list in and returns a list out; no shared mutable state

---

## 7. Feature Specifications

### 7.1 Google CSE Search (`search/google_cse.py`)
- Calls `customsearch.googleapis.com/customsearch/v1` with `dateRestrict=d1`
- Query template: `site:{ats_domain} {keywords} intext:"apply"`
- Paginates up to configurable max results per run
- Returns: list of `{url, title, snippet, ats_type}`

### 7.2 ATS Domain Registry (`search/ats_sites.py`)
- Supported domains: `boards.greenhouse.io`, `jobs.lever.co`, `wd1.myworkdayjobs.com`, `jobs.ashbyhq.com`, `jobs.smartrecruiters.com`
- Maps domain → parser type (`greenhouse | lever | workday | ashby | smartrecruiters`)

### 7.3 Job Parsers (`parser/`)
- **Greenhouse**: `GET https://boards-api.greenhouse.io/v1/boards/{company}/jobs/{id}` — returns structured JSON (title, description, location, departments)
- **Lever**: `GET https://api.lever.co/v0/postings/{company}/{id}?mode=json` — returns structured JSON
- **Generic (BeautifulSoup)**: Extract `<title>`, visible text body; normalize whitespace

### 7.4 Relevance Scorer (`scoring.py`)
- Inputs: parsed job dict + config keyword list + location preference
- Scoring breakdown (example):
  - Keyword match in title: +30 pts
  - Keyword match in description: +20 pts
  - Location match (remote / target city): +20 pts
  - Seniority match (mid/senior vs junior): +20 pts
  - Recent posting bonus (< 6 hrs): +10 pts
- Returns: integer 0–100

### 7.5 Deduplicator (`deduplicator.py`)
- Normalizes URL (strip UTM params, trailing slash)
- Computes SHA-256 of normalized URL
- Checks `job_lead.url_hash`; if found, return `seen=True`
- Fallback: SOQL `SELECT Id FROM Job_Application__c WHERE Job_Posting_URL__c = '{url}'`

### 7.6 Claude Enrichment (`enrichment.py`)
- Single Claude API call per new company (not per job)
- Prompt: given company name + homepage URL (if available), return JSON with:
  - `mission`: string
  - `core_values`: list[str]
  - `hq_address`: `{street, city, state, postal_code, country}`
- Gracefully handles Claude returning partial data

### 7.7 Salesforce Writer (`sf_writer.py`)
- **Account upsert**: `upsert` on `Name` + `Type = 'Job Application'`; populates `Company_Research__c`, billing address fields
- **Job_Application__c create**: fields populated from parsed job + enrichment; `Status__c = 'Draft'`
- Returns SF record IDs for PG update

### 7.8 `job_lead` Table (`db.py`)
- Insert on discovery (status = `new`)
- Update to `pushed` + set `sf_job_app_id`, `sf_account_id` on success
- Update to `skipped` when below daily cap threshold
- Update to `failed` on SF write error (preserves error message)

---

## 8. Technology Stack

### Core

| Component | Technology | Notes |
|-----------|-----------|-------|
| Language | Python 3.11+ | Type hints throughout |
| Salesforce client | `simple_salesforce` | Reused from Salesforce_Backup |
| PostgreSQL client | `psycopg2` | Reused from Salesforce_Backup |
| HTTP client | `requests` | Google CSE + ATS public APIs |
| HTML parsing | `beautifulsoup4` + `lxml` | Generic parser fallback |
| AI enrichment | `anthropic` SDK | Claude API for company research |
| CLI | `argparse` (stdlib) | No heavy framework needed for MVP |

### External APIs

| API | Purpose | Auth |
|-----|---------|------|
| Google Custom Search API | Job discovery | `GOOGLE_API_KEY` + `GOOGLE_CSE_ID` |
| Greenhouse Jobs API | Structured job parsing | Public (no auth) |
| Lever Postings API | Structured job parsing | Public (no auth) |
| Anthropic Claude API | Company enrichment | `ANTHROPIC_API_KEY` |
| Salesforce REST API | Record creation | `SF_USERNAME`, `SF_PASSWORD`, `SF_SECURITY_TOKEN` |

### Phase 2 Additions (out of MVP scope)

- `APScheduler` — nightly cron within Docker
- `PyYAML` — multi-keyword profile configs
- Docker Compose — containerized service

---

## 9. Security & Configuration

### Environment Variables

```bash
# Google
GOOGLE_API_KEY=...
GOOGLE_CSE_ID=...

# Anthropic
ANTHROPIC_API_KEY=...

# Salesforce
SF_USERNAME=...
SF_PASSWORD=...
SF_SECURITY_TOKEN=...
SF_DOMAIN=login                # or 'test' for sandbox

# PostgreSQL (existing Salesforce_Backup DB)
PG_HOST=...
PG_PORT=5432
PG_DBNAME=...
PG_USER=...
PG_PASSWORD=...

# Pipeline tuning
DAILY_LIMIT=20
DEFAULT_KEYWORDS=Software Developer,Software Engineer
LOCATION_PREFERENCE=Remote
SENIORITY_TARGETS=mid,senior
```

### Security Scope

- ✅ All secrets via environment variables; no secrets in code or config files
- ✅ `_require()` pattern raises `EnvironmentError` at startup for missing required vars
- ✅ `.env.example` committed; `.env` in `.gitignore`
- ✅ Read-only access to Greenhouse/Lever public APIs (no auth tokens needed)
- ✅ Salesforce writes are additive only (create/upsert, never delete)
- ❌ OAuth2 for Salesforce (username+password flow is sufficient for a personal CLI tool)
- ❌ Secret rotation / vault integration (out of scope)

---

## 10. API Specification

### Google Custom Search

```
GET https://customsearch.googleapis.com/customsearch/v1
  ?key={GOOGLE_API_KEY}
  &cx={GOOGLE_CSE_ID}
  &q=site:boards.greenhouse.io {keywords} intext:"apply"
  &dateRestrict=d1
  &num=10
```

### Greenhouse Jobs API

```
GET https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs/{job_id}

Response:
{
  "id": 4012345,
  "title": "Senior Software Engineer",
  "location": {"name": "Remote"},
  "content": "<html>...",
  "updated_at": "2026-03-25T06:00:00Z"
}
```

### Lever Postings API

```
GET https://api.lever.co/v0/postings/{company_slug}/{posting_id}?mode=json

Response:
{
  "id": "abc-123",
  "text": "Senior Software Engineer",
  "categories": {"location": "Remote", "team": "Engineering"},
  "description": "...",
  "createdAt": 1742900000000
}
```

### Claude Enrichment Request (internal)

```python
prompt = f"""
Return JSON only. For the company "{company_name}", provide:
- mission: one-sentence company mission
- core_values: list of 3-5 core values (strings)
- hq_address: {{street, city, state, postal_code, country}}

If any field is unknown, use null.
"""
```

---

## 11. Success Criteria

### MVP Success Definition

The pipeline runs end-to-end without errors, discovers at least one real job posting per run, creates valid Salesforce records, and marks them correctly in PostgreSQL.

### Functional Requirements

- ✅ `python -m job_finder` runs without crashing on a machine with valid env vars
- ✅ `--dry-run` produces structured log output without writing to SF
- ✅ At least one job per ATS type is correctly parsed
- ✅ Duplicate URLs are not pushed to Salesforce on subsequent runs
- ✅ All new `Job_Application__c` records have `Status__c = 'Draft'`
- ✅ All new `Account` records have `Type = 'Job Application'`
- ✅ `Company_Research__c` is populated for new accounts
- ✅ `BillingCity`, `BillingState`, `BillingCountry` populated where Claude returned data
- ✅ `job_lead` rows have correct status (`pushed | skipped | failed`) after each run
- ✅ Daily limit is respected (never more than `DAILY_LIMIT` SF writes per run)

### Quality Indicators

- Scorer correctly ranks "Senior Software Engineer - Remote" above "Junior QA Analyst - On-site"
- No SF API calls are made in `--dry-run` mode
- Backoff retries succeed on transient SF 503s without crashing
- Missing optional fields (salary, recruiter) don't raise exceptions

---

## 12. Implementation Phases

### Phase 1 — Core Pipeline (MVP)

**Goal:** Working end-to-end pipeline, runnable via CLI.

**Deliverables:**
- ✅ `sql/01_job_lead_schema.sql` — `job_lead` table
- ✅ `config.py` — env var loading with `_require()`
- ✅ `db.py` — PG connection + `job_lead` CRUD
- ✅ `search/ats_sites.py` — domain registry
- ✅ `search/google_cse.py` — CSE client with pagination
- ✅ `deduplicator.py` — URL hash + SOQL fallback
- ✅ `parser/greenhouse.py` — Greenhouse API parser
- ✅ `parser/lever.py` — Lever API parser
- ✅ `parser/generic.py` — BeautifulSoup fallback
- ✅ `scoring.py` — 0–100 relevance scorer
- ✅ `enrichment.py` — Claude API company enrichment
- ✅ `sf_writer.py` — Account upsert + Job_Application__c create
- ✅ `orchestrator.py` — pipeline coordinator
- ✅ `__main__.py` — CLI with `--dry-run`, `--keywords`, `--limit`
- ✅ `.env.example`
- ✅ `requirements.txt`

**Validation:** `python -m job_finder --dry-run --limit 5` returns 5 scored results; full run creates SF records.

---

### Phase 2 — Automation

**Goal:** Unattended nightly runs via Docker.

**Deliverables:**
- ✅ `Dockerfile` + `docker-compose.yml`
- ✅ APScheduler nightly job (configurable time, default 2 AM)
- ✅ YAML keyword profiles (`profiles/default.yaml`, `profiles/salesforce_dev.yaml`)
- ✅ Run summary log (jobs found / pushed / skipped / failed)
- ✅ Optional: email/Slack notification on completion

**Validation:** Container runs nightly for 7 days without intervention; `job_lead` shows daily entries.

---

### Phase 3 — Recruiter Extraction

**Goal:** Identify and record recruiters from ATS postings.

**Prerequisites:**
- Deploy `Account.Type = 'Recruiter Account'` picklist value to Salesforce (manual Setup UI step)

**Deliverables:**
- ✅ Recruiter name/email extraction from Greenhouse/Lever posting payloads
- ✅ `Account` upsert for recruiting firm (`Type = 'Recruiter Account'`)
- ✅ `Contact` upsert (deduped by email)
- ✅ `Job_Application__c.Recruiter__c` populated

**Validation:** Jobs with recruiter info have linked `Contact` records in Salesforce.

---

## 13. Future Considerations

- **Cover letter draft generation** — use Claude to generate a tailored cover letter from `Company_Research__c` + job description
- **Indeed/LinkedIn scraping** — extend search beyond ATS-direct postings (requires Playwright/Selenium; higher maintenance)
- **Relevance feedback loop** — user marks applications as "strong match" in SF; score weights updated accordingly
- **Multi-user support** — parameterize SF credentials per user profile
- **Slack/email digest** — morning summary of overnight discoveries
- **Interview prep assistant** — Claude generates STAR-format prep questions from job description + company values

---

## 14. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Google CSE quota exhaustion (100 free queries/day) | Pipeline stops mid-run | Implement query budgeting; log usage; consider paid tier |
| ATS sites changing HTML structure | Generic parser returns garbage | Unit tests against saved HTML fixtures; alert on low parse confidence scores |
| Claude API latency on large batches | Run takes >10 min | Batch company enrichment; cache by company name in `job_lead` or a separate `company_cache` table |
| Salesforce API governor limits | SF writes fail | `_with_backoff()` + daily cap keeps volume well below limits; monitor with SF debug logs |
| `job_lead` / `jobapplication` table confusion | Duplicate records or missed dedup | Clear naming convention + `job_lead` comments documenting its role as cache, not mirror |

---

## 15. Appendix

### Existing Code to Reuse

| Pattern | Source File |
|---------|-------------|
| `simple_salesforce` connection | `~/Docker_Projects/Salesforce_Backup/src/salesforce.py` |
| `_with_backoff()` retry decorator | `~/Docker_Projects/Salesforce_Backup/src/salesforce.py:103` |
| `psycopg2` connection helper | `~/Docker_Projects/Salesforce_Backup/src/database.py` |
| `_require()` env config | `~/Docker_Projects/Salesforce_Backup/src/config.py` |
| SF create → PG update pattern | `~/Docker_Projects/Salesforce_Backup/src/write_back.py` |

### Salesforce Object Reference

| Object | Key Fields | Notes |
|--------|-----------|-------|
| `Job_Application__c` | `Job_Title__c`, `Job_Description__c`, `Job_Posting_URL__c`, `Status__c`, `Account__c`, `Recruiter__c`, `Employment_Type__c` | Target record; created with `Status='Draft'` |
| `Account` | `Name`, `Type`, `Company_Research__c`, `BillingStreet/City/State/PostalCode/Country` | Upserted on `Name`; `Type='Job Application'` |

### Setup Checklist

1. ☐ Google Cloud: Enable Custom Search API → obtain `GOOGLE_API_KEY`
2. ☐ Google CSE: Create Programmable Search Engine with all 5 ATS domains → obtain `GOOGLE_CSE_ID`
3. ☐ Anthropic: Obtain `ANTHROPIC_API_KEY`
4. ☐ PostgreSQL: Run `sql/01_job_lead_schema.sql` against the existing Salesforce_Backup database
5. ☐ Copy `.env.example` → `.env` and populate all values
6. ☐ (Phase 3 only) Add `'Recruiter Account'` to `Account.Type` picklist in Salesforce Setup UI
