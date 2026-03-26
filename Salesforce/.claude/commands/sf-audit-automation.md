---
description: "Produce a per-object automation map showing all triggers, flows, workflow rules, and validation rules. Identifies potential conflicts and shows Salesforce order of execution."
argument-hint: [ObjectApiName__c]
---

# sf-audit-automation

Cross-reference all automation on a given Salesforce object to produce a comprehensive automation map organized by the Salesforce order of execution. This command is **read-only** and never modifies org data.

---

## Phase 0: Validate Input

1. Parse `$ARGUMENTS` to extract the target Salesforce object API name.
   - Valid examples: `Account`, `Contact`, `Invoice__c`, `Work_Order__c`
   - The argument should be a single object API name (standard or custom).

2. If `$ARGUMENTS` is empty or missing:
   - Ask the user: "Which Salesforce object would you like to audit? Please provide the API name (e.g., `Account`, `Invoice__c`)."
   - Wait for the user's response before proceeding.

3. Store the object API name in a variable for use throughout the command:
   - `OBJECT_API_NAME` = the provided argument
   - `OBJECT_BASE_NAME` = the object name without `__c` suffix (used for matching related Apex classes)
     - e.g., `Invoice__c` → `Invoice`, `Work_Order__c` → `Work_Order`
     - For standard objects, `OBJECT_BASE_NAME` = `OBJECT_API_NAME` (e.g., `Account` → `Account`)

4. Determine the org alias:
   - Read `context/INDEX.md` to find connected orgs.
   - If exactly one org is listed, use that alias automatically.
   - If multiple orgs are listed, ask the user which org to audit.
   - If no orgs are listed or `INDEX.md` does not exist, tell the user:
     "No connected orgs found. Run `/sf-get-existing-org-object-context <alias>` first to populate org context."
   - Store the selected alias as `ORG_ALIAS`.

5. Verify that `context/{ORG_ALIAS}/` directory exists.
   - If it does not exist, tell the user:
     "No context has been gathered for org '{ORG_ALIAS}'. Run `/sf-get-existing-org-object-context {ORG_ALIAS}` to populate context first."

---

## Phase 1: Load Context Files

Read cached context from all relevant skill inventory files. For each source below, search for entries matching `OBJECT_API_NAME`. Track which sources were successfully loaded and which are missing.

Initialize empty collections for each automation type. As you read each inventory file, populate the corresponding collection.

### 1.1 — Apex Triggers (sf-trigger-patterns)

Read `context/{ORG_ALIAS}/apex/_inventory.md`

- Scan the inventory for triggers whose "Object" column matches `OBJECT_API_NAME`.
- For each matching trigger, note:
  - Trigger Name
  - Trigger Contexts (before insert, after insert, before update, after update, before delete, after delete, after undelete)
  - Handler Class name
  - Processor Class name(s)
- If detail files exist at `context/{ORG_ALIAS}/apex/{TriggerName}.md`, read them to get:
  - The full list of trigger contexts
  - Handler class reference
  - Processor class references
  - Any recursion-guard patterns

If the inventory file does not exist:
- Record: "Apex triggers — **Not yet scanned**. Run `/sf-get-existing-org-object-context {ORG_ALIAS}` to populate."

### 1.2 — Flows (sf-flows)

Read `context/{ORG_ALIAS}/flows/_inventory.md`

- Scan for flows where the "Object" or "Trigger Object" column matches `OBJECT_API_NAME`.
- Filter to record-triggered flows (ProcessType = `AutoLaunchedFlow` with a TriggerType).
- For each matching flow, note:
  - DeveloperName / Label
  - TriggerType (RecordBeforeSave, RecordAfterSave, RecordBeforeDelete)
  - Trigger Event (Create, Update, Create or Update, Delete)
  - Entry Conditions (if available)
  - Element summary (number/types of elements)
  - Active version number
- If detail files exist at `context/{ORG_ALIAS}/flows/{DeveloperName}.md`, read them to get:
  - Trigger configuration (object, event, condition logic)
  - Entry conditions with field references
  - Element-by-element summary (decisions, assignments, record updates, subflows, etc.)
  - Any scheduled paths

Categorize each flow into one of:
- **Before-Save Flows** (TriggerType = RecordBeforeSave)
- **After-Save Flows** (TriggerType = RecordAfterSave)
- **Before-Delete Flows** (TriggerType = RecordBeforeDelete)

If the inventory file does not exist:
- Record: "Flows — **Not yet scanned**. Run `/sf-get-existing-org-object-context {ORG_ALIAS}` to populate."

### 1.3 — Workflow Rules & Field Updates (sf-automation-legacy)

Read `context/{ORG_ALIAS}/automation-legacy/_inventory.md`

- Scan for workflow rules where the "Object" column matches `OBJECT_API_NAME`.
- For each matching workflow rule, note:
  - Rule Name
  - Active status
  - Evaluation criteria (created, created and every time it's edited, created and any time it's edited to subsequently meet criteria)
  - Associated field updates (names and target fields)
  - Associated email alerts (names and templates)
  - Associated outbound messages
  - Associated tasks
- If detail files exist, read them for full action configuration.

If the inventory file does not exist:
- Record: "Workflow rules — **Not yet scanned**. Run `/sf-get-existing-org-object-context {ORG_ALIAS}` to populate."

### 1.4 — Validation Rules (sf-validation-rules)

Read `context/{ORG_ALIAS}/validation-rules/_inventory.md`

- Scan for validation rules where the "Object" column matches `OBJECT_API_NAME`.
- For each matching rule, note:
  - Rule API Name
  - Active status
  - Description
  - Error condition formula (if available in detail files)
  - Error message
  - Error location (top of page or specific field)
- If detail files exist at `context/{ORG_ALIAS}/validation-rules/{RuleName}.md`, read them for full formula and configuration.

If the inventory file does not exist:
- Record: "Validation rules — **Not yet scanned**. Run `/sf-get-existing-org-object-context {ORG_ALIAS}` to populate."

### 1.5 — Related Apex Classes (sf-apex-classes)

Read `context/{ORG_ALIAS}/apex-classes/_inventory.md`

- Search for classes whose names contain `OBJECT_BASE_NAME` (case-insensitive partial match).
  - e.g., for `Invoice__c`, look for classes containing "Invoice" — `InvoiceService`, `InvoiceBatch`, `InvoiceHelper`, `InvoiceTriggerHandler`, etc.
- For each matching class, note:
  - Class Name
  - Category (inferred from naming: Service, Batch, Scheduler, Helper, Handler, Processor, Selector, Test, Controller, Utility, Unknown)
  - Size (character count or line count if available)
  - Last Modified Date
- Exclude test classes from the main list but note their existence separately.

If the inventory file does not exist:
- Record: "Apex classes — **Not yet scanned**. Run `/sf-get-existing-org-object-context {ORG_ALIAS}` to populate."

### 1.6 — Summary of Context Availability

After loading all sources, produce an internal summary:

```
Context Sources Loaded:
- [x] Apex Triggers      — {N} triggers found
- [x] Flows              — {N} flows found
- [ ] Workflow Rules      — Not scanned
- [x] Validation Rules   — {N} rules found
- [x] Apex Classes       — {N} classes found
```

This summary will be included in the final output.

---

## Phase 2: Live Query (Optional Enrichment)

Check `context/{ORG_ALIAS}/META.md` for the last scan timestamp. If the last scan is older than 7 days, or if any inventory files were missing from Phase 1, inform the user:

"Some context may be stale or missing. Would you like me to run live queries against the org to enrich the audit? (This requires an active SF CLI connection to `{ORG_ALIAS}`.)"

If the user agrees (or if you determine enrichment is needed), run the following queries using `sf data query` with the appropriate flags.

### 2.1 — Active Apex Triggers

Use the **Tooling API** (`--use-tooling-api` flag):

```bash
sf data query --query "SELECT Name, Status, TableEnumOrId, Body, LastModifiedDate, LastModifiedBy.Name FROM ApexTrigger WHERE TableEnumOrId = '{OBJECT_API_NAME}' AND NamespacePrefix = null AND Status = 'Active'" --use-tooling-api --target-org {ORG_ALIAS} --json
```

- Parse the JSON result.
- For each trigger, extract the trigger contexts from the `Body` field by scanning for `before insert`, `after insert`, `before update`, `after update`, `before delete`, `after delete`, `after undelete`.
- Cross-reference with cached context and add any missing triggers.

### 2.2 — Record-Triggered Flows

Use the **Tooling API**:

```bash
sf data query --query "SELECT Definition.DeveloperName, Definition.ActiveVersionId, VersionNumber, Status, ProcessType, TriggerType, Description FROM Flow WHERE Status = 'Active' AND ProcessType IN ('AutoLaunchedFlow','RecordBeforeDelete','RecordBeforeSave','RecordAfterSave') AND Definition.NamespacePrefix = null" --use-tooling-api --target-org {ORG_ALIAS} --json
```

- The Tooling API Flow object does not directly expose the trigger object name in SOQL.
- To determine which flows target our object:
  1. First check the cached flow detail files (which contain the object reference from the flow XML).
  2. If not available, retrieve the flow metadata for active record-triggered flows:
     ```bash
     sf project retrieve start --metadata "Flow:{DeveloperName}" --target-org {ORG_ALIAS} --output-dir /tmp/sf-audit-flows
     ```
  3. Parse the retrieved XML to find `<start><object>{OBJECT_API_NAME}</object></start>`.
- Only include flows that target `OBJECT_API_NAME`.
- Cross-reference with cached context and add any missing flows.

### 2.3 — Workflow Rules

Use the **Tooling API**:

```bash
sf data query --query "SELECT Id, Name, TableEnumOrId FROM WorkflowRule WHERE NamespacePrefix = null" --use-tooling-api --target-org {ORG_ALIAS} --json
```

- Note: `TableEnumOrId` may contain an Entity ID (e.g., `01I...`) rather than the API name for custom objects.
- To resolve, first query `EntityDefinition`:
  ```bash
  sf data query --query "SELECT DurableId, QualifiedApiName FROM EntityDefinition WHERE QualifiedApiName = '{OBJECT_API_NAME}'" --use-tooling-api --target-org {ORG_ALIAS} --json
  ```
- Match `TableEnumOrId` against both the API name (for standard objects) and the DurableId.
- For matching workflow rules, query associated actions:
  ```bash
  sf data query --query "SELECT Id, Name, FieldName, Operation, LiteralValue, Formula FROM WorkflowFieldUpdate WHERE EntityDefinition.QualifiedApiName = '{OBJECT_API_NAME}'" --use-tooling-api --target-org {ORG_ALIAS} --json
  ```
  ```bash
  sf data query --query "SELECT Id, Name, Description FROM WorkflowAlert WHERE EntityDefinition.QualifiedApiName = '{OBJECT_API_NAME}'" --use-tooling-api --target-org {ORG_ALIAS} --json
  ```
- Cross-reference with cached context and add any missing workflow rules.

### 2.4 — Validation Rules

Use the **Tooling API**:

```bash
sf data query --query "SELECT Id, ValidationName, Active, Description, ErrorDisplayField, ErrorMessage, LastModifiedDate, LastModifiedBy.Name FROM ValidationRule WHERE EntityDefinition.QualifiedApiName = '{OBJECT_API_NAME}' AND NamespacePrefix = null" --use-tooling-api --target-org {ORG_ALIAS} --json
```

- Cross-reference with cached context and add any missing validation rules.

### 2.5 — Merge Results

After live queries complete:
- Merge live query results with cached context.
- Prefer live query data when there are conflicts (it is fresher).
- Note in the output which items came from cache vs. live query.

---

## Phase 3: Build Automation Map

Produce the comprehensive automation map output. This is the primary deliverable of the command.

### Output Format

Present the following to the user:

```markdown
# Automation Map — {OBJECT_API_NAME}
**Org:** {ORG_ALIAS}
**Generated:** {current date/time}
**Context Sources:** {summary from Phase 1.6}

---

## Salesforce Order of Execution (with this object's automation)

The numbers below follow Salesforce's documented order of execution for record save operations.
Items marked with ➤ indicate automation found on this object.

 1. System validation (required fields, field formats, field lengths)
 2. Before-save record-triggered flows {➤ if any found}
 3. Before triggers (Apex) {➤ if any found}
 4. System validation re-runs after before triggers
 5. Custom validation rules {➤ if any found}
 6. Duplicate rules
 7. Record saved to database (not yet committed)
 8. After triggers (Apex) {➤ if any found}
 9. Assignment rules
10. Auto-response rules
11. Workflow rules {➤ if any found}
12. Workflow field updates (can re-fire steps 2-8)
13. After-save record-triggered flows {➤ if any found}
14. Entitlement rules
15. Roll-up summary field calculations
16. Criteria-based sharing evaluation
17. Transaction committed

---

## Before-Save Flows

| # | Flow Label | Developer Name | Trigger Event | Entry Conditions | Key Elements | Version |
|---|---|---|---|---|---|---|
| 1 | {Label} | {DeveloperName} | Create / Update / Create or Update | {summary of entry conditions or "None (runs always)"} | {e.g., "3 assignments, 1 decision"} | v{N} |

_(None found)_ — if empty

---

## Before Triggers (Apex)

| # | Trigger Name | Contexts | Handler Class | Processor(s) | Recursion Guard |
|---|---|---|---|---|---|
| 1 | {TriggerName} | before insert, before update | {HandlerClass} | {Processor1}, {Processor2} | {Yes/No/Unknown} |

_(None found)_ — if empty

---

## Custom Validation Rules

| # | Rule Name | Active | Description | Error Location |
|---|---|---|---|---|
| 1 | {ValidationName} | Yes/No | {Description or first 100 chars of formula} | {Field name or "Top of page"} |

_(None found)_ — if empty

---

## After Triggers (Apex)

| # | Trigger Name | Contexts | Handler Class | Processor(s) | Recursion Guard |
|---|---|---|---|---|---|
| 1 | {TriggerName} | after insert, after update, after delete | {HandlerClass} | {Processor1}, {Processor2} | {Yes/No/Unknown} |

_(None found)_ — if empty

---

## Workflow Rules (LEGACY)

> :warning: **Legacy automation** — Salesforce recommends migrating workflow rules to Flow.
> Workflow field updates re-trigger before-save flows and before/after triggers (steps 2-8).

| # | Rule Name | Active | Evaluation Criteria | Field Updates | Email Alerts | Other Actions |
|---|---|---|---|---|---|---|
| 1 | {RuleName} | Yes/No | {criteria type} | {field1, field2} | {alert1} | {tasks, outbound msgs} |

_(None found)_ — if empty

---

## After-Save Flows

| # | Flow Label | Developer Name | Trigger Event | Entry Conditions | Key Elements | Version |
|---|---|---|---|---|---|---|
| 1 | {Label} | {DeveloperName} | Create / Update / Create or Update | {summary of entry conditions or "None (runs always)"} | {e.g., "2 record updates, 1 subflow, 1 decision"} | v{N} |

_(None found)_ — if empty

---

## Delete Automation

Automation that fires on record deletion or undeletion.

| # | Type | Name | Details |
|---|---|---|---|
| 1 | Before-Delete Flow | {name} | {trigger event, entry conditions} |
| 2 | Before-Delete Trigger | {name} | before delete context in {TriggerName} |
| 3 | After-Delete Trigger | {name} | after delete context in {TriggerName} |
| 4 | After-Undelete Trigger | {name} | after undelete context in {TriggerName} |

_(None found)_ — if empty

---

## Related Apex Classes

Classes whose names suggest a relationship with {OBJECT_API_NAME} (matched on `{OBJECT_BASE_NAME}`):

| # | Class Name | Category | Description / Purpose | Size | Last Modified |
|---|---|---|---|---|---|
| 1 | {ClassName} | Service | {inferred purpose} | {N} chars | {date} |
| 2 | {ClassName} | Batch | {inferred purpose} | {N} chars | {date} |
| 3 | {ClassName} | Test | {inferred purpose} | {N} chars | {date} |

**Category legend:** Service, Batch, Scheduler, Helper, Handler, Processor, Selector, Controller, Utility, Test, Other

_(None found)_ — if empty

---

## Conflict Analysis

Analyze the collected automation for potential conflicts, race conditions, and execution-order issues. Check each of the following scenarios:

### Check 1: Before-save flow + Before trigger coexistence
If BOTH before-save flows AND before triggers exist:
- **CONFLICT**: Both execute on the same record save. Before-save flow runs FIRST (step 2), then before trigger (step 3).
- The flow's field changes ARE visible to the trigger's `Trigger.new` records.
- If both set the same field, the trigger's value wins (it runs second).
- **Risk:** Developers may not realize the flow has already modified field values before the trigger sees them.
- **Recommendation:** Document which fields each automation modifies. Ensure no overlapping field assignments, or consolidate into one layer.

### Check 2: Workflow field update re-evaluation
If workflow rules with field updates exist AND (before-save flows OR before/after triggers exist):
- **CONFLICT**: Workflow field updates (step 12) cause Salesforce to re-evaluate and re-fire before-save flows (step 2) and before/after triggers (steps 3, 8).
- This means triggers and flows may execute TWICE per save operation.
- **Risk:** If triggers/flows lack recursion guards, this can cause:
  - Duplicate DML operations
  - Unexpected field overwrites
  - Governor limit consumption
- **Recommendation:** Ensure all triggers use a static recursion guard. Consider migrating workflow rules to a flow to eliminate re-evaluation.

### Check 3: Multiple after-save flows
If more than one after-save flow exists for the same trigger event (e.g., two flows on "after update"):
- **CONFLICT**: Salesforce does NOT guarantee execution order between multiple flows on the same object and event.
- **Risk:** If Flow A creates a child record and Flow B queries child records, Flow B may or may not see Flow A's records.
- **Recommendation:** Consolidate into a single after-save flow with decision elements, or ensure complete independence between flows.

### Check 4: Multiple before-save flows
If more than one before-save flow exists for the same trigger event:
- **CONFLICT**: Same as Check 3 — no guaranteed execution order.
- **Risk:** If both flows set the same field, the result is unpredictable.
- **Recommendation:** Consolidate into a single before-save flow.

### Check 5: Validation rule + before-save flow field defaults
If validation rules exist AND before-save flows exist that set field values:
- **CONFLICT**: Before-save flows run BEFORE custom validation rules (step 2 vs step 5).
- Fields set by the before-save flow WILL be evaluated by validation rules.
- **Risk:** If a validation rule requires a field to be blank on insert, but a before-save flow sets a default value, the validation will fail.
- **Recommendation:** Review validation rule formulas against before-save flow field assignments.

### Check 6: After trigger + after-save flow coexistence
If BOTH after triggers AND after-save flows exist:
- **CONFLICT**: After triggers run FIRST (step 8), then after-save flows (step 13).
- Both can perform DML on related records.
- **Risk:** The after-save flow may overwrite changes made by the after trigger on related records. Or the combined DML may approach governor limits.
- **Recommendation:** Document what each automation does. Ensure they operate on different related records, or consolidate.

### Check 7: Delete automation gaps
If delete triggers exist but no before-delete flow (or vice versa):
- **INFO**: Not necessarily a conflict, but worth noting for completeness.
- If the object has a recycle bin workflow, ensure after-undelete automation exists if after-delete automation cleans up related records.

### Output format for conflicts:

If conflicts are found:
```
### :warning: Potential Conflicts Detected

**1. Before-save flow and before trigger coexist (Steps 2 + 3)**
- Before-save flow `{FlowName}` and trigger `{TriggerName}` both fire on {event}.
- Flow runs first; trigger sees flow's changes.
- Review for overlapping field assignments.

**2. Workflow re-evaluation risk (Step 12 → Steps 2-8)**
- Workflow rule `{RuleName}` has field update `{FieldUpdateName}`.
- This will re-fire: {list of before-save flows and triggers}.
- Ensure recursion guards are in place.

...
```

If no conflicts are found:
```
### :white_check_mark: No Conflicts Detected

Automation layers on {OBJECT_API_NAME} are cleanly separated:
- {summary of why there are no conflicts, e.g., "Only after-save flows exist — no trigger/flow overlap"}
```

---

## Recommendations

Based on the full analysis, provide actionable recommendations:

1. **Migration opportunities**: If workflow rules exist, recommend migrating to Flow with specific guidance.
2. **Consolidation opportunities**: If multiple flows fire on the same event, recommend consolidation.
3. **Missing recursion guards**: If triggers exist without detected recursion guards and re-evaluation is possible, flag this.
4. **Missing test coverage**: If trigger/handler classes exist but no matching test class was found in related Apex classes, note this.
5. **Documentation gaps**: If cached context is missing for some automation types, recommend running the appropriate scan commands.
6. **Order of execution awareness**: If the automation spans multiple execution steps, provide a simplified execution sequence specific to this object.

Example:
```
### Recommendations

1. **Migrate workflow rules to Flow** — {N} workflow rule(s) found. Salesforce has deprecated workflow rules
   for new orgs. Migrating to an after-save flow would eliminate the re-evaluation cycle (step 12 → steps 2-8)
   and reduce automation complexity.

2. **Consolidate after-save flows** — {N} after-save flows fire on the same event. Merge into a single flow
   with decision elements to guarantee execution order and simplify troubleshooting.

3. **Add recursion guard** — Trigger `{TriggerName}` may fire twice due to workflow field update re-evaluation.
   Ensure the handler class uses a static Boolean guard (e.g., `TriggerHandler.hasRun`).

4. **Scan missing context** — Apex classes have not been scanned. Run `/sf-get-existing-org-object-context {ORG_ALIAS}`
   to populate the full automation picture.
```

---

## Simplified Execution Sequence

If automation exists in multiple execution steps, produce a condensed, object-specific execution sequence:

```
### Execution Sequence for {OBJECT_API_NAME} (on Create + Update)

  Insert/Update triggered
    │
    ├─ Step 2:  Before-save flow "{FlowName}" runs
    │           → Sets {FieldA}, {FieldB}
    │
    ├─ Step 3:  Before trigger "{TriggerName}" runs
    │           → Handler: {HandlerClass}
    │           → Processors: {Processor1} (before insert), {Processor2} (before update)
    │
    ├─ Step 5:  Validation rules evaluated
    │           → {Rule1}: checks {condition}
    │           → {Rule2}: checks {condition}
    │
    ├─ Step 7:  Record saved (not committed)
    │
    ├─ Step 8:  After trigger "{TriggerName}" runs
    │           → Processors: {Processor3} (after insert), {Processor4} (after update)
    │
    ├─ Step 11: Workflow rule "{RuleName}" evaluates
    │           → Field update: {FieldC} = {value}
    │           ⟳ RE-EVALUATION: Steps 2-8 re-fire
    │
    ├─ Step 13: After-save flow "{FlowName2}" runs
    │           → Creates {related record}, sends {notification}
    │
    └─ Step 17: Transaction committed
```
```

---

## Phase 4: Save Report (Optional)

After presenting the automation map to the user, ask:

"Would you like me to save this automation map to `context/{ORG_ALIAS}/audit/{OBJECT_API_NAME}_automation_map.md`?"

If the user confirms:

1. Ensure the directory `context/{ORG_ALIAS}/audit/` exists (create it if not).
2. Write the full automation map output to `context/{ORG_ALIAS}/audit/{OBJECT_API_NAME}_automation_map.md`.
3. Include a metadata header in the saved file:
   ```markdown
   <!-- Generated by /sf-audit-automation on {date} -->
   <!-- Org: {ORG_ALIAS} | Object: {OBJECT_API_NAME} -->
   <!-- Re-run this command to refresh -->
   ```
4. Confirm to the user: "Automation map saved to `context/{ORG_ALIAS}/audit/{OBJECT_API_NAME}_automation_map.md`."

---

## Important Notes

- **This command is read-only** — it never modifies org data or metadata.
- **Primary data source is cached context** — live queries are optional enrichment only.
- **The conflict analysis is the most valuable output** — it prevents automation bugs before they happen.
- **Run this before implementing any new trigger or flow** on an object to understand the existing automation landscape.
- **If context files are missing**, recommend running `/sf-get-existing-org-object-context {ORG_ALIAS}` first to populate the cache, then re-run this command.
- **Standard objects** (Account, Contact, Opportunity, Case, etc.) work the same as custom objects — just pass the API name without `__c`.
- **Managed package automation** is excluded by default (filtered by `NamespacePrefix = null` in all queries). Only org-specific automation is included.
