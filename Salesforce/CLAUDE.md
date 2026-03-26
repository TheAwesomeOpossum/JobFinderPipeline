# Claude Code — Salesforce Project Conventions

This file is auto-loaded by Claude Code at the start of every session in this directory.

---

## Project Structure

```
.claude/commands/  <- Slash-command definitions (auto-discovered by Claude Code)
skills/            <- Reusable reference libraries (loaded by commands that need them)
projects/          <- Feature docs organized by org alias (requirements, plans, phase files)
  {alias}/         <- One sub-folder per connected org alias
    {feature}/     <- One sub-folder per feature (created by sf-create-feature-requirements-doc)
      requirements.md  <- PRD/requirements doc (output of sf-create-feature-requirements-doc)
      master-plan.md   <- Master plan with phase registry (output of sf-plan-feature)
      phase-1-{name}.md  <- Phase 1 plan (output of sf-plan-feature)
      phase-2-{name}.md  <- Phase 2 plan (output of sf-plan-feature --next), etc.
context/           <- Persistent org state cache (re-derivable from org; never hand-edit)
  INDEX.md         <- Master org registry; lists connected orgs and last-scan dates
  {alias}/         <- Per-org context directory (created on first scan)
    META.md        <- Org connection info, scan history, freshness check history
    objects/       <- Managed by sf-get-existing-org-object-context (base layer)
    apex/          <- Managed by sf-trigger-patterns skill context spec
    apex-classes/  <- Managed by sf-apex-classes skill context spec
    flows/         <- Managed by sf-flows skill context spec
    validation-rules/ <- Managed by sf-validation-rules skill context spec
    permissions/   <- Managed by sf-permissions skill context spec
    layouts/       <- Managed by sf-layouts skill context spec
    data-architecture/ <- Managed by sf-data-architecture skill context spec
    automation-legacy/ <- Managed by sf-automation-legacy skill context spec
    ui-components/ <- Managed by sf-ui-components skill context spec
    integration/   <- Managed by sf-integration skill context spec
    fsl/           <- Managed by sf-fsl skill context spec (if FSL installed)
    cpq/           <- Managed by sf-cpq skill context spec (if CPQ installed)
    experience-cloud/ <- Managed by sf-experience-cloud skill context spec (if sites exist)
    reporting/     <- Managed by sf-reporting skill context spec
    email-notifications/ <- Managed by sf-email-notifications skill context spec
    security-advanced/ <- Managed by sf-security-advanced skill context spec
    assignment-rules/ <- Managed by sf-assignment-rules skill context spec
    audit/         <- Freshness-check output logs and automation maps
```

---

## Getting Started

Run `/sf-init-project <alias>` to bootstrap a new project. This will:
1. Create or connect to an SFDX project
2. Authenticate with a Salesforce org
3. Run a comprehensive scan across all registered skills
4. Detect naming conventions used in the org
5. Output a full architecture summary

---

## Context Caching System

The `context/` directory stores persistent org state so Claude does not re-query the org from scratch every session.

### Memory Split Rule

| Information | Where to store |
|---|---|
| Org state that can be re-queried (objects, fields, Apex names, picklists, rules, flows, components) | `context/{alias}/` |
| Human decisions that cannot be re-queried (manual Setup steps, role hierarchy decisions, permission set group intentions, public group API names) | `~/.claude/.../memory/` |

### How context is created

Run `/sf-init-project <alias>` for first-time setup (recommended), or `/sf-get-existing-org-object-context <alias>` for a full rescan.

Context is **never pre-scaffolded** -- the directory for an alias is created on first scan. If `context/{alias}/` doesn't exist, no context has been gathered yet.

### How context is kept fresh

Run `/sf-check-context-freshness <alias>` to detect changes since the last scan.

Context is considered stale if the last scan timestamp in `context/{alias}/META.md` is more than 7 days old, or if a freshness check shows changed components.

### Extension model

Each skill that manages org metadata declares a `## Context Specification` block in its `SKILL.md`. The orchestrator commands (`sf-init-project`, `sf-get-existing-org-object-context`, `sf-check-context-freshness`, `sf-load-feature-context`) discover registered skills by reading all `skills/*/SKILL.md` files at runtime. **No hardcoded metadata types.** Adding a new skill = adding org context support for that metadata type automatically.

### Naming Convention Detection

Every skill's inventory scan includes a **Detected Naming Conventions** section at the top of its `_inventory.md` file. During scans, all discovered API names are analyzed to extract org-specific patterns (prefixes, suffixes, casing, separators). These conventions are used by implement commands and the PRD generator to ensure new metadata matches the org's existing norms.

---

## Command Reference

### Lifecycle Commands (run in this order)
| Command | Purpose |
|---|---|
| `/sf-prime [alias]` | Session start: load org context, check freshness, detect in-progress features |
| `/sf-create-feature-requirements-doc <description>` | Formalize conversation into feature requirements doc with user stories |
| `/sf-plan-feature <requirements-path>` | Generate master plan + Phase 1 plan with architecture decisions and research |
| `/sf-plan-feature --next <feature-name>` | Generate the next phase plan for an in-progress feature |
| `/sf-execute <phase-plan-path>` | Execute ONE phase through a PIV loop: Implement -> Unit Test -> E2E Test -> User Review -> Commit |
| `/sf-commit [-m "msg"]` | SF-aware git commit with phase-scoped metadata categorization |

### Utility Commands
| Command | Purpose |
|---|---|
| `/sf-init-project <alias>` | Bootstrap new project: connect to org, full scan across all skills |
| `/sf-get-existing-org-object-context <alias>` | Full rescan: write context files for all registered skills |
| `/sf-check-context-freshness <alias>` | Check what changed in org since last scan |
| `/sf-load-feature-context <spec-file>` | Load only context files relevant to a feature |
| `/sf-audit-automation <ObjectApiName>` | Map all automation on an object: triggers, flows, workflows, validation rules |
| `/sf-implement-objects <spec>` | Generate + deploy objects, fields, layouts, profiles, permsets |
| `/sf-implement-trigger <summary>` | Generate + deploy trigger stack (trigger, handler, processor, test class) |

### Recommended Workflow — PIV Loop Model

Each feature is implemented through a series of PIV (Plan-Implement-Validate) loops:

```
1. /sf-prime                              -> Load org context, detect in-progress features
2. Conversation                           -> Discuss what you want to build
3. /sf-create-feature-requirements-doc    -> Formalize into requirements doc
                                              Output: projects/{alias}/{feature}/requirements.md
4. /sf-plan-feature                       -> Generate master plan + Phase 1 plan
                                              Output: projects/{alias}/{feature}/master-plan.md
                                                      projects/{alias}/{feature}/phase-1-{name}.md
5. /sf-execute phase-1.md                 -> PIV loop for Phase 1:
                                              Implement -> Unit Tests -> E2E Tests -> User Review -> Commit
6. /sf-plan-feature --next {feature}      -> Generate Phase 2 plan
                                              Output: projects/{alias}/{feature}/phase-2-{name}.md
7. /sf-execute phase-2.md                 -> PIV loop for Phase 2
8. ... repeat until all phases complete
```

### PIV Loop — Three-Tier Validation

Every phase goes through three testing tiers before commit:

| Tier | Type | What Happens | Gate |
|---|---|---|---|
| 1 | Unit Tests | Apex test classes deployed + run. Regression tests from all prior phases also run. | ALL pass, ≥85% new coverage, ≥75% org-wide |
| 2 | E2E Testing | Browser automation (preferred) or guided CLI to verify end-to-end workflows in org | ALL scenarios pass |
| 3 | User Review | User reviews code/declarative changes + manually tests in org | User explicitly approves |

### Test Class Rule
Target ONE test class per Apex class. During development phases, temporary extras are OK, but consolidate during the final phase to prevent bulk test class accumulation in the org.

---

## Context Specification Standard (for skill authors)

To add org context tracking for a new metadata type, add this block to the skill's `SKILL.md`:

```markdown
## Context Specification

- metadata_type: MyType
- context_path: {alias}/my-type/
- inventory_file: {alias}/my-type/_inventory.md
- detail_file_pattern: {alias}/my-type/{ApiName}.md

### Full Inventory Query
Uses: standard API  (or: tooling API)
\```sql
SELECT ApiName, LastModifiedDate, LastModifiedBy.Name
FROM SomeObject
WHERE NamespacePrefix = null
ORDER BY ApiName
\```

### Change Detection Query
Uses: standard API  (or: tooling API)
\```sql
SELECT ApiName, LastModifiedDate, LastModifiedBy.Name
FROM SomeObject
WHERE LastModifiedDate > {LAST_SCAN}
ORDER BY LastModifiedDate DESC
LIMIT 50
\```

### Inventory Columns
API Name | Label | Status | Last Scanned

### Detail File Sections
Identity, Key Fields, Last Deployed Version

### Naming Convention Detection
Analyze all {type} names and extract:
- **Pattern 1:** description
- **Pattern 2:** description
- Report findings in `## Detected Naming Conventions` at the top of `_inventory.md`
```

- `{LAST_SCAN}` is replaced at runtime with the timestamp from `context/{alias}/META.md`
- Full Inventory Query has no date filter (gets everything, used by init/full scans)
- Change Detection Query uses `{LAST_SCAN}` (used by freshness checks)

---

## General Conventions

- **Deploy order:** Objects/Fields -> Profile -> FlexiPage -> Layouts -> PermSets -> Sharing Rules -> Validation Rules -> Apex Classes -> Triggers/Flows
- **Never deploy profile permissions before the fields they reference exist in the org**
- **Public Groups must exist in the org before deploying sharing rules that reference them**
- **Always retrieve before editing** profiles, permission sets, sharing rule files, and layouts
- **Never create a second trigger for an object** -- check for existing trigger first (use `/sf-audit-automation` to verify)
- **Always check for existing flows** before creating new automation -- use `/sf-audit-automation` to see what already fires on an object
- **Follow org naming conventions** -- every inventory file has a Detected Naming Conventions section; use those patterns for new metadata
- **Naming default (if no convention detected):** label spaces -> underscores -> append `__c` for custom API names
- **When adding values to a Global Value Set, always retrieve and deploy the GVS + every RecordType that restricts its visible values together** -- the RecordType's allowed values list must include the new value or it will exist in the GVS but remain invisible to records of that RecordType

---

## Behavioral Rules

These rules govern how Claude behaves in every conversation within this project. They are mandatory.

### Auto-Run (read-only operations -- execute without asking)

1. **When the user describes a feature or change:**
   - Check if `context/INDEX.md` exists and has an org registered
   - If no org: "No org context found. Run `/sf-prime` or `/sf-init-project <alias>` to get started."
   - If org exists: read `context/{alias}/META.md` for freshness. If stale (>7 days), warn once.
   - Load `context/{alias}/objects/_inventory.md` and check if mentioned objects exist
   - Summarize what you found about affected objects

2. **When the user mentions a Salesforce object or field (by any name):**
   - Users often use **labels**, **approximate names**, or **partial names** instead of API names (e.g., "work order" instead of `Work_Order__c`, "serial number" instead of `Serial_Number__c`, "the status field" when multiple status fields exist)
   - **Always resolve names before acting.** Search `context/{alias}/objects/_inventory.md` and relevant detail files to find likely matches:
     - Strip spaces, convert to API-name format, check for `__c` suffix variants
     - Search by label (field labels are stored in detail files)
     - Look for partial/substring matches across all objects and fields
   - **If exactly one match:** proceed silently — read its detail file, trigger inventory, and flow inventory
   - **If multiple possible matches:** present the candidates and ask which one they mean before proceeding (e.g., "I found 3 status fields on Work_Order__c: `Status__c`, `Approval_Status__c`, and `Payment_Status__c`. Which one?")
   - **If no match found:** tell the user and ask for clarification — do NOT guess or assume it doesn't exist (it may be a standard field, a managed package field, or the context may be stale)
   - Summarize: "{Object} exists with {N} fields, {M} triggers, {P} flows"

3. **When the user asks about automation on an object:**
   - Run `/sf-audit-automation` logic automatically -- do NOT ask "would you like me to audit?"

4. **When context is needed for any operation:**
   - Run `/sf-load-feature-context` logic automatically -- do NOT ask "should I load context?"

### Ask Before (write operations -- always get confirmation)

1. Before generating a feature requirements doc: "Want me to formalize this into a requirements doc?"
2. Before generating an implementation plan: "Ready to create the implementation plan?"
3. Before deploying metadata to the org: show exactly what will be deployed, ask "Proceed?"
4. Before creating or modifying files in force-app/: show file path and summary of changes
5. Before committing to git: show proposed commit message and file list

### Intent Detection

| User Says | Claude Does |
|---|---|
| User mentions an object/field by label or approximate name | Resolve to API name(s) via context files -> confirm if ambiguous -> then proceed |
| "I want to add/build/create..." | Check context -> resolve names -> summarize affected objects -> gather requirements -> offer requirements doc |
| "Plan this" / "create a plan" | Run `/sf-plan-feature` |
| "What automation exists on {Object}?" / "What existing logic exists on {Object}?" | Run `/sf-audit-automation` automatically |
| "What does this org look like?" | Read and present architecture summary |
| "Deploy/implement this" | Run `/sf-execute` with plan path |
| "Commit/save changes" | Run `/sf-commit` |
| "Start/prime/begin" | Run `/sf-prime` |
| "Is the org up to date?" | Run `/sf-check-context-freshness` |

### Conversation Flow

```
User starts talking
  |
  +-- No org context? -> Guide to /sf-prime
  |
  +-- EXPLORE intent ("what does...", "show me...")
  |     -> Load context silently, present findings
  |
  +-- BUILD intent ("I want to add...", "create...", "build...")
  |     -> Load context -> summarize state -> gather requirements
  |     -> Offer requirements doc -> offer plan -> offer execute -> offer commit
  |
  +-- FIX intent ("bug", "not working", "fix...")
  |     -> Load context -> audit automation -> analyze conflicts -> propose fix
  |
  +-- AUDIT intent ("check", "what automation", "what changed")
        -> Run appropriate audit automatically -> present results
```

---

## Skills Available

### Reference Skills (no context spec)
| Skill | Purpose | Loaded By |
|---|---|---|
| `skills/sf-cli/SKILL.md` | Salesforce CLI v2 command reference, XML formats, deploy patterns | Referenced by all commands |

### Context-Tracked Skills (have context spec -- auto-discovered by orchestrator commands)

#### Core
| Skill | Metadata Types | Context Path |
|---|---|---|
| `skills/sf-trigger-patterns/SKILL.md` | ApexTrigger, ApexClass (trigger-related) | `{alias}/apex/` |
| `skills/sf-apex-classes/SKILL.md` | ApexClass (all non-trigger), scheduled/async jobs | `{alias}/apex-classes/` |
| `skills/sf-flows/SKILL.md` | Flow, FlowDefinition | `{alias}/flows/` |
| `skills/sf-validation-rules/SKILL.md` | ValidationRule | `{alias}/validation-rules/` |
| `skills/sf-permissions/SKILL.md` | Profile, PermissionSet | `{alias}/permissions/` |

#### Architecture
| Skill | Metadata Types | Context Path |
|---|---|---|
| `skills/sf-data-architecture/SKILL.md` | RecordType, CMDT, CustomSetting, CustomLabel, GlobalValueSet, FieldSet, PlatformEvent | `{alias}/data-architecture/` |
| `skills/sf-layouts/SKILL.md` | Layout, FlexiPage, CompactLayout | `{alias}/layouts/` |
| `skills/sf-ui-components/SKILL.md` | LWC, Aura, VF Page, QuickAction, CustomTab | `{alias}/ui-components/` |
| `skills/sf-integration/SKILL.md` | NamedCredential, RemoteSiteSetting, CspTrustedSite, ExternalDataSource | `{alias}/integration/` |

#### Automation
| Skill | Metadata Types | Context Path |
|---|---|---|
| `skills/sf-automation-legacy/SKILL.md` | WorkflowRule, WorkflowFieldUpdate, WorkflowAlert, ApprovalProcess | `{alias}/automation-legacy/` |

#### Cloud-Specific
| Skill | Metadata Types | Context Path |
|---|---|---|
| `skills/sf-fsl/SKILL.md` | ServiceTerritory, WorkType, SkillRequirement, ServiceResource, OperatingHours | `{alias}/fsl/` |
| `skills/sf-cpq/SKILL.md` | SBQQ__ProductRule__c, SBQQ__PriceRule__c, SBQQ__QuoteTemplate__c, SBQQ__DiscountSchedule__c | `{alias}/cpq/` |
| `skills/sf-experience-cloud/SKILL.md` | Network, ExperienceBundle, NavigationMenuItem | `{alias}/experience-cloud/` |

#### Specialized
| Skill | Metadata Types | Context Path |
|---|---|---|
| `skills/sf-reporting/SKILL.md` | Report, Dashboard, ListView | `{alias}/reporting/` |
| `skills/sf-email-notifications/SKILL.md` | EmailTemplate, CustomNotificationType | `{alias}/email-notifications/` |
| `skills/sf-security-advanced/SKILL.md` | PermissionSetGroup, DuplicateRule, MatchingRule | `{alias}/security-advanced/` |
| `skills/sf-assignment-rules/SKILL.md` | AssignmentRule, AutoResponseRule, EscalationRule | `{alias}/assignment-rules/` |
