---
description: "Introspect a connected Salesforce org to understand its current metadata state before making changes."
argument-hint: [target-org-alias]
---

# SF Org Context

Run this command to understand the current object structure of the org before implementing any metadata changes. This prevents duplicating existing objects/fields and reveals what needs to be created vs. updated.

**Usage:** `/sf-get-existing-org-object-context <alias>` — if no alias provided, use the configured default org.

---

## Phase 1: Confirm Org Connection

```bash
sf org display --target-org <alias>
```

- Confirm the org is authenticated
- Capture and record: `instanceUrl`, `apiVersion`, `username`, `orgId`
- If this command fails: **stop immediately** and instruct the user to run `sf org login web --alias <alias>` before proceeding

---

## Phase 2: Custom Object Inventory

```bash
sf sobject list --sobject-type custom --json --target-org <alias>
```

- Capture the full list of custom objects in the org
- Cross-reference with local `force-app/main/default/objects/` directory
  - Objects in org but not local → may need retrieval
  - Objects local but not in org → not yet deployed
- For any objects **relevant to the current work**, run describe:

```bash
sf sobject describe --sobject ObjectName__c --json --target-org <alias>
```

Capture for each relevant object:

- All field names and API names
- Field types
- Required status
- Relationship names (for Lookup/MasterDetail fields)
- Existing picklist values

---

## Phase 3: Retrieve Current Metadata

Retrieve latest versions of metadata types that will be modified. On large orgs, narrow to specific objects rather than retrieving everything.

```bash
# Retrieve specific objects (preferred over retrieving all CustomObjects)
sf project retrieve start --metadata "CustomObject:ObjectName__c" --target-org <alias>

# Retrieve System Administrator profile
sf project retrieve start --metadata "Profile:Admin" --target-org <alias>

# Retrieve permission sets (narrow to specific ones if known)
sf project retrieve start --metadata "PermissionSet" --target-org <alias>

# Retrieve layouts for relevant objects
sf project retrieve start --metadata "Layout:ObjectName__c-ObjectName Layout" --target-org <alias>

# Retrieve FlexiPages for relevant objects (if they exist)
sf project retrieve start --metadata "FlexiPage" --target-org <alias>
```

---

## Phase 4: Read Local File Structure

After retrieval, read and understand the current local state:

1. Read `force-app/main/default/profiles/Admin.profile-meta.xml`
   - Note existing `<objectPermissions>` entries
   - Note existing `<fieldPermissions>` entries
   - These must be preserved when appending new permissions

2. List directory contents:
   - `force-app/main/default/objects/` — what objects exist locally
   - `force-app/main/default/layouts/` — what layouts exist
   - `force-app/main/default/permissionsets/` — what permsets exist
   - `force-app/main/default/flexipages/` — what Lightning pages exist

3. For each relevant object directory, read the object XML and all field XMLs to understand the current schema

---

## Phase 5: Gap Analysis

Compare the introspection data against any provided spec or plan. Categorize every item:

- **To Create:** Objects or fields that do not exist in org or local files
- **To Update:** Objects/fields that exist but need modification (new fields added, profile permissions missing, layout needs new fields, etc.)
- **Already Exists:** Items that match the spec exactly — no action needed

Flag any discrepancies:

- Local files that are out of sync with org
- Fields in org that conflict with planned field API names
- `relationshipName` values already in use
- Profile permissions already present (avoid duplicates)

---

## Output Report

Produce this report at the end of the command:

```
## Org Context Summary

### Connection
- Alias: <alias>
- Instance URL: <url>
- API Version: <version>
- Username: <username>
- Org ID: <id>

### Custom Objects in Org
<complete list of custom objects from sf sobject list>

### Objects Relevant to Current Work
For each relevant object:
- Object: ObjectName__c
  - Existing fields: [list with types]
  - Profile access (Admin): [CRUD status]
  - Layouts: [list]
  - FlexiPages: [list]
  - Permission sets covering this object: [list]

### Gap Analysis
**To Create:**
- [ ] ObjectName__c (new custom object)
- [ ] ObjectName__c.FieldName__c (Text 255)

**To Update:**
- [ ] Admin profile — add objectPermissions for ObjectName__c
- [ ] ObjectName__c-ObjectName Layout — add 3 new fields

**Already Exists (no action needed):**
- ObjectName__c.ExistingField__c matches spec

### Warnings
- ⚠️ Local Admin.profile-meta.xml is 2 days older than last deploy — consider re-retrieving
- ⚠️ relationshipName "MyObjects" is already used by ExistingLookup__c — choose a different name
- ⚠️ force-app/main/default/objects/ has no local copy of ObjectName__c — retrieve recommended
```

---

## Phase 6: Persist Context

After the gap analysis output is complete, write persistent context files so future sessions can load cached state instead of re-querying.

### Step 6a: Create directory structure (if not already present)

Create these directories if they do not exist:
```
context/{alias}/
context/{alias}/objects/
context/{alias}/audit/
```

### Step 6b: Write object detail files

For each **relevant object** described in Phase 2, write `context/{alias}/objects/{ObjectName__c}.md`:

```markdown
# {ObjectName__c} — {Label}

_Last scanned: {TIMESTAMP}_
_Source: sf-get-existing-org-object-context_

## Identity
- API Name: {ObjectName__c}
- Label: {Label}
- Plural Label: {PluralLabel}
- Sharing Model: {sharingModel}
- Deployment Status: {deploymentStatus}

## Fields

| API Name | Label | Type | Required | Details |
|---|---|---|---|---|
| Name | Name | Text | true | Auto-name field |
| {FieldName__c} | {Field Label} | {Type} | {true/false} | {length/picklist values/referenceTo as applicable} |

## Relationships
| Field API Name | Type | References | Relationship Name |
|---|---|---|---|
| {LookupField__c} | Lookup | {ParentObject__c} | {RelName} |

## Validation Rules (if any found in org)
| Rule Name | Active | Description |
|---|---|---|
| {RuleName} | true | {description} |

## Apex Triggers
| Trigger Name | Status |
|---|---|
| {TriggerName} | Active |
_(or: No triggers found for this object)_

## Layouts
{list of layout names found in org/local files}

## Permission Sets Covering This Object
{list of permission set names from org query, or "None found"}

## Local File Status
- Object XML: {exists locally / not retrieved}
- Fields local: {N of M fields present locally}
```

### Step 6c: Write the objects inventory file

Write `context/{alias}/objects/_inventory.md`:

```markdown
# Objects Inventory — {alias}

_Last scanned: {TIMESTAMP}_

| Object API Name | Label | Custom Fields (count) | Triggers | Last Modified in Org | In Local Files |
|---|---|---|---|---|---|
| {ObjectName__c} | {Label} | {N} | {Yes/No} | {LastModifiedDate} | {Yes/No} |
```

Include ALL custom objects found in Phase 2 (the full `sf sobject list` output), not just the ones described in detail.

### Step 6d: Write META.md

Write or update `context/{alias}/META.md`:

```markdown
# Org Meta — {alias}

## Connection Info
- Alias: {alias}
- Org ID: {orgId}
- Instance URL: {instanceUrl}
- Username: {username}
- API Version: {apiVersion}

## Scan History

| Timestamp | Type | Summary |
|---|---|---|
| {TIMESTAMP} | full-scan | {N} custom objects found; {M} described in detail |
```

If `META.md` already exists, **append** a new row to the Scan History table — do not overwrite the file.

### Step 6e: Update context/INDEX.md

Read `context/INDEX.md`. Find the row for this alias if it exists; update it. If no row exists, append a new row:

```
| {alias} | {orgId} | {instanceUrl} | {username} | {TIMESTAMP} | _(not yet run)_ | context/{alias}/ |
```

Update the "Last Full Scan" column to the current timestamp.

Also update the Object Inventory Summary table with one row per custom object found.

---

## Phase 5.5: Run Registered Skill Full Scans

After the object-level gap analysis, discover and run full inventory queries for all registered skills. This ensures the initial context cache is comprehensive across all metadata types.

### Step 5.5a: Discover Registered Skills

Read all files matching `skills/*/SKILL.md`. For each file, look for a `## Context Specification` block. Extract:
- `metadata_type` — the type(s) this skill tracks
- `context_path` — where inventory files live (e.g., `{alias}/flows/`)
- `inventory_file` — path to `_inventory.md`
- **Full Inventory Query** — the query with no `{LAST_SCAN}` date filter (gets everything)
- **Change Detection Query** — the query with `{LAST_SCAN}` placeholder (used by freshness checks later)
- API type: `tooling API` or `standard API`
- **Naming Convention Detection** section — what naming patterns to analyze

Log which skills were discovered:
```
Discovered registered skills for full scan:
  - sf-flows → Flow (tooling API)
  - sf-apex-classes → ApexClass (tooling API)
  - sf-validation-rules → ValidationRule (tooling API)
  - sf-permissions → Profile, PermissionSet (standard API)
  - sf-trigger-patterns → ApexClass, ApexTrigger (tooling API)
  - sf-data-architecture → RecordType, CustomLabel, GlobalValueSet, FieldSet, PlatformEvent (mixed)
  - sf-layouts → Layout, FlexiPage, CompactLayout (tooling API)
  - sf-automation-legacy → WorkflowRule, WorkflowFieldUpdate, WorkflowAlert (tooling API)
  - sf-ui-components → LWC, Aura, ApexPage, QuickAction, CustomTab (tooling API)
  - sf-integration → NamedCredential, RemoteSiteSetting, CspTrustedSite, ExternalDataSource (tooling API)
  - sf-fsl → ServiceTerritory, WorkType, SkillRequirement, ServiceResource, OperatingHours (standard API)
  - sf-cpq → SBQQ__ProductRule__c, SBQQ__PriceRule__c, SBQQ__QuoteTemplate__c (standard API)
  - sf-experience-cloud → Network, ExperienceBundle, NavigationMenuItem (mixed)
  - sf-reporting → Report, Dashboard, ListView (standard API)
  - sf-email-notifications → EmailTemplate, CustomNotificationType (mixed)
  - sf-security-advanced → PermissionSetGroup, DuplicateRule, MatchingRule (mixed)
  - sf-assignment-rules → AssignmentRule, AutoResponseRule, EscalationRule (metadata API retrieve)
  [... any others found ...]
```

### Step 5.5b: Run Full Inventory Queries

For each registered skill:

1. Create the context directory: `context/{alias}/{context_path}/` (if not present)
2. Run the **Full Inventory Query** (use `--use-tooling-api` if specified, `--json` for parsing)
3. Parse the query results
4. **Analyze naming conventions:** Examine all API names/DeveloperNames returned and detect patterns per the skill's `Naming Convention Detection` section
5. Write the `_inventory.md` file with:
   - `## Detected Naming Conventions` section at the top (patterns found, with counts/percentages)
   - `## Inventory` table below, formatted per the skill's `Inventory Columns`
6. If the skill specifies detail files (e.g., sf-flows for record-triggered flows), write those too
7. If a query fails (e.g., object type doesn't exist in this org edition — common for FSL, CPQ, Experience Cloud), log a warning and skip that skill — do not abort

### Step 5.5c: Handle Metadata API Skills

Some skills (e.g., sf-assignment-rules) require Metadata API retrieve rather than SOQL queries. For these:

1. Run the retrieve command specified in the skill's Context Specification
2. Parse the retrieved XML files
3. Write the inventory file from the parsed XML

### Step 5.5d: Log Skill Scan Summary

After all skills have been scanned, log a summary:
```
Skill scan summary:
  - sf-flows: 23 active flows found (15 record-triggered, 5 screen, 3 scheduled)
  - sf-apex-classes: 142 non-managed classes found (categorized: 38 test, 12 batch, 8 schedulable, ...)
  - sf-validation-rules: 67 validation rules found across 18 objects
  - sf-permissions: 14 permission sets, 8 profiles found
  - sf-fsl: SKIPPED (FSL managed package not installed)
  - sf-cpq: SKIPPED (SBQQ namespace not found)
  [...]
```

---

## Notes

- Always run this command before `sf-implement-objects` when working in a non-scratch org
- Re-run if significant time has passed since last retrieval (someone else may have made changes)
- The gap analysis output is the primary input for `sf-implement-objects`
- Phase 6 writes to `context/` only — it does not modify org data or Salesforce project files
- Context files are re-derivable from the org at any time; they are a cache, not source of truth
- Phase 5.5 may take several minutes on large orgs — it runs many queries. Progress is logged per-skill.
- Skills whose metadata types don't exist in the org (e.g., CPQ, FSL) are gracefully skipped
