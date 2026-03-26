# Master Plan: Job Search Config

**Generated:** 2026-03-26
**Org:** AwesomeOpossumDevHub (https://your-org.develop.my.salesforce.com)
**Requirements Source:** `projects/AwesomeOpossumDevHub/job-search-config/requirements.md`
**Context Freshness:** Last scanned 0 days ago (2026-03-26T17:37:00Z)
**Integration Context:** JobFinder Python pipeline reads active configs via REST API SOQL at scheduler startup; writes back `Last_Run_At__c` and `Last_Run_Summary__c` via PATCH after each run; populates `Search_Config__c` on `JobApplication__c` at insert time. No managed packages. Existing `AnthropicClaude` named credential and remote site setting already in place. All reads/writes occur outside Salesforce automation (REST API only).
**Status:** In Progress

---

## Architecture Decisions

### Decision 1: Automation — Schedule Hour/Minute Range Enforcement
**Selected:** Validation Rules
**Rationale:** Pure numeric field-level constraints with no cross-object logic. VRs are the simplest, most admin-maintainable option. Org has 1 existing VR (`Must_Specify_Type` on `Award__c`) — consistent `Snake_Case_Descriptive` naming pattern. Null values pass correctly (Salesforce treats null numbers as 0 in comparisons — 0 is a valid hour/minute).
**Skill Reference:** `skills/sf-validation-rules/SKILL.md`

### Decision 2: Automation — Keywords Required When Activating
**Selected:** Validation Rule
**Rationale:** Conditional required field exactly matching Pattern 1 in the VR skill. No side effects needed — just block the save. Admin-maintainable without any code.
**Skill Reference:** `skills/sf-validation-rules/SKILL.md`

### Decision 3: No Flows or Triggers
**Selected:** No additional automation beyond VRs
**Rationale:** All reads and writes occur via the JobFinder Python pipeline through REST API — entirely outside Salesforce automation order of execution. `JobApplicationTrigger` is unaffected by the new nullable lookup field (no formula dependencies, no required constraints, no trigger events added).

### Decision 4: MultiselectPicklist — GVS Reference
**Selected:** Reference existing `Skills` Global Value Set — do NOT recreate
**Rationale:** `Skills` GVS already exists and is shared by `Job__c` and `Experience__c`. `Job_Search_Config__c` has no record types, so no RecordType GVS filtering update needed.
**Skill Reference:** `skills/sf-data-architecture/SKILL.md`

### Decision 5: Permission Set Migration
**Selected:** Create `Anthropic_Claude` → assign to integration user → verify access → remove `Althropic_Claude` assignment → delete `Althropic_Claude`
**Rationale:** Strict sequencing prevents integration user access gap. Never delete old perm set before new one is confirmed active. Phased 2 days before Phase 3 deploy ensures clean baseline.

### Decision 6: FlexiPage — `Job_Search_Config__c` Record Page
**Selected:** Create new FlexiPage via metadata deploy; activate manually post-deploy
**Rationale:** Metadata deploy cannot auto-activate or assign as org default. Manual activation step included in Phase 3 Tier 3 checklist. Following existing org pattern: all custom objects use standard layout + FlexiPage.

### Decision 7: Phase Structure
**Selected:** 3 deploy phases; Phase 4 testing from requirements folded into Phase 3 Tier 2 E2E
**Rationale:** Data Model and Security are naturally separated — Phase 2 perm set deploy must happen after all fields from Phase 1 exist in the org (cannot reference non-existent fields in field permissions). Phase 3 UI/VR work completes the feature. Testing is not a separate deploy phase — it's Tier 2/3 of the PIV loop in Phase 3.

---

## Naming Conventions

Based on org patterns detected in context inventories:

| Element | Convention | Example Applied |
|---|---|---|
| Objects | PascalCase with underscores | `Job_Search_Config__c` |
| Fields | PascalCase with underscores | `Required_Skills__c`, `Min_Annual_Salary__c` |
| Validation Rules | Snake_Case descriptive | `Schedule_Hour_Range`, `Keywords_Required_When_Active` |
| Permission Sets | Descriptive PascalCase | `Anthropic_Claude` |
| FlexiPages | Descriptive (no object suffix needed) | `Job_Search_Config` |
| Page Layouts | `{Object Label} Layout` | `Job Search Config Layout` |
| List Views | Descriptive phrase | `Active Configs` |
| Custom Tab | Object label plural | `Job Search Configs` |

---

## Phase Registry

| Phase | Name | Scope | Plan File | Status |
|---|---|---|---|---|
| 1 | Data Model | `Job_Search_Config__c` object + 11 fields + `Search_Config__c` lookup on `JobApplication__c` + Admin profile FLS | `phase-1-data-model.md` | Plan Generated |
| 2 | Security | Create `Anthropic_Claude` perm set (replaces `Althropic_Claude`); assign to integration user; remove old | — | Not Started |
| 3 | UI & Validation | 3 VRs + `Job Search Config Layout` + `Job_Search_Config` FlexiPage + custom tab + `Resume_Builder` app update + `Job_Application` FlexiPage update + `Active Configs` list view | — | Not Started |

---

## Regression Test Registry

| Test Class | Phase Added | Verification Command | Status |
|---|---|---|---|

_(Empty — no Apex in this feature. Regression runs via `RunLocalTests` after each declarative phase to catch unintended breakage.)_

---

## Prior Phase Summaries

_(Populated as phases complete.)_

---

## Acceptance Criteria Tracking

| # | Acceptance Criterion | Phase(s) | Status |
|---|---|---|---|
| AC-1 | Active configs readable by pipeline SOQL (all 9 fields queryable) | Phase 1 | Not Started |
| AC-2 | Write-back updates `Last_Run_At__c` and `Last_Run_Summary__c` | Phase 1, Phase 2 | Not Started |
| AC-3 | `Search_Config__c` lookup on `JobApplication__c` — nullable, clears on parent delete | Phase 1 | Not Started |
| AC-4 | VRs fire correctly — schedule hour/minute range + keywords required on activate | Phase 3 | Not Started |
| AC-5 | `Job Search Configs` tab visible in Resume Lightning app | Phase 3 | Not Started |
| AC-6 | `Search_Config__c` field visible on `Job_Application` FlexiPage | Phase 3 | Not Started |
| AC-7 | `Anthropic_Claude` perm set grants correct access; `Althropic_Claude` removed from org | Phase 2 | Not Started |
| AC-8 | "Active Configs" list view shows only `Is_Active__c = true` records | Phase 3 | Not Started |
