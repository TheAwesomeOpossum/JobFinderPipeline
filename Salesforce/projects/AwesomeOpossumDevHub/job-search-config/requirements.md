# PRD: Job Search Config

_Generated: 2026-03-26 18:30_
_Org: AwesomeOpossumDevHub (https://your-org.develop.my.salesforce.com)_
_Context freshness: Last scan 2026-03-26 (0 days ago)_

---

## 1. Executive Summary

- **What:** Create a new `Job_Search_Config__c` custom object that allows a Salesforce user to manage JobFinder pipeline search configurations from the Salesforce UI. Each active record drives one independent nightly job search run. Add a lookup field on `JobApplication__c` to link each application back to the config that produced it.
- **Why:** Replace static YAML config files with Salesforce-managed records so search parameters (keywords, skills, salary floor, schedule) can be created, edited, activated, and deactivated without touching the codebase. The pipeline reads active configs at startup via REST API and falls back to local YAML files if Salesforce is unreachable.
- **Who:** Pipeline integration user (`your-sf-user@example.com`) reads and writes-back to records automatically. System administrators create and manage config records via the UI.
- **Impact:** New object `Job_Search_Config__c`, new lookup field on `JobApplication__c`, new custom tab in the Resume Lightning app, new `Anthropic_Claude` permission set replacing the typo'd `Althropic_Claude`.

---

## 2. Current State Analysis

### 2a. Affected Objects

| Object | Exists | Custom Fields | Triggers | Active Flows | Validation Rules |
|--------|--------|---------------|----------|--------------|------------------|
| `Job_Search_Config__c` | **New** | 0 (being created) | None | None | None |
| `JobApplication__c` | Yes | Unknown count | `JobApplicationTrigger` (Active, v62) | None | None |

### 2b. Existing Automation on Affected Objects

**`Job_Search_Config__c`:**
- No existing automation (new object).

**`JobApplication__c`:**
- **Before-save:** `JobApplicationTrigger` — handler/processor unknown (context not fully scanned); fires on insert/update
- **After-save:** Same trigger (after insert/update likely)
- **Async:** None
- **Validation:** None
- **Legacy:** None

The lookup field addition (`Search_Config__c`) is a passive, nullable field — it carries no business logic. No interaction with `JobApplicationTrigger` is expected.

### 2c. Existing Permissions

- **`Althropic_Claude`** — org-built permission set (typo in API name). Currently the integration user permission set. Will be replaced by `Anthropic_Claude`.
- **System Administrator** — full org access by default; will receive explicit CRUD on new object for clarity in permset/profile deploy.
- **Sharing model for new object:** Private (only owner and admins can see records unless explicitly shared). Integration user has full access via System Administrator–equivalent permissions.

### 2d. Existing UI

- **FlexiPage `Job_Application`** — existing Lightning record page for `JobApplication__c`. The `Search_Config__c` lookup field will be added to this page.
- **Resume Lightning App** — confirmed via `Resume_UtilityBar` FlexiPage. The new `Job_Search_Config__c` custom tab will be added here.
- **No existing page layouts** — all objects in this org use the standard layout + FlexiPage pattern. A new standard page layout will be created for `Job_Search_Config__c` and assigned.

---

## 3. Proposed Data Model Changes

### 3a. New Objects

| Object Label | API Name | Sharing Model | Record Types | Description |
|-------------|----------|---------------|-------------|-------------|
| Job Search Config | `Job_Search_Config__c` | Private | None | Stores search parameters for one independent nightly pipeline run. |

**Additional object properties:**
- Record Name Field: Auto-name (Text, user-defined, e.g., "Salesforce Developer Nightly")
- Allow Reports: Yes
- Allow Activities: No
- Track Field History: Yes — on `Keywords__c`, `Required_Skills__c`, `Is_Active__c`

### 3b. New Fields on `Job_Search_Config__c`

| Field Label | API Name | Type | Required | Default | Notes |
|------------|----------|------|----------|---------|-------|
| Keywords | `Keywords__c` | Text Area (255) | No | — | Comma-separated search terms. e.g. `Salesforce Developer, Salesforce Engineer` |
| Required Skills | `Required_Skills__c` | MultiselectPicklist | No | — | References `Skills` GVS. `restricted: true`, `visibleLines: 5`. Any-of matching — job must contain at least one. |
| Bonus Skills | `Bonus_Skills__c` | MultiselectPicklist | No | — | References `Skills` GVS. `restricted: true`, `visibleLines: 5`. Each matched skill adds +5 to relevance score (max +20). Never filters. |
| Daily Limit | `Daily_Limit__c` | Number (3, 0) | No | 10 | Max job applications pushed per run. |
| Min Annual Salary | `Min_Annual_Salary__c` | Currency (12, 0) | No | 0 | Jobs with posted salary ceiling below this are filtered. 0 = disabled. |
| Days Back | `Days_Back__c` | Number (2, 0) | No | 1 | Calendar days back to search for new postings. |
| Schedule Hour (UTC) | `Schedule_Hour__c` | Number (2, 0) | No | 2 | Hour (0–23 UTC) the search runs. |
| Schedule Minute | `Schedule_Minute__c` | Number (2, 0) | No | 0 | Minute (0–59) within the hour. |
| Is Active | `Is_Active__c` | Checkbox | No | false | Only `true` records are loaded by the pipeline scheduler. |
| Last Run At | `Last_Run_At__c` | Date/Time | No | — | Written by pipeline after each successful run. Read-only in layout. |
| Last Run Summary | `Last_Run_Summary__c` | Long Text Area (32768) | No | — | JSON written back by pipeline. e.g. `{"found":45,"new":12,"pushed":5}`. Read-only in layout. |

> **GVS Note:** `Required_Skills__c` and `Bonus_Skills__c` both reference the existing `Skills` Global Value Set. Do NOT recreate it. The GVS already exists (`context/AwesomeOpossumDevHub/data-architecture/_inventory.md`).

> **Semicolon delimiter note:** Salesforce MultiselectPicklist fields store values as semicolon-delimited strings (e.g. `"Apex;SOQL;Flow Builder"`). The pipeline splits on `;` to produce Python lists.

### 3c. New Fields on Existing Objects

| Object | Field Label | API Name | Type | Required | Default | Notes |
|--------|------------|----------|------|----------|---------|-------|
| `JobApplication__c` | Search Config | `Search_Config__c` | Lookup(`Job_Search_Config__c`) | No | — | Links application to the config that produced it. Nullable — YAML-fallback runs leave blank. |

**Lookup field properties:**
- Related list label on `Job_Search_Config__c`: `Job Applications`
- What to do if lookup record is deleted: **Clear the field value (don't delete the child record)**
- Required: No
- Do NOT add the related list to the `Job_Application` FlexiPage — navigation is one-directional (app → config click-through only). The related list on `Job_Search_Config__c` is sufficient.

### 3d. New Relationships

| Parent Object | Child Object | Relationship Type | Relationship Name | Notes |
|--------------|-------------|-------------------|-------------------|-------|
| `Job_Search_Config__c` | `JobApplication__c` | Lookup | `Search_Config` | Nullable; no cascade delete |

---

## 4. Proposed Automation

### 4a. Automation Decision Matrix

| # | Business Logic | Recommended | Rationale |
|---|---------------|-------------|-----------|
| 1 | Validate Schedule Hour range (0–23) | Validation Rule | Simple formula, no cross-object logic needed |
| 2 | Validate Schedule Minute range (0–59) | Validation Rule | Same — pure field-level constraint |
| 3 | Require Keywords when activating config | Validation Rule | Declarative constraint, no side effects needed |

### 4b. New Flows

None required. All business logic is handled via validation rules. Pipeline reads/writes occur via REST API outside of Salesforce automation.

### 4c. New Trigger Stack

None required. No Apex is needed for this feature. The pipeline handles all reads and writes via REST API. `JobApplicationTrigger` already exists on `JobApplication__c` — no modification needed.

### 4d. Validation Rules

| Rule Name | Object | Formula | Error Message | Active |
|-----------|--------|---------|---------------|--------|
| `Schedule_Hour_Range` | `Job_Search_Config__c` | `Schedule_Hour__c < 0 \|\| Schedule_Hour__c > 23` | "Schedule Hour must be between 0 and 23 (UTC)." | Yes |
| `Schedule_Minute_Range` | `Job_Search_Config__c` | `Schedule_Minute__c < 0 \|\| Schedule_Minute__c > 59` | "Schedule Minute must be between 0 and 59." | Yes |
| `Keywords_Required_When_Active` | `Job_Search_Config__c` | `Is_Active__c = true && ISBLANK(Keywords__c)` | "Keywords are required before activating a search config." | Yes |

### 4e. Conflict Assessment

**✅ No automation conflicts detected.**

- `Job_Search_Config__c` is a brand-new object with no existing automation. All three validation rules are self-contained field constraints with no cross-object dependencies.
- `JobApplication__c` has `JobApplicationTrigger` (active). The new `Search_Config__c` field is a nullable lookup — it adds no trigger events, no formula dependencies, and no required constraints. The trigger's before/after save logic is unaffected by a new lookup field being populated at insert time by the pipeline.

---

## 5. UI Requirements

### 5a. Existing Components to Modify

| Component | Type | Change Required |
|-----------|------|-----------------|
| `Job_Application` | FlexiPage | Add `Search_Config__c` lookup field to an existing or new section |

**Placement on `Job_Application` FlexiPage:** Add a new section "Source" (or append to an existing relevant section) containing `Search_Config__c`. This enables click-through from any job application to the config that produced it.

### 5b. New Components

| Component | Type | Target | Description |
|-----------|------|--------|-------------|
| `Job_Search_Config__c` standard tab | Custom Tab | Resume Lightning App | Provides top-level navigation to the config object |
| `Job_Search_Config__c` record page | FlexiPage | `Job_Search_Config__c` | Standard record page using the layout below |

**Tab details:**
- Tab label: `Job Search Configs`
- Tab style: Choose a relevant icon (e.g., search or settings icon)
- Add to: **Resume Lightning app** (confirmed via `Resume_UtilityBar` FlexiPage in context)

### 5c. Page Layout

**Object:** `Job_Search_Config__c`
**Layout name:** `Job Search Config Layout`

| Section | Fields | Layout |
|---------|--------|--------|
| Search Configuration | Keywords (full width) | 1-column |
| Search Configuration | Required Skills, Bonus Skills | 2-column (side by side) |
| Thresholds & Limits | Daily Limit, Min Annual Salary, Days Back | 2-column |
| Schedule | Schedule Hour (UTC), Schedule Minute, Is Active | 2-column |
| Pipeline Feedback _(read-only)_ | Last Run At, Last Run Summary | 2-column / 1-column |

`Last_Run_At__c` and `Last_Run_Summary__c` are placed in the layout read-only (no FLS restriction — layout placement only). Any user with Edit access can technically modify them, but they are not presented as editable in standard usage.

### 5d. List View

**Object:** `Job_Search_Config__c`
**List view name:** `Active Configs`
**Filter:** `Is_Active__c = true`
**Columns:** Name · Keywords · Daily Limit · Schedule Hour (UTC) · Schedule Minute · Last Run At
**Visibility:** Visible to all users

---

## 6. Integration Requirements

| Integration | Direction | Type | Description |
|------------|-----------|------|-------------|
| JobFinder Pipeline (Python) | Inbound read | REST API SOQL | Pipeline reads active configs at scheduler startup via `simple_salesforce` |
| JobFinder Pipeline write-back | Outbound write | REST API PATCH | Pipeline writes `Last_Run_At__c` and `Last_Run_Summary__c` after each run |
| JobFinder Pipeline app creation | Outbound write | REST API POST | Pipeline populates `Search_Config__c` on `JobApplication__c` records at insert time |

**SOQL read contract (pipeline startup):**
```sql
SELECT Id, Name, Keywords__c, Required_Skills__c, Bonus_Skills__c,
       Daily_Limit__c, Min_Annual_Salary__c, Schedule_Hour__c,
       Schedule_Minute__c, Days_Back__c
FROM Job_Search_Config__c
WHERE Is_Active__c = true
ORDER BY Schedule_Hour__c ASC, Schedule_Minute__c ASC
```

**Field → Python dict mapping:**

| SF Field | Python Key | Transform |
|----------|------------|-----------|
| `Name` | `profile_name` | direct |
| `Keywords__c` | `keywords` | direct (comma-separated string) |
| `Required_Skills__c` | `required_skills` | split on `;`, strip whitespace → list |
| `Bonus_Skills__c` | `bonus_skills` | split on `;`, strip whitespace → list |
| `Daily_Limit__c` | `limit` | `int()` |
| `Min_Annual_Salary__c` | `min_annual_salary` | `float()` |
| `Schedule_Hour__c` | `schedule_hour` | `int()` |
| `Schedule_Minute__c` | `schedule_minute` | `int()` |
| `Days_Back__c` | `days` | `int()` |

**Write-back contract:**
```python
sf.Job_Search_Config__c.update(record_id, {
    "Last_Run_At__c":      datetime.utcnow().isoformat() + "Z",
    "Last_Run_Summary__c": json.dumps(summary_dict),
})
```

**JobApplication lookup population:**
```python
# In create_job_application() payload:
"Search_Config__c": job.get("sf_search_config_id") or None
```

`sf_search_config_id` is carried through the run from the profile dict. Jobs run from YAML fallback have `sf_search_config_id = None` and the lookup is left blank. Pipeline changes to wire this up are deferred to a separate phase.

---

## 7. Permission & Security Model

### 7a. Object-Level Security (OLS)

| Object | Permission Set / Profile | Create | Read | Update | Delete |
|--------|--------------------------|--------|------|--------|--------|
| `Job_Search_Config__c` | `Anthropic_Claude` (integration user) | ✓ | ✓ | ✓ | ✗ |
| `Job_Search_Config__c` | System Administrator | ✓ | ✓ | ✓ | ✓ |
| `JobApplication__c` | `Anthropic_Claude` (integration user) | ✓ | ✓ | ✓ | ✗ |

### 7b. Field-Level Security (FLS)

All fields on `Job_Search_Config__c` — visible and editable for `Anthropic_Claude` and System Administrator, with the following note:

| Object.Field | `Anthropic_Claude` | System Administrator | Notes |
|-------------|-------------------|---------------------|-------|
| `Job_Search_Config__c.*` (all fields) | Visible + Editable | Visible + Editable | Integration user needs Edit on `Last_Run_At__c` and `Last_Run_Summary__c` for write-back |
| `JobApplication__c.Search_Config__c` | Visible + Editable | Visible + Editable | Integration user must populate at insert time |

### 7c. Record-Level Security (RLS)

| Object | OWD | Sharing Rules Needed | Notes |
|--------|-----|---------------------|-------|
| `Job_Search_Config__c` | Private | No | Integration user is System Administrator–equivalent; sees all records. Admin users manage all records. |

### 7d. Permission Set Changes

| Action | Old API Name | New API Name | New Label | Assigned To |
|--------|-------------|-------------|-----------|-------------|
| Replace (create new, deprecate old) | `Althropic_Claude` | `Anthropic_Claude` | Anthropic Claude | `your-sf-user@example.com` |

**`Anthropic_Claude` permission set must include:**
- All permissions previously in `Althropic_Claude` (retrieve before modifying)
- `Job_Search_Config__c`: Read, Create, Edit on object + all fields
- `JobApplication__c.Search_Config__c`: Read, Edit on field

**Deprecation plan for `Althropic_Claude`:**
1. Retrieve the existing `Althropic_Claude` permission set to capture current permissions
2. Create `Anthropic_Claude` with all existing + new permissions
3. Assign `Anthropic_Claude` to `your-sf-user@example.com`
4. Remove `Althropic_Claude` assignment from `your-sf-user@example.com`
5. Delete `Althropic_Claude` permission set

---

## 8. Implementation Phases

### Phase 1: Data Model
| # | Deliverable | Deploy Type | Dependencies |
|---|------------|-------------|-------------|
| 1 | Create `Job_Search_Config__c` object | Metadata Deploy | None |
| 2 | Deploy all 11 fields on `Job_Search_Config__c` | Metadata Deploy | Object exists |
| 3 | Deploy `Search_Config__c` lookup on `JobApplication__c` | Metadata Deploy | `Job_Search_Config__c` object exists |

_Deploy order: Object → Fields → Lookup field on child object_

### Phase 2: Security
| # | Deliverable | Deploy Type | Dependencies |
|---|------------|-------------|-------------|
| 4 | Retrieve existing `Althropic_Claude` permission set | Retrieve | — |
| 5 | Create `Anthropic_Claude` permission set (with all prior + new permissions) | Metadata Deploy | All fields exist |
| 6 | Assign `Anthropic_Claude` to `your-sf-user@example.com` | Data operation | Perm set deployed |
| 7 | Remove `Althropic_Claude` assignment and delete perm set | Data operation + Delete | New perm set assigned |

_⚠️ Never deploy field permissions before the fields they reference exist in the org._

### Phase 3: Validation Rules & Layout
| # | Deliverable | Deploy Type | Dependencies |
|---|------------|-------------|-------------|
| 8 | Deploy 3 validation rules on `Job_Search_Config__c` | Metadata Deploy | Object and fields exist |
| 9 | Create `Job Search Config Layout` page layout | Metadata Deploy | Fields exist |
| 10 | Create custom tab for `Job_Search_Config__c` | Metadata Deploy | Object exists |
| 11 | Add tab to Resume Lightning app | Metadata Deploy | Tab exists |
| 12 | Update `Job_Application` FlexiPage — add `Search_Config__c` field | Retrieve → Modify → Deploy | Lookup field deployed |
| 13 | Create "Active Configs" list view | Metadata Deploy | Object and `Is_Active__c` field exist |

_Deploy order: Validation Rules → Layout → Tab → App → FlexiPage_
_⚠️ Always retrieve FlexiPage before editing — never overwrite from scratch._

### Phase 4: Validation & Testing
| # | Deliverable | Notes |
|---|------------|-------|
| 14 | Create 2 test records (1 active, 1 inactive) | Validate pipeline SOQL returns only active record |
| 15 | Smoke test pipeline read | `sf.query("SELECT Name, Keywords__c FROM Job_Search_Config__c WHERE Is_Active__c = true")` |
| 16 | Validate write-back | Manually trigger write-back, confirm `Last_Run_At__c` and `Last_Run_Summary__c` update |
| 17 | Validate lookup field | Create a `JobApplication__c` record with `Search_Config__c` populated, confirm click-through works |

### Estimated Implementation Effort

| Phase | Estimated Effort | Notes |
|-------|-----------------|-------|
| Data Model | Low | Pure metadata, no code |
| Security | Low | One perm set create + one delete |
| Validation Rules + Layout | Low | Declarative only |
| Testing | Low | Manual smoke tests |
| **Total** | **Low** | No Apex, no flows — fully declarative |

---

## 9. Risks & Conflicts

| # | Risk | Severity | Likelihood | Mitigation |
|---|------|----------|-----------|------------|
| 1 | **Automation conflicts** — `JobApplicationTrigger` fires on insert of records that include `Search_Config__c` | Low | Low | Trigger is unaware of the new field; nullable lookup causes no side effects. No changes to trigger needed. |
| 2 | **GVS `Skills` value mismatch** — pipeline does case-insensitive substring matching; GVS `fullName` values must match job posting text | Medium | Low | GVS values are already used by `Job__c.Skills__c` and `Experience__c.Skills__c` — they are known-good tokens. |
| 3 | **Permission set migration** — deleting `Althropic_Claude` before assigning `Anthropic_Claude` could break the integration user's access | High | Low if sequenced correctly | Strict sequencing: assign new → verify → remove old. Never delete old perm set before new one is confirmed active. |
| 4 | **Semicolon delimiter** — `MultiselectPicklist` stores as semicolon-delimited string; pipeline must split on `;` not `,` | Medium | Low | Clearly documented in pipeline integration contract. Must verify in integration test. |
| 5 | **Page layout + FlexiPage** — no custom page layouts exist yet in this org; standard layouts are assigned | Low | Low | Create a new layout for `Job_Search_Config__c`, assign it. For `Job_Application`, retrieve the existing FlexiPage before editing. |
| 6 | **Data migration** — existing `JobApplication__c` records will have a null `Search_Config__c` lookup | Low | Certain | Intentional and documented — YAML-fallback records have no linked config. No backfill needed. |

---

## 10. Test Plan

### Unit Tests

No Apex code is introduced. No test classes are required.

### Integration / End-to-End Tests

| # | Scenario | Objects Involved | Steps | Expected Outcome |
|---|----------|-----------------|-------|-----------------|
| 1 | Active config is read by pipeline | `Job_Search_Config__c` | Create active record → run pipeline SOQL | Record appears in results |
| 2 | Inactive config is excluded | `Job_Search_Config__c` | Create inactive record → run pipeline SOQL | Record NOT in results |
| 3 | Write-back succeeds | `Job_Search_Config__c` | Run pipeline or simulate write → check fields | `Last_Run_At__c` and `Last_Run_Summary__c` updated |
| 4 | Lookup field populated on job application | `JobApplication__c`, `Job_Search_Config__c` | Insert `JobApplication__c` with `Search_Config__c` set → inspect record | Lookup shows correct config; click-through works |
| 5 | Lookup cleared on config delete | `JobApplication__c`, `Job_Search_Config__c` | Delete a config record | Child `JobApplication__c` records have null `Search_Config__c`, not deleted |
| 6 | Validation — activate without keywords | `Job_Search_Config__c` | Set `Is_Active__c = true`, leave `Keywords__c` blank → save | Error: "Keywords are required before activating a search config." |
| 7 | Validation — bad schedule hour | `Job_Search_Config__c` | Set `Schedule_Hour__c = 25` → save | Error: "Schedule Hour must be between 0 and 23 (UTC)." |
| 8 | Validation — bad schedule minute | `Job_Search_Config__c` | Set `Schedule_Minute__c = 60` → save | Error: "Schedule Minute must be between 0 and 59." |

### Manual Testing Checklist

| # | Step | Action | Expected Result |
|---|------|--------|-----------------|
| 1 | Navigate to Resume app | Open Lightning app | "Job Search Configs" tab is visible |
| 2 | Create first config | Fill in "Salesforce Developer Nightly" example record | Record saves; "Active Configs" list view shows it |
| 3 | View page layout | Open the record | All 4 sections visible; Pipeline Feedback section shows blank fields |
| 4 | Edit `Last_Run_At__c` directly | Try to edit via inline edit | Field is not editable in layout (read-only placement) |
| 5 | Open `JobApplication__c` record | Navigate to any job app | `Search_Config__c` field appears in layout (blank for existing records) |
| 6 | Perm set verification | Log in as `your-sf-user@example.com` | Can Read + Edit `Job_Search_Config__c`; cannot delete |
| 7 | Pipeline smoke test | Run `sf.query(...)` from pipeline | Returns active config records with correct field values |

---

## 11. Naming Conventions Applied

| Category | Convention | Example Applied |
|----------|-----------|-----------------|
| Objects | PascalCase with underscores | `Job_Search_Config__c` |
| Fields | PascalCase with underscores | `Required_Skills__c`, `Min_Annual_Salary__c` |
| Validation Rules | Snake_Case descriptive | `Schedule_Hour_Range`, `Keywords_Required_When_Active` |
| Permission Sets | Descriptive PascalCase | `Anthropic_Claude` |
| FlexiPages | `{Object}_Record_Page` or `{Feature}` | `Job_Application` (existing, no rename) |
| Page Layouts | `{Object Label} Layout` | `Job Search Config Layout` |
| List Views | Descriptive phrase | `Active Configs` |

---

## Appendix A: Context Files Referenced

| File | Source | Last Updated |
|------|--------|-------------|
| `context/AwesomeOpossumDevHub/META.md` | sf-init-project | 2026-03-26 |
| `context/AwesomeOpossumDevHub/objects/_inventory.md` | sf-init-project | 2026-03-26 |
| `context/AwesomeOpossumDevHub/apex/_inventory.md` | sf-trigger-patterns | 2026-03-26 |
| `context/AwesomeOpossumDevHub/layouts/_inventory.md` | sf-layouts | 2026-03-26 |
| `context/AwesomeOpossumDevHub/permissions/_inventory.md` | sf-permissions | 2026-03-26 |
| `context/AwesomeOpossumDevHub/data-architecture/_inventory.md` | sf-data-architecture | 2026-03-26 |
| `/home/your-username/Full_Stack_Applications/JobFinder/docs/sf_job_search_config_requirements.md` | User-provided spec | — |

Total context files loaded: 7 / 15 budget

---

## Appendix B: Areas Not Analyzed

| Area | Reason |
|------|--------|
| Flows | Not applicable — no flows in this org, none proposed |
| Legacy Automation | Not applicable — no workflow rules in this org |
| Reports & Dashboards | Not selected — no reporting work in scope |
| Experience Cloud | Not selected — not applicable to this feature |
| Integration (named credentials) | Existing `AnthropicClaude` named credential and `AnthropicClaude` remote site setting are already in place for pipeline callouts |

---

## Appendix C: Example Records to Create During Testing

**Record 1 — Salesforce Developer Nightly (Active)**
```
Name:            Salesforce Developer Nightly
Keywords:        Salesforce Developer, Salesforce Engineer, SFDC Developer
Required Skills: Apex; Lightning Web Components; Flow Builder; SOQL; Screen Flows
Bonus Skills:    Batch Apex; Queueable Apex; Integration Cloud; CPQ; Experience Cloud
Daily Limit:     10
Min Salary:      145000
Days Back:       1
Schedule Hour:   2
Schedule Minute: 30
Is Active:       ✓
```

**Record 2 — Salesforce Architect Nightly (Active)**
```
Name:            Salesforce Architect Nightly
Keywords:        Salesforce Architect, Salesforce Solutions Architect, SFDC Architect
Required Skills: Apex; Lightning Web Components; Integration Cloud
Bonus Skills:    CPQ; Marketing Cloud; Analytics Cloud; Field Service Lightning
Daily Limit:     8
Min Salary:      160000
Days Back:       1
Schedule Hour:   3
Schedule Minute: 0
Is Active:       ✓
```
