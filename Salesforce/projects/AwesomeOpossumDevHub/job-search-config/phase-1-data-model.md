# Phase 1: Data Model

**Feature:** Job Search Config
**Org:** AwesomeOpossumDevHub
**Phase:** 1 of 3
**Master Plan:** `projects/AwesomeOpossumDevHub/job-search-config/master-plan.md`
**Generated:** 2026-03-26

---

## Prior Phase Summary

This is Phase 1 — no prior phases.

---

## Phase Goals

- Create `Job_Search_Config__c` custom object with Private sharing model and field history tracking
- Deploy all 11 custom fields on `Job_Search_Config__c` (including 2 MultiselectPicklist fields referencing the `Skills` GVS)
- Deploy `Search_Config__c` lookup field on `JobApplication__c` (nullable, clears on parent delete)
- Grant System Administrator profile full CRUD OLS and read+edit FLS on all new fields
- Establish the data contract the pipeline reads at startup (9 fields queryable via SOQL)

---

## Success Criteria

| # | Criterion | Verification Method | Tier |
|---|---|---|---|
| SC-1 | `Job_Search_Config__c` object exists in org with `sharingModel = Private` | `sf sobject describe --sobject Job_Search_Config__c --json` | Tier 2 (E2E) |
| SC-2 | All 11 custom fields exist with correct types | `sf sobject describe --sobject Job_Search_Config__c --json` — verify each field name and type | Tier 2 (E2E) |
| SC-3 | Pipeline SOQL query runs without error (all 9 read-contract fields accessible) | Run the pipeline startup query from the CLI | Tier 2 (E2E) |
| SC-4 | `Search_Config__c` lookup exists on `JobApplication__c`, nullable | `sf sobject describe --sobject JobApplication__c --json` — check field type and required=false | Tier 2 (E2E) |
| SC-5 | Lookup clears on parent delete — child record survives | Delete a `Job_Search_Config__c` record that has child `JobApplication__c` records | Tier 3 (User Review) |
| SC-6 | System Administrator can create/read/edit `Job_Search_Config__c` records | Create a record in the UI as Admin | Tier 3 (User Review) |
| SC-7 | Regression — all existing Apex tests still pass | `sf apex run test --test-level RunLocalTests` | Tier 1 (regression-only) |

---

## Skill & Context References

Load these before executing:
- `skills/sf-cli/SKILL.md` — deploy/retrieve commands, field XML formats, profile permission blocks
- `skills/sf-data-architecture/SKILL.md` — MultiselectPicklist GVS reference pattern
- `context/AwesomeOpossumDevHub/objects/_inventory.md` — confirms `JobApplication__c` exists; `Job_Search_Config__c` is new
- `context/AwesomeOpossumDevHub/data-architecture/_inventory.md` — confirms `Skills` GVS exists (developer name: `Skills`)
- `context/AwesomeOpossumDevHub/apex/_inventory.md` — confirms `JobApplicationTrigger` is active; no changes to it in this phase

---

## Task List

---

### TASK 1: Create `Job_Search_Config__c` Object

- **What:** Create the custom object definition with Private sharing model and field history enabled.
- **File:** `force-app/main/default/objects/Job_Search_Config__c/Job_Search_Config__c.object-meta.xml`
- **Create the directory first:**
  ```bash
  mkdir -p force-app/main/default/objects/Job_Search_Config__c/fields
  ```
- **File content:**
  ```xml
  <?xml version="1.0" encoding="UTF-8"?>
  <CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
      <deploymentStatus>Deployed</deploymentStatus>
      <description>Stores search parameters for one independent nightly JobFinder pipeline run. Each active record drives one scheduled search.</description>
      <enableHistory>true</enableHistory>
      <label>Job Search Config</label>
      <nameField>
          <label>Name</label>
          <trackHistory>false</trackHistory>
          <type>Text</type>
      </nameField>
      <pluralLabel>Job Search Configs</pluralLabel>
      <sharingModel>Private</sharingModel>
  </CustomObject>
  ```
- **Deploy:**
  ```bash
  sf project deploy start \
    --metadata "CustomObject:Job_Search_Config__c" \
    --target-org AwesomeOpossumDevHub --wait 10
  ```
- **Validate (dry run):**
  ```bash
  sf project deploy start \
    --metadata "CustomObject:Job_Search_Config__c" \
    --target-org AwesomeOpossumDevHub --dry-run --wait 10
  ```
- **Gotchas:**
  - `sharingModel` must be `Private` — `ControlledByParent` is NOT valid here (this is not a Master-Detail child)
  - `deploymentStatus` must be `Deployed` or fields/layouts will fail to reference it
  - `enableHistory` on the object must be deployed before any field with `<trackHistory>true</trackHistory>`

---

### TASK 2: Create and Deploy All 11 Fields on `Job_Search_Config__c`

- **What:** Create field XML files for all 11 custom fields. Deploy them all in a single operation after the object exists.
- **Directory:** `force-app/main/default/objects/Job_Search_Config__c/fields/`

#### File: `Keywords__c.field-meta.xml`
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Keywords__c</fullName>
    <label>Keywords</label>
    <description>Comma-separated search terms. e.g. Salesforce Developer, Salesforce Engineer</description>
    <type>TextArea</type>
    <trackHistory>true</trackHistory>
    <required>false</required>
</CustomField>
```

#### File: `Required_Skills__c.field-meta.xml`
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Required_Skills__c</fullName>
    <label>Required Skills</label>
    <description>References Skills GVS. Any-of matching — job must contain at least one. Pipeline splits on semicolon delimiter.</description>
    <type>MultiselectPicklist</type>
    <valueSet>
        <restricted>true</restricted>
        <valueSetName>Skills</valueSetName>
    </valueSet>
    <visibleLines>5</visibleLines>
    <trackHistory>true</trackHistory>
    <required>false</required>
</CustomField>
```

#### File: `Bonus_Skills__c.field-meta.xml`
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Bonus_Skills__c</fullName>
    <label>Bonus Skills</label>
    <description>References Skills GVS. Each matched skill adds +5 to relevance score (max +20). Never filters out jobs. Pipeline splits on semicolon delimiter.</description>
    <type>MultiselectPicklist</type>
    <valueSet>
        <restricted>true</restricted>
        <valueSetName>Skills</valueSetName>
    </valueSet>
    <visibleLines>5</visibleLines>
    <trackHistory>false</trackHistory>
    <required>false</required>
</CustomField>
```

#### File: `Daily_Limit__c.field-meta.xml`
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Daily_Limit__c</fullName>
    <label>Daily Limit</label>
    <description>Max job applications pushed to Salesforce per run.</description>
    <type>Number</type>
    <precision>3</precision>
    <scale>0</scale>
    <defaultValue>10</defaultValue>
    <trackHistory>false</trackHistory>
    <required>false</required>
    <unique>false</unique>
</CustomField>
```

#### File: `Min_Annual_Salary__c.field-meta.xml`
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Min_Annual_Salary__c</fullName>
    <label>Min Annual Salary</label>
    <description>Jobs with posted salary ceiling below this are filtered. 0 = disabled.</description>
    <type>Currency</type>
    <precision>12</precision>
    <scale>0</scale>
    <defaultValue>0</defaultValue>
    <trackHistory>false</trackHistory>
    <required>false</required>
</CustomField>
```

#### File: `Days_Back__c.field-meta.xml`
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Days_Back__c</fullName>
    <label>Days Back</label>
    <description>Calendar days back to search for new postings.</description>
    <type>Number</type>
    <precision>2</precision>
    <scale>0</scale>
    <defaultValue>1</defaultValue>
    <trackHistory>false</trackHistory>
    <required>false</required>
    <unique>false</unique>
</CustomField>
```

#### File: `Schedule_Hour__c.field-meta.xml`
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Schedule_Hour__c</fullName>
    <label>Schedule Hour (UTC)</label>
    <description>Hour (0-23 UTC) the search runs. Validated by Schedule_Hour_Range validation rule.</description>
    <type>Number</type>
    <precision>2</precision>
    <scale>0</scale>
    <defaultValue>2</defaultValue>
    <trackHistory>false</trackHistory>
    <required>false</required>
    <unique>false</unique>
</CustomField>
```

#### File: `Schedule_Minute__c.field-meta.xml`
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Schedule_Minute__c</fullName>
    <label>Schedule Minute</label>
    <description>Minute (0-59) within the hour. Validated by Schedule_Minute_Range validation rule.</description>
    <type>Number</type>
    <precision>2</precision>
    <scale>0</scale>
    <defaultValue>0</defaultValue>
    <trackHistory>false</trackHistory>
    <required>false</required>
    <unique>false</unique>
</CustomField>
```

#### File: `Is_Active__c.field-meta.xml`
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Is_Active__c</fullName>
    <label>Is Active</label>
    <description>Only true records are loaded by the pipeline scheduler at startup.</description>
    <type>Checkbox</type>
    <defaultValue>false</defaultValue>
    <trackHistory>true</trackHistory>
</CustomField>
```

#### File: `Last_Run_At__c.field-meta.xml`
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Last_Run_At__c</fullName>
    <label>Last Run At</label>
    <description>Written by pipeline after each successful run. Read-only in layout — do not present as editable.</description>
    <type>DateTime</type>
    <trackHistory>false</trackHistory>
    <required>false</required>
</CustomField>
```

#### File: `Last_Run_Summary__c.field-meta.xml`
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Last_Run_Summary__c</fullName>
    <label>Last Run Summary</label>
    <description>JSON written back by pipeline. e.g. {"found":45,"new":12,"pushed":5}. Read-only in layout.</description>
    <type>LongTextArea</type>
    <length>32768</length>
    <visibleLines>5</visibleLines>
    <trackHistory>false</trackHistory>
    <required>false</required>
</CustomField>
```

- **Deploy all 11 fields together (after TASK 1 deploy succeeds):**
  ```bash
  sf project deploy start \
    --source-dir force-app/main/default/objects/Job_Search_Config__c/fields \
    --target-org AwesomeOpossumDevHub --wait 10
  ```
- **Validate (dry run):**
  ```bash
  sf project deploy start \
    --source-dir force-app/main/default/objects/Job_Search_Config__c/fields \
    --target-org AwesomeOpossumDevHub --dry-run --wait 10
  ```
- **Pattern Reference:** `skills/sf-cli/SKILL.md` — Section 6 (field type mapping), Section 7 (directory structure)
- **Gotchas:**
  - Deploy object (TASK 1) BEFORE deploying fields — `CustomObject` must exist in org first
  - `MultiselectPicklist` with `<valueSetName>Skills</valueSetName>` references the GVS by its developer name (`Skills`). Do NOT use `<valueSetDefinition>` — that would create a local picklist and break the GVS link
  - `<trackHistory>true</trackHistory>` on `Keywords__c`, `Required_Skills__c`, `Is_Active__c` requires `<enableHistory>true</enableHistory>` on the object (set in TASK 1)
  - `<defaultValue>` for Number/Currency fields: if deploy rejects this element, remove it and set defaults via Setup → Object Manager → field edit after deploy

---

### TASK 3 (Sub-task A for TASK 2): Admin Profile FLS — `Job_Search_Config__c`

- **What:** Retrieve the Admin profile, add object-level permissions and field-level security for all 11 new fields on `Job_Search_Config__c`. Deploy.
- **Retrieve:**
  ```bash
  sf project retrieve start --metadata "Profile:Admin" --target-org AwesomeOpossumDevHub
  ```
- **File:** `force-app/main/default/profiles/Admin.profile-meta.xml`
- **Add the following block** (check for existing `<objectPermissions>` entry for `Job_Search_Config__c` before adding — do not duplicate):

  ```xml
  <!-- Object-level permissions for Job_Search_Config__c -->
  <objectPermissions>
      <allowCreate>true</allowCreate>
      <allowDelete>true</allowDelete>
      <allowEdit>true</allowEdit>
      <allowRead>true</allowRead>
      <modifyAllRecords>true</modifyAllRecords>
      <object>Job_Search_Config__c</object>
      <viewAllRecords>true</viewAllRecords>
  </objectPermissions>
  ```

- **Add the following fieldPermissions blocks** (11 total — one per field):

  ```xml
  <fieldPermissions>
      <editable>true</editable>
      <field>Job_Search_Config__c.Keywords__c</field>
      <readable>true</readable>
  </fieldPermissions>
  <fieldPermissions>
      <editable>true</editable>
      <field>Job_Search_Config__c.Required_Skills__c</field>
      <readable>true</readable>
  </fieldPermissions>
  <fieldPermissions>
      <editable>true</editable>
      <field>Job_Search_Config__c.Bonus_Skills__c</field>
      <readable>true</readable>
  </fieldPermissions>
  <fieldPermissions>
      <editable>true</editable>
      <field>Job_Search_Config__c.Daily_Limit__c</field>
      <readable>true</readable>
  </fieldPermissions>
  <fieldPermissions>
      <editable>true</editable>
      <field>Job_Search_Config__c.Min_Annual_Salary__c</field>
      <readable>true</readable>
  </fieldPermissions>
  <fieldPermissions>
      <editable>true</editable>
      <field>Job_Search_Config__c.Days_Back__c</field>
      <readable>true</readable>
  </fieldPermissions>
  <fieldPermissions>
      <editable>true</editable>
      <field>Job_Search_Config__c.Schedule_Hour__c</field>
      <readable>true</readable>
  </fieldPermissions>
  <fieldPermissions>
      <editable>true</editable>
      <field>Job_Search_Config__c.Schedule_Minute__c</field>
      <readable>true</readable>
  </fieldPermissions>
  <fieldPermissions>
      <editable>true</editable>
      <field>Job_Search_Config__c.Is_Active__c</field>
      <readable>true</readable>
  </fieldPermissions>
  <fieldPermissions>
      <editable>true</editable>
      <field>Job_Search_Config__c.Last_Run_At__c</field>
      <readable>true</readable>
  </fieldPermissions>
  <fieldPermissions>
      <editable>true</editable>
      <field>Job_Search_Config__c.Last_Run_Summary__c</field>
      <readable>true</readable>
  </fieldPermissions>
  ```

- **Hold off on deploying yet** — TASK 5 (Sub-task A for the lookup field) will add one more `fieldPermissions` block to this same profile. Do both TASK 3 and TASK 5 edits before the single deploy.
- **Gotchas:**
  - NEVER add `fieldPermissions` for standard fields (`Name`, `OwnerId`, `CreatedById`, etc.) — custom fields only
  - The `Admin.profile-meta.xml` is large — search for existing `Job_Search_Config__c` entries before adding to avoid duplicates
  - Do NOT deploy the Admin profile before the fields are deployed (`Unknown property 'FieldPermissions.field'` error if field doesn't exist in org)

---

### TASK 4 (Sub-task B for TASK 2): Page Layout for `Job_Search_Config__c` — DEFERRED

- **Deferred to Phase 3.** The `Job Search Config Layout` page layout is created in Phase 3 along with the FlexiPage.
- **No action required in Phase 1.**
- **Dependency note:** Phase 3 TASK for the layout must happen after all fields from Phase 1 are deployed (layout references fields by name — deploy will fail if fields don't exist in org).

---

### TASK 5 (Sub-task C for TASK 2): RecordType Picklist Availability — N/A

- **N/A.** `Job_Search_Config__c` has no record types (intentional per requirements). No RecordType filtering update needed for `Required_Skills__c` or `Bonus_Skills__c`.

---

### TASK 6: Create and Deploy `Search_Config__c` Lookup on `JobApplication__c`

- **What:** Add a nullable lookup field on `JobApplication__c` pointing to `Job_Search_Config__c`. Cleared (not deleted) when the parent config is deleted.
- **File:** `force-app/main/default/objects/JobApplication__c/fields/Search_Config__c.field-meta.xml`
- **Create directory if needed:**
  ```bash
  mkdir -p force-app/main/default/objects/JobApplication__c/fields
  ```
- **File content:**
  ```xml
  <?xml version="1.0" encoding="UTF-8"?>
  <CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
      <fullName>Search_Config__c</fullName>
      <label>Search Config</label>
      <description>Links this job application to the Job Search Config that produced it. Null for YAML-fallback runs.</description>
      <type>Lookup</type>
      <referenceTo>Job_Search_Config__c</referenceTo>
      <relationshipName>Job_Applications</relationshipName>
      <relationshipLabel>Job Applications</relationshipLabel>
      <deleteConstraint>SetNull</deleteConstraint>
      <required>false</required>
  </CustomField>
  ```
- **Deploy (after `Job_Search_Config__c` object exists from TASK 1):**
  ```bash
  sf project deploy start \
    --metadata "CustomField:JobApplication__c.Search_Config__c" \
    --target-org AwesomeOpossumDevHub --wait 10
  ```
- **Validate (dry run):**
  ```bash
  sf project deploy start \
    --metadata "CustomField:JobApplication__c.Search_Config__c" \
    --target-org AwesomeOpossumDevHub --dry-run --wait 10
  ```
- **Pattern Reference:** `skills/sf-cli/SKILL.md` — Section 6 (Lookup field example)
- **Gotchas:**
  - `<deleteConstraint>SetNull</deleteConstraint>` is what produces "Clear the field value" behavior. Do NOT use `Cascade` (would delete child `JobApplication__c` records when config is deleted)
  - `<relationshipName>Job_Applications</relationshipName>` — this is used in SOQL as `Job_Applications__r` from the parent side. It must be unique across all fields on `JobApplication__c`
  - The `JobApplicationTrigger` is active on this object — the new field is passive/nullable and will NOT cause trigger events or affect existing trigger logic
  - Deploy `Job_Search_Config__c` object (TASK 1) BEFORE this field (the `<referenceTo>` must exist in org)

---

### TASK 7 (Sub-task A for TASK 6): Admin Profile FLS — `Search_Config__c`

- **What:** Add `fieldPermissions` for `JobApplication__c.Search_Config__c` to the Admin profile. This is done in the same profile file already opened in TASK 3 — add this one block, then do the single deploy.
- **Add this block** to `force-app/main/default/profiles/Admin.profile-meta.xml`:

  ```xml
  <fieldPermissions>
      <editable>true</editable>
      <field>JobApplication__c.Search_Config__c</field>
      <readable>true</readable>
  </fieldPermissions>
  ```

- **Now deploy the Admin profile** (combining all TASK 3 + TASK 7 additions in one deploy):
  ```bash
  sf project deploy start \
    --metadata "Profile:Admin" \
    --target-org AwesomeOpossumDevHub --wait 10
  ```
- **Gotchas:**
  - Deploy `Search_Config__c` field (TASK 6) BEFORE deploying the Admin profile — field must exist in org first
  - Do NOT add a `fieldPermissions` block for the standard `Name` field or other standard fields on `JobApplication__c`

---

### TASK 8 (Sub-task B for TASK 6): Page Layout for `JobApplication__c` — DEFERRED

- **Deferred to Phase 3.** The `Search_Config__c` field is added to the `Job_Application` FlexiPage in Phase 3.
- **Context:** This org has 0 custom page layouts per the inventory scan. The `Job_Application` FlexiPage uses `force:detailPanel` which renders the standard Salesforce layout. Adding `Search_Config__c` to the FlexiPage via a field component in Phase 3 achieves the UI placement without creating a custom layout.
- **No action required in Phase 1.**

---

### TASK 9 (Sub-task C for TASK 6): RecordType Picklist Availability — N/A

- **N/A.** `Search_Config__c` is a Lookup field, not a Picklist or MultiselectPicklist. No RecordType filtering applies.

---

## Deployment Sequence Summary

Run in this exact order — each step depends on the prior one succeeding:

```
1. TASK 1:   Deploy Job_Search_Config__c object
2. TASK 2:   Deploy all 11 fields on Job_Search_Config__c
3. TASK 6:   Deploy Search_Config__c lookup on JobApplication__c
4. TASK 3+7: Retrieve Admin profile → add all FLS blocks → deploy Admin profile
```

Combined deploy command for steps 1-3 (if deploying source-first without dry runs):
```bash
sf project deploy start \
  --source-dir force-app/main/default/objects \
  --target-org AwesomeOpossumDevHub --wait 10
```
> ⚠️ Only use the combined command if you want to deploy ALL local object metadata at once. If other in-progress object changes exist locally, deploy individual components instead.

---

## Testing Framework

### Tier 1: Unit Tests

**Applies to this phase: NO** — Phase 1 is declarative only (object, fields, lookup, profile). No Apex classes created or modified.

**Regression run (still required):**
```bash
sf apex run test --test-level RunLocalTests --target-org AwesomeOpossumDevHub --result-format human --wait 10
```
Gate: All existing tests pass. Any failure here indicates a declarative change broke an existing test — investigate before proceeding.

---

### Tier 2: E2E Testing

| # | Scenario | Steps | Expected Result | Verification |
|---|---|---|---|---|
| E2E-1 | Object exists with correct sharing model | `sf sobject describe --sobject Job_Search_Config__c --target-org AwesomeOpossumDevHub --json` | Output includes `"sharingModel": "Private"` | Inspect JSON output |
| E2E-2 | All 11 fields exist with correct types | Same describe output | `keywords__c` = TextArea, `required_skills__c` = MultiselectPicklist, `is_active__c` = Boolean, `last_run_summary__c` = Textarea (long), etc. | Inspect field entries in `fields[]` array |
| E2E-3 | Pipeline startup SOQL runs without error | `sf data query --query "SELECT Id, Name, Keywords__c, Required_Skills__c, Bonus_Skills__c, Daily_Limit__c, Min_Annual_Salary__c, Schedule_Hour__c, Schedule_Minute__c, Days_Back__c FROM Job_Search_Config__c WHERE Is_Active__c = true ORDER BY Schedule_Hour__c ASC, Schedule_Minute__c ASC" --target-org AwesomeOpossumDevHub` | Returns 0 rows with no error (no records yet) | Zero rows returned, no error |
| E2E-4 | `Search_Config__c` exists on `JobApplication__c` | `sf sobject describe --sobject JobApplication__c --target-org AwesomeOpossumDevHub --json` | Field `Search_Config__c` present, type=Reference, referenceTo=Job_Search_Config__c, nillable=true | Inspect field in JSON |
| E2E-5 | Lookup clears on parent delete | (1) Insert a `Job_Search_Config__c` record via UI. (2) Insert a `JobApplication__c` record with `Search_Config__c` set to that config ID. (3) Delete the config record. (4) Query the job application. | `JobApplication__c` record survives; `Search_Config__c` field is null | `sf data query --query "SELECT Id, Search_Config__c FROM JobApplication__c WHERE Id = '<id>'" --target-org AwesomeOpossumDevHub` |
| E2E-6 | Skills GVS values load in picklist | Create a `Job_Search_Config__c` record in UI | `Required_Skills__c` and `Bonus_Skills__c` dropdowns show Skills GVS values | Visual UI check |

---

### Tier 3: User Review

**Code review checklist:**
- [ ] Object XML: `sharingModel=Private`, `deploymentStatus=Deployed`, `enableHistory=true`
- [ ] MultiselectPicklist fields reference `<valueSetName>Skills</valueSetName>` (not a local `valueSetDefinition`)
- [ ] Lookup field `deleteConstraint=SetNull` (not Cascade)
- [ ] `trackHistory=true` only on `Keywords__c`, `Required_Skills__c`, `Is_Active__c`
- [ ] Admin profile: objectPermissions for `Job_Search_Config__c` present; fieldPermissions for all 11 fields + `Search_Config__c` present; no standard field entries

**User E2E testing checklist:**
- [ ] Open Setup → Object Manager → `Job_Search_Config__c` — confirm object exists with correct label and sharing model
- [ ] Open Object Manager → `Job_Search_Config__c` → Fields & Relationships — confirm all 11 fields with correct labels and types
- [ ] Open Setup → Profiles → System Administrator → Object Settings → `Job_Search_Config__c` — confirm full CRUD access
- [ ] Navigate to any `JobApplication__c` record — `Search Config` field should be visible (blank) in the layout (note: FlexiPage update is Phase 3 — field exists in org but is not yet on the page)
- [ ] Confirm `Search_Config__c` lookup clear-on-delete behavior (E2E-5 above)

---

## Phase Completion Protocol

When all tasks, tier 1 regression, and tier 2/3 tests pass:

1. **Update master plan Phase Registry:** Set Phase 1 status to `Complete`
2. **No regression test classes to add** (no Apex in this phase)
3. **Write Phase Summary** — add to `Prior Phase Summaries` in master plan:
   ```
   ### Phase 1: Data Model — Complete
   - Deployed: Job_Search_Config__c object, 11 custom fields (Keywords__c, Required_Skills__c,
     Bonus_Skills__c, Daily_Limit__c, Min_Annual_Salary__c, Days_Back__c, Schedule_Hour__c,
     Schedule_Minute__c, Is_Active__c, Last_Run_At__c, Last_Run_Summary__c),
     Search_Config__c lookup on JobApplication__c, Admin profile FLS
   - Test classes: none (declarative phase)
   - Key decisions: [any decisions made during implementation, e.g. defaultValue behavior]
   - Known issues: [any issues discovered]
   ```
4. **Update Acceptance Criteria:** Mark AC-1 and AC-3 as `Complete` (AC-2 partially addressed — write-back field exists; full perm set access confirmed in Phase 2)
5. **Commit:**
   ```bash
   /sf-commit
   ```
6. **Next step:** Run `/sf-plan-feature --next job-search-config` to generate the Phase 2 plan.
