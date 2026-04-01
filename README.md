# JobFinder

A nightly job discovery pipeline that searches multiple job boards for Salesforce Developer roles, scores and filters results, and pushes qualified listings to a Salesforce org as `JobApplication__c` records.

## How It Works

1. **Search** — Queries Greenhouse, Lever, Workday, Ashby, SmartRecruiters, and LinkedIn via the Serper (Google Search) API using keywords from your Salesforce config
2. **Deduplicate** — Skips any URL already seen in PostgreSQL or Salesforce
3. **Parse** — Fetches each job page and extracts title, company, location, salary, and description
4. **Score** — Ranks jobs 0–100 based on keyword match, remote status, seniority, recency, and bonus skills
5. **Filter** — Drops jobs below a salary threshold or minimum score
6. **Enrich** — Calls Claude API for company research (mission, values, HQ)
7. **Push** — Creates `JobApplication__c` records in Salesforce for the top N jobs

Configuration is driven by `Job_Search_Config__c` records in Salesforce, so you can adjust keywords, salary thresholds, and schedules directly from the SF UI.

## Requirements

- Docker + Docker Compose
- A running PostgreSQL container (the project reuses `sf_postgres` from the `salesforce-backup` stack)
- [Serper.dev](https://serper.dev) API key (Google Search)
- Anthropic API key (Claude — for company enrichment)
- Salesforce org with `JobApplication__c` and `Job_Search_Config__c` custom objects

## Setup

### 1. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
SERPER_API_KEY=...
ANTHROPIC_API_KEY=...

SF_USERNAME=you@yourorg.com
SF_PASSWORD=yourpassword
SF_SECURITY_TOKEN=yourtoken
SF_DOMAIN=login

PG_HOST=sf_postgres        # Docker container name of the PostgreSQL instance
PG_PORT=5432
PG_DBNAME=salesforce_backup
PG_USER=sfuser
PG_PASSWORD=...
PG_SSLMODE=require

MIN_ANNUAL_SALARY=145000   # Jobs with a known salary below this are filtered out
LOCATION_PREFERENCE=Remote
SENIORITY_TARGETS=mid,senior,staff,principal,lead
```

### 2. Initialize the database

```bash
psql -h localhost -U sfuser -d salesforce_backup -f sql/schema.sql
```

### 3. Configure Salesforce

Create one or more active `Job_Search_Config__c` records in your Salesforce org:

| Field | Example | Description |
|---|---|---|
| `Keywords__c` | `Salesforce Developer,Salesforce Engineer` | Comma-separated search terms |
| `Bonus_Skills__c` | `Apex;LWC;CPQ` | Semicolon-separated skills that boost score |
| `Daily_Limit__c` | `10` | Max jobs pushed to SF per run |
| `Min_Annual_Salary__c` | `145000` | Hard salary floor (0 = disabled) |
| `Schedule_Hour__c` | `2` | UTC hour for nightly run |
| `Schedule_Minute__c` | `30` | UTC minute for nightly run |
| `Is_Active__c` | `true` | Only active records are loaded |

### 4. Start the scheduler

```bash
docker compose up -d --build
```

The container connects to Salesforce on startup, loads active config records, and schedules a nightly run for each one.

## Running Manually

Run a one-off search without pushing to Salesforce:

```bash
docker exec jf_scheduler python3 -m job_finder \
  --keywords "Salesforce Developer,Salesforce Engineer" \
  --limit 10 \
  --dry-run \
  --verbose
```

Backfill the last 7 days:

```bash
docker exec jf_scheduler python3 -m job_finder \
  --keywords "Salesforce Developer" \
  --limit 20 \
  --days 7 \
  --dry-run
```

## YAML Profiles (fallback)

If Salesforce is unreachable, the scheduler falls back to YAML files in `profiles/`:

- `profiles/default.yaml` — broad software engineering search
- `profiles/salesforce_dev.yaml` — Salesforce Developer / Engineer roles
- `profiles/salesforce_architect.yaml` — Salesforce Architect roles

## Scoring

Jobs are scored 0–100. Key signals:

| Signal | Points |
|---|---|
| Keyword match in title | +30 |
| Keyword match in description | +20 |
| Remote / WFH / work from home | +20 |
| US location | +10 |
| Senior / mid / staff / lead seniority | +20 |
| Developer / architect / consultant title | +15 |
| Engineer / technical title (non-sales) | +15 |
| Bonus skill match (per skill, max 4) | +5 each |
| Junior / entry-level | −10 |
| Non-US location (explicit country) | −25 |
| Non-technical role title | −20 |
| Recent posting (< 24 hours) | +10 |

## Project Structure

```
job_finder/
├── __main__.py          CLI entry point
├── scheduler.py         APScheduler daemon — runs nightly per SF config
├── orchestrator.py      Pipeline coordinator (all 8 stages)
├── scoring.py           0–100 relevance scorer
├── enrichment.py        Claude API company research
├── sf_writer.py         Salesforce record creation
├── sf_config_reader.py  Reads Job_Search_Config__c from SF
├── deduplicator.py      URL deduplication (PG + SF)
├── salary_extractor.py  Salary parsing from job text
├── db.py                PostgreSQL helpers
├── config.py            Environment variable loading
├── search/
│   ├── google_cse.py    Serper API client
│   └── ats_sites.py     ATS domain registry
└── parser/
    ├── greenhouse.py    Greenhouse Jobs Board API
    ├── lever.py         Lever API
    ├── linkedin.py      LinkedIn job page parser
    └── generic.py       BeautifulSoup fallback
```

## Tests

```bash
python3 -m pytest tests/ -q
```

155 tests, no external calls required (all network interactions are mocked).
