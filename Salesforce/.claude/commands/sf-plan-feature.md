---
description: "Generate a Salesforce-specific master plan with per-phase implementation plans. Analyzes org patterns, researches best practices, presents architecture decisions, and outputs Phase 1 as a self-contained plan file ready for /sf-execute. Use --next to generate subsequent phase plans."
argument-hint: [path-to-requirements-doc OR --next feature-name]
---

# SF Plan Feature

Generates a master plan directory with per-phase plan files for a Salesforce feature. Uses the PIV (Plan-Implement-Validate) loop model — only Phase 1 is generated upfront; subsequent phases are generated on-demand via `--next`, allowing learning from earlier phases to improve later plans.

**Usage:**
- `/sf-plan-feature projects/{alias}/{feature}/requirements.md` — Initial planning from a requirements doc
- `/sf-plan-feature --next {feature-name}` — Generate the next phase plan for an existing feature

**This command is read-only with respect to the org.** It only reads context files, loads skill references, performs research, and generates plan documents.

---

## Two Modes

### Mode 1: Initial Planning (default)
`/sf-plan-feature projects/{alias}/{feature}/requirements.md`

Reads requirements, analyzes the org, makes architecture decisions, determines phase count, generates a master plan and a Phase 1 plan file.

### Mode 2: Next Phase Generation
`/sf-plan-feature --next {feature-name}`

Reads the existing master plan, finds the next unstarted phase, and generates a self-contained phase plan file incorporating prior phase summaries and regression tests.

---

# MODE 1: INITIAL PLANNING

---

## Phase 0: Pre-Flight

### Step 0a: Parse Arguments

Check `$ARGUMENTS`:

If `$ARGUMENTS` starts with `--next`:
- Switch to **Mode 2** (see MODE 2 section below).
- The remainder of `$ARGUMENTS` after `--next` is the `{feature-name}`.
- **Stop Mode 1 processing.**

If `$ARGUMENTS` is empty or blank:
- Ask the user: "Please provide the path to the feature requirements document."
- Wait for response before proceeding.

If `$ARGUMENTS` is a file path:
- Treat it as the path to the requirements document.
- Verify the file exists. If not, report the error and stop.

### Step 0b: Read Requirements Document

Read the entire requirements document into memory. This file is the primary input for all subsequent phases.

If the file is empty or unreadable:
- Output: "Requirements document is empty or could not be read: `{path}`"
- **Stop.**

### Step 0c: Verify Org Context Exists

Read `context/INDEX.md`.

If the file does not exist or contains no orgs in the connected orgs table:
- Output: "No org context found. Run `/sf-init-project <alias>` first to connect an org and gather context."
- **Stop.**

If only **one** org is registered:
- Use that alias automatically.
- Display: `Using org: {alias}`

If **multiple** orgs are registered:
- Present the list to the user and ask which org this plan targets.
- Wait for user selection before proceeding.

### Step 0d: Check Context Freshness

Read `context/{alias}/META.md` and extract the `LAST_SCAN` timestamp.

Calculate the number of days since the last scan.

If the scan is **more than 7 days old**:
```
Warning: Context was last scanned {N} days ago ({LAST_SCAN}).
         The implementation plan may not reflect recent org changes.
         Consider running `/sf-check-context-freshness {alias}` before proceeding.
         Continuing with cached context...
```

Do NOT stop for stale context — warn and continue.

If `LAST_SCAN` is blank or missing:
```
Warning: No full scan timestamp found in META.md. Context may be incomplete.
         Consider running `/sf-get-existing-org-object-context {alias}` for a full scan.
         Continuing with whatever context is available...
```

### Step 0e: Create Output Directory

Derive `{feature-name}` from the requirements document path:
- If the path matches `projects/{alias}/{feature-name}/requirements.md`, extract the second-to-last path component as `{feature-name}`.
- If the path doesn't match that pattern, fall back to deriving `{feature-name}` from the PRD's Executive Summary title, converting to lowercase with hyphens (e.g., `invoice-automation`, `work-order-scheduling`).

The output directory is the same folder as the requirements document — no new directory creation is needed since `sf-create-feature-requirements-doc` already created it. Verify it exists:
```bash
mkdir -p projects/{alias}/{feature-name}/
```

Display: `Using plan directory: projects/{alias}/{feature-name}/`

---

## Phase 1: Read & Understand Requirements

### Step 1a: Parse the Requirements Document

Analyze the requirements document and extract the following sections (adapt to whatever structure the document uses):

- **Executive Summary** — High-level description of the feature
- **User Stories** — Who benefits and what they need
- **Affected Objects** — Which Salesforce objects are involved (existing or new)
- **Business Rules** — Logic, calculations, validations, conditions
- **Acceptance Criteria** — How to verify the feature works correctly
- **UI Requirements** — Any screens, pages, or layout changes needed
- **Integration Requirements** — External systems, APIs, managed packages

For each section, note what is explicitly stated vs. what must be inferred.

### Step 1b: Identify What Needs to Be Built

Categorize every requirement into implementation categories:

| Category | Examples |
|---|---|
| New Objects | Custom objects that don't exist in the org yet |
| New Fields | Fields to add to existing or new objects |
| Automation | Triggers, flows, scheduled jobs, process automation |
| Validation | Validation rules, formula constraints |
| UI Components | LWC, Aura, FlexiPages, page layouts, custom tabs |
| Security | Profile updates, permission sets, sharing rules, OWD changes |
| Data Architecture | Record types, custom metadata types, custom settings |
| Integrations | Callouts, named credentials, platform events, middleware |
| Reporting | Report types, dashboards, list views |

### Step 1c: Managed Package & Integration Question (CRITICAL)

**ASK THE USER:**
```
Before I analyze the org, I need to understand the integration landscape for this feature:

1. Does this feature involve integration with any managed packages installed in the org?
   (e.g., AcctSeed, Salesforce CPQ, Field Service Lightning, DocuSign, Conga, nCino)

2. Does this feature require communication with any external systems?
   (e.g., REST/SOAP APIs, middleware like MuleSoft or Informatica, external databases)

3. Are there any existing integrations that touch the same objects this feature affects?

Why this matters:
- Managed package objects have governor limit implications and their triggers fire in unpredictable order
- External integrations may require async patterns (callouts cannot be made from triggers)
- Some packages have their own automation frameworks that must be respected
- Cross-package field references require namespace prefixes
```

Wait for the user's response. Document the answer and carry it through all subsequent phases as `INTEGRATION_CONTEXT`.

---

## Phase 2: Codebase & Org Intelligence

Run the following three analyses. These are conceptually parallel — gather all information before drawing conclusions.

### Step 2a: Org Architecture Analysis

Load all relevant context inventories for the target org. For each inventory file, check if it exists before attempting to read — not all orgs will have all context areas populated.

**Core inventories to check:**

| Inventory File | What It Tells Us |
|---|---|
| `context/{alias}/objects/_inventory.md` | Which custom objects exist, their relationships |
| `context/{alias}/flows/_inventory.md` | Existing flows on all objects |
| `context/{alias}/apex/_inventory.md` | Existing triggers and their objects |
| `context/{alias}/apex-classes/_inventory.md` | Full Apex class inventory (handlers, processors, services, tests) |
| `context/{alias}/validation-rules/_inventory.md` | Existing validation rules by object |
| `context/{alias}/data-architecture/_inventory.md` | Record types, custom metadata types, custom settings |
| `context/{alias}/ui-components/_inventory.md` | LWC and Aura components |
| `context/{alias}/integration/_inventory.md` | Named credentials, remote site settings, auth providers |
| `context/{alias}/permissions/_inventory.md` | Permission sets, profiles |

**Domain-specific inventories (load if relevant to the feature):**

| Inventory File | When to Load |
|---|---|
| `context/{alias}/fsl/_inventory.md` | Feature touches Field Service objects |
| `context/{alias}/cpq/_inventory.md` | Feature touches CPQ objects |
| `context/{alias}/experience-cloud/_inventory.md` | Feature involves communities or portals |
| `context/{alias}/reporting/_inventory.md` | Feature includes reporting requirements |
| `context/{alias}/email-notifications/_inventory.md` | Feature involves email alerts or templates |
| `context/{alias}/assignment-rules/_inventory.md` | Feature involves lead/case assignment |

For each requirement, create a mapping:

```markdown
| Requirement | Existing Components | Net New Components |
|---|---|---|
| "Track invoice status" | Invoice__c exists, Status__c field exists | New: Invoice_Status_History__c object, 3 fields |
| "Auto-calculate totals" | Invoice_Line_Item__c exists | New: rollup trigger logic |
```

### Step 2b: Pattern Recognition

Analyze the org's established patterns by reading the inventory files:

**Naming conventions:**
- Read the `## Detected Naming Conventions` section from each inventory file that has one.
- Note prefixes, suffixes, casing patterns, abbreviation standards.
- All new metadata names in the plan must follow these conventions.

**Automation style analysis:**
- Count all triggers from `context/{alias}/apex/_inventory.md`
- Count all record-triggered flows from `context/{alias}/flows/_inventory.md`
- Calculate automation weight per object:
  - `trigger weight = trigger count + related apex class count`
  - `flow weight = flow count`
- Present findings per object: "Invoice__c has 1 trigger but 14 related Apex classes vs 2 flows"
- Determine the org's automation profile:
  - **Flow-heavy:** >70% flows — lean toward flows for new automation
  - **Trigger-heavy:** >70% triggers — lean toward triggers for consistency
  - **Mixed:** No clear dominance — choose per-requirement based on complexity

**Architecture patterns:**
- Check for existing interfaces: `TriggerHandlerInterface`, `RecordProcessorInterface`, `ITriggerHandler`
- Check for base classes: `TriggerHandler`, `TriggerFramework`
- Check for service layer pattern: classes named `*Service`, `*Selector`, `*Domain`
- Check for utility classes: `*Utils`, `*Helper`, `*Constants`
- Note these patterns — the plan must follow them, not introduce competing ones.

### Step 2c: Existing Automation Audit

For **every object** mentioned in the requirements (existing objects only), perform a full automation audit:

**For each affected object, compile:**

1. **Triggers:**
   - Trigger name, contexts (before/after insert/update/delete/undelete)
   - Handler class(es) called by the trigger
   - Processor/service classes called by the handler
   - Test classes covering the trigger stack
   - Total related Apex class count

2. **Record-Triggered Flows:**
   - Flow name, trigger event (create/update/create+update/delete)
   - Entry conditions (if any)
   - Whether it runs before-save or after-save

3. **Legacy Automation:**
   - Workflow rules and their field updates
   - Process Builder processes (if any remain)

4. **Validation Rules:**
   - Rule name, formula, error message
   - Active/inactive status

5. **Order of Execution mapping** for each object (per Salesforce documentation):
   - System validations > before-save flows > before triggers > custom validations/VRs > after triggers > after-save flows > workflow rules > etc.

**Calculate automation weight per object:**

```markdown
### Automation Weight: {ObjectName__c}

| Type | Count | Details |
|---|---|---|
| Triggers | 1 | InvoiceTrigger |
| Related Apex Classes | 14 | 1 handler, 4 processors, 3 services, 6 test classes |
| Record-Triggered Flows | 2 | Invoice_Set_Defaults (before-save), Invoice_Notify_Owner (after-save) |
| Validation Rules | 5 | 4 active, 1 inactive |
| Workflow Rules | 0 | — |
| **Total Weight** | **22** | Trigger stack is significantly more complex than flow layer |
```

This weight informs whether adding more trigger logic is manageable or whether the trigger stack is already overloaded.

---

## Phase 3: Architecture Decision Research

For EACH piece of business logic identified in the requirements, perform the following analysis.

### Step 3a: Load Skill Decision Guides

Read the decision guides from the following skill files. Each skill contains a decision guide section that provides criteria for when to use that approach.

| Skill File | Decision Guide Content |
|---|---|
| `skills/sf-flows/SKILL.md` | Flow vs Trigger decision criteria, order of execution implications |
| `skills/sf-trigger-patterns/SKILL.md` | Trigger architecture, handler pattern, bulkification requirements, recursion prevention |
| `skills/sf-validation-rules/SKILL.md` | VR formula patterns, when VR is sufficient vs. when code is needed |
| `skills/sf-ui-components/SKILL.md` | LWC vs Aura vs Visualforce decision guide, Screen Flow for admin-maintained UI |
| `skills/sf-data-architecture/SKILL.md` | Custom Metadata Type vs Custom Settings, Record Types vs picklist-based branching |
| `skills/sf-apex-classes/SKILL.md` | Async decision guide: Batch vs Queueable vs Future vs Platform Events |

Read each file. If a skill file does not exist, note it and proceed — not all skills may be installed.

### Step 3b: Analyze Org's Existing Patterns

Apply the pattern recognition results from Phase 2b to weight decisions:

- **If the org is 80%+ triggers:** Weight toward triggers for consistency. Introducing flows into a trigger-heavy org creates split-brain maintenance burden.
- **If a trigger handler interface exists:** All new triggers MUST use it. Do not introduce a competing pattern.
- **If a service layer pattern exists:** New business logic classes must follow the same layering.
- **Exception:** Even in trigger-heavy orgs, **simple field defaults** (setting a default value on insert) are better as before-save flows — they don't consume DML, are visible to admins, and Salesforce explicitly recommends this pattern.

**Apex complexity factor:**
Do not just count triggers vs. flows. A single trigger may route through a handler to dozens of processor and service classes. Factor in:
- Classes directly related to each trigger (handler, processors, services, helpers)
- Total lines of code in the trigger stack (if available)
- Test class coverage

This reveals whether the trigger architecture is simple (1 trigger > 1 handler > 1 processor) or deeply layered (1 trigger > 1 handler > 5 processors > 3 services > 2 utilities). A deeply layered stack means adding trigger logic is costlier than it appears.

### Step 3c: Live Research on Best Practices

**IMPORTANT:** Salesforce has an extreme number of customization options — far more than what these skills cover. The skills represent common approaches but are NOT exhaustive.

During research, actively look for community patterns, platform features, and approaches that may be better than standard options. Be open to recommending approaches not covered by existing skills.

For each business logic requirement, research:

1. **Governor limit implications:**
   - SOQL query limits (100 sync / 200 async)
   - DML statement limits (150)
   - Heap size (6MB sync / 12MB async)
   - CPU time (10s sync / 60s async)
   - How does each approach consume these limits in bulk scenarios?

2. **Scalability:**
   - How does the approach handle bulk operations (200+ records via Data Loader)?
   - What happens at 10,000 records? 100,000?
   - Does it need to be bulkified? (Apex yes, flows auto-bulkify in many cases)

3. **Maintainability:**
   - Admin-maintainable (flow, validation rule) vs. developer-required (trigger, LWC)?
   - Who will maintain this after initial deployment?
   - Is the team Apex-capable or admin-only?

4. **Platform direction:**
   - Salesforce is pushing flows over triggers for most use cases
   - Flow Builder improvements each release (Spring/Summer/Winter)
   - But complex cross-object logic with error handling still benefits from Apex

5. **Community best practices and alternative approaches:**
   - Research Salesforce StackExchange, Trailhead, Salesforce Architects blog
   - Look for patterns not covered by existing skills:
     - Change Data Capture for async processing
     - Dynamic Forms for flexible page layouts
     - Custom Metadata-driven frameworks for configurable logic
     - Invocable Actions for flow-callable Apex
     - Orchestrator for multi-step processes
     - Platform Events for decoupled architectures

6. **Async processing patterns — evaluate when needed:**

   | Pattern | Best For | Key Characteristics |
   |---|---|---|
   | **Queueable** | Async with state, chained processing | Supports callouts (with `Database.AllowsCallouts`), can chain jobs, passes complex objects |
   | **Batchable** | Millions of records, controlled chunks | Separate governor limits per `execute()`, `start/execute/finish` lifecycle |
   | **Future Methods** | Simple fire-and-forget callouts from triggers | Lightweight, no chaining, no complex state, `@future(callout=true)` |
   | **Platform Events** | Decoupled processing, publish/subscribe | Separate transaction = separate limits, retry-capable, event-driven |

   Not needed for most features, but critical when:
   - The feature involves external callouts (callouts are prohibited in trigger context)
   - Object relationships are deep and processing is expensive
   - Managed packages consume significant governor limits in the same transaction
   - Data volumes exceed what synchronous processing can handle

### Step 3d: Produce Decision Matrix

For EACH piece of business logic identified in the requirements, produce a decision matrix:

```markdown
### Decision: {Requirement Description}

**Context:** {Brief description of what this logic does}
**Affected Object(s):** {Object(s) involved}
**Automation Weight:** {From Phase 2c — e.g., "Invoice__c has 22 automation components, trigger-heavy"}

| Approach | Pros | Cons | Org Fit | Recommendation |
|---|---|---|---|---|
| Before-Save Flow | No DML consumed, admin-maintainable, SF-recommended for defaults | Limited to triggering record only, no cross-object updates | Org has {N} similar before-save flows | Recommended |
| Before-Insert Trigger | Full Apex power, unit testable, integrates with handler pattern | Adds complexity to trigger stack ({N} related classes), requires developer | Org uses {HandlerPattern} | Alternative |
| Validation Rule | Simplest implementation, no code, immediate feedback | Can only block saves, cannot modify data | Org has {N} VRs on this object | Not suitable (need to modify data) |
| Queueable Apex | Separate governor limits, supports callouts | Eventual consistency, harder to test, user doesn't see immediate result | Only if integration needed | Conditional |

**Selected approach:** {Approach} — {One-sentence rationale referencing org data}
```

Produce one matrix per business logic requirement. Every matrix must reference org-specific data (component counts, pattern names, existing automation weights), not generic advice.

---

## Phase 4: Clarifying Questions (CRITICAL)

Based on the analysis from Phases 2 and 3, compile a list of targeted questions for the user. These questions must be specific and present concrete options — never ask open-ended questions.

### Types of Questions to Ask

**Architecture choices:**
```
Your org primarily uses triggers ({trigger_count} triggers vs {flow_count} flows = {percentage}% trigger-based).
For this feature's automation, should I:
  A) Follow the trigger pattern for consistency (recommended for complex logic)
  B) Use flows for simpler logic pieces, triggers for complex ones (hybrid)
  C) Use flows wherever possible (aligns with Salesforce direction)
```

**Trade-off decisions:**
```
The "{requirement}" calculation could be implemented as:
  A) Roll-Up Summary field (simplest, but only works for master-detail relationships)
  B) Before-save flow with Get Records (flexible, admin-maintainable, but adds SOQL queries)
  C) After-save trigger processor (most powerful, integrates with existing {HandlerClass}, but adds to trigger stack of {N} classes)

Given approximately {N} records on this object, I recommend option {X} because {reason}.
Does this align with your preference?
```

**Approach confirmations:**
```
For {object}, I recommend:
  - Before-save flow for field defaults (no DML, admin-visible)
  - After-save trigger processor for related record updates (integrates with existing InvoiceTriggerHandler)
  - Validation rule for the "{business rule}" constraint (simplest enforcement)

This splits automation by complexity level and follows your org's existing patterns. Agree?
```

**Edge cases:**
```
The requirements mention "{scenario}". What should happen when:
  A) {Edge case 1} — Option A: {behavior}, Option B: {behavior}
  B) {Edge case 2} — Option A: {behavior}, Option B: {behavior}
```

**UI approach decisions:**
```
The "{requirement}" needs user input. Options:
  A) Screen Flow — admin-configurable, faster to build, embeddable in Lightning pages
  B) LWC — fully custom UX, richer interactions, requires developer for changes
  C) Quick Action with Flow — minimal UI, launched from record page button

For this use case, I recommend {X} because {reason}.
```

**WAIT for ALL answers before proceeding to Phase 5.** Do not generate the plan until all clarifying questions are resolved.

---

## Phase 5: Determine Phase Count & Scope

Determine how many PIV loop phases this feature needs based on complexity.

### Scoring

- New objects/fields — data model phase (+1 per ~3 objects, merge with security if small)
- Permissions/sharing — security phase (merge with data model if just Admin profile)
- Trigger stacks/flows/VRs — business logic phase(s) (+1 per complex trigger or flow group)
- LWC/FlexiPages/layouts — UI phase
- Validation rules — bundle with the phase that creates the fields they validate

### Merge Rules

- <5 fields on existing objects + Admin profile update only — single phase
- Security-only changes — merge into data model phase
- Never merge business logic with UI (different failure modes)
- VRs go in same phase as automation they interact with

### Phase Count

- **Minimum:** 1 phase (simple change)
- **Typical:** 2-4 phases
- **Maximum:** no hard cap

### Present Phase Breakdown

Present the phase breakdown to the user for confirmation:

```
Feature will be implemented in {N} phases:
  Phase 1: Data Model — {scope description}
  Phase 2: Business Logic — {scope description}
  Phase 3: UI — {scope description}
```

Wait for user confirmation or adjustments before proceeding.

---

## Phase 6: Generate Master Plan

Write `projects/{alias}/{feature-name}/master-plan.md` with the following sections:

### Section 1: Header

```markdown
# Master Plan: {Feature Name}

**Generated:** {timestamp}
**Org:** {alias} ({instanceUrl})
**Requirements Source:** {path-to-requirements-doc}
**Context Freshness:** Last scanned {N} days ago ({LAST_SCAN})
**Integration Context:** {Summary of user's answer from Phase 1c}
**Status:** In Progress
```

### Section 2: Architecture Decisions

Include the final decision matrices from Phase 3d, updated with user's answers from Phase 4.

```markdown
## Architecture Decisions

### Decision 1: {Requirement}
**Selected:** {Approach}
**Rationale:** {Why, referencing org data and user preference}
**Skill Reference:** `skills/{skill-name}/SKILL.md`

### Decision 2: ...
```

### Section 3: Naming Conventions

```markdown
## Naming Conventions

Based on org patterns detected in context inventories:

| Element | Convention | Example |
|---|---|---|
| Objects | {detected pattern} | {example from plan} |
| Fields | {detected pattern} | {example from plan} |
| Apex Classes | {detected pattern} | {example from plan} |
| Flows | {detected pattern} | {example from plan} |
| Permission Sets | {detected pattern} | {example from plan} |
| LWC | {detected pattern} | {example from plan} |
```

### Section 4: Phase Registry

```markdown
## Phase Registry

| Phase | Name | Scope | Plan File | Status |
|---|---|---|---|---|
| 1 | {name} | {scope description} | `phase-1-{name}.md` | Plan Generated |
| 2 | {name} | {scope description} | — | Not Started |
| 3 | {name} | {scope description} | — | Not Started |
```

All phases are "Not Started" except Phase 1, which is "Plan Generated".

### Section 5: Regression Test Registry

```markdown
## Regression Test Registry

This section accumulates test classes and their verification commands as phases complete.
Tests listed here MUST pass before any subsequent phase is considered complete.

| Test Class | Phase Added | Verification Command | Status |
|---|---|---|---|
```

Empty initially. Populated as phases complete.

### Section 6: Prior Phase Summaries

```markdown
## Prior Phase Summaries

This section is populated as phases complete, providing context for subsequent phases.
```

Empty initially. Each completed phase adds a summary here.

### Section 7: Acceptance Criteria Tracking

```markdown
## Acceptance Criteria Tracking

| # | Acceptance Criterion | Phase(s) | Status |
|---|---|---|---|
| AC-1 | {Criterion from requirements} | Phase 1, Phase 2 | Not Started |
| AC-2 | {Criterion from requirements} | Phase 3 | Not Started |
```

Maps each acceptance criterion to the phase(s) that address it.

---

## Phase 7: Generate Phase 1 Plan

Write `projects/{alias}/{feature-name}/phase-1-{name}.md` as a **SELF-CONTAINED** document. An implementer should need nothing beyond this file and the referenced skills.

### Section 1: Header

```markdown
# Phase 1: {Phase Name}

**Feature:** {Feature Name}
**Org:** {alias}
**Phase:** 1 of {M}
**Master Plan:** `projects/{alias}/{feature-name}/master-plan.md`
**Generated:** {timestamp}
```

### Section 2: Prior Phase Summary

```markdown
## Prior Phase Summary

This is Phase 1 — no prior phases.
```

### Section 3: Phase Goals

```markdown
## Phase Goals

- {Goal 1 — what this phase accomplishes}
- {Goal 2}
- {Goal 3}
```

### Section 4: Success Criteria

```markdown
## Success Criteria

| # | Criterion | Verification Method | Tier |
|---|---|---|---|
| SC-1 | {criterion} | {how to verify} | Tier 1 (Unit Test) |
| SC-2 | {criterion} | {how to verify} | Tier 2 (E2E) |
| SC-3 | {criterion} | {how to verify} | Tier 3 (User Review) |
```

### Section 5: Skill & Context References

```markdown
## Skill & Context References

Load these before executing:
- `skills/sf-trigger-patterns/SKILL.md` — for {reason}
- `skills/sf-data-architecture/SKILL.md` — for {reason}
- `context/{alias}/objects/{ObjectName__c}.md` — existing object context
```

### Section 6: Task List

```markdown
## Task List

### TASK 1: {Component Name}
- **What:** {description}
- **File:** `force-app/main/default/{metadata-type}/{filename}`
- **Deploy:** `sf project deploy start --source-dir {path} --target-org {alias}`
- **Validate:** `sf project deploy start --source-dir {path} --target-org {alias} --dry-run`
- **Pattern Reference:** `skills/{skill}/SKILL.md` — Section: {section}
- **Gotchas:** {Specific warnings — deploy order dependencies, retrieve-first requirements}

### TASK 2: {Component Name}
...
```

Every TASK must include: what to create/modify, file path, deploy command, validate command, pattern reference, and gotchas.

For **every new custom field on any object**, the task list MUST include these sub-tasks as explicit named TASK items immediately after the field deploy task — never leave them implied by a skill reference or bundled into the field task itself:

**MANDATORY sub-tasks for each new field (in this order):**

**Sub-task A — Profile FLS:**
- What: Retrieve Admin profile, add `<fieldPermissions>` block (read+edit for editable fields, read-only for formula/rollup fields), deploy
- Retrieve: `sf project retrieve start --metadata "Profile:Admin" --target-org {alias}`
- Deploy: `sf project deploy start --metadata "Profile:Admin" --target-org {alias} --wait 10`
- GOTCHA: Never add fieldPermissions for standard fields (Name, OwnerId, etc.) — custom fields only
- GOTCHA: Check for existing entries before appending — do not duplicate blocks already in the file

**Sub-task B — Page Layout(s):**
- What: For EVERY layout that exists on the object, retrieve the layout, add the new field to an appropriate section, deploy
- Discover all layouts on an object via Tooling API: `sf data query --query "SELECT Layout.Name FROM ProfileLayout WHERE TableEnumOrId = '{ObjectApiName}'" --use-tooling-api --target-org {alias}`
- OR retrieve all layouts at once: `sf project retrieve start --metadata "Layout:{ObjectApiName}" --target-org {alias}`
- GOTCHA: If the org uses managed packages, layouts may require namespace prefixes in their retrieve name even though the Tooling API omits them — see `skills/sf-cli/SKILL.md` → "Managed Package Layout Retrieve" for the correct pattern
- GOTCHA: Always retrieve before editing — never build layouts from scratch or you will lose related lists, quick actions, and managed sections

**Sub-task C — Picklist Record Type Availability (picklist fields only):**
- Apply ONLY when the new field type is Picklist or MultiselectPicklist
- Check whether the object has Record Types: `sf data query --query "SELECT DeveloperName FROM RecordType WHERE SobjectType = '{ObjectApiName}'" --target-org {alias}`
- If NO record types exist: mark this sub-task N/A in the plan
- If YES record types exist: add a named TASK to verify each picklist value is enabled for every applicable Record Type. Retrieve the object metadata, inspect `<picklistValues>` blocks inside each `<recordTypeInfos>`, and deploy any required RecordType updates
- CRITICAL: If the picklist field references a Global Value Set, retrieve and deploy the GVS + ALL RecordTypes that restrict its values in a single deploy operation

For triggers, always include:
- Check for existing trigger on the object (never create a second trigger)
- Handler class and processor class file paths
- Test class file path and minimum test scenarios
- Recursion prevention approach

For flows, always include:
- Flow type (record-triggered before-save, after-save, screen, scheduled, etc.)
- Entry conditions
- Whether it needs to be added to a Lightning page

### Section 7: Testing Framework

```markdown
## Testing Framework

### Testing Tier Applicability

**Not every phase needs unit tests.** Only write Apex tests for Apex classes and Flows. Declarative-only phases skip Tier 1 test generation (but still run regression).

| Phase Content | Tier 1 (Unit Tests) | Tier 2 (E2E) | Tier 3 (User Review) |
|---|---|---|---|
| Objects, fields, layouts, FlexiPages | SKIP | YES | YES |
| Validation rules | SKIP | YES — verify rules fire | YES |
| Permission sets, profiles, sharing rules | SKIP | YES — verify access | YES |
| Apex triggers, handlers, processors | YES | YES | YES |
| Batch, Schedulable, Queueable | YES | YES | YES |
| Flows (record-triggered, screen) | YES — test via DML that triggers flow | YES | YES |
| LWC components | SKIP (use Jest) | YES | YES |

### Tier 1: Unit Tests

**Applies to this phase:** {YES — this phase includes Apex/Flows / NO — declarative only, skip to Tier 2}

**If YES:**

**One test class per Apex class** — consolidate if multiple were created during development.

| Test Class | Tests For | Scenarios |
|---|---|---|
| {TestClassName} | {ApexClassName} | Happy path, Bulk 200, Negative, Null handling |

**Flow testing:** Test via Apex DML that triggers the flow, then assert outcomes. Don't test flow structure — test the RESULT.

**VR testing:** Only if VRs interact with Apex logic. Verify VRs in Tier 2 (E2E) by default, not in Apex tests.

**Regression tests from prior phases:** None (Phase 1) / {list from master plan registry}

**Execution:**
- Run phase tests: `sf apex run test --class-names {TestClass1} {TestClass2} --target-org {alias} --result-format human`
- Run all regression: `sf apex run test --test-level RunLocalTests --target-org {alias}`

**If NO (declarative-only):**
- Skip test class generation
- Still run regression: `sf apex run test --test-level RunLocalTests` to catch breakage from declarative changes

**Gate criteria:** All tests pass (new + regression), minimum 85% coverage per new class, 75% org-wide.

### Tier 2: E2E Testing

**Approach:** Browser automation primary (agent-browser), CLI fallback if MFA/SSO blocks.

| # | Scenario | Steps | Expected Result | Verification Query |
|---|---|---|---|---|
| E2E-1 | {scenario} | {step-by-step} | {expected} | {SOQL or UI check} |

### Tier 3: User Review

**Code review checklist:**
- [ ] Bulk-safe (no SOQL/DML in loops)
- [ ] Governor limits respected
- [ ] Follows org naming conventions
- [ ] Follows org architecture patterns
- [ ] Error handling present

**Declarative review checklist:**
- [ ] Flow/VR logic matches requirements
- [ ] Field labels are user-friendly
- [ ] Help text populated on custom fields

**User E2E testing checklist:**
- [ ] {User-facing scenario 1}
- [ ] {User-facing scenario 2}
```

### Section 8: Phase Completion Protocol

```markdown
## Phase Completion Protocol

When all tasks and tests pass:

1. **Update master plan Phase Registry:** Set Phase 1 status to "Complete"
2. **Add to Regression Test Registry:** List all test classes from this phase
3. **Write Phase Summary:** Add to Prior Phase Summaries in master plan:
   ```
   ### Phase 1: {Name} — Complete
   - Deployed: {list of components}
   - Test classes: {list}
   - Key decisions: {any runtime decisions made during implementation}
   - Known issues: {any issues discovered}
   ```
4. **Update Acceptance Criteria:** Mark any fully addressed ACs as "Complete"
5. **Commit:** Stage and commit all source files and updated plan files
```

---

## Phase 8: Output

After saving both plan files, display a summary:

```
==================================================
  Master Plan: {Feature Name}
==================================================

  Org:              {alias}
  Phases:           {N} total

  Architecture Decisions:
    - {Decision 1 summary}
    - {Decision 2 summary}
    - {Decision 3 summary}

  Phase Breakdown:
    Phase 1: {Name} — {N} tasks [PLAN GENERATED]
    Phase 2: {Name} — Not Started
    Phase 3: {Name} — Not Started

==================================================

  Master plan: projects/{alias}/{feature-name}/master-plan.md
  Phase 1 plan: projects/{alias}/{feature-name}/phase-1-{name}.md

  Next step: Run `/sf-execute projects/{alias}/{feature-name}/phase-1-{name}.md` to begin Phase 1.

==================================================
```

---

# MODE 2: NEXT PHASE GENERATION (`--next`)

`/sf-plan-feature --next {feature-name}`

Generates the next phase plan for an existing feature, incorporating lessons learned from prior phases.

---

## Step 1: Load Master Plan

Resolve `{alias}` from `context/INDEX.md` (same logic as Mode 1 Phase 0c — use the single registered org, or ask if multiple).

Read `projects/{alias}/{feature-name}/master-plan.md`.

If the file does not exist:
- Output: "No master plan found at `projects/{alias}/{feature-name}/master-plan.md`. Run `/sf-plan-feature projects/{alias}/{feature-name}/requirements.md` first."
- **Stop.**

Find the next phase with status "Not Started" in the Phase Registry table.

If all phases are "Complete" or "Plan Generated":
- Check if any phase is "Plan Generated" but not "Complete":
  - Output: "Phase {N} plan has been generated but not yet executed. Run `/sf-execute projects/{alias}/{feature-name}/phase-{N}-{name}.md` first."
- If all phases are "Complete":
  - Output: "All phases complete! Feature `{feature-name}` is fully implemented."
- **Stop.**

## Step 2: Build Phase Context

From the master plan, gather:

- **Prior Phase Summaries** — what has already been built, what decisions were made at runtime
- **Regression Test Registry** — all test classes that must still pass
- **Architecture Decisions** — the decisions made during initial planning
- **Phase scope** — from the Phase Registry, what this phase covers
- **Acceptance Criteria** — which ACs this phase addresses

## Step 3: Generate Phase Plan

Write `projects/{alias}/{feature-name}/phase-{N}-{name}.md` using the same structure as Phase 7 above, but with these differences:

### Prior Phase Summary

Populated from the master plan's Prior Phase Summaries section:

```markdown
## Prior Phase Summary

### Phase 1: {Name} — Complete
- Deployed: {list of components}
- Test classes: {list}
- Key decisions: {any runtime decisions}
- Known issues: {any discovered issues}

### Phase 2: {Name} — Complete
...
```

### Regression Tests

Include all tests from the Regression Test Registry:

```markdown
### Regression Tests (from prior phases)

These tests MUST pass before this phase is considered complete:

| Test Class | Phase | Command |
|---|---|---|
| {TestClass1} | Phase 1 | `sf apex run test --class-names {TestClass1} --target-org {alias} --result-format human` |
| {TestClass2} | Phase 2 | `sf apex run test --class-names {TestClass2} --target-org {alias} --result-format human` |

**Run all regression tests:**
`sf apex run test --class-names {TestClass1} {TestClass2} ... --target-org {alias} --result-format human`
```

### Tasks

Tasks are specific to this phase's scope from the Phase Registry.

## Step 4: Update Master Plan

Update `projects/{alias}/{feature-name}/master-plan.md`:
- Set the phase status to "Plan Generated" in the Phase Registry
- Add the plan file path to the Phase Registry

## Step 5: Output

```
==================================================
  Phase {N}: {Name}
==================================================

  Feature:          {Feature Name}
  Tasks:            {N} tasks
  Regression Tests: {N} from prior phases

  Phase {N} plan: projects/{alias}/{feature-name}/phase-{N}-{name}.md

  Next step: Run `/sf-execute projects/{alias}/{feature-name}/phase-{N}-{name}.md`

==================================================
```

---

# Notes

- **Phase 1 only is generated upfront; subsequent phases on-demand.** This allows learning from earlier phases to improve later plans.
- **Each phase plan is self-contained** — can be executed in a fresh context window with no bloated context.
- **The master plan is the single source of truth** for progress, regression tests, and phase summaries.
- **Architecture decisions are made ONCE** (in initial planning) and stored in the master plan.
- **Phase count is flexible** — simple features = 1 phase, complex = 3-5+.
- **Test class consolidation:** target ONE test class per Apex class to prevent bulk test class accumulation.
- This command is **read-only** with respect to the org — it only reads context and generates documents.
- Decision matrices must show **org-specific data** (component counts, pattern names, automation weights), not generic advice.
- Phase 4 questions must present **concrete options with recommendations**, not open-ended prompts.
- If a skill file referenced in Phase 3a does not exist, note it in the plan as a gap but do not stop execution.
- The `INTEGRATION_CONTEXT` from Phase 1c must influence async pattern decisions in Phase 3 — if external callouts are needed, synchronous trigger logic is not an option.
