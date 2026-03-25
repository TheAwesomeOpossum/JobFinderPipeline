# Feature: Phase 1 MVP — End-to-End Job Discovery Pipeline

The following plan is complete, but validate documentation and codebase patterns before implementing.
Pay special attention to naming of existing utils, types, and models. Import from the right files.

## Feature Description

Build the complete JobFinder Phase 1 MVP: a Python CLI tool that queries Google Custom Search API
for freshly posted jobs on ATS platforms (Greenhouse, Lever, Workday, Ashby, SmartRecruiters),
parses job details, scores relevance, deduplicates against PostgreSQL and Salesforce, enriches
qualifying jobs via Claude API, and pushes `Job_Application__c` + `Account` records to Salesforce.

## User Story

As an active job seeker
I want to run `python -m job_finder` each morning
So that I have a curated inbox of freshly posted, high-relevance engineering jobs in Salesforce ready for triage

## Problem Statement

Manually searching job boards daily is time-consuming, and most viable postings are days old by
discovery. ATS platforms (Greenhouse, Lever, etc.) publish structured job data that Google indexes
directly — adding `dateRestrict=d1` surfaces only the last 24 hours of postings, positioning the
applicant among the first 20–50 to apply.

## Solution Statement

A stateless pipeline: Google CSE → deduplicate → parse → score → filter+cap → Claude enrich →
Salesforce write → PostgreSQL update. Each stage takes a list in, returns a list out. No shared
mutable state between stages. CLI supports `--dry-run`, `--keywords`, `--limit` flags.

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: High
**Primary Systems Affected**: Google CSE, Greenhouse API, Lever API, Anthropic Claude API, Salesforce, PostgreSQL
**Dependencies**: `simple-salesforce`, `psycopg2-binary`, `requests`, `beautifulsoup4`, `lxml`, `anthropic`, `python-dotenv`

---

## CONTEXT REFERENCES

### Relevant Codebase Files — MUST READ BEFORE IMPLEMENTING

- `~/Docker_Projects/Salesforce_Backup/src/config.py` (lines 9–13) — `_require()` pattern: exact function to mirror in `job_finder/config.py`
- `~/Docker_Projects/Salesforce_Backup/src/salesforce.py` (lines 14–27) — `connect()` to Salesforce via `simple_salesforce`: mirror for `sf_writer.py`
- `~/Docker_Projects/Salesforce_Backup/src/salesforce.py` (lines 103–115) — `_with_backoff()` retry: copy verbatim into `sf_writer.py` (or a shared `utils.py`)
- `~/Docker_Projects/Salesforce_Backup/src/database.py` (lines 11–22) — psycopg2 `connect()`: mirror in `db.py`
- `~/Docker_Projects/Salesforce_Backup/src/write_back.py` (lines 59–106) — SF write loop with per-record error handling + PG status update: architectural template for `orchestrator.py`

### New Files to Create

```
job_finder/
├── __init__.py
├── __main__.py
├── config.py
├── db.py
├── deduplicator.py
├── scoring.py
├── enrichment.py
├── sf_writer.py
├── orchestrator.py
├── search/
│   ├── __init__.py
│   ├── ats_sites.py
│   └── google_cse.py
└── parser/
    ├── __init__.py
    ├── greenhouse.py
    ├── lever.py
    └── generic.py
sql/
└── 01_job_lead_schema.sql
tests/
├── __init__.py
├── test_config.py
├── test_db.py
├── test_deduplicator.py
├── test_scoring.py
├── test_enrichment.py
├── test_sf_writer.py
├── test_search_google_cse.py
├── test_search_ats_sites.py
├── test_parser_greenhouse.py
├── test_parser_lever.py
└── test_parser_generic.py
requirements.txt
.env.example
```

### Relevant Documentation — READ BEFORE IMPLEMENTING

- [Google Custom Search API Reference](https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list)
  - `num` max is **10** per request; `start` max is 91 (total 100 results hard cap)
  - `dateRestrict=d1` = last 1 day by Google's index date (not post date — may lag 1–3 days)
  - 100 free queries/day; $5/1000 beyond that
- [Greenhouse Job Board API](https://developers.greenhouse.io/job-board.html)
  - `GET https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs/{job_id}?content=true`
  - **GOTCHA**: `?content=true` is required — without it, `content` field is absent
  - `first_published` = post date; `updated_at` may equal `first_published`
- [Lever Postings API](https://github.com/lever/postings-api/blob/master/README.md)
  - `GET https://api.lever.co/v0/postings/{company_slug}/{posting_id}?mode=json`
  - **GOTCHA**: `createdAt` is **millisecond epoch** — divide by 1000 before `datetime.fromtimestamp()`
  - **GOTCHA**: Without `?mode=json`, the endpoint returns HTML, not JSON
- [simple-salesforce Docs](https://simple-salesforce.readthedocs.io/en/latest/)
  - **CRITICAL GOTCHA**: `sf.Account.upsert('Name/...')` is unreliable — `Name` is NOT an `idLookup` field
  - Use query-then-create pattern: match on `Website` first (more unique than Name), fall back to `Name + Type` if no website available
  - `sf.Job_Application__c.create(payload)` returns `{'id': '...', 'success': True, 'errors': []}`
- [Anthropic Python SDK](https://docs.anthropic.com/en/api/getting-started)
  - Use `output_config` with `json_schema` (SDK ≥ 0.77.0) for guaranteed JSON — eliminates markdown fences
  - `response.content[0].text` → `json.loads()`
  - Model: `claude-sonnet-4-6`, `max_tokens=1024`

### Patterns to Follow

**`_require()` config pattern** (mirror from `Salesforce_Backup/src/config.py:9–13`):
```python
def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(f"Required environment variable '{key}' is not set.")
    return value
```

**`_with_backoff()` retry** (mirror from `Salesforce_Backup/src/salesforce.py:103–115`):
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
            logger.warning("Attempt %d failed: %s. Retrying in %ds...", attempt + 1, exc, wait)
            time.sleep(wait)
```

**Logging pattern** (match Salesforce_Backup style):
```python
import logging
logger = logging.getLogger(__name__)
# Usage: logger.info("Querying: %s", soql[:200])
```

**Stateless pipeline stages** — each function signature:
```python
def parse_job(raw: dict) -> dict | None:   # returns enriched dict or None on failure
def score_job(job: dict) -> dict:           # mutates job["score"]; returns same dict
def enrich_jobs(jobs: list[dict]) -> list[dict]:  # one Claude call per unique company
```

**Account query-then-create pattern** (Website-first match, Name fallback):
```python
# Primary match: Website is more unique than Name
website = job.get("website_url") or ""
safe_name = job["company"].replace("'", "\\'")

if website:
    result = sf.query(
        f"SELECT Id FROM Account WHERE Website = '{website}' AND Type = 'Job Application'"
    )
else:
    result = sf.query(
        f"SELECT Id FROM Account WHERE Name = '{safe_name}' AND Type = 'Job Application'"
    )

if result['totalSize'] == 1:
    sf.Account.update(result['records'][0]['Id'], payload)
    account_id = result['records'][0]['Id']
else:
    account_id = sf.Account.create(payload)['id']
# payload always includes Website so future runs match on it
```

**URL normalization + SHA-256 hash**:
```python
from urllib.parse import urlparse, urlunparse, urlencode, parse_qsl
import hashlib
UTM_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"}
def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip().rstrip("/"))
    clean_qs = urlencode([(k, v) for k, v in parse_qsl(parsed.query) if k not in UTM_PARAMS])
    return urlunparse(parsed._replace(scheme=parsed.scheme.lower(),
                                       netloc=parsed.netloc.lower(),
                                       query=clean_qs, fragment=""))
def hash_url(url: str) -> str:
    return hashlib.sha256(normalize_url(url).encode("utf-8")).hexdigest()
```

**psycopg2 parameterized queries** — always use `%(key)s` syntax with dict, never f-strings:
```python
cur.execute("INSERT INTO job_lead (url_hash, url) VALUES (%(url_hash)s, %(url)s)", row_dict)
```

**Internal Job dict schema** — this flows through every pipeline stage:
```python
{
    # Set by search stage
    "url": str,
    "url_hash": str,
    "title": str,
    "company": str,
    "ats_type": str,       # "greenhouse"|"lever"|"workday"|"ashby"|"smartrecruiters"
    "snippet": str,        # from Google CSE
    # Set by parser stage
    "description": str,    # plain text for scoring + SF
    "description_html": str,
    "location": str,
    "department": str | None,
    "posted_at": str | None,   # ISO 8601 YYYY-MM-DD
    # Set by scorer
    "score": int,              # 0–100
    # Set by enrichment stage
    "mission": str | None,
    "core_values": list[str],
    "hq_address": dict | None,  # {street, city, state, postal_code, country}
    "website_url": str | None,  # company homepage URL — used as Account.Website + upsert key
    # Set after SF write
    "sf_job_app_id": str | None,
    "sf_account_id": str | None,
}
```

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation

Set up the project scaffolding, SQL schema, dependencies, and config loading before any business logic.

**Tasks:**
- Create `sql/01_job_lead_schema.sql` with `job_lead` table
- Create `requirements.txt` and `.env.example`
- Create `job_finder/config.py` (env var loading with `_require()`)
- Create package `__init__.py` files for `job_finder/`, `job_finder/search/`, `job_finder/parser/`

### Phase 2: Core Data Layer

Build the PostgreSQL CRUD layer and URL deduplication logic.

**Tasks:**
- Create `job_finder/db.py` — psycopg2 connection + `job_lead` CRUD functions
- Create `job_finder/deduplicator.py` — URL normalization, SHA-256 hash, PG + SOQL fallback check

### Phase 3: Search & Parse

Implement the discovery and parsing stages.

**Tasks:**
- Create `job_finder/search/ats_sites.py` — ATS domain registry + query builder
- Create `job_finder/search/google_cse.py` — paginated CSE client
- Create `job_finder/parser/greenhouse.py` — Greenhouse Jobs API parser
- Create `job_finder/parser/lever.py` — Lever Postings API parser
- Create `job_finder/parser/generic.py` — BeautifulSoup fallback parser
- Create `job_finder/scoring.py` — 0–100 relevance scorer

### Phase 4: Enrichment & Write

Implement the outbound integrations.

**Tasks:**
- Create `job_finder/enrichment.py` — Claude API company research
- Create `job_finder/sf_writer.py` — Salesforce Account + Job_Application__c write
- Create `job_finder/orchestrator.py` — pipeline coordinator
- Create `job_finder/__main__.py` — CLI entry point

### Phase 5: Testing

Write unit tests covering all modules.

---

## STEP-BY-STEP TASKS

### 1. CREATE `sql/01_job_lead_schema.sql`

- **IMPLEMENT**: `job_lead` table with all columns per PRD §7.8; include trigger for `updated_at`
- **SCHEMA**:
```sql
CREATE TABLE IF NOT EXISTS job_lead (
    id              SERIAL PRIMARY KEY,
    url_hash        CHAR(64)     NOT NULL UNIQUE,
    url             TEXT         NOT NULL,
    title           TEXT,
    company         TEXT,
    ats_type        VARCHAR(30),
    score           INTEGER,
    req_number      TEXT,
    status          VARCHAR(20)  NOT NULL DEFAULT 'new',
    sf_job_app_id   VARCHAR(18),
    sf_account_id   VARCHAR(18),
    error_message   TEXT,
    discovered_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_job_lead_status ON job_lead (status);
CREATE INDEX IF NOT EXISTS idx_job_lead_discovered ON job_lead (discovered_at DESC);
-- trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER trg_job_lead_updated_at
BEFORE UPDATE ON job_lead
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```
- **VALIDATE**: `psql $DATABASE_URL -f sql/01_job_lead_schema.sql && echo "OK"`

---

### 2. CREATE `requirements.txt`

- **IMPLEMENT**: Pin exact versions; include all runtime and test dependencies
```
simple-salesforce==1.12.6
psycopg2-binary==2.9.9
python-dotenv==1.0.1
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=5.0.0
anthropic>=0.86.0
pytest>=8.0.0
pytest-mock>=3.14.0
```
- **VALIDATE**: `pip install -r requirements.txt`

---

### 3. CREATE `.env.example`

- **IMPLEMENT**: All env vars from PRD §9; comments explaining each group
```bash
# Google Custom Search
GOOGLE_API_KEY=your_google_api_key
GOOGLE_CSE_ID=your_cse_id

# Anthropic
ANTHROPIC_API_KEY=your_anthropic_api_key

# Salesforce (username+password flow)
SF_USERNAME=your.email@example.com
SF_PASSWORD=yourSalesforcePassword
SF_SECURITY_TOKEN=yourSecurityToken
SF_DOMAIN=login

# PostgreSQL (reuse Salesforce_Backup DB)
PG_HOST=localhost
PG_PORT=5432
PG_DBNAME=salesforce_backup
PG_USER=sfuser
PG_PASSWORD=changeme
PG_SSLMODE=require

# Pipeline tuning
DAILY_LIMIT=20
DEFAULT_KEYWORDS=Software Developer,Software Engineer
LOCATION_PREFERENCE=Remote
SENIORITY_TARGETS=mid,senior
```
- **VALIDATE**: `diff .env.example .env.example` (syntax check; actual values go in `.env`)

---

### 4. CREATE `job_finder/__init__.py`, `job_finder/search/__init__.py`, `job_finder/parser/__init__.py`

- **IMPLEMENT**: All three are empty files (package markers)
- **VALIDATE**: `python -c "import job_finder; import job_finder.search; import job_finder.parser; print('OK')"`

---

### 5. CREATE `job_finder/config.py`

- **IMPLEMENT**: Load all env vars; `_require()` for mandatory vars; sensible defaults for optional
- **PATTERN**: Mirror `Salesforce_Backup/src/config.py:9–13` exactly for `_require()`
- **IMPORTS**: `os`, `python-dotenv load_dotenv`
```python
import os
from dotenv import load_dotenv

load_dotenv()

def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(f"Required environment variable '{key}' is not set.")
    return value

# Google
GOOGLE_API_KEY = _require("GOOGLE_API_KEY")
GOOGLE_CSE_ID  = _require("GOOGLE_CSE_ID")

# Anthropic
ANTHROPIC_API_KEY = _require("ANTHROPIC_API_KEY")

# Salesforce
SF_USERNAME       = _require("SF_USERNAME")
SF_PASSWORD       = _require("SF_PASSWORD")
SF_SECURITY_TOKEN = _require("SF_SECURITY_TOKEN")
SF_DOMAIN         = os.getenv("SF_DOMAIN", "login")

# PostgreSQL
PG_HOST    = os.getenv("PG_HOST", "localhost")
PG_PORT    = int(os.getenv("PG_PORT", "5432"))
PG_DBNAME  = _require("PG_DBNAME")
PG_USER    = _require("PG_USER")
PG_PASSWORD = _require("PG_PASSWORD")
PG_SSLMODE = os.getenv("PG_SSLMODE", "require")

# Pipeline tuning
DAILY_LIMIT         = int(os.getenv("DAILY_LIMIT", "20"))
DEFAULT_KEYWORDS    = os.getenv("DEFAULT_KEYWORDS", "Software Developer,Software Engineer")
LOCATION_PREFERENCE = os.getenv("LOCATION_PREFERENCE", "Remote")
SENIORITY_TARGETS   = [s.strip().lower() for s in os.getenv("SENIORITY_TARGETS", "mid,senior").split(",")]

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
```
- **GOTCHA**: `config.py` runs `_require()` on import — missing vars crash at startup, not mid-run
- **VALIDATE**: `python -c "import job_finder.config; print('Config OK')"`

---

### 6. CREATE `job_finder/db.py`

- **IMPLEMENT**: psycopg2 connection + all `job_lead` CRUD operations the orchestrator needs
- **PATTERN**: Mirror `Salesforce_Backup/src/database.py:11–22` for `connect()`
- **IMPORTS**: `psycopg2`, `job_finder.config`
- **FUNCTIONS** (implement all):
  - `connect() -> psycopg2.connection` — returns connection with `autocommit=False`
  - `insert_job_lead(conn, job: dict) -> int` — INSERT with `ON CONFLICT (url_hash) DO NOTHING`; returns PG row id
  - `mark_pushed(conn, url_hash: str, sf_job_app_id: str, sf_account_id: str) -> None`
  - `mark_skipped(conn, url_hash: str) -> None`
  - `mark_failed(conn, url_hash: str, error_message: str) -> None`
  - `url_hash_exists(conn, url_hash: str) -> bool` — used by deduplicator
- **GOTCHA**: Use `%(key)s` parameterized placeholders with dict, never f-strings in SQL
- **VALIDATE**: `python -c "from job_finder.db import connect; print('db OK')"`

---

### 7. CREATE `job_finder/deduplicator.py`

- **IMPLEMENT**: URL normalization, SHA-256 hash, PG lookup, SOQL fallback
- **IMPORTS**: `hashlib`, `urllib.parse`, `logging`, `job_finder.db`, `simple_salesforce.Salesforce`
- **FUNCTIONS**:
  - `normalize_url(url: str) -> str` — strip UTM params, trailing slash, lowercase scheme+host
  - `hash_url(url: str) -> str` — SHA-256 hex of normalized URL
  - `is_duplicate(conn, sf, url: str) -> bool`:
    1. Compute `url_hash = hash_url(url)`
    2. Call `db.url_hash_exists(conn, url_hash)` — if True, return True
    3. Fallback: SOQL `SELECT Id FROM Job_Application__c WHERE Job_Posting_URL__c = '{url}'`; if any records, return True
    4. Return False

```python
UTM_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"}

def normalize_url(url: str) -> str:
    from urllib.parse import urlparse, urlunparse, urlencode, parse_qsl
    parsed = urlparse(url.strip().rstrip("/"))
    clean_qs = urlencode([(k, v) for k, v in parse_qsl(parsed.query) if k not in UTM_PARAMS])
    return urlunparse(parsed._replace(
        scheme=parsed.scheme.lower(), netloc=parsed.netloc.lower(),
        query=clean_qs, fragment=""
    ))

def hash_url(url: str) -> str:
    import hashlib
    return hashlib.sha256(normalize_url(url).encode("utf-8")).hexdigest()
```

- **GOTCHA**: The SOQL fallback uses the raw (non-normalized) URL for the SF query — SF stores whatever URL was pushed, which may not be normalized
- **VALIDATE**: `python -c "from job_finder.deduplicator import hash_url; print(hash_url('https://boards.greenhouse.io/acme/jobs/123?utm_source=foo'))"`

---

### 8. CREATE `job_finder/search/ats_sites.py`

- **IMPLEMENT**: ATS domain list, domain→parser-type mapping, query builder
- **IMPORTS**: none (stdlib only)
- **CONTENT**:
```python
# Map ATS domain → parser type
ATS_SITES = [
    {"domain": "boards.greenhouse.io",      "ats_type": "greenhouse"},
    {"domain": "jobs.lever.co",             "ats_type": "lever"},
    {"domain": "wd1.myworkdayjobs.com",     "ats_type": "workday"},
    {"domain": "jobs.ashbyhq.com",          "ats_type": "ashby"},
    {"domain": "jobs.smartrecruiters.com",  "ats_type": "smartrecruiters"},
]

def build_query(domain: str, keywords: str) -> str:
    """Build a Google CSE query string for a given ATS domain."""
    return f'site:{domain} {keywords} intext:"apply"'
```
- **VALIDATE**: `python -c "from job_finder.search.ats_sites import ATS_SITES, build_query; print(build_query('boards.greenhouse.io', 'Software Engineer'))"`

---

### 9. CREATE `job_finder/search/google_cse.py`

- **IMPLEMENT**: Paginated Google CSE client; returns raw result list across all ATS sites
- **IMPORTS**: `requests`, `logging`, `job_finder.config`, `job_finder.search.ats_sites`
- **CONSTANTS**: `CSE_ENDPOINT = "https://customsearch.googleapis.com/customsearch/v1"`, `MAX_RESULTS_PER_QUERY = 100`, `PAGE_SIZE = 10`
- **FUNCTIONS**:
  - `search_one_site(domain: str, ats_type: str, keywords: str, max_results: int = 10) -> list[dict]`:
    - Paginate with `start=1, 11, 21, ...` up to `min(max_results, 100)`
    - Each page: GET with params `key`, `cx`, `q`, `num=10`, `start`, `dateRestrict=d1`
    - Parse response `items` list; each item → `{"url": item["link"], "title": item["title"], "snippet": item.get("snippet",""), "ats_type": ats_type}`
    - If `items` absent from response, stop pagination (no more results)
    - On HTTP error, log and return accumulated results (don't crash)
  - `search_all_ats(keywords: str, max_per_site: int = 10) -> list[dict]`:
    - Loop over `ATS_SITES`, call `search_one_site` for each
    - Return combined flat list
- **GOTCHA**: `num` max is 10 — never set higher; API ignores values > 10
- **GOTCHA**: 100 free queries/day total — with 5 ATS sites × N pages, budget carefully; default to 1 page per site (10 results each = 5 queries)
- **VALIDATE**: `python -c "from job_finder.search.google_cse import search_all_ats" # (dry import only)`

---

### 10. CREATE `job_finder/parser/greenhouse.py`

- **IMPLEMENT**: Parse job details from Greenhouse Jobs Board API
- **IMPORTS**: `re`, `requests`, `logging`, `datetime`
- **URL PATTERN**: `https://boards.greenhouse.io/{company_slug}/jobs/{job_id}`
  - Also handle: `https://job-boards.greenhouse.io/{company_slug}/jobs/{job_id}`
- **FUNCTIONS**:
  - `can_parse(url: str) -> bool` — returns True if URL matches greenhouse pattern
  - `parse(raw: dict) -> dict | None`:
    1. Extract `company_slug` + `job_id` from `raw["url"]` via regex
    2. `GET https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs/{job_id}?content=true`
    3. Map response fields to internal job dict schema
    4. `posted_at = data.get("first_published", "")[:10]` (ISO date prefix)
    5. Strip HTML from `content` for `description` plain text (use `BeautifulSoup(content, "lxml").get_text(" ")`)
    6. Return dict on success; log and return None on error
- **REGEX**:
```python
_GH_RE = re.compile(r'(?:boards|job-boards)\.greenhouse\.io/([^/]+)/jobs/(\d+)')
```
- **GOTCHA**: Must append `?content=true` — without it, `content` key is absent from response
- **GOTCHA**: `content` field is HTML — strip to plain text before storing in `description`
- **VALIDATE**: Unit test with a fixture response dict (see testing section)

---

### 11. CREATE `job_finder/parser/lever.py`

- **IMPLEMENT**: Parse job details from Lever Postings API
- **IMPORTS**: `re`, `requests`, `logging`, `datetime`
- **URL PATTERN**: `https://jobs.lever.co/{company_slug}/{posting_id}`
- **FUNCTIONS**:
  - `can_parse(url: str) -> bool`
  - `parse(raw: dict) -> dict | None`:
    1. Extract slugs via regex
    2. `GET https://api.lever.co/v0/postings/{company_slug}/{posting_id}?mode=json`
    3. Map response fields
    4. `posted_at = datetime.fromtimestamp(data["createdAt"] / 1000).strftime("%Y-%m-%d")`
    5. Use `data.get("descriptionPlain", "")` for `description`
    6. Location: `data.get("categories", {}).get("location", "")`
    7. Return dict or None on error
- **REGEX**:
```python
_LV_RE = re.compile(r'jobs\.lever\.co/([^/]+)/([^/?]+)')
```
- **GOTCHA**: `createdAt` is **millisecond epoch** — divide by 1000. Forgetting this gives a date in year ~55000.
- **GOTCHA**: Must include `?mode=json` — without it, endpoint returns HTML, `requests` gets a 200 with HTML body, `response.json()` raises `JSONDecodeError`
- **VALIDATE**: Unit test with fixture

---

### 12. CREATE `job_finder/parser/generic.py`

- **IMPLEMENT**: BeautifulSoup fallback parser for Workday, Ashby, SmartRecruiters
- **IMPORTS**: `requests`, `logging`, `bs4.BeautifulSoup`, `bs4.Comment`
- **FUNCTIONS**:
  - `can_parse(url: str) -> bool` — always returns True (catch-all)
  - `parse(raw: dict) -> dict | None`:
    1. `resp = requests.get(raw["url"], timeout=15, headers={"User-Agent": "Mozilla/5.0"})`
    2. **`resp.encoding = resp.apparent_encoding`** (critical — fixes garbled text)
    3. `soup = BeautifulSoup(resp.text, "lxml")`
    4. Remove noise tags: `for tag in soup(["script","style","nav","footer","header","noscript"]): tag.decompose()`
    5. Extract title from `<title>` tag; split on ` | ` or ` - ` and take first part
    6. Get visible text with `soup.get_text(" ", strip=True)` (after removing noise tags)
    7. `description` = truncate visible text to 5000 chars
    8. Return dict or None on error

- **GOTCHA**: Set `resp.encoding = resp.apparent_encoding` before `.text` — without this, non-ASCII characters in job descriptions are garbled
- **GOTCHA**: `lxml` must be installed — it's faster and handles malformed ATS HTML. Import will fail if not in requirements.txt
- **VALIDATE**: `python -c "from job_finder.parser.generic import parse" # dry import`

---

### 13. CREATE `job_finder/scoring.py`

- **IMPLEMENT**: 0–100 relevance scorer per PRD §7.4
- **IMPORTS**: `logging`, `re`, `job_finder.config`
- **SCORING BREAKDOWN** (must sum to ≤ 100):

| Signal | Max Points | Logic |
|--------|-----------|-------|
| Keyword in title | 30 | Any keyword from `config.DEFAULT_KEYWORDS` found in title (case-insensitive) |
| Keyword in description | 20 | Same keywords found in description body |
| Location match | 20 | "remote" in location OR `config.LOCATION_PREFERENCE.lower()` in location |
| Seniority match | 20 | Any of `config.SENIORITY_TARGETS` in title/description; -10 if "junior"/"entry level" found |
| Recent posting | 10 | `posted_at` is today or yesterday |

- **FUNCTIONS**:
  - `score(job: dict) -> int` — returns integer 0–100; adds `job["score"] = result` and returns job
  - Return `max(0, min(100, total))` to clamp

- **VALIDATE**: `python -c "from job_finder.scoring import score; j={'title':'Senior Software Engineer','description':'remote python','location':'Remote','posted_at':'$(date +%Y-%m-%d)','score':0}; print(score(j))"`

---

### 14. CREATE `job_finder/enrichment.py`

- **IMPLEMENT**: Single Claude API call per unique company; returns mission, core_values, hq_address, website_url
- **IMPORTS**: `json`, `logging`, `anthropic`, `job_finder.config`
- **CONSTANTS**: `MODEL = "claude-sonnet-4-6"`, `MAX_TOKENS = 1024`
- **JSON SCHEMA** for `output_config` (SDK ≥ 0.77.0 feature — use it):
```python
_SCHEMA = {
    "type": "object",
    "properties": {
        "mission":     {"type": ["string", "null"]},
        "core_values": {"type": "array", "items": {"type": "string"}},
        "website_url": {"type": ["string", "null"]},  # company homepage, e.g. "https://acmecorp.com"
        "hq_address":  {
            "type": ["object", "null"],
            "properties": {
                "street": {"type": ["string", "null"]},
                "city":   {"type": ["string", "null"]},
                "state":  {"type": ["string", "null"]},
                "postal_code": {"type": ["string", "null"]},
                "country": {"type": ["string", "null"]},
            },
        },
    },
    "required": ["mission", "core_values", "website_url", "hq_address"],
    "additionalProperties": False,
}
```
- **FUNCTIONS**:
  - `enrich_company(company_name: str) -> dict`:
    - Create `anthropic.Anthropic()` client (reads `ANTHROPIC_API_KEY` from env)
    - Call `client.messages.create(model=MODEL, max_tokens=MAX_TOKENS, messages=[...], output_config={"format": {"type": "json_schema", "schema": _SCHEMA}})`
    - Return `json.loads(response.content[0].text)`
    - On any exception, log warning and return `{"mission": None, "core_values": [], "website_url": None, "hq_address": None}`
  - `enrich_jobs(jobs: list[dict]) -> list[dict]`:
    - Build company→enrichment cache: one `enrich_company` call per unique `job["company"]`
    - Merge enrichment into each job dict (mutate in place)
    - Return jobs list

- **GOTCHA**: Cache by company name — never call Claude once per job, only once per unique company per run
- **GOTCHA**: `output_config` with `json_schema` eliminates markdown fence wrapping; `response.content[0].text` is always valid JSON
- **VALIDATE**: `python -c "from job_finder.enrichment import enrich_company" # dry import`

---

### 15. CREATE `job_finder/sf_writer.py`

- **IMPLEMENT**: Salesforce Account query-then-create + Job_Application__c create
- **IMPORTS**: `logging`, `time`, `simple_salesforce.Salesforce`, `simple_salesforce.SalesforceExpiredSession`, `job_finder.config`
- **PATTERN**: Mirror `_with_backoff()` from `Salesforce_Backup/src/salesforce.py:103–115` verbatim
- **PATTERN**: Mirror `connect()` from `Salesforce_Backup/src/salesforce.py:14–27`
- **FUNCTIONS**:
  - `connect() -> Salesforce` — authenticate via `SF_USERNAME`, `SF_PASSWORD`, `SF_SECURITY_TOKEN`, `SF_DOMAIN`
  - `upsert_account(sf: Salesforce, job: dict) -> str`:
    - Escape single quotes: `safe_name = job["company"].replace("'", "\\'")`
    - **Primary match**: if `job.get("website_url")`, SOQL `WHERE Website = '{website}' AND Type = 'Job Application'`
    - **Fallback match**: if no website, SOQL `WHERE Name = '{safe_name}' AND Type = 'Job Application'`
    - If `totalSize == 1`: call `sf.Account.update(id, payload)`; return id
    - Else: call `sf.Account.create(payload)`; return `result["id"]`
    - Payload includes: `Name`, `Type='Job Application'`, `Website` (from `job["website_url"]`), `Company_Research__c` (from enrichment), `BillingStreet/City/State/PostalCode/Country` (from `hq_address`)
  - `create_job_application(sf: Salesforce, job: dict, account_id: str) -> str`:
    - Build payload from job dict; map to exact SF API field names per PRD §15
    - `sf.Job_Application__c.create(payload)` wrapped in `_with_backoff()`
    - Return `result["id"]`
  - `write_job(sf: Salesforce, job: dict) -> tuple[str, str]`:
    - Calls `upsert_account` → `create_job_application`
    - Returns `(sf_job_app_id, sf_account_id)`

- **SF FIELD MAPPING** for `Job_Application__c.create()`:
```python
payload = {
    # Do NOT set Name — a Salesforce trigger auto-populates it as "Company: Title (MM/YYYY)"
    "Job_Title__c":        job["title"],
    "Job_Description__c":  job["description"][:32768],  # LongTextArea max (field length = 32768)
    "Job_Posting_URL__c":  job["url"],
    "Status__c":           "Draft",
    "Account__c":          account_id,
    "Company_Research__c": _build_research_text(job),  # mission + core values, written here not on Account
    "Employment_Type__c":  None,  # not available from ATS at this stage; omit or set to "Full Time"
}
```
- **GOTCHA**: Do NOT set `Name` on `Job_Application__c` — a Salesforce trigger populates it automatically in format `"Company Name: Position Name (MM/YYYY)"`. Setting it manually will conflict with the trigger.
- **GOTCHA**: `Name` on `Account` is NOT an `idLookup` field — do NOT use `sf.Account.upsert('Name/...')`. Use the Website-first query-then-create pattern above.
- **NOTE**: `Company_Research__c` confirmed on `JobApplication__c` (LongTextArea, 32768 chars). The `Account` object also has `Company_Research__c` — populate both: Account gets mission+values for context; JobApplication__c gets the same text for AI resume/cover-letter generation.
- **GOTCHA**: Escape single quotes in company name before injecting into SOQL: `safe_name = company_name.replace("'", "\\'")`
- **GOTCHA**: `Job_Description__c` is a LongTextArea — truncate to 32,000 chars to avoid `STRING_TOO_LONG` error
- **VALIDATE**: `python -c "from job_finder.sf_writer import connect" # dry import`

---

### 16. CREATE `job_finder/orchestrator.py`

- **IMPLEMENT**: Top-level pipeline coordinator; calls all stages in order
- **IMPORTS**: `logging`, `job_finder.config`, `job_finder.db`, `job_finder.deduplicator`, `job_finder.scoring`, `job_finder.enrichment`, `job_finder.sf_writer`, `job_finder.search.google_cse`, `job_finder.parser.greenhouse`, `job_finder.parser.lever`, `job_finder.parser.generic`
- **PATTERN**: Mirror write-back loop from `Salesforce_Backup/src/write_back.py:59–106` for per-job error handling
- **PARSER REGISTRY**:
```python
from job_finder.parser import greenhouse, lever, generic
PARSERS = [greenhouse, lever, generic]  # order matters — generic is catch-all

def _get_parser(url: str):
    for p in PARSERS:
        if p.can_parse(url):
            return p
    return generic
```
- **FUNCTION** `run(keywords: str, limit: int, dry_run: bool) -> dict`:
```
1. pg_conn = db.connect()
2. sf = sf_writer.connect()  (skip if dry_run)
3. raw_results = google_cse.search_all_ats(keywords, max_per_site=10)
4. For each result: check is_duplicate(pg_conn, sf, url); collect new_results
5. For each new result: parse with _get_parser(url); collect parsed (skip None)
6. For each parsed: score; sort by score desc
7. qualified = scored[:limit]; skipped = scored[limit:]
8. For job in qualified+skipped: db.insert_job_lead(pg_conn, job) with status='new'
9. For job in skipped: db.mark_skipped(pg_conn, job["url_hash"])
10. If dry_run: log summary and return
11. qualified = enrichment.enrich_jobs(qualified)  (one Claude call per company)
12. For job in qualified:
    try:
        sf_job_app_id, sf_account_id = sf_writer.write_job(sf, job)
        db.mark_pushed(pg_conn, job["url_hash"], sf_job_app_id, sf_account_id)
    except SalesforceExpiredSession: raise
    except Exception as e:
        db.mark_failed(pg_conn, job["url_hash"], str(e)[:2000])
        logger.error("Failed: %s — %s", job["url"], e)
13. pg_conn.close()
14. Return summary dict: {found, new, parsed, qualified, pushed, skipped, failed}
```
- **GOTCHA**: Close `pg_conn` in a `finally` block to prevent connection leaks
- **GOTCHA**: `SalesforceExpiredSession` must re-raise immediately (session can't be retried without re-auth)
- **VALIDATE**: `python -c "from job_finder.orchestrator import run; print('orchestrator OK')"`

---

### 17. CREATE `job_finder/__main__.py`

- **IMPLEMENT**: `argparse` CLI with `--dry-run`, `--keywords`, `--limit` flags; logging setup; calls `orchestrator.run()`
- **IMPORTS**: `argparse`, `logging`, `sys`, `job_finder.config`, `job_finder.orchestrator`
- **CLI INTERFACE**:
```python
parser = argparse.ArgumentParser(description="JobFinder — discover freshly posted engineering jobs")
parser.add_argument("--dry-run", action="store_true", help="Run full pipeline without writing to Salesforce")
parser.add_argument("--keywords", default=config.DEFAULT_KEYWORDS, help="Comma-separated search keywords")
parser.add_argument("--limit", type=int, default=config.DAILY_LIMIT, help="Max jobs to push to Salesforce")
```
- **LOGGING SETUP**:
```python
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
```
- **EXIT CODE**: `sys.exit(1)` if `summary["failed"] > 0`, else `sys.exit(0)`
- **VALIDATE**: `python -m job_finder --help`

---

### 18. CREATE `tests/` (unit tests)

- **IMPLEMENT**: Pytest unit tests for every module; mock all external I/O
- **PATTERN**: Use `pytest-mock`'s `mocker.patch()` to mock `requests.get`, `anthropic.Anthropic`, `simple_salesforce.Salesforce`, `psycopg2.connect`
- **KEY TESTS**:
  - `test_config.py`: missing required var raises `EnvironmentError`
  - `test_deduplicator.py`: URL normalization strips UTM params; hash is deterministic; duplicate detection returns True
  - `test_scoring.py`: senior remote job scores higher than junior on-site job
  - `test_parser_greenhouse.py`: fixture JSON response maps to expected internal dict; `?content=true` is appended to API URL
  - `test_parser_lever.py`: `createdAt` milliseconds converts to correct date; `?mode=json` appended
  - `test_parser_generic.py`: HTML noise tags stripped; encoding set from `apparent_encoding`
  - `test_sf_writer.py`: query-then-create path for new Account; update path for existing Account
  - `test_enrichment.py`: one Claude call per unique company, not per job

- **FIXTURE PATTERN** (example for greenhouse):
```python
GREENHOUSE_RESPONSE = {
    "id": 12345, "title": "Senior Software Engineer",
    "company_name": "Acme Corp",
    "location": {"name": "Remote"},
    "content": "<p>We are hiring...</p>",
    "first_published": "2026-03-25T06:00:00Z",
    "departments": [{"name": "Engineering"}],
    "absolute_url": "https://boards.greenhouse.io/acme/jobs/12345"
}
```
- **VALIDATE**: `python -m pytest tests/ -v`

---

## TESTING STRATEGY

### Unit Tests

Each module tested in isolation. All external I/O (HTTP, DB, SF, Anthropic) mocked via `pytest-mock`.

**Framework**: `pytest` + `pytest-mock`
**Location**: `tests/` flat directory
**Convention**: `test_{module_name}.py`

### Integration Tests

Not required for MVP. Manual validation steps serve this purpose (see Level 4 below).

### Edge Cases

- `score()` with missing `posted_at` (None) — don't crash, score as 0 for recency signal
- `parse()` returning None when API returns 404 — orchestrator skips gracefully
- Company name with single quotes (e.g., "O'Reilly") — SOQL injection in `upsert_account()`
- `Job_Description__c` longer than 32,000 chars — truncate before SF write
- Lever `createdAt` missing from response — default to None for `posted_at`
- Google CSE returns 0 items (quota exhausted) — log warning, return empty list, don't crash
- Dry run — SF `connect()` must not be called
- Duplicate URL appears in both PG and SF — return True on PG check, never reach SF fallback

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style

```bash
# Verify all Python files parse (no syntax errors)
python -m py_compile job_finder/config.py job_finder/db.py job_finder/deduplicator.py job_finder/scoring.py job_finder/enrichment.py job_finder/sf_writer.py job_finder/orchestrator.py job_finder/__main__.py job_finder/search/google_cse.py job_finder/search/ats_sites.py job_finder/parser/greenhouse.py job_finder/parser/lever.py job_finder/parser/generic.py

# Verify imports work
python -c "import job_finder; import job_finder.search; import job_finder.parser; print('All imports OK')"
```

### Level 2: Unit Tests

```bash
python -m pytest tests/ -v --tb=short
```

### Level 3: Integration Tests (requires .env populated)

```bash
# Smoke test: config loads without errors
python -c "from job_finder import config; print('Config loaded OK')"

# DB connection test (requires PG running)
python -c "from job_finder.db import connect; conn = connect(); print('PG connected'); conn.close()"

# SF connection test (requires SF credentials)
python -c "from job_finder.sf_writer import connect; sf = connect(); print('SF connected:', sf.base_url)"
```

### Level 4: Manual Validation

```bash
# Full dry run — verify pipeline runs without SF writes
python -m job_finder --dry-run --limit 5

# Custom keyword dry run
python -m job_finder --dry-run --keywords "Salesforce Developer" --limit 3

# Full run (writes to SF) — verify Job_Application__c records appear in Salesforce
python -m job_finder --limit 5

# Verify deduplication — run again immediately; should find 0 new jobs
python -m job_finder --dry-run --limit 5
```

### Level 5: Database Audit

```bash
# Inspect job_lead table after a run
psql "$DATABASE_URL" -c "SELECT status, count(*) FROM job_lead GROUP BY status;"
psql "$DATABASE_URL" -c "SELECT url_hash, title, company, score, status, sf_job_app_id FROM job_lead ORDER BY discovered_at DESC LIMIT 10;"
```

---

## ACCEPTANCE CRITERIA

- [ ] `python -m job_finder --help` prints usage without errors
- [ ] `python -m job_finder --dry-run --limit 5` runs end-to-end without crashing; logs 5 scored jobs
- [ ] No SF API calls are made during `--dry-run`
- [ ] Duplicate URLs are skipped on second run (0 new records pushed)
- [ ] All `Job_Application__c` records have `Status__c = 'Draft'`
- [ ] All `Account` records have `Type = 'Job Application'`
- [ ] `Company_Research__c` is populated for newly created Accounts
- [ ] `BillingCity`, `BillingState`, `BillingCountry` populated where Claude returned data
- [ ] `job_lead` rows have correct status (`pushed | skipped | failed`) after each run
- [ ] Daily limit respected: never more than `DAILY_LIMIT` SF writes per run
- [ ] "Senior Software Engineer - Remote" scores higher than "Junior QA Analyst - On-site"
- [ ] All unit tests pass: `python -m pytest tests/ -v` exits 0
- [ ] O'Reilly (single-quote company) doesn't break SOQL query
- [ ] `python -m job_finder --keywords "Salesforce Developer" --limit 3` searches for that keyword

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in dependency order (sql → config → db → search → parser → scoring → enrich → sf_writer → orchestrator → __main__)
- [ ] Each task validated immediately after implementation
- [ ] `python -m pytest tests/ -v` passes
- [ ] `python -m job_finder --dry-run --limit 5` succeeds end-to-end
- [ ] Full run creates valid Salesforce records
- [ ] `job_lead` table shows correct statuses
- [ ] No linting/syntax errors (`python -m py_compile ...`)
- [ ] `.env` values never committed to git (`.gitignore` has `.env`)

---

## NOTES

### Critical Architecture Decisions

1. **Account upsert strategy**: Do NOT use `sf.Account.upsert('Name/...')` — `Name` is not an `idLookup` External ID field in Salesforce. Instead: use `Account.Website` as the primary match key (Claude enrichment returns `website_url`; websites are far more unique than company names). If `website_url` is None, fall back to `Name + Type`. Always populate `Website` on create so future runs match on it.

2. **Lever timestamp**: `createdAt` is millisecond epoch, not seconds. `datetime.fromtimestamp(data["createdAt"] / 1000)` — forgetting the `/1000` gives a date in year ~55000 with no exception thrown.

3. **Google CSE 100-result cap**: The API hard-caps at 100 total results regardless of pagination. With 5 ATS sites × 10 results each = 50 queries for 1 page each, or 500 queries for 10 pages. Stay within 100 free queries/day budget by defaulting to 1 page per site per run.

4. **Anthropic `output_config`**: The `json_schema` approach (SDK ≥ 0.77.0) guarantees the response is pure JSON — no markdown code fences, no preamble text. This is cleaner than prompt-engineering + regex stripping. Use it.

5. **Greenhouse `?content=true`**: Without this query param, the `content` field (job description HTML) is absent from the response. The API returns a 200 with metadata only — no error, no indication. This is the most common Greenhouse integration bug.

6. **Pipeline statelessness**: Each stage (search → parse → score → enrich → write) takes a list in, returns a list out. No module-level mutable state. This makes testing clean and stages independently replaceable.

7. **Google CSE API deprecation**: As of early 2026, the Custom Search JSON API is closed to new customers. Existing customers have until January 1, 2027 to migrate. If `GOOGLE_API_KEY` already works, proceed. If not, explore [SerpAPI](https://serpapi.com/) as an alternative.

### Design Trade-offs

- **PG-first deduplication**: Checking `job_lead.url_hash` before any SF SOQL call keeps the fast path entirely local. The SOQL fallback handles the bootstrapping case (empty PG DB on first run).
- **Plain text for Salesforce**: `Job_Description__c` receives plain text (not HTML) to avoid rendering issues in Salesforce list views and email templates.
- **Per-company enrichment caching**: `enrichment.py` caches by company name within a single run, not across runs. For cross-run caching, add a `company_cache` PG table in Phase 2.
