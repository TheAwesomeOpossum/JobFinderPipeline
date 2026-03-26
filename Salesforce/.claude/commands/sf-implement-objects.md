---
description: "Implement Salesforce custom objects, fields, profiles, page layouts, and permission sets from a spec. Generates metadata XML files and deploys to the connected org."
argument-hint: [path-to-spec-or-plan]
---

# SF Implement Objects

Takes a spec or plan, generates all required Salesforce metadata XML files, and deploys them to the connected org in the correct order.

**Core principle: Deploy in phases — objects/fields → profile → flexipage → layouts → permsets. Never deploy profile permissions before the fields they reference exist in the org.**

**Usage:** `/sf-implement-objects <path-to-spec>` or `/sf-implement-objects` (will prompt for spec)

---

## Naming Convention: Label → API Name

**Rule:** When deriving an API name from a label, replace every space with an underscore `_`, then append `__c`.

| Label | API Name |
|---|---|
| Interview Job | `Interview_Job__c` |
| Work Order Line | `Work_Order_Line__c` |
| Estimated Cost | `Estimated_Cost__c` |
| Status | `Status__c` |

Apply this rule consistently to **object names, field names, relationship names, permission set names, and layout names**. The `<label>` tag always uses the human-readable label with spaces; the `<fullName>` tag and all filenames always use the underscore form.

---

## Phase 0: Pre-flight

1. Confirm org connection:
   ```bash
   sf org display --target-org <alias>
   ```
   If this fails, stop and instruct user to authenticate first.

2. Check cached context before re-querying the org:

   a. Read `context/INDEX.md`. If the alias row exists with a `Last Full Scan` timestamp:
      - Check if the scan is less than 7 days old
      - If current (< 7 days): read `context/{alias}/objects/_inventory.md` and any relevant `context/{alias}/objects/{ObjectName__c}.md` files to understand the current state — **skip re-querying for those objects**
      - If stale (≥ 7 days): warn the user and offer to run `/sf-check-context-freshness {alias}` first

   b. If `context/INDEX.md` does not exist or the alias has no scan timestamp: run `sf-get-existing-org-object-context` now before proceeding. The gap analysis output is required to know what to create vs. update.

3. Confirm project structure exists:
   - Check for `force-app/main/default/` directory
   - If starting a new project: `sf project generate --name . --template empty`
   - Ensure these subdirectories exist (create if missing):
     - `force-app/main/default/objects/`
     - `force-app/main/default/profiles/`
     - `force-app/main/default/layouts/`
     - `force-app/main/default/permissionsets/`
     - `force-app/main/default/flexipages/`

4. Read the spec/plan in full before generating any files.

---

## Phase 1: Object Metadata Generation

For each **new** custom object in the spec:

**CREATE** `force-app/main/default/objects/{ObjectName__c}/{ObjectName__c}.object-meta.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <deploymentStatus>Deployed</deploymentStatus>
    <label>Object Label</label>
    <pluralLabel>Object Labels</pluralLabel>
    <nameField>
        <label>Name</label>
        <type>Text</type>
    </nameField>
    <sharingModel>ReadWrite</sharingModel>
</CustomObject>
```

- Set `sharingModel` based on the object's relationships:
  - Object has a Master-Detail field → `ControlledByParent`
  - Otherwise → `ReadWrite` (or `Private` if specified in spec)
  - **NEVER** set `ControlledByParent` unless the object will have a Master-Detail field
- Set `deploymentStatus` to `Deployed`
- Use the spec's label and plural label exactly in `<label>`/`<pluralLabel>` tags
- **API name** (directory name, filename, `<fullName>`) = label with spaces replaced by `_`, plus `__c` suffix (e.g. `"Work Order"` → `Work_Order__c`)

For each **existing** object that needs new fields: retrieve first, then read the existing XML — only modify what the spec requires.

---

## Phase 2: Field Metadata Generation

For each field in the spec, **CREATE** `force-app/main/default/objects/{ObjectName__c}/fields/{FieldName__c}.field-meta.xml`

**GOTCHA:** `<fullName>` inside the XML must exactly match the filename (minus `.field-meta.xml`)

**NAMING:** Field API name = label with spaces replaced by `_`, plus `__c` (e.g. label `"Scheduled Date"` → `<fullName>Scheduled_Date__c</fullName>`, filename `Scheduled_Date__c.field-meta.xml`). The `<label>` tag keeps the original human-readable form with spaces.

**GOTCHA:** Lookup/MasterDetail `<relationshipName>` must be unique across ALL fields in the org — check sf-get-existing-org-object-context output for conflicts

**GOTCHA:** Standard fields (`Name`, `OwnerId`, `CreatedById`, etc.) do not need field XML files

Use the type mapping from `skills/sf-cli/SKILL.md` section 6 to determine the correct XML structure for each field type.

---

## Phase 3: Deploy Objects + Fields

```bash
sf project deploy start --metadata "CustomObject:{ObjectName__c}" --target-org <alias> --wait 10
```

Deploy each object separately for clearer error messages. Check the exit code after each deploy.

**If deploy fails:**
- Read the error message carefully
- Common fixes:
  - `sharingModel ControlledByParent` error → change to `ReadWrite` in object XML, redeploy
  - `duplicate relationshipName` → rename the `<relationshipName>` in the offending field XML, redeploy
  - `Entity type not found` for a referenceTo → that parent object doesn't exist yet; deploy it first
  - `fullName mismatch` → ensure `<fullName>` in XML matches the filename

**Do not proceed to Phase 4 until all objects and fields deploy successfully.**

---

## Phase 3.5: Validation Rules (Interactive)

1. Load `skills/sf-validation-rules/SKILL.md`

2. **Reason silently** through each new object and its fields using these field-type heuristics:
   - **Date fields** → consider date range (end > start), future date enforcement
   - **Picklist fields** → consider status transition lock (PRIORVALUE + ISCHANGED), picklist dependency rules
   - **Currency/Number fields** → consider positive-value enforcement, numeric range
   - **Lookup fields** → consider conditional required (required when another field has a specific value)
   - **Checkbox fields** → consider immutable-after-checked (cannot uncheck once set)
   - **Text fields** → consider conditional required when another field equals a specific value
   - **Status fields** → consider preventing backward progression (e.g., can't reopen Closed)

3. Produce a **numbered list** of suggested validation rules. For each:
   - Rule name (no spaces, underscore-separated)
   - Proposed formula (using functions from skill Section 3)
   - Suggested `errorDisplayField`
   - One-sentence reason

4. **USER INPUT REQUIRED** — Present the suggestions and ask:
   > "Which validation rules would you like to create? Options:
   > - **all** — create all suggested rules
   > - **[numbers]** — pick specific rules by number (e.g., 1, 3)
   > - **custom** — describe a rule you want instead
   > - **skip** — no validation rules for now"

5. **If skip:** Log `Phase 3.5: Skipped` and proceed to Phase 4.

6. **If accepted (all, numbered, or custom):** For each approved rule, generate:
   ```
   force-app/main/default/objects/{Obj__c}/validationRules/{RuleName}.validationRule-meta.xml
   ```
   Use the XML skeleton from skill Section 1. Reference Section 4 patterns for the formula structure.

   **GOTCHA callouts when generating:**
   - `<fullName>` must exactly match the filename — no spaces allowed in either
   - The formula evaluates `TRUE` when the save is **blocked** (inverted logic — think "when should this fail?")
   - Cross-object validation uses `LookupField__r.TargetField__c` dot notation (Section 4 Pattern 8)

7. **Deploy:**
   ```bash
   sf project deploy start \
     --metadata "ValidationRule:{ObjectName__c}" \
     --target-org <alias> --wait 10
   ```
   Deploy each object's rules separately for clearer error messages.

8. **Common deploy errors and fixes:**
   | Error | Fix |
   |---|---|
   | `PRIORVALUE` error on insert | Wrap formula with `NOT(ISNEW())` — ISCHANGED/PRIORVALUE are always false on insert |
   | Invalid field reference | Confirm field API name with `sf sobject describe --sobject {Obj__c}` |
   | Formula character limit exceeded | Break complex logic into intermediate formula fields, then reference those fields |
   | `fullName mismatch` | Ensure `<fullName>` in XML exactly matches the filename (minus `.validationRule-meta.xml`) |

9. **Gate:** Do not proceed to Phase 4 until all validation rules deploy successfully or this phase is skipped.

---

## Phase 4: Profile Update (System Administrator)

Always retrieve a fresh copy before editing:

```bash
sf project retrieve start --metadata "Profile:Admin" --target-org <alias>
```

Read the existing `Admin.profile-meta.xml`. Then **APPEND** (never overwrite) new blocks to it.

For each new object, append one `<objectPermissions>` block:
```xml
<objectPermissions>
    <allowCreate>true</allowCreate>
    <allowDelete>true</allowDelete>
    <allowEdit>true</allowEdit>
    <allowRead>true</allowRead>
    <modifyAllRecords>true</modifyAllRecords>
    <object>ObjectName__c</object>
    <viewAllRecords>true</viewAllRecords>
</objectPermissions>
```

For each new custom field, append one `<fieldPermissions>` block:
```xml
<fieldPermissions>
    <editable>true</editable>
    <field>ObjectName__c.FieldName__c</field>
    <readable>true</readable>
</fieldPermissions>
```

**GOTCHA:** Append new blocks just before the closing `</Profile>` tag — do not re-sort or reformat existing blocks

**GOTCHA:** Do NOT add fieldPermissions for standard fields (Name, OwnerId, CreatedById, LastModifiedById, IsDeleted, SystemModstamp, CreatedDate, LastModifiedDate)

**GOTCHA:** Check for existing entries first — do not duplicate permissions already in the file

Deploy:
```bash
sf project deploy start --metadata "Profile:Admin" --target-org <alias> --wait 10
```

---

## Phase 4.5: Extended Permissions Configuration (Interactive)

Load `skills/sf-permissions/SKILL.md`

**STATE:** "System Admin already has full access from Phase 4. Do you want to configure additional permissions (OWD changes, permission sets for other profiles, or sharing rules)? (yes / no)"

**If no:** Log `Phase 4.5: Skipped`. Write minimal memory entry (see Step 6 below), then proceed to Phase 5.

**If yes:** Continue through the steps below.

---

### Step 1 — Check Memory

Read `~/.claude/projects/-home-your-username/memory/MEMORY.md` and look for a `## Salesforce Org Permissions Layout` section. If found, display it as current context so the user can see the existing permissions state before making decisions.

---

### Step 2 — Offer Org Introspection (USER INPUT REQUIRED)

> "Query the org for existing permission sets, OWD, and user assignments to inform your decisions? (yes / no)"

If **yes:** Run these 3 queries from skill Section 9:
1. List all permission sets (query 1)
2. Retrieve OWD for each new object (query 2, once per object)
3. Query permission set assignments for relevant users if a user ID is known (query 3)

Present results as a concise summary table before the next step.

---

### Step 3 — Branching Menu (USER INPUT REQUIRED)

Present this menu and wait for the user's choice:

```
What would you like to configure?
(A) Create a new permission set
(B) Add permissions to an existing permission set
(C) Update OWD for one or more of the new objects
(D) Create sharing rules
(E) Multiple of the above — I'll describe what I need
```

---

#### Path A / B — Permission Set

Ask these questions **sequentially** (wait for each answer before asking the next):

1. **Developer name and label?**
   - Developer name = no spaces, no special chars (e.g., `Field_Tech_Read`)
   - Label = human-readable (e.g., `Field Tech - Read Access`)

2. **Object access level for each new object?**
   - Options: Read Only / Read+Edit / Full CRUD / Full Admin / None
   - Use the access level table from skill Section 4

3. **Which fields should be readable? Which should also be editable?**
   - List field API names for each access tier
   - Standard fields (Name, OwnerId, etc.) do not need fieldPermissions entries

4. **Does this permission set need ViewAllRecords or ModifyAllRecords on any object?**
   - Remind user: these bypass all sharing rules — only grant if truly required

5. **Who are the intended users?** (Documentation only — not deployed as metadata)
   - Record this in memory for the org permissions layout

**Path B only:** Retrieve the existing permission set first, then append new blocks — **never overwrite** the existing file.
```bash
sf project retrieve start --metadata "PermissionSet:{PermSetName}" --target-org <alias>
```

Generate XML using the skeleton from skill Section 4.

---

#### Path C — OWD Change

For each object the user wants to change:
1. Show the current `<sharingModel>` value (from Step 2 introspection or Phase 1 spec)
2. Ask: **Private / Read / ReadWrite / ControlledByParent?**
3. **GOTCHA warnings:**
   - `ControlledByParent` is only valid if the object has a Master-Detail field — warn explicitly if it does not
   - Changing OWD on objects with existing data triggers a sharing recalculation — warn user, especially for production

Update `<sharingModel>` in the object's `.object-meta.xml` file, then redeploy the object:
```bash
sf project deploy start --metadata "CustomObject:{ObjectName__c}" --target-org <alias> --wait 10
```

---

#### Path D — Sharing Rules

Ask these questions **sequentially:**

1. **Owner-based or criteria-based?**
2. **Developer name for the rule?** (no spaces, underscore-separated)
3. If **owner-based:** Which Public Group owns the source records? Which group receives access?
   If **criteria-based:** Which field + value determines which records are shared? Which group receives access?
4. **Access level:** Read or ReadWrite?
5. **Do the referenced Public Groups exist in the org?**
   - **WARN if not:** Public Groups must be created manually in Setup → Public Groups **before** the sharing rule is deployed. Deploying a sharing rule that references a non-existent group will fail.

Check for an existing `force-app/main/default/sharingRules/{ObjectName__c}.sharingRules-meta.xml`:
- If it exists: retrieve first, then **append** new rules — never overwrite
- If it doesn't exist: create the file with the full XML skeleton

Use templates from skill Section 6.

---

### Step 4 — Confirm Before Deploy (USER INPUT REQUIRED)

Present a summary of all files that will be generated or modified:
- List each file path and what will change
- Wait for user confirmation: **"yes / adjust"**

Do not generate or deploy anything until the user confirms.

---

### Step 5 — Deploy in Order

Deploy in this exact sequence (skip steps that aren't needed for this session):

```bash
# 1. Objects — only if OWD changed (Path C)
sf project deploy start --metadata "CustomObject:{ObjectName__c}" --target-org <alias> --wait 10

# 2. Permission sets — Path A or B
sf project deploy start --metadata "PermissionSet:{PermSetName}" --target-org <alias> --wait 10

# 3. Sharing rules — always last (depends on objects + public groups existing in org)
sf project deploy start --metadata "SharingRules:{ObjectName__c}" --target-org <alias> --wait 10
```

Check exit codes after each deploy. Do not proceed to the next deploy if one fails.

---

### Step 6 — Write Memory

Update `~/.claude/projects/-home-your-username/memory/MEMORY.md`:

**If phase was skipped:**
- Find or add the `## Salesforce Org Permissions Layout` section
- Add a row to the OWD table for each new object (use the `<sharingModel>` from Phase 1)
- Add a note: "Session {date}: Only System Administrator configured — Phase 4.5 skipped"

**If phase was completed:**
- Search for existing `## Salesforce Org Permissions Layout` section
- If found: **append** new rows/entries to the relevant subsections — never delete prior sessions' data
- If not found: add the full section using the format from skill Section 10
- Record: OWD values, permission sets created/updated (with intended users), sharing rules created, any public groups or role hierarchy notes discussed

Update the `_Last updated_` line to today's date and the current project name.

**Gate:** Do not proceed to Phase 5 until all deploys succeed or this phase is skipped.

---

## Phase 5: Lightning Record Page (FlexiPage)

For each new custom object, **CREATE** `force-app/main/default/flexipages/{ObjectName}_Record_Page.flexipage-meta.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<FlexiPage xmlns="http://soap.sforce.com/2006/04/metadata">
    <flexiPageRegions>
        <itemInstances>
            <componentInstance>
                <componentInstanceProperties>
                    <name>collapsed</name>
                    <value>false</value>
                </componentInstanceProperties>
                <componentInstanceProperties>
                    <name>numVisibleActions</name>
                    <value>3</value>
                </componentInstanceProperties>
                <componentName>force:highlightsPanel</componentName>
            </componentInstance>
        </itemInstances>
        <name>header</name>
        <type>Region</type>
    </flexiPageRegions>
    <flexiPageRegions>
        <itemInstances>
            <componentInstance>
                <componentName>force:detailPanel</componentName>
            </componentInstance>
        </itemInstances>
        <name>main</name>
        <type>Region</type>
    </flexiPageRegions>
    <masterLabel>{ObjectLabel} Record Page</masterLabel>
    <sobjectType>{ObjectName__c}</sobjectType>
    <template>flexipage:recordHomeTemplateDesktop</template>
    <type>RecordPage</type>
</FlexiPage>
```

Deploy:
```bash
sf project deploy start --metadata "FlexiPage:{ObjectName}_Record_Page" --target-org <alias> --wait 10
```

After deploy, output this prompt to the user:

```
⚠️ MANUAL STEPS REQUIRED — Complete in Salesforce Setup:

1. Activate Lightning Record Page:
   Setup → Lightning App Builder → "{ObjectLabel} Record Page"
   → Click Activate → Set as Org Default for Desktop AND Phone → Save

2. Create a Custom Tab:
   Setup → Tabs → Custom Object Tabs → New
   → Object: {ObjectName__c} → choose a Tab Style → Next → Save

3. Add to your Lightning App:
   Setup → App Manager → [your app] → Edit
   → Navigation Items → add "{ObjectLabel}" tab → Save
```

---

## Phase 6: Page Layout Generation/Update

**Filename convention:** `{ObjectApiName}-{LayoutName}.layout-meta.xml`

For **new** objects, create a minimal layout:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Layout xmlns="http://soap.sforce.com/2006/04/metadata">
    <layoutSections>
        <customLabel>false</customLabel>
        <detailHeading>true</detailHeading>
        <editHeading>true</editHeading>
        <label>Information</label>
        <layoutColumns>
            <layoutItems>
                <behavior>Required</behavior>
                <field>Name</field>
            </layoutItems>
            <layoutItems>
                <behavior>Edit</behavior>
                <field>FieldName__c</field>
            </layoutItems>
        </layoutColumns>
        <layoutColumns>
            <layoutItems>
                <behavior>Edit</behavior>
                <field>AnotherField__c</field>
            </layoutItems>
        </layoutColumns>
        <style>TwoColumnsTopToBottom</style>
    </layoutSections>
</Layout>
```

- Distribute new fields across two columns (left column: first half of fields, right column: second half)
- Put `Name` field first in the left column
- `<behavior>` values: `Required`, `Edit`, `Readonly`

For **existing** layouts: retrieve first, then add new fields to an existing section without removing existing fields.

Deploy:
```bash
sf project deploy start --metadata "Layout:{ObjectName__c}-{LayoutName}" --target-org <alias> --wait 10
```

**FLAG:** Complex layout work (multiple sections, related lists, record type-specific layouts) → use future `sf-implement-layouts` command

---

## Phase 7: Permission Set Generation/Update

For each **new** permission set in the spec, **CREATE** `force-app/main/default/permissionsets/{PermSetName}.permissionset-meta.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<PermissionSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <description>What this permission set grants</description>
    <label>Permission Set Label</label>
    <objectPermissions>
        <allowCreate>true</allowCreate>
        <allowDelete>false</allowDelete>
        <allowEdit>true</allowEdit>
        <allowRead>true</allowRead>
        <modifyAllRecords>false</modifyAllRecords>
        <object>ObjectName__c</object>
        <viewAllRecords>false</viewAllRecords>
    </objectPermissions>
    <fieldPermissions>
        <editable>true</editable>
        <field>ObjectName__c.FieldName__c</field>
        <readable>true</readable>
    </fieldPermissions>
</PermissionSet>
```

For **existing** permission sets: retrieve first, then append new objectPermissions/fieldPermissions blocks.

Deploy:
```bash
sf project deploy start --metadata "PermissionSet:{PermSetName}" --target-org <alias> --wait 10
```

---

## Phase 8: Final Validation

```bash
# Dry-run full project to confirm no remaining consistency issues
sf project deploy start --source-dir force-app --dry-run --target-org <alias> --wait 10

# Verify each created object has all planned fields
sf sobject describe --sobject ObjectName__c --json --target-org <alias>
```

Check the describe output for each object:
- All planned fields are present
- Field types match the spec
- Required/optional status is correct

Open the org for visual verification:
```bash
sf org open --target-org <alias>
```

Then navigate to: Setup → Object Manager → confirm objects and fields are visible

---

## Output Report

At the end of the command, produce this summary:

```
## Implementation Summary

### Objects Created/Updated
- ✅ ObjectName__c (created) — force-app/main/default/objects/ObjectName__c/

### Fields Created
**ObjectName__c**
- ✅ FieldOne__c (Text 255)
- ✅ FieldTwo__c (Picklist)
- ✅ LookupField__c (Lookup → ParentObject__c)

### Profile Permissions Added (Admin)
- ✅ ObjectName__c — full CRUD + ViewAll + ModifyAll
- ✅ FieldOne__c, FieldTwo__c, LookupField__c — read/edit

### Lightning Record Pages Created
- ✅ ObjectName_Record_Page — deployed (manual activation required)

### Layouts Created/Updated
- ✅ ObjectName__c-ObjectName Layout (created)

### Permission Sets Created/Updated
- ✅ MyPermSet (created)

### Validation Rules Created
- ✅ {ObjectName__c}.{RuleName} — {brief description}
- (or: Phase 3.5 skipped — no validation rules created)

### Permissions Configured (Phase 4.5)
- ✅ Permission Sets: {PermSetName} (created/updated)
- ✅ OWD changes: {ObjectName__c} → {sharingModel}
- ✅ Sharing Rules: {ObjectName__c}.{RuleName}
- (or: Phase 4.5 skipped — only System Administrator access configured)

### Memory Writes
- ✅ ~/.claude/projects/-home-your-username/memory/MEMORY.md — Org Permissions Layout updated

### Deploy Results
- Phase 3 (Objects/Fields): ✅ Success
- Phase 3.5 (Validation Rules): ✅ Success / ⏭ Skipped
- Phase 4 (Profile): ✅ Success
- Phase 4.5 (Extended Permissions): ✅ Success / ⏭ Skipped
- Phase 5 (FlexiPage): ✅ Success
- Phase 6 (Layout): ✅ Success
- Phase 7 (PermSet): ✅ Success
- Phase 8 (Dry-run validation): ✅ No errors

### Files Modified
- force-app/main/default/objects/ObjectName__c/ObjectName__c.object-meta.xml
- force-app/main/default/objects/ObjectName__c/fields/FieldOne__c.field-meta.xml
- force-app/main/default/objects/ObjectName__c/validationRules/{RuleName}.validationRule-meta.xml
- force-app/main/default/profiles/Admin.profile-meta.xml
- force-app/main/default/flexipages/ObjectName_Record_Page.flexipage-meta.xml
- force-app/main/default/layouts/ObjectName__c-ObjectName Layout.layout-meta.xml
- force-app/main/default/permissionsets/MyPermSet.permissionset-meta.xml
- force-app/main/default/sharingRules/ObjectName__c.sharingRules-meta.xml

### Next Steps
1. ⚠️ Complete Lightning Record Page manual activation (see Phase 5 prompt above)
2. Verify in Setup → Object Manager that all objects and fields appear correctly
3. Assign permission sets to appropriate users/profiles
4. Run /commit to commit generated metadata files to git
5. If permission sets were created — assign them to users in Setup → Users → Permission Set Assignments
6. If OWD changed to Private — verify sharing rules cover all intended access paths before deploying to production
```

---

## Future Commands (flagged, not in scope)

- `sf-implement-layouts` — full layout control: multi-section, related lists, record type-specific layouts
- `sf-implement-validation-rules` — Standalone command for adding validation rules to already-deployed objects (Phase 3.5 handles inline for new objects)
- `sf-implement-flows` — Flow XML (complex enough for its own skill)
- `sf-implement-record-types` — RecordType + profileRecordTypeVisibilities
- `sf-org-diff` — diff local files vs. org for CI/CD drift detection
