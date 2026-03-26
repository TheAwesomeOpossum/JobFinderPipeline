---
description: "Prime the current session with Salesforce org context. Checks context existence and freshness, loads org architecture summary, and outputs an org state dashboard. Run this at the start of every session."
argument-hint: [target-org-alias]
---

# /sf-prime

Prime Claude with Salesforce org context for the current session.

---

## Phase 0: Determine Org Alias

1. If the user provided an argument, use it as `ORG_ALIAS`. Skip to Phase 1.

2. If no argument was provided, silently read `context/INDEX.md`.

3. Parse the org registry table in INDEX.md:
   - **One org registered:** Use it automatically. Output:
     ```
     Using org: {alias}
     ```
   - **Multiple orgs registered:** Ask the user:
     ```
     Multiple orgs are registered:
     {list each alias with its instance URL}
     Which org do you want to prime for this session?
     ```
     Wait for response. Store selection as `ORG_ALIAS`.
   - **No orgs registered (or INDEX.md does not exist):** Set `ORG_ALIAS` to `null`. Proceed to Phase 1.

4. Store the resolved value as `ORG_ALIAS`.

---

## Phase 1: Context Existence Check

### Case A: No alias at all (no orgs in INDEX.md and no argument provided)

- Ask the user:
  ```
  No Salesforce org is connected yet. What alias would you like to use?
  (This should match your `sf org login` alias — e.g., "myorg", "dev", "sandbox")
  ```
- Wait for the user's response. Store it as `ORG_ALIAS`.
- Output:
  ```
  No org context found for '{ORG_ALIAS}'. Running initial project setup...
  ```
- **Auto-invoke** `/sf-init-project {ORG_ALIAS}` — run it directly, do not merely suggest it.
- After init completes, skip Phase 2 (context was just created) and proceed to Phase 3.

### Case B: Alias resolved but no context directory

- Check whether `context/{ORG_ALIAS}/` directory exists.
- **If the directory does NOT exist:**
  - Output:
    ```
    No org context found for '{ORG_ALIAS}'. Running initial project setup...
    ```
  - **Auto-invoke** `/sf-init-project {ORG_ALIAS}` — run it directly, do not merely suggest it.
  - After init completes, skip Phase 2 (context was just created) and proceed to Phase 3.

### Case C: Context directory exists

- Output nothing. Proceed to Phase 2.

---

## Phase 2: Context Freshness Check

1. Read `context/{ORG_ALIAS}/META.md`.
2. Extract the `last_scan` timestamp from the file.
3. Calculate `DAYS_SINCE_SCAN` = (today's date) minus (last_scan date).

### If DAYS_SINCE_SCAN > 7 (stale context)

- Output:
  ```
  Context is {DAYS_SINCE_SCAN} days old. Checking for changes...
  ```
- Silently execute the `/sf-check-context-freshness {ORG_ALIAS}` logic:
  - Discover all registered skills by reading `skills/*/SKILL.md` files.
  - For each skill with a Context Specification, run its change-detection query
    against the org using `sf data query` with the `{LAST_SCAN}` timestamp.
  - Collect results into modified/new component counts.
- Parse the freshness report and summarize:
  ```
  {X} modified, {Y} new components detected since last scan.
  ```
- If significant changes were found (X + Y > 10):
  ```
  Context has drifted. Consider `/sf-init-project {ORG_ALIAS}` for a full rescan.
  ```
- If no changes or minimal changes:
  ```
  Minor drift detected. Context is still usable.
  ```

### If DAYS_SINCE_SCAN <= 7 (current context)

- Output:
  ```
  Context is current (scanned {DAYS_SINCE_SCAN} days ago).
  ```

---

## Phase 3: Load Architecture Summary

### Primary path: architecture-summary.md exists

1. Check for `context/{ORG_ALIAS}/audit/architecture-summary.md`.
2. If the file exists, read and internalize:
   - **Connection info** — instance URL, username, API version
   - **Metadata inventory counts** — objects, classes, triggers, flows, etc.
   - **Detected naming conventions** — prefixes, suffixes, patterns
   - **Managed packages** — namespace prefixes and component counts
   - **Top automated objects** — objects with the most automation components
   - **Org complexity assessment** — Small / Medium / Large rating
3. Store all parsed values for the Phase 4 dashboard.

### Fallback path: no architecture summary

1. If `architecture-summary.md` does not exist, read individual inventory files to
   build the summary on-the-fly. Check each of these files (skip any that do not exist):

   | File | Provides |
   |---|---|
   | `context/{ORG_ALIAS}/objects/_inventory.md` | Custom object count, managed vs org-built |
   | `context/{ORG_ALIAS}/apex-classes/_inventory.md` | Apex class count |
   | `context/{ORG_ALIAS}/flows/_inventory.md` | Flow count (active vs inactive) |
   | `context/{ORG_ALIAS}/apex/_inventory.md` | Trigger count |
   | `context/{ORG_ALIAS}/validation-rules/_inventory.md` | Validation rule count |
   | `context/{ORG_ALIAS}/permissions/_inventory.md` | Permission set count |
   | `context/{ORG_ALIAS}/lwc/_inventory.md` | LWC component count |
   | `context/{ORG_ALIAS}/named-credentials/_inventory.md` | Named credential count |

2. For each inventory file that exists:
   - Count the rows in the markdown table (exclude header and separator rows).
   - If the inventory distinguishes managed vs org-built (e.g., a Namespace column),
     split the count accordingly.

3. Derive complexity and automation density from the counts:
   - **Org Complexity:** Small (< 50 custom objects) / Medium (50-200) / Large (200+)
   - **Automation Density:** Calculate average automations per object.
     Low (< 1) / Medium (1-3) / High (> 3)

4. Read `context/{ORG_ALIAS}/META.md` for connection info if not already loaded.

---

## Phase 4: Output Org State Dashboard

Display a concise priming summary using the values gathered in Phase 3.
Format exactly as shown (omit rows where data is unavailable):

```
## Org Primed: {ORG_ALIAS}

**Connection:** {instanceUrl} | {username} | API v{apiVersion}

| Metadata | Count |
|---|---|
| Custom Objects (org-built) | {N} |
| Custom Objects (managed) | {M} |
| Apex Classes | {N} |
| Apex Triggers | {N} |
| Active Flows | {N} |
| Validation Rules | {N} |
| Permission Sets | {N} |
| LWC Components | {N} |
| Named Credentials | {N} |

**Managed Packages:** {namespace list with counts, e.g., "npe01 (12), npsp (47), sfLma (3)"}
**Org Complexity:** {Small / Medium / Large}
**Automation Density:** {Low / Medium / High} — {avg} automations per object
**Top Automated Objects:** {Object1} ({N} automations), {Object2} ({N}), {Object3} ({N})
**Naming Conventions:** {1-line summary of dominant patterns from inventory files}
**Context Freshness:** Scanned {DAYS_SINCE_SCAN} days ago | {CURRENT / STALE}
```

### Dashboard formatting rules
- Use "CURRENT" if DAYS_SINCE_SCAN <= 7, "STALE" if > 7.
- If a count is unknown, omit that row entirely rather than showing "0" or "?".
- Keep managed packages to one line; if more than 5, show top 5 and "+ {N} more".
- Top Automated Objects should list up to 3 objects sorted by total automation count
  (triggers + flows + validation rules + workflow rules).

---

## Phase 5: Session Guidance

After the dashboard, output the following guidance block:

```
Ready to work. Here's what I can do:

**Build something new:**
  Tell me about a feature you want to build — I'll load context, check for
  conflicts, and guide you through requirements, planning, and implementation.

**Explore the org:**
  Ask "what automation exists on {Object}?" — I'll map all triggers, flows, and rules.
  Ask "what objects are in this org?" — I'll show the full inventory.

**Check org state:**
  Run `/sf-check-context-freshness` to see what changed since last scan.

**Resume work:**
  If you have an existing requirements doc or plan, point me to it and I'll
  pick up where we left off.
```

### Step 5b: Detect In-Progress Features

After the guidance block, scan `projects/**/master-plan.md` for any master plans with incomplete phases.

For each found:
- Read the master plan's Phase Registry table
- Find the first "Not Started" or "Plan Generated" phase
- Extract `{alias}` and `{feature-name}` from the file path (`projects/{alias}/{feature-name}/master-plan.md`)
- Display:

```
**In-progress feature detected:**
  Feature: {feature-name}
  Org: {alias}
  Progress: Phase {completed} of {total} complete
  Next: Phase {N} — {phase-name}
  Resume: `/sf-execute projects/{alias}/{feature-name}/phase-{N}-{name}.md`
  Generate next phase: `/sf-plan-feature --next {feature-name}`
```

If the next phase plan file doesn't exist yet (only outlined in master plan), suggest generating it first.

---

## Behavioral Notes

- **Safe to re-run.** This command refreshes the dashboard without side effects.
  Re-running does not re-scan the org or modify context files.
- **Phase 1 auto-invokes init** instead of merely suggesting it. This eliminates
  dead ends where the user is told to run a command but doesn't.
- **Phase 2 runs freshness checks silently.** No user action is needed for
  read-only queries against the org. Only the summary is shown.
- **Phase 4 is deliberately concise.** The full architecture summary stays in the
  file; the dashboard is a quick-reference snapshot, not a full report.
- **This command replaces the template project's `/prime` command.** It is the
  Salesforce-specific equivalent, tailored to org context and metadata workflows.
- **Do not output intermediate progress** for Phases 0 and 3. Only Phase 1 (if init
  is needed), Phase 2 (freshness status), Phase 4 (dashboard), and Phase 5 (guidance)
  produce visible output.
