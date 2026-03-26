# Org Architecture Summary — AwesomeOpossumDevHub

_Generated: 2026-03-26T17:37:00Z_
_Command: sf-init-project_

---

### Connection
- Alias: AwesomeOpossumDevHub
- Org Type: Production (Dev Hub)
- Instance: https://your-org.develop.my.salesforce.com
- Username: your-sf-user@example.com
- API Version: 66.0

---

### Detected Managed Packages

_(No managed packages detected — this is a clean org with all org-built metadata)_

---

### Metadata Inventory

| Category | Count | Skill | Status |
|---|---|---|---|
| Custom Objects (org-built) | 16 | base layer | Scanned |
| Custom Metadata Types | 2 | base layer | Scanned |
| Apex Classes | 56 | sf-apex-classes | Scanned |
| Apex Triggers | 5 | sf-trigger-patterns | Scanned |
| Active Flows | 0 | sf-flows | Scanned |
| Validation Rules | 1 | sf-validation-rules | Scanned |
| Permission Sets (org-built) | 3 | sf-permissions | Scanned |
| Permission Sets (system) | 11 | sf-permissions | Scanned |
| Profiles | 47 | sf-permissions | Scanned |
| Page Layouts | 0 | sf-layouts | Scanned |
| FlexiPages | 27 | sf-layouts | Scanned |
| Workflow Rules | 0 | sf-automation-legacy | Scanned |
| LWC Components | 39 | sf-ui-components | Scanned |
| Aura Components | 5 | sf-ui-components | Scanned |
| Visualforce Pages | 30 | sf-ui-components | Scanned |
| Named Credentials | 1 | sf-integration | Scanned |
| Remote Site Settings | 2 | sf-integration | Scanned |
| Record Types | 3 | sf-data-architecture | Scanned |
| Global Value Sets | 1 | sf-data-architecture | Scanned |
| Platform Events | 0 | sf-data-architecture | Scanned |
| Email Templates | 40 | sf-email-notifications | Scanned |
| Custom Notification Types | 0 | sf-email-notifications | Scanned |
| Reports | 25 | sf-reporting | Scanned |
| Dashboards | 0 | sf-reporting | Scanned |
| Permission Set Groups | 0 | sf-security-advanced | Scanned |
| Duplicate Rules | 0 | sf-security-advanced | Scanned |
| Experience Cloud Sites | 4 | sf-experience-cloud | Scanned |
| FSL Objects | N/A | sf-fsl | SKIPPED (not installed) |
| CPQ Rules | N/A | sf-cpq | SKIPPED (not installed) |

**Total metadata components tracked:** ~321

---

### Detected Naming Conventions (Cross-Skill Summary)

- **Objects/Fields:** PascalCase, multi-word with underscores (e.g., `JobApplication__c`, `Resume_Award__c`). Junction objects follow `{Parent}_{Child}__c` pattern. No namespace prefix.
- **Apex Classes:** `{Object}TriggerHandler`, `{Object}Processor`, `{Feature}Controller`, `{Class}Test` suffix for tests, `{Domain}Helper` for utilities, `*Interface` for interfaces
- **Apex Triggers:** `{ObjectName}Trigger` — one trigger per object, always delegates to handler
- **Flows:** N/A (no flows in this org)
- **Validation Rules:** Snake_Case descriptive names (e.g., `Must_Specify_Type`)
- **Permission Sets:** `{Feature}_{Role}` pattern (e.g., `Experience_Profile_Manager`)
- **LWC Components:** camelCase, feature-grouped (`resume*`, `portfolio*`, `*LWR` for LWR variants)
- **FlexiPages:** PascalCase with underscores (e.g., `Resume_Builder`, `Job_Application`)
- **Record Types:** PascalCase with underscores (e.g., `Work_Experience`, `Personal_Experience`)
- **Custom Metadata Types:** PascalCase + `__mdt` (e.g., `AIPromptConfig__mdt`)

---

### Standard Object Triggers Detected

| Object | Trigger Name | Status |
|---|---|---|
| Account | AccountTrigger | Active |

---

### Objects with Most Automation

| Object | Triggers | Flows | Workflow Rules | Validation Rules | Total |
|---|---|---|---|---|---|
| Experience__c | 1 | 0 | 0 | 0 | 1 |
| Interview__c | 1 | 0 | 0 | 0 | 1 |
| JobApplication__c | 1 | 0 | 0 | 0 | 1 |
| Job__c | 1 | 0 | 0 | 0 | 1 |
| Award__c | 0 | 0 | 0 | 1 | 1 |

All custom objects have low automation density. No conflicts or complex automation stacks.

---

### Org Complexity Assessment

- **Org Size:** Small (16 org-built custom objects)
- **Automation Complexity:** Low (5 triggers, 0 flows, 0 workflow rules — all Apex-based)
- **Managed Package Footprint:** None — 100% org-built
- **Legacy Automation:** None (no workflow rules or process builders)
- **Key Observations:**
  - Trigger handler pattern used consistently (TriggerHandlerInterface + RecordProcessorInterface)
  - Heavy AI integration via Anthropic Claude API (AIResumeGeneratorController, AIInterviewGuideController)
  - 4 Experience Cloud sites (2 live portfolio sites)
  - 39 LWC + 30 VF pages = rich UI layer
  - Resume PDF generation via VF: ResumePDF, ResumeOnePagePDF, CoverLetterPDF, FAANGResume, SteampunkResume
  - 2 custom CMDT types for AI prompt and resume config
  - Typo in permission set name: `Althropic_Claude` (missing 'n')
  - Typo in FlexiPage: `Strenghts` (should be `Strengths`)

---

### Data Model Summary

**Core Application Objects:**
- `Job__c` — Job listing/posting
- `JobApplication__c` — Application to a job (links Job + Contact/Account)
- `Interview__c` — Interview tracking
- `InterviewContact__c` — Junction: Interview to Contact

**Resume Builder Objects:**
- `Resume__c` — Master resume record
- `Resume_Award__c` — Junction: Resume ↔ Award
- `Resume_Education__c` — Junction: Resume ↔ Education
- `Resume_Experience__c` — Junction: Resume ↔ Experience
- `Resume_Strength__c` — Junction: Resume ↔ Strength

**Profile Component Objects:**
- `AboutMe__c` — About me section
- `Award__c` — Awards (1 validation rule: Must_Specify_Type)
- `Education__c` — Education history
- `Experience__c` — Work/internship/personal experience (3 record types)
- `Strength__c` — Skills/strengths

**AI & Config Objects:**
- `AnthropicSettings__c` — Anthropic API settings
- `CoverLetter__c` — AI-generated cover letters
- `AIPromptConfig__mdt` — CMDT for AI prompt templates
- `ResumeOwnerConfig__mdt` — CMDT for resume owner configuration

---

### Next Steps

1. Run `/sf-load-feature-context <spec-file>` to load context relevant to your first feature
2. Run `/sf-create-feature-requirements-doc <description>` to formalize a new feature
3. Run `/sf-audit-automation <ObjectName__c>` to see all automation on a specific object
4. Context will stay fresh for ~7 days. Run `/sf-check-context-freshness AwesomeOpossumDevHub` to check for changes.
