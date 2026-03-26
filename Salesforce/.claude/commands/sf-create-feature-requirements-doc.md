---
description: "Formalize a conversation into a Salesforce feature requirements document with user stories, affected objects, business rules, and acceptance criteria. Uses org context to identify existing architecture and potential conflicts."
argument-hint: [feature-description-or-path-to-spec]
---

# SF Create Feature Requirements Document

Formalize the current conversation's requirements into a structured feature requirements document. This captures the WHAT (business requirements, user stories, acceptance criteria) — not the HOW (technical implementation, which is handled by `/sf-plan-feature`).

**Usage:**
- `/sf-create-feature-requirements-doc "Add invoice tracking to Work Orders"` — inline description
- `/sf-create-feature-requirements-doc path/to/feature-spec.md` — file-based spec
- `/sf-create-feature-requirements-doc` — will prompt for feature description

**This command is read-only with respect to the org.** It only reads cached context files and generates a document.

**Output:** `projects/{alias}/{feature-name}/requirements.md`
**Next step:** `/sf-plan-feature projects/{alias}/{feature-name}/requirements.md`

---

## Phase 0: Pre-Flight

### Step 0a: Verify Context Exists

Read `context/INDEX.md`.

If the file does not exist or contains no orgs in the connected orgs table:
- Output: "No org context found. Run `/sf-init-project <alias>` first."
- **Stop.**

If the file exists, extract the list of registered orgs and their `Last Full Scan` timestamps.

### Step 0b: Determine Org Alias

If only **one** org is registered in `context/INDEX.md`:
- Use that alias automatically
- Display: `Using org: {alias}`

If **multiple** orgs are registered:
- Present the list to the user and ask which org this PRD is for
- Wait for user selection before proceeding

### Step 0c: Check Context Freshness

Read `context/{alias}/META.md` and extract the `LAST_SCAN` timestamp.

Calculate the number of days since the last scan.

If the scan is **more than 7 days old**:
```
⚠️  Context was last scanned {N} days ago ({LAST_SCAN}).
    Results may not reflect recent org changes.
    Consider running `/sf-check-context-freshness {alias}` after generating the PRD.
    Continuing with cached context...
```

Do NOT stop for stale context — warn and continue.

If `LAST_SCAN` is blank or missing:
```
⚠️  No full scan timestamp found in META.md. Context may be incomplete.
    Consider running `/sf-get-existing-org-object-context {alias}` for a full scan.
    Continuing with whatever context is available...
```

### Step 0d: Extract Org Metadata

From `context/{alias}/META.md`, extract:
- `instanceUrl` — the org's instance URL
- `orgId` — the org's ID
- `alias` — the org alias
- `LAST_SCAN` — when context was last gathered

Store these for inclusion in the PRD header.

---

## Phase 1: Gather Feature Requirements

### Step 1a: Obtain Raw Requirements

Check `$ARGUMENTS`:

**If `$ARGUMENTS` is a file path** (contains `/` or ends in `.md`, `.txt`, `.yaml`, `.yml`):
- Read the file at the given path
- If the file does not exist, output: "File not found: {path}" and **stop**
- Use the file contents as the raw requirements text

**If `$ARGUMENTS` is a text description** (non-empty string that is not a file path):
- Use the text directly as the raw requirements

**If `$ARGUMENTS` is empty or not provided:**
- Ask the user: "Describe the feature you want to build. Include as much detail as possible about what it should do, who will use it, and which objects are involved."
- Wait for the user's response
- Use the response as the raw requirements text

### Step 1b: Parse Explicit Object References

Scan the raw requirements text for:

1. **Custom objects** — any token matching the pattern `*__c` (case-insensitive)
   - Example: `Work_Order__c`, `Invoice__c`, `Payment_Line__c`
2. **Custom platform events** — any token matching `*__e`
   - Example: `Invoice_Created__e`
3. **Standard objects** — match against the known standard object list:
   - Account, Contact, Case, Opportunity, Lead, Task, Event, User, Product2, Pricebook2, PricebookEntry, Order, OrderItem, Contract, Quote, QuoteLineItem, Campaign, CampaignMember, ContentDocument, ContentVersion, FeedItem, ServiceAppointment, WorkOrder, WorkOrderLineItem, Asset, Entitlement, ServiceContract, ServiceTerritory, ServiceResource, OperatingHours, ResourcePreference, SkillRequirement
4. **Custom metadata types** — any token matching `*__mdt`

Build the list: `affected_objects[]`

### Step 1c: Parse Implicit Object Hints

Scan the raw requirements text for business terms that commonly map to Salesforce objects. Check if any of these terms appear and cross-reference against the objects inventory (`context/{alias}/objects/_inventory.md`) to find matches:

Common mappings to check:
- "invoice" / "billing" → look for `Invoice*` objects
- "payment" → look for `Payment*` objects
- "work order" / "service" → `WorkOrder`, `ServiceAppointment`
- "account" / "customer" / "client" → `Account`
- "contact" / "person" → `Contact`
- "opportunity" / "deal" / "pipeline" → `Opportunity`
- "case" / "support" / "ticket" → `Case`
- "quote" / "proposal" → `Quote`, `SBQQ__Quote__c`
- "product" / "catalog" → `Product2`, `SBQQ__Product__c`
- "territory" / "scheduling" → `ServiceTerritory`, `ServiceAppointment`
- "asset" / "equipment" → `Asset`
- "subscription" / "renewal" → look for `Subscription*` objects

For each match found in the inventory, add to `affected_objects[]` if not already present.

Present the detected objects to the user for confirmation:
```
Detected objects relevant to this feature:
  - {ObjectName} (explicit reference)
  - {ObjectName} (inferred from "{business term}")

Does this look right? Any objects to add or remove?
```

Wait for user confirmation. Update `affected_objects[]` based on feedback.

### Step 1d: Parse Feature Type Hints

Scan the raw requirements for keywords that indicate what types of Salesforce components are needed:

| Keywords Found | Feature Type |
|---|---|
| "create", "new object", "new field", "data model" | Data Model Changes |
| "trigger", "before save", "after save", "DML" | Apex Triggers |
| "flow", "automation", "auto-create", "auto-update" | Flows |
| "validation", "required", "must be", "cannot be" | Validation Rules |
| "permission", "access", "security", "sharing", "visibility" | Permissions & Security |
| "page", "component", "UI", "screen", "form", "button" | UI Components |
| "report", "dashboard", "analytics", "metrics" | Reports & Dashboards |
| "email", "notification", "alert" | Email & Notifications |
| "API", "integration", "callout", "webhook", "sync" | Integration |
| "CPQ", "quote", "price", "discount" | CPQ |
| "field service", "FSL", "scheduling", "dispatch" | Field Service |
| "community", "portal", "experience" | Experience Cloud |

Store the detected feature types: `feature_types[]`

### Step 1e: Parse User/Persona References

Scan for references to who will use this feature:
- Role names (e.g., "admin", "manager", "technician", "sales rep")
- Profile names (e.g., "System Administrator", "Standard User")
- Permission set names
- Public group names
- Queue names

Store as `target_personas[]`

---

## Phase 2: Interactive Context Selection

### Step 2a: Discover Available Context Areas

Read all `skills/*/SKILL.md` files to discover registered skills with context specifications.

For each skill that has a `## Context Specification` section, extract:
- `metadata_type` — the type of metadata managed
- `context_path` — where context is stored under `context/{alias}/`
- `inventory_file` — the `_inventory.md` path

Then check which inventory files actually exist under `context/{alias}/`. Only areas with existing inventory files are "available."

For each available area, count the number of entries in the inventory file (lines in the inventory table, excluding the header row).

### Step 2b: Build the Context Menu

Present the interactive checklist to the user. Only show areas where the inventory file exists. Mark areas that don't have inventory files as "(not scanned)".

Auto-select the following areas by default (mark with `[x]`):
- Objects & Fields
- Flows & Automation
- Apex Code
- Permissions & Security
- Validation Rules

All other areas default to unselected `[ ]`.

Additionally, auto-select any area that matches a `feature_types[]` entry from Phase 1d.

Present:
```
Which context areas are relevant to this feature?
Default selections are based on detected feature types. Confirm or adjust:

[x] Objects & Fields — {N} custom objects cached
[x] Flows & Automation — {N} active flows cached
[x] Apex Code — {N} classes cached
[ ] Legacy Automation — {N} workflow rules cached (or: not scanned)
[x] Permissions & Security — {N} permission sets, {M} profiles cached
[x] Validation Rules — {N} rules cached
[ ] UI Components — {N} LWC, {M} Aura, {P} VF pages cached (or: not scanned)
[ ] Layouts & Pages — {N} layouts, {M} FlexiPages cached (or: not scanned)
[ ] Integration — {N} named credentials, {M} remote sites cached (or: not scanned)
[ ] Data Architecture — {N} record types, {M} CMDTs, {P} custom labels cached (or: not scanned)
[ ] Reports & Dashboards — {N} reports, {M} dashboards cached (or: not scanned)
[ ] Email & Notifications — {N} templates cached (or: not scanned)
[ ] Field Service (FSL) — {N} territories, {M} work types (or: not scanned)
[ ] CPQ — {N} product rules, {M} price rules (or: not scanned)
[ ] Experience Cloud — {N} sites (or: not scanned)

Enter your selections (e.g., "1,2,3,5" or "all" or "default" to keep current):
```

Wait for the user's selection. Parse the response and build: `selected_areas[]`

---

## Phase 3: Load Selected Context

### Step 3a: Load Inventory Files

For each area in `selected_areas[]`:

1. Read the `_inventory.md` file for that area
2. Extract the **Detected Naming Conventions** section (if present) — store for use in PRD generation
3. Parse the inventory table into a structured list

If the inventory file does not exist for a selected area:
- Note: "Context not available for {area} — will be marked for manual review in PRD"
- Continue to the next area

### Step 3b: Filter to Relevant Entries

For each inventory loaded, filter entries to those relevant to the feature:

**Objects & Fields inventory:**
- Include all entries in `affected_objects[]`
- Include objects that share a prefix with affected objects (e.g., if `Invoice__c` is affected, also include `Invoice_Line__c`)
- Include junction objects that relate two affected objects

**Flows inventory:**
- Include flows whose `Object` column matches any entry in `affected_objects[]`
- Include scheduled/platform-event flows that reference affected objects in their description

**Apex inventory:**
- Include triggers on affected objects
- Include handlers/processors whose names contain affected object names
- Include test classes for the above

**Validation Rules inventory:**
- Include rules on affected objects

**Permissions inventory:**
- Include permission sets that reference affected objects
- Include profiles that have been customized for affected objects

**All other inventories:**
- Include entries that reference affected objects in any column
- Include entries that match keywords from `feature_types[]`

### Step 3c: Load Detail Files (Budget-Aware)

Maintain a running count of loaded files. **Budget: 15 files maximum.**

Priority order for loading detail files:
1. Object detail files for `affected_objects[]` that already exist — HIGH priority
2. Flow detail files for record-triggered flows on affected objects — HIGH priority
3. Apex detail files for triggers/handlers on affected objects — MEDIUM priority
4. Validation rule detail files on affected objects — MEDIUM priority
5. Permission set detail files — LOW priority (inventory summary is usually sufficient)
6. All other detail files — LOW priority

For each detail file loaded, extract:
- Last modified date
- Key configuration details
- Relationships to other components

If the budget is exhausted before all desired files are loaded:
```
ℹ️  Context budget reached (15 files loaded). Remaining areas will use inventory-level summaries only.
```

### Step 3d: Extract Naming Conventions

From the loaded context, compile the detected naming conventions:

- **Object naming:** e.g., `Prefix_EntityName__c` or `EntityName__c`
- **Field naming:** e.g., `Entity_Field_Name__c` or `FieldName__c`
- **Apex class naming:** e.g., `ObjectNameTriggerHandler`, `ObjectNameProcessor`
- **Flow naming:** e.g., `ObjectName - Before Save - Description`
- **Permission set naming:** e.g., `App_Name - Role - Access Level`
- **UI component naming:** e.g., `appNameComponentName` (camelCase for LWC)

These conventions will be applied to all proposed metadata names in the PRD.

---

## Phase 4: Automation Audit for Affected Objects

For each object in `affected_objects[]`, build an automation map by combining data from loaded context.

### Step 4a: Build Automation Map

For each affected object, compile:

**Triggers:**
- Check Apex inventory for triggers on this object
- If detail file was loaded, extract: trigger events (before insert, after update, etc.), handler class, active status
- If no detail file, note from inventory: trigger name, last modified

**Record-Triggered Flows:**
- Check Flows inventory for flows on this object
- Categorize by: Before Save, After Save (same transaction), After Save (async)
- If detail file was loaded, extract: entry conditions, actions, DML operations

**Workflow Rules (Legacy):**
- Check Legacy Automation inventory for workflow rules on this object
- Note: active vs. inactive, field updates, email alerts

**Process Builders (Legacy):**
- Check Legacy Automation inventory for process builders on this object
- Note: active vs. inactive, criteria, actions

**Validation Rules:**
- Check Validation Rules inventory for rules on this object
- If detail file was loaded, extract: error condition formula, active status

**Approval Processes:**
- Check if any approval processes exist on this object

Produce a consolidated automation map per object:

```
{ObjectName} Automation Map:
├── Before Save
│   ├── Trigger: {TriggerName} → {HandlerClass} (before insert, before update)
│   ├── Flow: {FlowName} (before save, active)
│   └── Validation: {RuleName} (active)
├── After Save
│   ├── Trigger: {TriggerName} → {HandlerClass} (after insert, after update)
│   ├── Flow: {FlowName} (after save, active)
│   └── Workflow: {RuleName} (field update on {FieldName})
└── Async
    └── Flow: {FlowName} (after save, async, active)
```

### Step 4b: Conflict Analysis

For each piece of business logic described in the feature requirements, analyze potential conflicts:

**Order of Execution Conflicts:**
- Will new automation fire in the same transaction as existing automation?
- Could new validation rules block saves that existing flows depend on?
- Could new triggers cause recursive processing with existing triggers?
- Will new before-save flows conflict with existing before-save flows on the same fields?

**Field Contention:**
- Do existing flows or triggers update the same fields that the new feature needs to update?
- Could concurrent field updates cause last-write-wins issues?

**Governor Limit Risks:**
- Will adding new automation to an object that already has heavy automation risk hitting governor limits?
- Are there existing SOQL queries in triggers that could combine with new queries to exceed limits?

**Data Integrity Conflicts:**
- Could new validation rules block existing automation from saving records?
- Could new required fields break existing integrations or data loads?

**Sharing and Visibility Conflicts:**
- Could new sharing rules conflict with existing OWD settings?
- Will new permission sets grant access that conflicts with existing security model?

Categorize each potential conflict:
- **HIGH** — Will likely cause errors or data issues if not addressed
- **MEDIUM** — May cause issues under certain conditions
- **LOW** — Theoretical risk, unlikely in practice

### Step 4c: Generate Conflict Summary

Produce a summary of all detected conflicts and recommended mitigations:

```
Automation Conflict Analysis:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{ObjectName}:
  ⚠️  HIGH: Existing trigger {TriggerName} updates {FieldName} in after-update context.
     New flow also updates {FieldName} → potential infinite loop.
     Mitigation: Add recursion guard in trigger handler OR consolidate logic into trigger.

  ⚠️  MEDIUM: Validation rule {RuleName} requires {FieldName} to be non-null.
     New flow sets {FieldName} to null under condition X.
     Mitigation: Update validation rule to exclude condition X, or change flow logic.

  ✅ No conflicts detected for: before-insert, before-update contexts.
```

If no conflicts are detected for an object:
```
  ✅ {ObjectName}: No automation conflicts detected. Clean separation from existing automation.
```

---

## Phase 5: Generate PRD

Using all gathered context from Phases 0-4, generate the PRD document. Apply the detected naming conventions from Step 3d to all proposed metadata names.

### PRD Template

Generate the following document, filling in all sections based on the gathered context and requirements:

```markdown
# PRD: {Feature Name}

_Generated: {YYYY-MM-DD HH:mm}_
_Org: {alias} ({instanceUrl})_
_Context freshness: Last scan {LAST_SCAN} ({N} days ago)_

---

## 1. Executive Summary

- **What:** {1-2 sentence description of the feature derived from the raw requirements}
- **Why:** {Business motivation — extract from requirements or note "Not specified in requirements"}
- **Who:** {Target users/personas from Step 1e, or "Not specified — review needed"}
- **Impact:** {List of affected objects and existing systems that will be modified}

---

## 2. Current State Analysis

### 2a. Affected Objects

| Object | Exists | Custom Fields | Triggers | Active Flows | Validation Rules |
|--------|--------|---------------|----------|--------------|------------------|
| {ObjectName} | Yes/New | {count from inventory} | {list from Phase 4} | {list from Phase 4} | {list from Phase 4} |

For each row:
- "Exists" = "Yes" if the object appears in the objects inventory, "New" if it will be created
- Field/trigger/flow/rule counts come from the loaded context
- If context was not available, show "?" and note "Context not loaded for this area"

### 2b. Existing Automation on Affected Objects

Insert the automation maps generated in Phase 4a, one per affected object.

For each affected object, present:

**{ObjectName}:**
- **Before-save:** {list all before-save automation: triggers (before insert/update), before-save flows, validation rules}
- **After-save:** {list all after-save automation: triggers (after insert/update/delete/undelete), after-save flows, workflow rules with field updates}
- **Async:** {list all async automation: async flows, platform event triggers, scheduled flows}
- **Validation:** {list all validation rules with brief description of what they enforce}
- **Legacy:** {list any workflow rules, process builders — note if active or inactive}

If no automation exists on the object: "No existing automation detected."

### 2c. Existing Permissions

From the permissions context (if loaded):
- **Relevant permission sets:** {list permission sets that grant access to affected objects}
- **Profile access:** {current CRUD for affected objects across key profiles}
- **Sharing model:** {OWD settings for affected objects}

If permissions context was not loaded: "Permissions context not loaded — manual review recommended."

### 2d. Existing UI

From the UI/layout context (if loaded):
- **LWC components:** {list any LWC components that reference affected objects}
- **Aura components:** {list any Aura components}
- **Visualforce pages:** {list any VF pages}
- **Page layouts:** {list layouts for affected objects}
- **FlexiPages:** {list Lightning pages for affected objects}

If UI context was not loaded: "UI context not loaded — manual review recommended."

---

## 3. Proposed Data Model Changes

### 3a. New Objects

| Object Label | API Name | Sharing Model | Record Types | Description |
|-------------|----------|---------------|-------------|-------------|
| {Label} | {API_Name__c} | {Private/Public Read/Public Read-Write} | {list or None} | {description} |

Apply detected object naming conventions. If no new objects needed, state: "No new objects required."

### 3b. New Fields on Existing Objects

| Object | Field Label | API Name | Type | Required | Default | Description |
|--------|------------|----------|------|----------|---------|-------------|
| {Object} | {Label} | {API_Name__c} | {Text/Number/Lookup/etc.} | {Yes/No} | {value or —} | {description} |

Apply detected field naming conventions. If no new fields needed, state: "No new fields required."

### 3c. New Record Types (if needed)

| Object | Record Type Label | API Name | Description |
|--------|------------------|----------|-------------|
| {Object} | {Label} | {API_Name} | {description} |

If no record types needed, state: "No new record types required."

### 3d. New Relationships

| Parent Object | Child Object | Relationship Type | Relationship Name | Description |
|--------------|-------------|-------------------|-------------------|-------------|
| {Parent} | {Child} | {Lookup/Master-Detail} | {RelName} | {description} |

If no new relationships needed, state: "No new relationships required."

---

## 4. Proposed Automation

### 4a. Automation Decision Matrix

For each piece of business logic identified in the requirements, recommend Flow vs Trigger based on:
- Complexity of the logic
- Need for transaction control
- Existing automation on the object (prefer consistency)
- Cross-object operations
- Bulk data processing needs

| # | Business Logic | Recommended | Rationale |
|---|---------------|-------------|-----------|
| 1 | {description} | Flow / Trigger | {why — consider existing automation patterns on the object} |

Decision guide:
- If the object already has a trigger framework → prefer adding to existing trigger
- If the logic is simple field updates → prefer before-save Flow
- If the logic requires complex DML across multiple objects → prefer Trigger
- If the logic is admin-maintainable → prefer Flow
- If governor limit risk is high → prefer Trigger (for bulkification control)

### 4b. New Flows (if any)

| Flow Label | API Name | Type | Object | Trigger Event | Description |
|-----------|----------|------|--------|---------------|-------------|
| {Label} | {API_Name} | {Record-Triggered/Screen/Scheduled/Platform Event} | {Object} | {Before Save/After Save/After Delete} | {description} |

Apply detected flow naming conventions. If no flows needed, state: "No new flows required."

### 4c. New Trigger Stack (if any)

| Component | Name | Description |
|-----------|------|-------------|
| Trigger | {ObjectName}Trigger | Routes all events to handler (if not already existing) |
| Handler | {ObjectName}TriggerHandler | Filters and routes to processor(s) |
| Processor | {ProcessorName} | Implements {specific logic} |
| Test Class | {ObjectName}TriggerTest | Tests {scenarios} |

Apply detected Apex naming conventions. If no trigger work needed, state: "No trigger work required."

**Important:** If a trigger already exists on the affected object, do NOT propose a second trigger. Instead, propose adding to the existing trigger handler/processor pattern.

### 4d. Conflict Assessment

Insert the conflict summary from Phase 4c.

Format:

**⚠️ Potential conflicts with existing automation:**

| # | Object | Conflict | Severity | Mitigation |
|---|--------|----------|----------|------------|
| 1 | {Object} | {specific conflict from Phase 4b} | HIGH/MEDIUM/LOW | {specific mitigation strategy} |

**✅ Clean areas (no conflicts detected):**
- {list objects/contexts with no conflicts}

If no conflicts at all: "✅ No automation conflicts detected. The proposed changes have clean separation from existing automation."

---

## 5. UI Requirements

### 5a. Existing Components to Modify

| Component | Type | Current Purpose | Change Required |
|-----------|------|----------------|-----------------|
| {ComponentName} | LWC/Aura/VF/Layout | {what it does now} | {what needs to change} |

If none: "No existing components need modification."

### 5b. New Components

| Component Name | Type | Target Object/Page | Description |
|---------------|------|-------------------|-------------|
| {componentName} | LWC/VF/FlexiPage | {where it goes} | {what it does} |

Apply detected UI naming conventions. If none needed: "No new UI components required."

### 5c. Layout Changes

| Object | Layout Name | Changes |
|--------|------------|---------|
| {Object} | {Layout Name} | Add fields: {list}. Add related list: {list}. |

If none: "No layout changes required."

---

## 6. Integration Requirements

| Integration | Direction | Type | Endpoint | Authentication | Description |
|------------|-----------|------|----------|---------------|-------------|
| {Name} | Inbound/Outbound | REST/SOAP/Platform Event | {URL or N/A} | {Named Credential/Auth Type} | {description} |

If no integrations needed: "No integration work required for this feature."

---

## 7. Permission & Security Model

### 7a. Object-Level Security (OLS)

| Object | Permission Set / Profile | Create | Read | Update | Delete |
|--------|------------------------|--------|------|--------|--------|
| {Object} | {PermSet/Profile} | ✓/✗ | ✓/✗ | ✓/✗ | ✓/✗ |

### 7b. Field-Level Security (FLS)

| Object.Field | Permission Set / Profile | Visible | Editable |
|-------------|------------------------|---------|----------|
| {Object.Field__c} | {PermSet/Profile} | ✓/✗ | ✓/✗ |

### 7c. Record-Level Security (RLS)

| Object | OWD | Sharing Rules Needed | Notes |
|--------|-----|---------------------|-------|
| {Object} | {Private/Public Read/Public Read-Write} | {Yes — criteria/ownership based / No} | {details} |

### 7d. New Permission Sets (if needed)

| Permission Set Label | API Name | Description | Assigned To |
|---------------------|----------|-------------|-------------|
| {Label} | {API_Name} | {description} | {roles/users} |

Apply detected permission set naming conventions. If none needed: "No new permission sets required. Existing permission sets cover the required access."

---

## 8. Implementation Phases

Follow Salesforce deploy order. Each phase lists the specific deliverables and their deploy sequence.

### Phase 1: Data Model
| # | Deliverable | Deploy Type | Dependencies |
|---|------------|-------------|-------------|
| 1 | {New Object / New Fields} | Metadata Deploy | None |
| 2 | {Record Types} | Metadata Deploy | Objects exist |

_Deploy order: Objects → Fields → Record Types_

### Phase 2: Security
| # | Deliverable | Deploy Type | Dependencies |
|---|------------|-------------|-------------|
| 3 | Update System Administrator profile | Retrieve-Modify-Deploy | Fields exist |
| 4 | Create/update permission sets | Metadata Deploy | Fields exist |
| 5 | Configure sharing rules (if needed) | Metadata Deploy | Public groups exist |

_Deploy order: Profile → Permission Sets → Sharing Rules_
_⚠️ Never deploy profile field permissions before the fields they reference exist in the org_
_⚠️ Public groups must exist in the org before deploying sharing rules that reference them_

### Phase 3: Business Logic
| # | Deliverable | Deploy Type | Dependencies |
|---|------------|-------------|-------------|
| 6 | Apex classes (handlers, processors, services) | Metadata Deploy | Objects/fields exist |
| 7 | Triggers (new or modified) | Metadata Deploy | Handler classes deployed |
| 8 | Flows (new or modified) | Metadata Deploy | Objects/fields exist |

_Deploy order: Classes → Triggers → Flows_
_⚠️ Never create a second trigger for an object — check for existing trigger first_

### Phase 4: UI
| # | Deliverable | Deploy Type | Dependencies |
|---|------------|-------------|-------------|
| 9 | LWC components (if any) | Metadata Deploy | Apex classes deployed |
| 10 | FlexiPages | Metadata Deploy | LWC deployed |
| 11 | Page layouts | Metadata Deploy | Fields exist |
| 12 | Custom tabs (if needed) | Metadata Deploy | Objects exist |

_Deploy order: LWC → FlexiPages → Layouts → Tabs_

### Phase 5: Validation & Testing
| # | Deliverable | Deploy Type | Dependencies |
|---|------------|-------------|-------------|
| 13 | Validation rules | Metadata Deploy | All automation deployed |
| 14 | Run all Apex tests | Test Execution | All code deployed |
| 15 | End-to-end validation | Manual Testing | Everything deployed |

_Deploy order: Validation Rules → Run Tests → Manual Validation_
_Note: Deploy validation rules LAST to avoid blocking automation during development_

### Estimated Implementation Effort

| Phase | Estimated Effort | Notes |
|-------|-----------------|-------|
| Data Model | {estimate} | {notes} |
| Security | {estimate} | {notes} |
| Business Logic | {estimate} | {notes} |
| UI | {estimate} | {notes} |
| Testing | {estimate} | {notes} |
| **Total** | **{total}** | |

---

## 9. Risks & Conflicts

| # | Risk | Severity | Likelihood | Mitigation |
|---|------|----------|-----------|------------|
| 1 | {risk from conflict analysis in Phase 4} | High/Medium/Low | High/Medium/Low | {specific mitigation strategy} |
| 2 | {data model risk} | — | — | — |
| 3 | {integration risk} | — | — | — |
| 4 | {governor limit risk} | — | — | — |
| 5 | {user adoption risk} | — | — | — |

Always include these standard risk categories (even if assessed as Low):
- **Automation conflicts** — from Phase 4 analysis
- **Governor limits** — if adding automation to heavily-automated objects
- **Data migration** — if existing records need backfill for new fields
- **Integration impact** — if changes affect inbound/outbound integrations
- **User adoption** — if the feature changes existing user workflows

---

## 10. Test Plan

### Unit Tests

| Test Class | Method | Scenario | Expected Outcome | Coverage Target |
|-----------|--------|----------|-----------------|-----------------|
| {TestClass} | {testMethod} | {scenario description} | {expected result} | {object/class covered} |

Minimum scenarios to cover:
- Positive path (happy path)
- Negative path (validation rule fires, error handling)
- Bulk operations (200+ records)
- Edge cases (null values, boundary conditions)
- Permission tests (user with/without access)

### Integration / End-to-End Tests

| # | Scenario | Objects Involved | Steps | Expected Outcome |
|---|----------|-----------------|-------|-----------------|
| 1 | {scenario} | {objects} | {steps} | {expected result} |

### Manual Testing Checklist

| # | Step | Action | Expected Result | Pass/Fail |
|---|------|--------|-----------------|-----------|
| 1 | {step} | {action} | {expected result} | |

---

## 11. Naming Conventions Applied

These naming conventions were detected from the org's existing metadata and applied throughout this PRD:

| Category | Convention | Example |
|----------|-----------|---------|
| Objects | {detected convention or "No convention detected — using Salesforce default"} | {example} |
| Fields | {detected convention} | {example} |
| Apex Classes | {detected convention} | {example} |
| Triggers | {detected convention} | {example} |
| Flows | {detected convention} | {example} |
| Permission Sets | {detected convention} | {example} |
| LWC Components | {detected convention} | {example} |
| Validation Rules | {detected convention} | {example} |

---

## Appendix A: Context Files Referenced

| File | Skill / Source | Last Updated |
|------|---------------|-------------|
| context/{alias}/META.md | Core | {timestamp} |
| context/{alias}/objects/_inventory.md | sf-data-architecture | {timestamp} |
| context/{alias}/flows/_inventory.md | sf-flows | {timestamp} |
| context/{alias}/apex/_inventory.md | sf-apex-classes | {timestamp} |
| {additional files loaded} | {skill} | {timestamp} |

Total context files loaded: {count} / 15 budget

---

## Appendix B: Areas Not Analyzed

The following context areas were either not selected or not available. Manual review is recommended for these areas before implementation:

| Area | Reason |
|------|--------|
| {area name} | Not selected / Not scanned |
```

---

## Phase 6: Output PRD

### Step 6a: Determine Output Path

Check if `$ARGUMENTS` included an explicit output path (e.g., `--output path/to/file.md` or a second argument that looks like a file path ending in `.md`).

**If explicit output path provided:**
- Use that path

**If no explicit output path:**
- Construct the default path: `projects/{alias}/{feature-name-slug}/requirements.md`
  - `{alias}` = the org alias resolved in Phase 0b
  - `{feature-name-slug}` = the feature name converted to lowercase, spaces replaced with hyphens, special characters removed
  - Example: org alias `my-dev-org`, feature "Invoice Tracking for Work Orders" → `projects/my-dev-org/invoice-tracking-for-work-orders/requirements.md`

### Step 6b: Create Output Directory

Create the feature directory:
```bash
mkdir -p projects/{alias}/{feature-name-slug}/
```

### Step 6c: Write the PRD File

Write the generated PRD document to the determined output path.

### Step 6d: Display Summary

Display the PRD inline in the conversation (the full document).

Then display:
```
PRD written to: {output-path}
```

---

## Phase 7: Next Steps

After generating the feature requirements doc, suggest the next action:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Feature requirements doc generated: {output-path}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Recommended next steps:

1. Review the Requirements
   - Verify the user stories capture the business need
   - Confirm affected objects and business rules are correct
   - Check acceptance criteria are measurable and complete
   - Adjust as needed

2. Generate Implementation Plan
   Run: /sf-plan-feature projects/{alias}/{feature-name}/requirements.md
   This will analyze your org's architecture, research best practices,
   present architecture decisions (Flow vs Apex, VR vs code, etc.),
   ask clarifying questions, and generate a phased implementation plan.

3. After the plan is approved:
   Run: /sf-execute {plan-path}
   This will implement the plan phase by phase.

4. After implementation:
   Run: /sf-commit
   This will commit all generated metadata to git.

5. Update Context Cache
   After implementation, run:
   /sf-check-context-freshness {alias}
   This ensures the context cache reflects the new metadata.

Note: This PRD is a starting point. Review and refine before implementation.
The quality of the analysis depends on the freshness and completeness of the cached org context.
```

---

## Error Handling

### No context directory
```
Error: No org context found.
The context/ directory does not exist or contains no registered orgs.

To get started:
1. Run /sf-init-project <alias> to connect an org and build initial context
2. Then re-run /sf-create-prd
```

### Missing inventory for selected area
Do NOT stop. Instead, note in the PRD:
```
⚠️ Context not available for {area name}.
   This area was not scanned during org context gathering.
   Manual review recommended before implementation.
   To scan: run /sf-check-context-freshness {alias} or re-scan the org.
```

### File read errors
If a context file cannot be read (corrupted, missing):
- Log a warning
- Continue with available data
- Note in the PRD appendix which files could not be loaded

### Empty requirements
If the user provides no meaningful feature description after prompting:
```
Cannot generate a PRD without feature requirements.
Please provide a description of what you want to build, including:
- What the feature does
- Who will use it
- Which objects or areas of Salesforce are involved
```

---

## Important Notes

- **Read-only command** — this command never modifies the org, never deploys metadata, never runs DML. It only reads cached context files and generates a document.
- **Context quality matters** — the PRD is only as good as the cached context. If context is stale or incomplete, the PRD will have gaps. Always note these gaps explicitly.
- **Naming conventions are critical** — using the wrong naming convention in a PRD that feeds into `/sf-implement-objects` will create inconsistently-named metadata. Always apply detected conventions.
- **Automation conflict analysis is the most valuable section** — this prevents the #1 source of Salesforce bugs (conflicting automation on the same object). Give this section extra attention.
- **Interactive selection prevents waste** — loading all context for a simple field addition is wasteful. Let the user choose what's relevant.
- **The PRD is a living document** — encourage the user to iterate on it before implementation. The first draft is a starting point, not a final spec.
