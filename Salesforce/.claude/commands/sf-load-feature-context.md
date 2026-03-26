---
description: "Load cached org context relevant to a specific feature spec, minimizing context window usage. Discovers registered skills at runtime — no hardcoded metadata types."
argument-hint: [path-to-feature-spec-or-description]
---

# SF Load Feature Context

Run this command at the start of a feature implementation session to pre-load only the org context relevant to the feature being built. Reads from the cached `context/` directory — does NOT re-query the org unless context is missing.

**Usage:** `/sf-load-feature-context <path-to-feature-spec>` or `/sf-load-feature-context` (will prompt for spec or description)

---

## Phase 1: Parse Feature Spec

Read the provided spec file or accept an inline feature description from the user.

Extract:
- **Explicit object names** (any token ending in `__c`, standard object names like `Account`, `Contact`)
- **Explicit class/trigger names** (any token ending in `Handler`, `Processor`, `Trigger`)
- **Keywords** describing the feature (field names, business concepts, operation types)
- **Feature type hints**: objects, Apex, flows, permissions, validation rules, etc.

Build a search list:
- `explicit_objects`: list of object API names mentioned directly
- `explicit_classes`: list of Apex class/trigger names mentioned directly
- `keywords`: list of business terms to match against inventory files

---

## Phase 2: Check INDEX.md and Scan Freshness

Read `context/INDEX.md`:
- Identify the org alias from the connected orgs table (if only one org is registered, use it; if multiple, ask the user which)
- Extract `Last Full Scan` timestamp for that alias

If `context/INDEX.md` does not exist or has no registered orgs:
- Output: "No org context found. Run `/sf-get-existing-org-object-context <alias>` first."
- Stop.

Evaluate freshness:
- If `Last Full Scan` is blank: warn that no full scan has been run
- If `Last Full Scan` is more than 7 days ago: display a warning:

```
⚠️  Context was last scanned {N} days ago. Consider running `/sf-check-context-freshness {alias}` before proceeding.
Continuing with cached context from {LAST_SCAN}.
```

Do NOT stop for stale context — warn and continue.

---

## Phase 3: Discover Registered Skills

Read all files matching `skills/*/SKILL.md`.

For each file, look for a `## Context Specification` block. Extract:
- `metadata_type`
- `context_path` (resolve `{alias}` with the actual alias)
- `inventory_file` (resolve `{alias}`)
- `detail_file_pattern` (resolve `{alias}`)

Build a map: `metadata_type → { context_path, inventory_file, detail_file_pattern }`

Also include the base-layer objects entry (not a skill, but always present):
- `metadata_type`: CustomObject
- `inventory_file`: `context/{alias}/objects/_inventory.md`
- `detail_file_pattern`: `context/{alias}/objects/{ObjectName__c}.md`

---

## Phase 4: Map Feature to Context Files

For each registered metadata type (including base-layer objects):

**Step 4a: Check if inventory file exists**

If the inventory file does not exist, skip this type and note:
```
  ⏭ {metadata_type}: no inventory file found (context not yet gathered for this type)
```

**Step 4b: Read inventory file**

Scan inventory rows for matches against:
1. Exact matches against `explicit_objects` or `explicit_classes` list (highest priority)
2. Fuzzy matches: does the row's API Name or Label contain any keyword from `keywords`?

Collect all matching rows with their detail file paths.

**Step 4c: Determine which detail files to load**

- For CustomObject type: each matched row has a detail file at `context/{alias}/objects/{ObjectName__c}.md`
- For Apex type: no detail files (inventory only)
- For other registered skills: use the skill's `detail_file_pattern` with `{ApiName}` replaced

**Context window budget:** Load at most **5–7 detail files total** across all metadata types.

If more than 7 detail files match:
- Present a candidate list to the user
- Ask: "These {N} context files matched your feature spec. Loading all would exceed the context budget (5-7 files). Which should I load? (list numbers or 'all if under 7')"
- Wait for user selection before loading

---

## Phase 5: Load and Present Context

For each selected context file, read it and output a structured summary:

```
## Feature Context Loaded — {feature name or spec filename}

Org: {alias} | Last scanned: {LAST_SCAN} {[STALE warning if applicable]}

---

### CustomObjects

#### {ObjectName__c} — {Label}
[contents of context/{alias}/objects/{ObjectName__c}.md]

Freshness: {last modified date from file} | {CURRENT / STALE}

---

### ApexClass / ApexTrigger  (sf-trigger-patterns)

_Relevant entries from inventory:_

| Name | Type | Status | Last Modified |
|---|---|---|---|
| {ClassName} | ApexClass | Active | 2025-01-10 |
| {TriggerName} | ApexTrigger | Active | 2025-01-08 |

[No detail files for Apex — retrieve with: `sf project retrieve start --metadata "ApexClass:{ClassName}" --target-org {alias}`]

---

### PermissionSet  (sf-permissions)

_Relevant entries from inventory:_

| API Name | Label | Last Modified |
|---|---|---|
| {PermSetName} | {Label} | 2025-01-05 |

[No detail files — retrieve with: `sf project retrieve start --metadata "PermissionSet:{PermSetName}" --target-org {alias}`]

---

[... one section per registered skill that had matches ...]

---

## Context Not Loaded (no matches)

The following registered metadata types had no inventory matches for this feature:
- [list of types with no matches]

---

## Recommended Pre-flight Checks

Based on the loaded context, consider running these before implementing:
{Conditional list based on what was found:}
- [ ] If any object shows STALE: re-run `sf-get-existing-org-object-context {alias}`
- [ ] If Apex matches found: check for existing triggers with `sf data query --query "SELECT Name FROM ApexTrigger WHERE Name LIKE '{ObjectName}%'" --target-org {alias}`
- [ ] If permissions matches found: retrieve fresh copies before editing
```

---

## Notes

- This command is read-only — it reads from `context/` files and presents them; it does not query the org or write any files
- If the spec mentions an object that has no context file but does appear in `_inventory.md`, load the inventory row and note: "Detail file missing — run a full object describe for {ObjectName__c}"
- Feature context loaded here replaces manual re-querying at the start of a session; the loaded data should be treated as the starting point for the implementation session's gap analysis
- After loading context, proceed directly to the relevant implement command (e.g., `/sf-implement-objects`, `/sf-implement-trigger`)
