---
description: "Check whether the cached org context is still current by running change-detection queries against the org. Discovers registered skills at runtime — no hardcoded metadata types."
argument-hint: [target-org-alias]
---

# SF Check Context Freshness

Run this command to find out what has changed in the org since the last context scan. Discovers all registered skills by reading `skills/*/SKILL.md` and runs their change-detection queries automatically.

**Usage:** `/sf-check-context-freshness <alias>`

---

## Phase 1: Load Timestamps

Read `context/{alias}/META.md`.

Extract:
- `LAST_SCAN` — timestamp of the last full context scan (written by `sf-get-existing-org-object-context`)
- `LAST_FRESHNESS_CHECK` — timestamp of the most recent freshness check run (may be absent on first run)

If `context/{alias}/META.md` does not exist:
- **Stop immediately**
- Output: "No context found for alias `{alias}`. Run `/sf-get-existing-org-object-context {alias}` first to build the initial context cache."

If `LAST_SCAN` is present, display it:
```
Context last fully scanned: {LAST_SCAN}
Days since scan: {N}
```

If the scan is more than 7 days old, display a warning:
```
⚠️  Context is {N} days old. Consider re-running `/sf-get-existing-org-object-context {alias}` for a full refresh.
```

---

## Phase 2: Confirm Org Connection

```bash
sf org display --target-org <alias>
```

If this fails: stop and instruct user to run `sf org login web --alias <alias>`.

---

## Phase 3: Discover Registered Skills

Read all files matching `skills/*/SKILL.md`.

For each file, look for a `## Context Specification` block. Extract:
- `metadata_type` — the type(s) this skill tracks
- `context_path` — where inventory files live
- `inventory_file` — path to the `_inventory.md` for this type
- Change detection queries (one or more SOQL blocks in the spec)
- API type: `tooling API` or `standard API`

Build a list of registered checks to run. Log which skills were discovered:
```
Discovered registered skills:
  - sf-trigger-patterns → ApexClass, ApexTrigger (tooling API)
  - sf-permissions → Profile, PermissionSet (standard API)
  [... any others found ...]
```

---

## Phase 4: Run Base-Layer Object Change Detection

These queries run for all orgs regardless of registered skills. Objects are the base layer managed by `sf-get-existing-org-object-context`.

### 4a. Custom object changes (Tooling API)

Replace `{LAST_SCAN}` with the timestamp extracted in Phase 1.

```sql
SELECT QualifiedApiName, LastModifiedDate, LastModifiedBy.Name
FROM EntityDefinition
WHERE LastModifiedDate > {LAST_SCAN}
AND QualifiedApiName LIKE '%__c'
ORDER BY LastModifiedDate DESC
LIMIT 50
```

```bash
sf data query \
  --query "SELECT QualifiedApiName, LastModifiedDate, LastModifiedBy.Name FROM EntityDefinition WHERE LastModifiedDate > {LAST_SCAN} AND QualifiedApiName LIKE '%__c' ORDER BY LastModifiedDate DESC LIMIT 50" \
  --use-tooling-api \
  --target-org <alias>
```

### 4b. Admin-level changes (SetupAuditTrail, standard API)

**Build the Section list dynamically** from registered skills discovered in Phase 3. For each skill's `metadata_type` values, map them to SetupAuditTrail Section names. Always include the base-layer sections.

Base-layer sections (always included):
- `CustomObject`, `CustomField`

Dynamically added from registered skills (map metadata_type → Section):
- ApexClass → `ApexClass`
- ApexTrigger → `ApexTrigger`
- Profile → `Profile`
- PermissionSet → `PermissionSet`
- Flow → `Flow`
- ValidationRule → `ValidationRule`
- Layout → `Layout`
- FlexiPage → `FlexiPage`
- WorkflowRule → `Workflow`
- ApprovalProcess → `ApprovalProcess`
- PermissionSetGroup → `PermissionSetGroup`
- DuplicateRule → `DuplicateRule`
- MatchingRule → `MatchingRule`
- AssignmentRule → `AssignmentRule`
- AutoResponseRule → `AutoResponseRule`
- EscalationRule → `EscalationRule`
- SharingRules → `SharingRules`
- NamedCredential → `NamedCredential`
- ConnectedApp → `ConnectedApp`
- CustomTab → `CustomTab`
- EmailTemplate → `EmailTemplate`
- Network → `Network`
- ExperienceBundle → `ExperienceBundle`

Build the IN clause from whatever skills are registered. If the list grows very large, split into multiple queries.

```bash
sf data query \
  --query "SELECT CreatedDate, CreatedBy.Name, Action, Section, Display FROM SetupAuditTrail WHERE CreatedDate > {LAST_SCAN} AND Section IN ({DYNAMIC_SECTION_LIST}) ORDER BY CreatedDate DESC LIMIT 100" \
  --target-org <alias>
```

Cross-reference results against `context/{alias}/objects/_inventory.md`:
- Objects in query results but not in inventory → **NEW** (not yet cached)
- Objects in both results and inventory → **MODIFIED** (cache is stale for these)
- Objects in inventory but not in results → **UNCHANGED** (cache is current)

---

## Phase 5: Run All Skill-Registered Change Detection Queries

For each registered skill discovered in Phase 3:

1. Replace `{LAST_SCAN}` in each query with the timestamp from Phase 1
2. Determine API type (`--use-tooling-api` flag or not)
3. Run the query:

```bash
sf data query \
  --query "{modified query with LAST_SCAN replaced}" \
  [--use-tooling-api if tooling API] \
  --target-org <alias>
```

4. Cross-reference results against the skill's `inventory_file`:
   - Items in query results but not in inventory → **NEW**
   - Items in both → **MODIFIED** (stale)
   - Items in inventory but not in results → **UNCHANGED**

If an inventory file does not yet exist for a skill's `context_path`, report all results as NEW and note that a full scan for that metadata type has not been run yet.

---

## Phase 6: Output Staleness Report

Produce a structured report grouped by metadata type:

```
## Context Freshness Report — {alias}

Last full scan: {LAST_SCAN}
Freshness check run: {NOW}

---

### Objects (Base Layer)

| Object | Status | Last Modified | Modified By |
|---|---|---|---|
| MyObject__c | UNCHANGED | 2025-01-10 | admin@example.com |
| NewObject__c | NEW | 2025-03-15 | developer@example.com |
| ChangedObject__c | MODIFIED | 2025-03-14 | admin@example.com |

Counts: {N} unchanged, {M} modified, {P} new

Recommended action: [none / re-run `/sf-get-existing-org-object-context {alias}` to update {M+P} stale entries]

---

### ApexClass / ApexTrigger  (sf-trigger-patterns)

| Name | Type | Status | Last Modified | Modified By |
|---|---|---|---|---|
| AccountTriggerHandler | ApexClass | UNCHANGED | 2025-01-08 | admin@example.com |
| NewTrigger | ApexTrigger | NEW | 2025-03-15 | developer@example.com |

Counts: {N} unchanged, {M} modified, {P} new

Recommended action: [none / re-run Apex context scan for stale entries]

---

### Profile / PermissionSet  (sf-permissions)

| Name | Type | Status | Last Modified | Modified By |
|---|---|---|---|---|
| MyPermSet | PermissionSet | MODIFIED | 2025-03-12 | admin@example.com |

Counts: {N} unchanged, {M} modified, {P} new

Recommended action: [none / re-retrieve and update permissions context]

---

[... one section per registered skill ...]

---

### SetupAuditTrail (last {N} admin changes)

| Date | Section | Action | Display | By |
|---|---|---|---|---|
| 2025-03-15 | ApexClass | created | NewTriggerHandler | developer@example.com |

---

## Summary

| Metadata Type | Unchanged | Modified | New | Action Needed |
|---|---|---|---|---|
| Objects | {N} | {M} | {P} | [yes/no] |
| ApexClass/Trigger | {N} | {M} | {P} | [yes/no] |
| Profile/PermSet | {N} | {M} | {P} | [yes/no] |

Overall status: [ALL CURRENT / STALE — {total stale count} components need refresh]
```

---

## Phase 7: Update Audit Record

Append a freshness-check row to `context/{alias}/META.md`:

```markdown
| {TIMESTAMP} | freshness-check | Objects: {N} unchanged/{M} modified/{P} new; ApexClass: ...; PermSet: ... |
```

Also write the full report output to `context/{alias}/audit/_recent_changes.md` (create the `audit/` directory if it does not exist), overwriting the previous run.

Update `context/INDEX.md`: set "Last Freshness Check" to the current timestamp for this alias row.

---

## Notes

- This command is read-only — it never modifies org data or local metadata files (only `META.md`, `audit/`, and `INDEX.md`)
- The `{LAST_SCAN}` placeholder must be formatted as an ISO-8601 datetime string, e.g. `2025-01-10T00:00:00.000+0000`
- SetupAuditTrail only retains 180 days of history — if the last scan is older than 180 days, the audit trail cannot fill the gap
- If a registered skill's change detection query returns an error (e.g. object doesn't exist in this org edition), log a warning and continue — do not abort the full check
