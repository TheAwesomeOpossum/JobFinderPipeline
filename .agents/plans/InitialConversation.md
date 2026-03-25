# JobFinder — Initial Planning Conversation

**Date**: 2026-03-25
**Context**: Initial planning session for the JobFinder application

---

## The Core Idea

From a Reddit post: most jobs on LinkedIn/Indeed are sourced from ATS (Applicant Tracking Systems) which Google indexes directly. You can search:

```
site:boards.greenhouse.io united states intext:"apply" (intext:"Software Developer" OR intext:"Software Engineer")
```

Adding `dateRestrict=d1` (last 24 hours) means you're among the first applicants. This tool automates that tactic nightly, enriches job data, and creates Salesforce records for tracking.

---

## What We're Building

A standalone Python CLI + nightly daemon at `~/Full_Stack_Applications/JobFinder/` that:

1. Searches ATS job boards (Greenhouse, Lever, Workday, Ashby, SmartRecruiters) via Google Custom Search API
2. Parses full job details (directly from Greenhouse/Lever public APIs; BeautifulSoup fallback for others)
3. Scores each job for relevance (0–100) using keyword matching + location + seniority
4. Deduplicates by URL hash (local PostgreSQL cache → SF SOQL fallback)
5. Caps at a daily limit (default 20) — top scorers win
6. For qualifying jobs:
   - Calls Claude API to get company mission, core values, and HQ address
   - Creates or finds an `Account` in Salesforce (`Type = 'Job Application'`, billing address populated)
   - Creates a `Job_Application__c` with `Status = 'Draft'` (triage queue)
7. Mirrors successful SF records to PostgreSQL (same existing DB as Salesforce_Backup)

---

## Key Decisions Made

| Decision | Choice | Reason |
|----------|--------|--------|
| Project location | New standalone (`~/Full_Stack_Applications/JobFinder/`) | Clean separation from backup service |
| Search method | Google Custom Search API | Best for broad discovery; requires API key + CSE ID |
| Run mode | Nightly daemon + CLI manual run | Automated but not uncontrolled |
| Qualification gating | `Status = 'Draft'` + relevance score + daily limit | Reuses existing SF picklist; no new SF objects needed |
| SF write path | Direct via `simple_salesforce` | Immediate feedback; PG mirrors after SF ID is returned |
| PostgreSQL staging | New `job_lead` table (seen-URL cache) | Existing `jobapplication` table is a sync mirror, not a staging area |
| Company enrichment | Claude API | Gets mission + core values + HQ address in one call |

---

## Salesforce Data Model (Existing)

**`Job_Application__c`** — target record for each discovered job:
- `Account__c` → Account (company)
- `Job_Title__c`, `Job_Description__c`, `Job_Posting_URL__c`
- `Status__c`: `Draft | Applied | Phone Screen | Interview | Decision | Accepted | Rejected | Withdrawn`
- `Recruiter__c` → Contact
- `Employment_Type__c`: Full Time | Contract | Contract to Hire
- `Work_Classification__c`: W2 | 1099C
- `Annual_Salary__c`, `Hourly_Rate__c`

**`Account`** (Company):
- `Type = 'Job Application'` for hiring companies discovered by this tool
- `Job__c` checkbox — **NOT set by this tool** (only when a `Job__c` employment record exists)
- `Company_Research__c` — populated by Claude API (mission + core values)
- `BillingStreet/City/State/PostalCode/Country` — populated by Claude API (for cover letters/thank-you notes)

**`Account`** (Recruiting Firm — Phase 3):
- `Type = 'Recruiter Account'` — **new picklist value needed** (Phase 3 prerequisite)
- Same enrichment + address fields

**`Contact`** (Recruiter — Phase 3):
- Linked to recruiting firm Account
- Deduped by email address
- Set on `Job_Application__c.Recruiter__c`

---

## Architecture

```
Google Custom Search API
        ↓
    Deduplicator ← job_lead PG table (seen-URL cache)
        ↓              ↑ fallback SOQL
   Job Parser
   (Greenhouse/Lever API, or BeautifulSoup generic)
        ↓
    Scorer (0–100)
        ↓
   Filter + Daily Limit
        ↓
   Claude Enrichment (mission + values + HQ address)
        ↓
   SF Writer
   ├─ upsert Account (Type='Job Application')
   ├─ create Job_Application__c (Status='Draft')
   └─ (Phase 3) upsert Contact + Account (Type='Recruiter Account')
        ↓
   job_lead table updated with SF IDs
        ↓
   Existing CDC listener syncs SF → jobapplication PG table
```

---

## Phases

### Phase 1 — Core Pipeline
End-to-end: search → parse → score → Claude enrichment → SF records

Key files: `config.py`, `search/google_cse.py`, `search/ats_sites.py`, `parser/greenhouse.py`, `parser/lever.py`, `parser/generic.py`, `scoring.py`, `deduplicator.py`, `enrichment.py`, `sf_writer.py`, `db.py`, `orchestrator.py`, `__main__.py`, `sql/01_job_lead_schema.sql`

CLI:
```bash
python -m job_finder --dry-run                          # no SF push
python -m job_finder --keywords "Salesforce Developer" --limit 5
```

### Phase 2 — Automation
Docker service + APScheduler for nightly runs. Multi-keyword YAML profiles.

### Phase 3 — Recruiter Extraction
Extract recruiter info from ATS pages → create Contact + recruiting firm Account.
**Requires**: Deploy `Account.Type = 'Recruiter Account'` picklist value to Salesforce first.

---

## Prerequisites

1. **Google Cloud**: Enable Custom Search API → get API key
2. **Google CSE**: Create Programmable Search Engine with all 5 ATS domains → get CSE ID
3. **Anthropic**: Get `ANTHROPIC_API_KEY`
4. **PostgreSQL**: Run `sql/01_job_lead_schema.sql` against the existing Salesforce_Backup DB
5. **Salesforce Phase 3**: Add `'Recruiter Account'` to `Account.Type` picklist via Setup UI

---

## Existing Code to Reuse (from `~/Docker_Projects/Salesforce_Backup/`)

| Pattern | File |
|---------|------|
| `simple_salesforce` connection | `src/salesforce.py` |
| `_with_backoff()` retry | `src/salesforce.py:103` |
| `psycopg2` connection | `src/database.py` |
| `_require()` env config | `src/config.py` |
| SF create → PG update pattern | `src/write_back.py` |

---

## Notes on `job_lead` Table

The table stores:
- `url_hash` (SHA-256 of normalized URL) — primary dedupe key, checked before any SF call
- `req_number` — job requisition number if present in the posting
- `status`: `new | pushed | skipped | failed`
- `sf_job_app_id` / `sf_account_id` — set after successful SF push

It is NOT a duplicate of the `jobapplication` table. `jobapplication` = SF mirror (written by CDC). `job_lead` = search audit + seen-URL cache (written by this tool).
