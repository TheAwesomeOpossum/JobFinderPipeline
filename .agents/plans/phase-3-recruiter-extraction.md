# Feature: Phase 3 — Recruiter Extraction

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils, types, and models. Import from the right files.

---

## Feature Description

Extend the JobFinder pipeline to extract recruiter contact information from Greenhouse and Lever ATS postings, create Salesforce `Contact` records for discovered recruiters, and link those contacts back to `Job_Application__c` via the `Recruiter__c` lookup field. The `job_lead` PostgreSQL table is updated with the resulting `sf_recruiter_contact_id`.

## User Story

As a job seeker
I want recruiter contacts automatically extracted and stored in Salesforce
So that I can reach out directly to recruiters for roles I'm applying to, without manual research.

## Problem Statement

Currently the pipeline creates `Account` + `Job_Application__c` records but leaves the `Recruiter__c` field on `Job_Application__c` empty. Greenhouse postings expose recruiter names via the public API; without automation, users must manually research and enter this data for every application.

## Solution Statement

1. **Parse** recruiter name from Greenhouse's `hiring_team.recruiters` payload field (name only — no email is exposed by the public API). Lever and Generic parsers emit `None` (no public recruiter field).
2. **Write** to Salesforce: create/upsert a `Contact` record for the recruiter, linked to the existing company `Account` (the `Job Application` Account already created in Stage 8).
3. **Link** `Job_Application__c.Recruiter__c` to the Contact's Id.
4. **Persist** `sf_recruiter_contact_id` in the `job_lead` PostgreSQL table.

> **Design decision (deviate from PRD's `Recruiter Account`):** The PRD mentions an `Account` with `Type = 'Recruiter Account'`. The Greenhouse/Lever public APIs do not expose whether a recruiter is an internal employee or an external staffing agency — only name is available. Creating a duplicate `Account` for the same company under a different `Type` introduces data quality issues. Instead, Phase 3 attaches the `Contact` to the existing `Job Application` Account. A separate `Recruiter Account` should be revisited in Phase 4 when external agency detection becomes feasible.

## Feature Metadata

**Feature Type**: Enhancement (Phase 3 of existing pipeline)
**Estimated Complexity**: Medium
**Primary Systems Affected**: `parser/greenhouse.py`, `sf_writer.py`, `db.py`, `orchestrator.py`, `sql/`
**Dependencies**: `simple_salesforce` (already installed), psycopg2 (already installed)

---

## CONTEXT REFERENCES

### Relevant Codebase Files — YOU MUST READ THESE BEFORE IMPLEMENTING

- `job_finder/parser/greenhouse.py` (lines 31-75) — Pattern for extracting fields from Greenhouse API response. We add recruiter extraction here from `data.get("hiring_team", {}).get("recruiters", [])`.
- `job_finder/parser/lever.py` (lines 58-76) — Return dict pattern. Must add `recruiter_name: None, recruiter_email: None` to output.
- `job_finder/parser/generic.py` (lines 57-73) — Same return dict pattern. Must add `recruiter_name: None, recruiter_email: None`.
- `job_finder/sf_writer.py` (lines 51-120) — All SF write operations. `upsert_account()` is the pattern to follow for `upsert_recruiter_contact()`. The `_with_backoff()` retry decorator at line 26 must be used for all SF API calls. `write_job()` at line 113 is the function we extend.
- `job_finder/db.py` (lines 48-81) — `mark_pushed()` at line 48 takes `url_hash`, `sf_job_app_id`, `sf_account_id`. We extend it to accept `sf_recruiter_contact_id` (nullable).
- `job_finder/orchestrator.py` (lines 103-114) — Stage 8 (SF write loop). The `db.mark_pushed()` call at line 106 must be updated.
- `sql/01_job_lead_schema.sql` — Existing table definition. We add one column via a migration script.
- `tests/test_sf_writer.py` — Full test pattern: `_set_env()`, `sys.modules.pop()`, `MockSF` class with `query()`, `_Object` inner class. Mirror this pattern exactly for recruiter tests.
- `tests/test_parser_greenhouse.py` (lines 6-15) — `GREENHOUSE_RESPONSE` fixture pattern. Must extend to include `hiring_team` field.

### New Files to Create

- `sql/02_add_recruiter_contact_id.sql` — Migration: adds `sf_recruiter_contact_id VARCHAR(18)` column to `job_lead`.
- `tests/test_sf_writer_recruiter.py` — Unit tests for recruiter Contact upsert and `write_job()` recruiter flow.

### Relevant Documentation — YOU SHOULD READ THESE BEFORE IMPLEMENTING

- [Greenhouse Jobs Board API](https://developers.greenhouse.io/job-board.html#get-a-job)
  - Section: GET a Job → Response schema → `hiring_team.recruiters[]`
  - Why: Confirms that `recruiters[].name`, `recruiters[].first_name`, `recruiters[].last_name` are available but NO email in the public API.
- [simple_salesforce Contact docs](https://simple-salesforce.readthedocs.io/en/latest/)
  - Section: CRUD on standard objects
  - Why: `sf.Contact.create(payload)` and `sf.Contact.update(id, payload)` follow same pattern as `sf.Account`.
- [Salesforce Contact standard fields](https://developer.salesforce.com/docs/atlas.en-us.object_reference.meta/object_reference/sforce_api_objects_contact.htm)
  - Key fields: `FirstName`, `LastName`, `Email`, `AccountId`
  - Why: Ensures correct API field names.

### Patterns to Follow

**Return dict pattern** (all parsers must include these keys — mirror `greenhouse.py:58-75`):

```python
return {
    **raw,
    "title":            ...,
    "company":          ...,
    # ... existing fields ...
    "recruiter_name":   "Jane Smith",   # str | None
    "recruiter_email":  None,            # str | None (not available from public APIs)
    "sf_recruiter_contact_id": None,
}
```

**SF query-then-create pattern** (mirror `sf_writer.upsert_account` lines 76-90):

```python
result = sf.query(f"SELECT Id FROM Contact WHERE Email = '{safe_email}' LIMIT 1")
if result["totalSize"] == 1:
    contact_id = result["records"][0]["Id"]
    _with_backoff(lambda: sf.Contact.update(contact_id, payload))
else:
    contact_id = _with_backoff(lambda: sf.Contact.create(payload))["id"]
return contact_id
```

**Dedup key priority** (Contact dedup):
1. Email match: `WHERE Email = '...'` (when `recruiter_email` is not None)
2. Name + AccountId fallback: `WHERE Name = '...' AND AccountId = '...'` (when only name is known)
3. No recruiter data → skip entire recruiter flow, return `None`

**Backoff requirement**: Every SF API call MUST be wrapped in `_with_backoff()`. No direct `sf.Contact.create()` without the wrapper.

**Error handling pattern** (mirror `orchestrator.py:109-113`):

```python
try:
    sf_recruiter_contact_id = sf_writer.upsert_recruiter_contact(sf, job, account_id)
except Exception as exc:
    logger.warning("Recruiter contact upsert failed for %s: %s", job.get("url"), exc)
    sf_recruiter_contact_id = None   # non-fatal: job was already pushed
```

**Naming conventions**:
- `recruiter_name` — job dict key for raw recruiter name string
- `recruiter_email` — job dict key for recruiter email (usually None)
- `sf_recruiter_contact_id` — job dict key and DB column name
- `upsert_recruiter_contact()` — sf_writer function name

**Logging pattern** (mirror sf_writer.py):
```python
logger.info("Upserted recruiter contact: %s → %s", recruiter_name, contact_id)
logger.warning("upsert_recruiter_contact skipped: no recruiter_name for %s", job.get("url"))
```

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation — Schema + Parser Updates

Add `recruiter_name` / `recruiter_email` fields to all parser outputs and migrate the database schema.

**Tasks:**
- SQL migration for `job_lead.sf_recruiter_contact_id`
- Extract `hiring_team.recruiters[0]` in Greenhouse parser
- Add `None` defaults for recruiter fields in Lever and Generic parsers

### Phase 2: Salesforce Writer — Recruiter Contact Upsert

Add `upsert_recruiter_contact()` to `sf_writer.py` and update `write_job()` to call it.

**Tasks:**
- Implement `upsert_recruiter_contact(sf, job, account_id)` with email-first / name-fallback dedup
- Update `write_job()` return type from `tuple[str, str]` to `tuple[str, str, str | None]`

### Phase 3: Integration — Orchestrator + DB

Wire the new `sf_recruiter_contact_id` through the orchestrator and persist it in PostgreSQL.

**Tasks:**
- Update `orchestrator.py` Stage 8 to handle recruiter contact ID (non-fatal error path)
- Update `db.mark_pushed()` to accept and write `sf_recruiter_contact_id`
- Update `db.py` SQL to include the new column

### Phase 4: Testing

Unit tests for recruiter extraction, SF upsert, and integration across the pipeline.

---

## STEP-BY-STEP TASKS

### CREATE `sql/02_add_recruiter_contact_id.sql`

- **IMPLEMENT**: Single `ALTER TABLE` statement adding `sf_recruiter_contact_id VARCHAR(18)` to `job_lead`. Include `IF NOT EXISTS` guard via column existence check.
- **PATTERN**: Mirror `sql/01_job_lead_schema.sql` header comment style.
- **GOTCHA**: `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` requires PostgreSQL 9.6+. Our stack uses psycopg2 — just use plain `ADD COLUMN IF NOT EXISTS`.
- **VALIDATE**: `python -c "import psycopg2; print('ok')"` (syntax check; actual migration requires running against DB)

```sql
-- Migration: add recruiter contact ID tracking to job_lead
ALTER TABLE job_lead
    ADD COLUMN IF NOT EXISTS sf_recruiter_contact_id VARCHAR(18);
```

### UPDATE `job_finder/parser/greenhouse.py`

- **IMPLEMENT**: After extracting `company` (line 56), extract recruiter from `data.get("hiring_team", {}).get("recruiters", [])`. Take index 0 if list is non-empty. Set `recruiter_name = recruiters[0].get("name")` (full name string). Set `recruiter_email = None` (not available in public API).
- **PATTERN**: `job_finder/parser/greenhouse.py:56-75` — follow existing field extraction pattern
- **IMPORTS**: No new imports needed.
- **GOTCHA**: `hiring_team` may be absent entirely in the API response (not all companies expose it). Guard with `or {}` and `or []`. Never raise on missing field.
- **VALIDATE**: `python -m pytest tests/test_parser_greenhouse.py -v`

Add to return dict (lines 58-75), after `website_url` and `sf_account_id`:
```python
"recruiter_name":          recruiter_name,
"recruiter_email":         None,
"sf_recruiter_contact_id": None,
```

Full extraction block to add before the return (after line 56):
```python
hiring_team = data.get("hiring_team") or {}
recruiters_list = hiring_team.get("recruiters") or []
recruiter_name = recruiters_list[0].get("name") if recruiters_list else None
```

### UPDATE `job_finder/parser/lever.py`

- **IMPLEMENT**: Add `recruiter_name: None, recruiter_email: None, sf_recruiter_contact_id: None` to the return dict (after `sf_account_id` at line 75).
- **PATTERN**: `job_finder/parser/lever.py:59-76` — mirror return dict structure
- **GOTCHA**: Lever public API (v0) does NOT expose recruiter info. Use None — do not attempt to extract.
- **VALIDATE**: `python -m pytest tests/test_parser_lever.py -v`

### UPDATE `job_finder/parser/generic.py`

- **IMPLEMENT**: Add `recruiter_name: None, recruiter_email: None, sf_recruiter_contact_id: None` to the return dict (after `sf_account_id` at line 73).
- **PATTERN**: `job_finder/parser/generic.py:57-73`
- **VALIDATE**: `python -m pytest tests/test_parser_generic.py -v`

### UPDATE `job_finder/sf_writer.py`

#### ADD function `upsert_recruiter_contact(sf, job, account_id)`

- **IMPLEMENT**: New function after `upsert_account()`. Accepts `sf: Salesforce`, `job: dict`, `account_id: str` (the company's Account ID). Returns `str | None` (Contact SF ID, or None if no recruiter data).
- **PATTERN**: Mirror `upsert_account()` lines 51-92 — same query-then-create structure with `_with_backoff()`
- **IMPORTS**: No new imports needed.
- **GOTCHA 1**: If `recruiter_name` is None or empty string → log warning and return `None` immediately. Do NOT create a Contact with an empty name.
- **GOTCHA 2**: Contact `Name` in SOQL must be escaped for single quotes (use same pattern as `safe_name` in `upsert_account`).
- **GOTCHA 3**: `sf.Contact.create()` requires at least `LastName`. If `recruiter_name` is a full name, split on space: `parts = recruiter_name.split(" ", 1)` → `FirstName = parts[0], LastName = parts[1] if len(parts) > 1 else parts[0]`.
- **GOTCHA 4**: Dedup priority: email first (if `recruiter_email` is not None), then name+AccountId fallback.
- **VALIDATE**: `python -m pytest tests/test_sf_writer_recruiter.py -v`

```python
def upsert_recruiter_contact(sf: Salesforce, job: dict, account_id: str) -> str | None:
    """
    Create or update a Contact for the recruiter in this job posting.
    Links to the company Account (account_id).
    Returns the Contact SF Id, or None if no recruiter info available.

    Dedup priority:
    1. Email match (when recruiter_email is not None)
    2. Name + AccountId match (fallback when only name is known)
    """
    recruiter_name = job.get("recruiter_name") or ""
    recruiter_email = job.get("recruiter_email") or ""

    if not recruiter_name:
        logger.warning("upsert_recruiter_contact: no recruiter_name — skipping for %s", job.get("url"))
        return None

    # Split full name into first/last for Contact creation
    parts = recruiter_name.strip().split(" ", 1)
    first_name = parts[0] if len(parts) > 0 else ""
    last_name = parts[1] if len(parts) > 1 else parts[0]  # fallback: use full name as last name

    payload = {
        "FirstName":  first_name or None,
        "LastName":   last_name,
        "AccountId":  account_id,
    }
    if recruiter_email:
        payload["Email"] = recruiter_email
    # Remove None values
    payload = {k: v for k, v in payload.items() if v is not None}

    safe_name = recruiter_name.replace("'", "\\'")
    safe_account_id = account_id.replace("'", "\\'")

    # Dedup by email first, then by name+account fallback
    if recruiter_email:
        safe_email = recruiter_email.replace("'", "\\'")
        result = sf.query(
            f"SELECT Id FROM Contact WHERE Email = '{safe_email}' LIMIT 1"
        )
    else:
        result = sf.query(
            f"SELECT Id FROM Contact WHERE Name = '{safe_name}' AND AccountId = '{safe_account_id}' LIMIT 1"
        )

    if result["totalSize"] == 1:
        contact_id = result["records"][0]["Id"]
        _with_backoff(lambda: sf.Contact.update(contact_id, payload))
    else:
        contact_id = _with_backoff(lambda: sf.Contact.create(payload))["id"]

    logger.info("Upserted recruiter contact: %s → %s", recruiter_name, contact_id)
    return contact_id
```

#### UPDATE `write_job()` to include recruiter flow

- **IMPLEMENT**: After `create_job_application()` call (line 119), call `upsert_recruiter_contact()`. Then update the `Job_Application__c` with `Recruiter__c` if a contact ID was returned. Update return type annotation from `tuple[str, str]` to `tuple[str, str, str | None]`.
- **PATTERN**: `sf_writer.write_job()` lines 113-120
- **GOTCHA 1**: Recruiter upsert is NON-FATAL. If it fails, log warning and continue. Do NOT let recruiter errors prevent the job application from being recorded.
- **GOTCHA 2**: `Recruiter__c` on `Job_Application__c` is a lookup to `Contact`. Set it via `sf.Job_Application__c.update(job_app_id, {"Recruiter__c": contact_id})` after creating the record. Do not set it in the initial create to keep the create payload simpler.
- **VALIDATE**: `python -m pytest tests/test_sf_writer_recruiter.py -v`

```python
def write_job(sf: Salesforce, job: dict) -> tuple[str, str, str | None]:
    """
    Write a job to Salesforce: upsert Account, create Job_Application__c, upsert recruiter Contact.
    Returns (sf_job_app_id, sf_account_id, sf_recruiter_contact_id).
    sf_recruiter_contact_id is None if no recruiter info or if recruiter upsert failed.
    """
    account_id = upsert_account(sf, job)
    job_app_id = create_job_application(sf, job, account_id)

    sf_recruiter_contact_id = None
    try:
        sf_recruiter_contact_id = upsert_recruiter_contact(sf, job, account_id)
        if sf_recruiter_contact_id:
            _with_backoff(lambda: sf.Job_Application__c.update(
                job_app_id, {"Recruiter__c": sf_recruiter_contact_id}
            ))
    except Exception as exc:
        logger.warning("Recruiter upsert failed for %s: %s — job was still pushed.", job.get("url"), exc)

    return job_app_id, account_id, sf_recruiter_contact_id
```

### UPDATE `job_finder/db.py`

#### UPDATE `mark_pushed()` signature

- **IMPLEMENT**: Add `sf_recruiter_contact_id: str | None = None` parameter to `mark_pushed()`. Update the SQL to include this column in the SET clause.
- **PATTERN**: `job_finder/db.py:48-60` — same UPDATE pattern
- **GOTCHA**: Use `DEFAULT NULL` behavior — when `sf_recruiter_contact_id` is None, the column stays NULL. The SQL `SET sf_recruiter_contact_id = %(sf_recruiter_contact_id)s` with a None value writes NULL, which is correct.
- **VALIDATE**: `python -m pytest tests/test_db.py -v`

```python
def mark_pushed(conn, url_hash: str, sf_job_app_id: str, sf_account_id: str,
                sf_recruiter_contact_id: str | None = None) -> None:
    """Update job_lead status to 'pushed' with Salesforce IDs."""
    sql = """
        UPDATE job_lead
        SET status = 'pushed',
            sf_job_app_id = %(sf_job_app_id)s,
            sf_account_id = %(sf_account_id)s,
            sf_recruiter_contact_id = %(sf_recruiter_contact_id)s
        WHERE url_hash = %(url_hash)s
    """
    with conn.cursor() as cur:
        cur.execute(sql, {
            "url_hash":               url_hash,
            "sf_job_app_id":          sf_job_app_id,
            "sf_account_id":          sf_account_id,
            "sf_recruiter_contact_id": sf_recruiter_contact_id,
        })
        conn.commit()
```

### UPDATE `job_finder/orchestrator.py`

- **IMPLEMENT**: In Stage 8 (line 103-114), unpack the new 3-tuple from `sf_writer.write_job()`. Pass `sf_recruiter_contact_id` to `db.mark_pushed()`.
- **PATTERN**: `job_finder/orchestrator.py:103-114`
- **GOTCHA**: `write_job()` now returns 3 values instead of 2. Update the unpacking line.
- **VALIDATE**: `python -m pytest tests/ -v` (full suite)

Change line 105-106 from:
```python
sf_job_app_id, sf_account_id = sf_writer.write_job(sf, job)
db.mark_pushed(pg_conn, job["url_hash"], sf_job_app_id, sf_account_id)
```
To:
```python
sf_job_app_id, sf_account_id, sf_recruiter_contact_id = sf_writer.write_job(sf, job)
db.mark_pushed(pg_conn, job["url_hash"], sf_job_app_id, sf_account_id, sf_recruiter_contact_id)
```

### CREATE `tests/test_sf_writer_recruiter.py`

- **IMPLEMENT**: Full test file for `upsert_recruiter_contact()` and the updated `write_job()`. Mirror `tests/test_sf_writer.py` exactly for test structure: `_set_env()`, `sys.modules.pop()`, `MockSF`.
- **PATTERN**: `tests/test_sf_writer.py` — MockSF class, `_make_job()`, `_set_env()` patterns
- **IMPORTS**: `sys`, `pytest`
- **GOTCHA**: The `MockSF` in this file must also track `Contact.create()` and `Contact.update()`. Extend the existing `MockSF` pattern by adding `contact_created` and `contact_updated` trackers with a `.Contact` property.

Tests to write:
1. `test_upsert_recruiter_contact_creates_new_contact_by_name` — no email, dedup by name+account
2. `test_upsert_recruiter_contact_creates_new_contact_by_email` — has email, dedup by email
3. `test_upsert_recruiter_contact_updates_existing_by_email` — found existing, calls update
4. `test_upsert_recruiter_contact_returns_none_when_no_name` — no recruiter_name → return None
5. `test_upsert_recruiter_contact_splits_full_name` — "Jane Smith" → FirstName=Jane, LastName=Smith
6. `test_upsert_recruiter_contact_single_word_name` — "Jenn" → LastName=Jenn (no FirstName)
7. `test_write_job_returns_three_tuple` — assert return is `(str, str, str|None)`
8. `test_write_job_still_succeeds_when_recruiter_upsert_raises` — verify job push is not aborted on recruiter failure
9. `test_write_job_sets_recruiter_on_job_application` — when contact returned, `Job_Application__c.update()` called with `Recruiter__c`
10. `test_write_job_skips_recruiter_update_when_no_contact` — when `recruiter_name` is None, no Contact operations

### UPDATE `tests/test_parser_greenhouse.py`

- **IMPLEMENT**: Extend `GREENHOUSE_RESPONSE` fixture to include `hiring_team` data. Add two new tests.
- **PATTERN**: `tests/test_parser_greenhouse.py` — extend `GREENHOUSE_RESPONSE` dict and `test_parse_maps_fields_correctly`
- **GOTCHA**: Updating `GREENHOUSE_RESPONSE` is safe — existing tests reference specific keys and won't break on addition of `hiring_team`.
- **VALIDATE**: `python -m pytest tests/test_parser_greenhouse.py -v`

Add to `GREENHOUSE_RESPONSE`:
```python
"hiring_team": {
    "hiring_managers": [{"id": 1, "first_name": "Alice", "last_name": "Johnson", "name": "Alice Johnson", "employee_id": None}],
    "recruiters":      [{"id": 2, "first_name": "Bob",   "last_name": "Smith",   "name": "Bob Smith",   "employee_id": None}],
    "coordinators":    [],
    "sourcers":        [],
}
```

New tests:
```python
def test_parse_extracts_recruiter_name(monkeypatch):
    """greenhouse.parse must extract recruiter name from hiring_team.recruiters[0]."""
    ...
    assert result["recruiter_name"] == "Bob Smith"
    assert result["recruiter_email"] is None

def test_parse_returns_none_recruiter_when_hiring_team_absent(monkeypatch):
    """When hiring_team is absent from API response, recruiter_name must be None."""
    # Use a GREENHOUSE_RESPONSE copy with hiring_team removed
    ...
    assert result["recruiter_name"] is None
```

### UPDATE `tests/test_parser_lever.py`

- **IMPLEMENT**: Add one test asserting that `recruiter_name` and `recruiter_email` are both `None` in the result.
- **VALIDATE**: `python -m pytest tests/test_parser_lever.py -v`

```python
def test_parse_recruiter_fields_are_none(monkeypatch):
    """Lever public API does not expose recruiter info — both fields must be None."""
    ...
    assert result["recruiter_name"] is None
    assert result["recruiter_email"] is None
```

### UPDATE `tests/test_db.py`

- **IMPLEMENT**: Add one test for the updated `mark_pushed()` signature with `sf_recruiter_contact_id`.
- **VALIDATE**: `python -m pytest tests/test_db.py -v`

---

## TESTING STRATEGY

### Unit Tests

Framework: `pytest` with `monkeypatch`. All tests are offline (mock SF + mock requests). Mirror `tests/test_sf_writer.py` pattern exactly.

**MockSF for recruiter tests** must track:
- `contact_created: list` — payloads passed to `Contact.create()`
- `contact_updated: list` — `(id, payload)` tuples from `Contact.update()`
- `contact_id_to_return: str` — returned from `Contact.create()`

### Integration Tests

Not added in this phase (integration requires live SF sandbox). Manual validation covers end-to-end.

### Edge Cases

1. `hiring_team` key absent from Greenhouse response → `recruiter_name = None`
2. `hiring_team.recruiters` is an empty list → `recruiter_name = None`
3. Recruiter name with apostrophe (e.g., `"O'Brien"`) → must be SOQL-escaped with `\\'`
4. `recruiter_name` is a single word (no space) → `LastName = name, FirstName` omitted from payload
5. `upsert_recruiter_contact()` raises `SalesforceExpiredSession` → must propagate (not caught by the non-fatal handler in `write_job()` — see gotcha below)
6. SF governor limit hit during recruiter write → `write_job()` catches exception, logs warning, returns `None` for contact ID — job application was already pushed
7. `recruiter_email` contains special characters → escape before inserting into SOQL

> **GOTCHA on `SalesforceExpiredSession`**: The `write_job()` non-fatal handler uses a broad `except Exception`. However, `SalesforceExpiredSession` is a subclass of `Exception`, so it WILL be caught and swallowed. To fix this, re-raise `SalesforceExpiredSession` in the except block — the orchestrator already handles it at a higher level.

Updated `write_job()` except block:
```python
except SalesforceExpiredSession:
    raise  # don't swallow session errors
except Exception as exc:
    logger.warning("Recruiter upsert failed for %s: %s — job was still pushed.", job.get("url"), exc)
```

Add `SalesforceExpiredSession` to the import in `sf_writer.py` (it's already imported at line 6).

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style

```bash
python -m py_compile job_finder/parser/greenhouse.py
python -m py_compile job_finder/parser/lever.py
python -m py_compile job_finder/parser/generic.py
python -m py_compile job_finder/sf_writer.py
python -m py_compile job_finder/db.py
python -m py_compile job_finder/orchestrator.py
```

### Level 2: Unit Tests — Individual Modules

```bash
python -m pytest tests/test_parser_greenhouse.py -v
python -m pytest tests/test_parser_lever.py -v
python -m pytest tests/test_parser_generic.py -v
python -m pytest tests/test_sf_writer.py -v
python -m pytest tests/test_sf_writer_recruiter.py -v
python -m pytest tests/test_db.py -v
```

### Level 3: Full Test Suite — Zero Regressions

```bash
python -m pytest tests/ -v
```

### Level 4: Manual Validation (requires live env vars)

```bash
# Dry run — recruiter info appears in log output but no SF write
python -m job_finder --dry-run --limit 3 --keywords "Software Engineer"

# Full run — verify Recruiter__c is set on created Job_Application__c records
python -m job_finder --limit 3 --keywords "Software Engineer"
# Then verify in Salesforce: open a Job_Application__c record → Recruiter__c field should be populated
```

### Level 5: DB Schema Migration

```bash
# Run against the actual PostgreSQL database (requires valid .env)
psql "$DATABASE_URL" -f sql/02_add_recruiter_contact_id.sql
# Verify:
psql "$DATABASE_URL" -c "\d job_lead" | grep recruiter
```

---

## ACCEPTANCE CRITERIA

- [ ] Greenhouse parser extracts `recruiter_name` from `hiring_team.recruiters[0].name`
- [ ] Greenhouse parser returns `recruiter_name = None` when `hiring_team` is absent
- [ ] Lever and Generic parsers return `recruiter_name = None`, `recruiter_email = None`
- [ ] `upsert_recruiter_contact()` creates a `Contact` when `recruiter_name` is present
- [ ] `upsert_recruiter_contact()` returns `None` (no exception) when `recruiter_name` is absent
- [ ] Contact dedup uses `Email` when available; falls back to `Name + AccountId`
- [ ] Single-word recruiter names result in valid `Contact` (LastName only, no FirstName)
- [ ] `Job_Application__c.Recruiter__c` is populated after a successful `write_job()` call
- [ ] `write_job()` is NOT aborted when recruiter upsert fails (log warning, continue)
- [ ] `SalesforceExpiredSession` is re-raised (not swallowed) in `write_job()`
- [ ] `db.mark_pushed()` accepts and writes `sf_recruiter_contact_id` (nullable)
- [ ] `job_lead.sf_recruiter_contact_id` column exists after running migration SQL
- [ ] `--dry-run` mode does NOT create any SF Contact records
- [ ] Full pytest suite passes with zero failures or errors
- [ ] No existing tests broken by return-type change on `write_job()` (3-tuple vs 2-tuple)

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each validation command passed immediately after the task
- [ ] `python -m pytest tests/ -v` passes with zero failures
- [ ] No syntax or compile errors in modified files
- [ ] Manual dry-run run confirms recruiter names appear in logs
- [ ] Manual full run confirms `Recruiter__c` populated on SF records (if live env available)
- [ ] All acceptance criteria checked off

---

## NOTES

### Why no separate `Recruiter Account`

The PRD specifies creating an `Account` with `Type = 'Recruiter Account'` for the recruiting firm. However, Greenhouse and Lever public APIs do not expose whether a recruiter is an internal employee or an external agency. Creating a duplicate `Account` for the same company under a different `Type` creates data quality issues and confusion in Salesforce. Phase 3 attaches the `Contact` directly to the existing `Job Application` Account for that company. If external agency detection is added in a future phase, the `Recruiter Account` pattern can be revisited then.

### Prerequisite: Salesforce `Account.Type` picklist

Per the PRD, the `Recruiter Account` picklist value must be added to `Account.Type` via Salesforce Setup UI before deploying this feature. This is a manual step that cannot be automated. Even though Phase 3 of this plan doesn't create `Recruiter Account` records, the prerequisite still applies if the PRD intent is to be followed fully.

Check that `Recruiter__c` exists as a lookup field on `Job_Application__c` pointing to `Contact`. If it doesn't exist, it must be created in Salesforce Setup (custom field, Lookup type → Contact).

### SOQL injection

All recruiter names and emails inserted into SOQL queries must use the `.replace("'", "\\'")` pattern (same as existing `safe_name` pattern in `upsert_account()`). This is the project's established pattern — do not use parameterized queries or different escaping.

### `write_job()` return type change — downstream impact

The return type changes from `tuple[str, str]` to `tuple[str, str, str | None]`. Check `orchestrator.py:105` (the only caller) and update it. No other callers exist in the current codebase. The existing `test_write_job_returns_both_ids` in `test_sf_writer.py` must be updated to unpack 3 values.

---

**Confidence Score: 8/10**

The plan is complete and implementable without additional research. The one uncertainty is whether `Recruiter__c` already exists as a custom lookup field on `Job_Application__c` in the user's Salesforce org — if it doesn't exist, the `sf.Job_Application__c.update()` call will fail with a Salesforce error. This can be confirmed before implementation by checking the org's field list or by attempting the update in a sandbox.
