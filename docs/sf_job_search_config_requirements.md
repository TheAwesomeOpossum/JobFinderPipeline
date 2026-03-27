# SF Requirements — Job_Search_Config__c

**Purpose**: Allow a Salesforce user to manage JobFinder search configurations directly from the
Salesforce UI. Each active `Job_Search_Config__c` record drives one independent nightly search run.
The pipeline reads these records at startup; if Salesforce is unreachable it falls back to local
YAML files.

**No Apex required.** The pipeline handles all reads and writes via the REST API.

---

## Prerequisite: Skills Global Value Set

The `Skills` Global Value Set **already exists** in this org — it is used by `Job__c.Skills__c`
and `Experience__c.Skills__c`. **Do not recreate it.**

Both skill fields on `Job_Search_Config__c` must reference this same GVS so the vocabulary is
shared across the entire org.

GVS metadata source:
```
/home/your-username/Salesforce_Projects/LWRPortfolioWebsite/force-app/main/default/
    globalValueSets/Skills.globalValueSet-meta.xml
```

### Salesforce-Relevant GVS Values (subset of 216+)

| GVS `fullName` | Use |
|---|---|
| `Apex` | Required Skills — Salesforce Dev |
| `Lightning Web Components` | Required Skills — Salesforce Dev |
| `Flow Builder` | Required Skills — Salesforce Dev |
| `SOQL` | Required Skills — Salesforce Dev |
| `Screen Flows` | Required Skills — Salesforce Dev |
| `Integration Cloud` | Required Skills — Architect |
| `Batch Apex` | Bonus Skills |
| `Queueable Apex` | Bonus Skills |
| `Invocable Apex` | Bonus Skills |
| `Scheduled Apex Jobs` | Bonus Skills |
| `Experience Cloud` | Bonus Skills |
| `CPQ` | Bonus Skills |
| `Marketing Cloud` | Bonus Skills |
| `Analytics Cloud` | Bonus Skills |
| `Field Service Lightning` | Bonus Skills |
| `Aura` | Bonus Skills |
| `Visualforce` | Bonus Skills |
| `SOSL` | Bonus Skills |
| `Process Builder` | Bonus Skills |

---

## Custom Object: `Job_Search_Config__c`

### Object Properties

| Property | Value |
|---|---|
| Object Label | Job Search Config |
| Object API Name | `Job_Search_Config__c` |
| Record Name Field | Text — user-defined (e.g. "Salesforce Developer Nightly") |
| Sharing Model | Private |
| Allow Reports | Yes |
| Allow Activities | No |
| Track Field History | Yes — track `Keywords__c`, `Required_Skills__c`, `Is_Active__c` |

---

### Fields

| Field Label | API Name | Type | Properties | Notes |
|---|---|---|---|---|
| Keywords | `Keywords__c` | Text Area | 255 chars | Comma-separated search terms. Example: `Salesforce Developer, Salesforce Engineer, SFDC Developer` |
| Required Skills | `Required_Skills__c` | **MultiselectPicklist** | `restricted: true` · `valueSetName: Skills` · `visibleLines: 5` | References `Skills` GVS. A job must contain **at least one** selected skill anywhere in the job description. Jobs matching none are dropped before being written to Salesforce. |
| Bonus Skills | `Bonus_Skills__c` | **MultiselectPicklist** | `restricted: true` · `valueSetName: Skills` · `visibleLines: 5` | References `Skills` GVS. Each selected skill found in a job description adds +5 to the relevance score (max +20). Never blocks a job — only boosts ranking. |
| Daily Limit | `Daily_Limit__c` | Number | 3,0 · Default: `10` | Maximum job applications pushed to Salesforce per run. |
| Min Annual Salary | `Min_Annual_Salary__c` | Currency | 12,0 · Default: `0` | Jobs whose posted salary ceiling is below this amount are filtered. `0` = disabled (no salary filter). |
| Days Back | `Days_Back__c` | Number | 2,0 · Default: `1` | How many calendar days back to search for new postings. |
| Schedule Hour (UTC) | `Schedule_Hour__c` | Number | 2,0 · Default: `2` | Hour (0–23) the search runs each day, in UTC. |
| Schedule Minute | `Schedule_Minute__c` | Number | 2,0 · Default: `0` | Minute (0–59) within the hour. |
| Is Active | `Is_Active__c` | Checkbox | Default: `false` | Only records where `Is_Active__c = true` are loaded by the scheduler. Uncheck to pause without deleting. |
| Last Run At | `Last_Run_At__c` | Date/Time | Read-only in UI | Set by the pipeline after each successful run. Do not expose as editable. |
| Last Run Summary | `Last_Run_Summary__c` | Long Text Area | 32768 chars · Read-only in UI | JSON string written back by pipeline. Example: `{"found": 45, "new": 12, "parsed": 12, "skills_filtered": 3, "salary_filtered": 1, "qualified": 5, "pushed": 5, "failed": 0}` |

---

### Field Metadata XML

Both skill fields follow the exact same pattern as `Job__c.Skills__c` and `Experience__c.Skills__c`:

**`Required_Skills__c.field-meta.xml`**
```xml
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Required_Skills__c</fullName>
    <label>Required Skills</label>
    <description>A job must contain at least one of these skills in its description to be imported into Salesforce. Any-of semantics — matching one is sufficient.</description>
    <inlineHelpText>Select skills that must appear in the job description. A job matching any one of these passes the filter. Leave blank to disable skill filtering for this config.</inlineHelpText>
    <required>false</required>
    <trackTrending>false</trackTrending>
    <type>MultiselectPicklist</type>
    <valueSet>
        <restricted>true</restricted>
        <valueSetName>Skills</valueSetName>
    </valueSet>
    <visibleLines>5</visibleLines>
</CustomField>
```

**`Bonus_Skills__c.field-meta.xml`**
```xml
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Bonus_Skills__c</fullName>
    <label>Bonus Skills</label>
    <description>Jobs mentioning these skills receive a relevance score boost (+5 per skill matched, max +20 total). This is not a filter — jobs are never excluded for lacking bonus skills.</description>
    <inlineHelpText>Select preferred skills. Jobs mentioning these will rank higher in the daily results but will never be excluded for lacking them.</inlineHelpText>
    <required>false</required>
    <trackTrending>false</trackTrending>
    <type>MultiselectPicklist</type>
    <valueSet>
        <restricted>true</restricted>
        <valueSetName>Skills</valueSetName>
    </valueSet>
    <visibleLines>5</visibleLines>
</CustomField>
```

---

### Validation Rules

| Rule | Formula | Error Message |
|---|---|---|
| Schedule Hour range | `Schedule_Hour__c < 0 \|\| Schedule_Hour__c > 23` | "Schedule Hour must be between 0 and 23 (UTC)." |
| Schedule Minute range | `Schedule_Minute__c < 0 \|\| Schedule_Minute__c > 59` | "Schedule Minute must be between 0 and 59." |
| Keywords required when active | `Is_Active__c = true && ISBLANK(Keywords__c)` | "Keywords are required before activating a search config." |

---

### Page Layout

**Section: Search Configuration**
- Keywords (full width)
- Required Skills, Bonus Skills (side by side)

**Section: Thresholds & Limits**
- Daily Limit, Min Annual Salary, Days Back

**Section: Schedule**
- Schedule Hour (UTC), Schedule Minute, Is Active

**Section: Pipeline Feedback** *(read-only)*
- Last Run At, Last Run Summary

---

### List View: "Active Configs"

Filter: `Is_Active__c = true`

Columns: Name · Keywords · Daily Limit · Schedule Hour · Schedule Minute · Last Run At

---

## `JobApplication__c` Field Addition

Add one field to the **existing** `JobApplication__c` object:

| Field Label | API Name | Type | Notes |
|---|---|---|---|
| Search Config | `Search_Config__c` | **Lookup(Job_Search_Config__c)** | Links each application to the config record that produced it. Nullable — jobs found via YAML fallback have no linked config. Do not mark required. |

**Lookup field properties:**
- Related object: `Job_Search_Config__c`
- Related list label: `Job Applications`
- Required: No
- What to do if the lookup record is deleted: **Don't delete this record; clear the value of the lookup field**

This enables:
- Click-through from any job application to the search config that found it
- List view / report filters on `Search_Config__r.Name`
- Aggregate reporting — how many applications came from each config

---

## Pipeline Integration Contract

### SOQL Read (at scheduler startup and before each run)

```sql
SELECT Id, Name, Keywords__c, Required_Skills__c, Bonus_Skills__c,
       Daily_Limit__c, Min_Annual_Salary__c, Schedule_Hour__c,
       Schedule_Minute__c, Days_Back__c
FROM Job_Search_Config__c
WHERE Is_Active__c = true
ORDER BY Schedule_Hour__c ASC, Schedule_Minute__c ASC
```

### Field → Python Dict Mapping

| SF Field | Python Key | Transformation |
|---|---|---|
| `Name` | `profile_name` | direct |
| `Keywords__c` | `keywords` | direct (comma-separated string) |
| `Required_Skills__c` | `required_skills` | **split on `;`** then strip whitespace → list |
| `Bonus_Skills__c` | `bonus_skills` | **split on `;`** then strip whitespace → list |
| `Daily_Limit__c` | `limit` | `int()` |
| `Min_Annual_Salary__c` | `min_annual_salary` | `float()` |
| `Schedule_Hour__c` | `schedule_hour` | `int()` |
| `Schedule_Minute__c` | `schedule_minute` | `int()` |
| `Days_Back__c` | `days` | `int()` |

> **Critical**: Salesforce MultiselectPicklist fields store selected values as a **semicolon-delimited
> string** (e.g. `"Apex;Lightning Web Components;SOQL"`). The pipeline splits on `;` to produce a Python
> list. GVS `fullName` values are used directly as search tokens — the pipeline does case-insensitive
> substring matching, so `"Lightning Web Components"` correctly matches `"lightning web components"` in
> a job posting.

### Write-back (after each run)

```python
sf.Job_Search_Config__c.update(record_id, {
    "Last_Run_At__c":      datetime.utcnow().isoformat() + "Z",
    "Last_Run_Summary__c": json.dumps(summary_dict),
})
```

### `JobApplication__c` lookup population

When the scheduler reads configs from Salesforce, each config record's `Id` is carried through the run and written to each resulting job application:

```python
# In create_job_application() payload:
"Search_Config__c": job.get("sf_search_config_id") or None,
```

`sf_search_config_id` is set by the scheduler on the profile dict before calling `orchestrator.run()`, and stamped onto each job alongside `search_profile` (the Postgres string). Jobs run from YAML fallback have `sf_search_config_id = None` and the lookup field is left blank.

> **Pipeline implementation deferred** — this write will be added in the phase that wires up SF-driven config reads.

---

## Permissions

**Integration user** (`your-sf-user@example.com`):
- `Job_Search_Config__c`: Read + Edit (Edit needed for `Last_Run_At__c` / `Last_Run_Summary__c` write-back)
- `JobApplication__c.Search_Config__c`: Read + Edit (to populate the lookup at insert time)

**Human admins managing configs**:
- `Job_Search_Config__c`: Read, Create, Edit, Delete on object and all fields

---

## Rollout Steps

1. Create `Job_Search_Config__c` in Setup → Object Manager
2. Add all fields from the table above
3. Add validation rules
4. Build the page layout (section groupings above)
5. Create the "Active Configs" list view
6. Add `Search_Config__c` Lookup(Job_Search_Config__c) to `JobApplication__c`
   - Set "What to do if the lookup record is deleted" → **Don't delete; clear the field**
   - Related list label: `Job Applications`
7. Update the integration user's profile/permission set with Read+Edit on both objects and all new fields
8. Create 2 test records (one `Is_Active__c = true`, one `false`) to validate pipeline reads them correctly
9. Smoke test: `python3 -c "from job_finder import sf_writer; sf = sf_writer.connect(); print(sf.query('SELECT Name, Keywords__c FROM Job_Search_Config__c WHERE Is_Active__c = true'))"`

---

## Example Records

**Salesforce Developer Nightly**
```
Keywords:        Salesforce Developer, Salesforce Engineer, SFDC Developer
Required Skills: Apex; Lightning Web Components; Flow Builder; SOQL; Screen Flows
Bonus Skills:    Batch Apex; Queueable Apex; Integration Cloud; CPQ; Experience Cloud
Daily Limit:     10
Min Salary:      $145,000
Schedule Hour:   2
Schedule Minute: 30
Is Active:       ✓
```

**Salesforce Architect Nightly**
```
Keywords:        Salesforce Architect, Salesforce Solutions Architect, SFDC Architect
Required Skills: Apex; Lightning Web Components; Integration Cloud
Bonus Skills:    CPQ; Marketing Cloud; Analytics Cloud; Field Service Lightning
Daily Limit:     8
Min Salary:      $160,000
Schedule Hour:   3
Schedule Minute: 0
Is Active:       ✓
```
