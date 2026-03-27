# Phase 3: UI & Validation

**Feature:** Job Search Config
**Org:** AwesomeOpossumDevHub
**Phase:** 3 of 3
**Master Plan:** `projects/AwesomeOpossumDevHub/job-search-config/master-plan.md`
**Generated:** 2026-03-27

---

## Prior Phase Summary

### Phase 2: Security — Complete (2026-03-27)
- Deployed: `Anthropic_Claude` permission set (OLS Read/Create/Edit on `Job_Search_Config__c`; FLS readable+editable on all 11 fields + `JobApplication__c.Search_Config__c`; `externalCredentialPrincipalAccesses` for `AnthropicClaudeAPI-AnthropicPrincipal` carried over)
- Data operations: Assigned `Anthropic_Claude` to `your-sf-user@example.com`; removed `Althropic_Claude` assignment; deleted `Althropic_Claude` from org via destructiveChanges
- Test classes: none (declarative + data operation phase)
- Regression: 86/88 passed (2 pre-existing `AIInterviewGuideControllerTest` failures unrelated to this phase)
- Key decisions: `sf data create record` does not support `PermSetAssignment` — used anonymous Apex instead; **SFDX project root is `JobFinderSF/` subdirectory — all `sf project deploy/retrieve` commands must run from there**
- Known issues: `AIInterviewGuideControllerTest` has 2 pre-existing failures (unrelated to this feature)

> ⚠️ **Phase 1 status note:** Phase 1 is marked "Plan Generated" in the master plan but was executed — Phase 2's successful completion (which required all 12 Phase 1 fields to exist in the org) confirms Phase 1 is functionally complete. The status was not updated after execution. All Phase 1 objects and fields are present in the org.

---

## Phase Goals

- Deploy 3 validation rules on `Job_Search_Config__c` (schedule hour range, schedule minute range, keywords required when active)
- Create and deploy the `Job Search Config Layout` page layout with all 11 fields organized per requirements, including read-only placement for pipeline write-back fields
- Assign the new layout to the System Administrator profile
- Create the `Job_Search_Config__c` custom tab and add it to the Resume Lightning App
- Create and deploy the `Job_Search_Config` FlexiPage record page; manually activate it post-deploy
- Retrieve and update the `Job_Application` FlexiPage to surface `Search_Config__c`
- Create the "Active Configs" list view
- Create the two test records from Appendix C of the requirements to verify end-to-end pipeline access

---

## Success Criteria

| # | Criterion | Verification Method | Tier |
|---|---|---|---|
| SC-1 | All 3 validation rules fire correctly | Insert records with invalid values in UI | Tier 2 (E2E) |
| SC-2 | `Job Search Config Layout` exists with all fields in correct sections | Setup → Object Manager → Job Search Config → Page Layouts | Tier 3 (User Review) |
| SC-3 | `Last_Run_At__c` and `Last_Run_Summary__c` are read-only in the layout | Attempt inline edit on a record | Tier 3 (User Review) |
| SC-4 | "Job Search Configs" tab appears in the Resume Lightning App | Navigate to Resume app | Tier 2 (E2E) |
| SC-5 | `Job_Search_Config` FlexiPage is activated as the org default for the object | Open any `Job_Search_Config__c` record | Tier 3 (User Review) |
| SC-6 | `Search_Config__c` field is visible on the `Job_Application` FlexiPage | Open any `JobApplication__c` record | Tier 2 (E2E) |
| SC-7 | "Active Configs" list view returns only `Is_Active__c = true` records | Create 1 active + 1 inactive record; open list view | Tier 2 (E2E) |
| SC-8 | Pipeline SOQL query returns the active test record with all 9 contract fields | Run startup SOQL from CLI | Tier 2 (E2E) |
| SC-9 | Regression — all existing Apex tests still pass | `sf apex run test --test-level RunLocalTests` (86/88 baseline; 2 pre-existing failures OK) | Tier 1 (regression-only) |

---

## Skill & Context References

Load these before executing:
- `skills/sf-cli/SKILL.md` — validation rule XML format, layout XML format, FlexiPage retrieve/deploy, list view XML
- `skills/sf-validation-rules/SKILL.md` — VR formula patterns, XML structure
- `context/AwesomeOpossumDevHub/layouts/_inventory.md` — confirms 0 existing custom layouts; 27 FlexiPages including `Job_Application` and `Award` (use `Award` as FlexiPage template)
- `context/AwesomeOpossumDevHub/objects/_inventory.md` — confirms `Job_Search_Config__c` and `JobApplication__c` exist

**Critical runtime fact from Phase 2:** All `sf project deploy/retrieve` commands must be run from the `JobFinderSF/` subdirectory (the SFDX project root). The workspace root is `Salesforce/` but the project lives at `Salesforce/JobFinderSF/`.

---

## Task List

---

### TASK 1: Deploy 3 Validation Rules on `Job_Search_Config__c`

- **What:** Create XML files for all 3 validation rules. All operate on the new object's own fields — no cross-object dependencies.
- **Create directory:**
  ```bash
  mkdir -p force-app/main/default/objects/Job_Search_Config__c/validationRules
  ```
- **Deploy directory:** `force-app/main/default/objects/Job_Search_Config__c/validationRules/`

#### File: `Schedule_Hour_Range.validationRule-meta.xml`
```xml
<?xml version="1.0" encoding="UTF-8"?>
<ValidationRule xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Schedule_Hour_Range</fullName>
    <active>true</active>
    <description>Ensures Schedule_Hour__c is between 0 and 23 (UTC). Null passes — Salesforce treats null numbers as 0 in comparisons, and 0 is a valid hour.</description>
    <errorConditionFormula>Schedule_Hour__c &lt; 0 || Schedule_Hour__c &gt; 23</errorConditionFormula>
    <errorMessage>Schedule Hour must be between 0 and 23 (UTC).</errorMessage>
</ValidationRule>
```

#### File: `Schedule_Minute_Range.validationRule-meta.xml`
```xml
<?xml version="1.0" encoding="UTF-8"?>
<ValidationRule xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Schedule_Minute_Range</fullName>
    <active>true</active>
    <description>Ensures Schedule_Minute__c is between 0 and 59. Null passes — treated as 0, which is a valid minute.</description>
    <errorConditionFormula>Schedule_Minute__c &lt; 0 || Schedule_Minute__c &gt; 59</errorConditionFormula>
    <errorMessage>Schedule Minute must be between 0 and 59.</errorMessage>
</ValidationRule>
```

#### File: `Keywords_Required_When_Active.validationRule-meta.xml`
```xml
<?xml version="1.0" encoding="UTF-8"?>
<ValidationRule xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Keywords_Required_When_Active</fullName>
    <active>true</active>
    <description>Prevents activating a search config without at least one keyword. A config with no keywords would drive a broad, unfocused search run.</description>
    <errorConditionFormula>AND(Is_Active__c, ISBLANK(Keywords__c))</errorConditionFormula>
    <errorMessage>Keywords are required before activating a search config.</errorMessage>
</ValidationRule>
```

- **Deploy all 3 together:**
  ```bash
  sf project deploy start \
    --source-dir force-app/main/default/objects/Job_Search_Config__c/validationRules \
    --target-org AwesomeOpossumDevHub --wait 10
  ```
- **Validate (dry run first):**
  ```bash
  sf project deploy start \
    --source-dir force-app/main/default/objects/Job_Search_Config__c/validationRules \
    --target-org AwesomeOpossumDevHub --dry-run --wait 10
  ```
- **Pattern Reference:** `skills/sf-validation-rules/SKILL.md` — XML format, formula escaping rules
- **Gotchas:**
  - `<` and `>` **must** be escaped as `&lt;` and `&gt;` inside XML formula elements. Unescaped angle brackets will cause a parse error at deploy time
  - `||` is a valid SF formula operator; no XML escaping needed for it
  - Validation rules are object-level metadata — deploy after the object and fields exist (already confirmed from Phase 1)
  - `ISBLANK()` is the correct function for TextArea fields (`ISNULL()` does not work for text fields)
  - `Is_Active__c` in an AND formula evaluates as a boolean directly — no `= TRUE` comparison needed

---

### TASK 2: Create `Job Search Config Layout` Page Layout

- **What:** Create the page layout XML for `Job_Search_Config__c` with 5 sections. `Last_Run_At__c` and `Last_Run_Summary__c` are placed read-only — users see them but cannot edit inline.
- **File:** `force-app/main/default/layouts/Job_Search_Config__c-Job Search Config Layout.layout-meta.xml`
- **Create directory if needed:**
  ```bash
  mkdir -p force-app/main/default/layouts
  ```
- **File content:**
  ```xml
  <?xml version="1.0" encoding="UTF-8"?>
  <Layout xmlns="http://soap.sforce.com/2006/04/metadata">
      <layoutSections>
          <customLabel>false</customLabel>
          <detailHeading>true</detailHeading>
          <editHeading>true</editHeading>
          <label>Search Configuration</label>
          <layoutColumns>
              <layoutItems>
                  <behavior>Edit</behavior>
                  <field>Keywords__c</field>
              </layoutItems>
          </layoutColumns>
          <style>OneColumn</style>
      </layoutSections>
      <layoutSections>
          <customLabel>false</customLabel>
          <detailHeading>true</detailHeading>
          <editHeading>true</editHeading>
          <label>Skills</label>
          <layoutColumns>
              <layoutItems>
                  <behavior>Edit</behavior>
                  <field>Required_Skills__c</field>
              </layoutItems>
          </layoutColumns>
          <layoutColumns>
              <layoutItems>
                  <behavior>Edit</behavior>
                  <field>Bonus_Skills__c</field>
              </layoutItems>
          </layoutColumns>
          <style>TwoColumnsTopToBottom</style>
      </layoutSections>
      <layoutSections>
          <customLabel>false</customLabel>
          <detailHeading>true</detailHeading>
          <editHeading>true</editHeading>
          <label>Thresholds &amp; Limits</label>
          <layoutColumns>
              <layoutItems>
                  <behavior>Edit</behavior>
                  <field>Daily_Limit__c</field>
              </layoutItems>
              <layoutItems>
                  <behavior>Edit</behavior>
                  <field>Min_Annual_Salary__c</field>
              </layoutItems>
          </layoutColumns>
          <layoutColumns>
              <layoutItems>
                  <behavior>Edit</behavior>
                  <field>Days_Back__c</field>
              </layoutItems>
          </layoutColumns>
          <style>TwoColumnsTopToBottom</style>
      </layoutSections>
      <layoutSections>
          <customLabel>false</customLabel>
          <detailHeading>true</detailHeading>
          <editHeading>true</editHeading>
          <label>Schedule</label>
          <layoutColumns>
              <layoutItems>
                  <behavior>Edit</behavior>
                  <field>Schedule_Hour__c</field>
              </layoutItems>
              <layoutItems>
                  <behavior>Edit</behavior>
                  <field>Is_Active__c</field>
              </layoutItems>
          </layoutColumns>
          <layoutColumns>
              <layoutItems>
                  <behavior>Edit</behavior>
                  <field>Schedule_Minute__c</field>
              </layoutItems>
          </layoutColumns>
          <style>TwoColumnsTopToBottom</style>
      </layoutSections>
      <layoutSections>
          <customLabel>false</customLabel>
          <detailHeading>true</detailHeading>
          <editHeading>false</editHeading>
          <label>Pipeline Feedback</label>
          <layoutColumns>
              <layoutItems>
                  <behavior>Readonly</behavior>
                  <field>Last_Run_At__c</field>
              </layoutItems>
          </layoutColumns>
          <layoutColumns>
              <layoutItems>
                  <behavior>Readonly</behavior>
                  <field>Last_Run_Summary__c</field>
              </layoutItems>
          </layoutColumns>
          <style>TwoColumnsTopToBottom</style>
      </layoutSections>
  </Layout>
  ```
- **Deploy:**
  ```bash
  sf project deploy start \
    --metadata "Layout:Job_Search_Config__c-Job Search Config Layout" \
    --target-org AwesomeOpossumDevHub --wait 10
  ```
- **Validate (dry run):**
  ```bash
  sf project deploy start \
    --metadata "Layout:Job_Search_Config__c-Job Search Config Layout" \
    --target-org AwesomeOpossumDevHub --dry-run --wait 10
  ```
- **Pattern Reference:** `skills/sf-cli/SKILL.md` — Layout file naming, XML structure
- **Gotchas:**
  - **File name MUST exactly match the pattern `{Object}-{LayoutName}.layout-meta.xml`** — spaces are preserved in the layout name portion. The file must be named `Job_Search_Config__c-Job Search Config Layout.layout-meta.xml` (space between "Job Search Config" and "Layout")
  - `<behavior>Readonly</behavior>` makes the field non-editable in the layout (read-only presentation) without requiring FLS read-only. The pipeline user still has Edit FLS — this is purely a UI constraint
  - `<editHeading>false</editHeading>` on Pipeline Feedback hides the section header in edit mode (the section only shows in view mode)
  - `&amp;` is required to escape `&` in XML — used in "Thresholds &amp; Limits"
  - The `Name` field does not need an explicit `<layoutItem>` — Salesforce renders the record Name in the page header automatically for custom objects
  - Deploy the layout BEFORE assigning it in the Admin profile (TASK 3)

---

### TASK 3: Admin Profile — Page Layout Assignment for `Job_Search_Config__c`

- **What:** Retrieve the Admin profile, add a `<layoutAssignments>` block for the new page layout, deploy. This assigns the layout to System Administrator users viewing `Job_Search_Config__c` records.
- **Retrieve first:**
  ```bash
  sf project retrieve start \
    --metadata "Profile:Admin" \
    --target-org AwesomeOpossumDevHub
  ```
- **File:** `force-app/main/default/profiles/Admin.profile-meta.xml`
- **Search the retrieved file** for any existing `<layoutAssignments>` block where `<layout>` begins with `Job_Search_Config__c`. If found, update it. If none found, add the following block (the XML `<layoutAssignments>` blocks are sorted alphabetically by `<layout>` value in the profile file — insert in sorted order):

  ```xml
  <layoutAssignments>
      <layout>Job_Search_Config__c-Job Search Config Layout</layout>
  </layoutAssignments>
  ```

- **Deploy:**
  ```bash
  sf project deploy start \
    --metadata "Profile:Admin" \
    --target-org AwesomeOpossumDevHub --wait 10
  ```
- **Verify via Setup:** Setup → Profiles → System Administrator → Object Settings → Job Search Config → Page Layout Assignment shows "Job Search Config Layout"
- **Gotchas:**
  - **Always retrieve before editing** the Admin profile — it is large and changes frequently. Editing the profile file from Phase 1/Phase 2 without a fresh retrieve will likely introduce stale content
  - The `<layout>` value must exactly match the deployed layout's full name: `Job_Search_Config__c-Job Search Config Layout`
  - For a custom object with no record types, no `<recordType>` element is needed in `<layoutAssignments>` — the single layout applies to all records
  - Do NOT re-add the FLS `<fieldPermissions>` blocks from Phase 1 — they are already in the org. The retrieve will have them; do not modify them
  - Deploy fails with `Unknown user permission` if the profile references permissions that don't exist in a lower API version — check API version matches `sfdx-project.json`

---

### TASK 4: Create `Job_Search_Config__c` Custom Tab

- **What:** Create a custom tab for the `Job_Search_Config__c` object so it appears as a top-level navigation item.
- **File:** `force-app/main/default/tabs/Job_Search_Config__c.tab-meta.xml`
- **Create directory if needed:**
  ```bash
  mkdir -p force-app/main/default/tabs
  ```
- **File content:**
  ```xml
  <?xml version="1.0" encoding="UTF-8"?>
  <CustomTab xmlns="http://soap.sforce.com/2006/04/metadata">
      <description>Manage Job Search Configuration records for the JobFinder pipeline.</description>
      <label>Job Search Configs</label>
      <motif>Custom58: Custom Tab 58</motif>
      <sobjectName>Job_Search_Config__c</sobjectName>
  </CustomTab>
  ```
- **Deploy:**
  ```bash
  sf project deploy start \
    --metadata "CustomTab:Job_Search_Config__c" \
    --target-org AwesomeOpossumDevHub --wait 10
  ```
- **Validate (dry run):**
  ```bash
  sf project deploy start \
    --metadata "CustomTab:Job_Search_Config__c" \
    --target-org AwesomeOpossumDevHub --dry-run --wait 10
  ```
- **Gotchas:**
  - The tab file must be named exactly `{ObjectApiName}.tab-meta.xml` — do NOT use the tab label as the filename
  - `<motif>` can be any valid Salesforce tab style (e.g., `Custom58: Custom Tab 58`). If deploy rejects the motif value, choose another from the Salesforce-documented list or use `Custom0: Custom Tab 0`
  - The tab API name in `<sobjectName>` must exactly match the deployed object API name `Job_Search_Config__c`
  - Deploy the tab BEFORE the app update (TASK 5) — the app XML references the tab by name

---

### TASK 5: Add Tab to Resume Lightning App

- **What:** Retrieve the Resume Lightning App, add the `Job_Search_Config__c` tab to its navigation, and deploy.
- **Step 1 — Retrieve the Resume app:**
  ```bash
  sf project retrieve start \
    --metadata "LightningComponentBundle:*" \
    --target-org AwesomeOpossumDevHub 2>/dev/null; \
  sf project retrieve start \
    --metadata "CustomApplication:Resume" \
    --target-org AwesomeOpossumDevHub
  ```
  If `CustomApplication:Resume` returns nothing, try:
  ```bash
  sf data query \
    --query "SELECT DeveloperName, Label FROM AppDefinition WHERE AppType = 'Classic' OR AppType = 'Lighting'" \
    --use-tooling-api \
    --target-org AwesomeOpossumDevHub
  ```
  Identify the app whose label is "Resume" and note its `DeveloperName`, then:
  ```bash
  sf project retrieve start \
    --metadata "CustomApplication:{DeveloperName}" \
    --target-org AwesomeOpossumDevHub
  ```
- **Output file:** `force-app/main/default/applications/Resume.app-meta.xml` (or matching DeveloperName)
- **Step 2 — Inspect the retrieved file.** Find the `<tabs>` section. It will contain existing tab entries like:
  ```xml
  <tabs>standard-Contact</tabs>
  <tabs>standard-Account</tabs>
  <tabs>Job__c</tabs>
  ```
- **Step 3 — Add the new tab** by inserting this line in the `<tabs>` section (position after existing custom object tabs, or at the end of the tabs list before closing the app element):
  ```xml
  <tabs>Job_Search_Config__c</tabs>
  ```
- **Step 4 — Deploy the updated app:**
  ```bash
  sf project deploy start \
    --metadata "CustomApplication:{AppApiName}" \
    --target-org AwesomeOpossumDevHub --wait 10
  ```
- **Verify:** Open the Resume Lightning App in org — "Job Search Configs" tab should appear in the navigation bar
- **Gotchas:**
  - **Always retrieve before editing** — the app XML file lists all nav tabs and settings; editing from scratch will lose existing tabs, utility bar bindings, and app settings
  - The tab entry for a custom object tab uses just the object API name: `<tabs>Job_Search_Config__c</tabs>` — **no** `__c` escaping or quotes needed
  - If the app uses `<navType>Standard</navType>`, tabs appear in the standard navigation bar. If it uses `<navType>Console</navType>`, tabs may appear differently — inspect the retrieved XML first
  - The `Resume_UtilityBar` FlexiPage is the app's utility bar (per context inventory naming pattern `{AppName}_UtilityBar`) — do not modify the utility bar file

---

### TASK 6: Create `Job_Search_Config` FlexiPage

- **What:** Create a Lightning record page for `Job_Search_Config__c`. The page uses `force:detailPanel` to render the page layout created in TASK 2. Cannot be auto-activated via metadata deploy — requires a manual activation step in Setup.
- **Step 1 — Retrieve the `Award` FlexiPage as a template:**
  ```bash
  sf project retrieve start \
    --metadata "FlexiPage:Award" \
    --target-org AwesomeOpossumDevHub
  ```
  Output: `force-app/main/default/flexipages/Award.flexipage-meta.xml`
- **Step 2 — Copy and modify:**
  - Copy `Award.flexipage-meta.xml` to `Job_Search_Config.flexipage-meta.xml`
  - Change `<sobjectType>` to `Job_Search_Config__c`
  - Change `<masterLabel>` to `Job Search Config`
  - Ensure the main content region includes a `force:detailPanel` component. The component that renders the page layout is identified by `<componentName>forceContent:layoutSection</componentName>` or `<componentName>force:detailPanel</componentName>` depending on the template. **Do not change the region structure** — only change the `sobjectType` and `masterLabel` elements.
  - Remove any `<parentFlexiPage>` reference if present (this is a new standalone page, not a variant)
- **File:** `force-app/main/default/flexipages/Job_Search_Config.flexipage-meta.xml`
- **Deploy:**
  ```bash
  sf project deploy start \
    --metadata "FlexiPage:Job_Search_Config" \
    --target-org AwesomeOpossumDevHub --wait 10
  ```
- **Step 3 — Manually activate in Setup (REQUIRED — cannot be done via metadata):**
  1. Go to Setup → App Builder → find `Job Search Config` in the list
  2. Click Edit
  3. Click Activation
  4. Set as Org Default for the `Job_Search_Config__c` object
  5. Save
- **Verify:** Navigate to any `Job_Search_Config__c` record — the custom page renders with all 5 layout sections visible
- **Gotchas:**
  - Metadata deploy creates the FlexiPage but does NOT activate it. Without manual activation, Salesforce uses the default record layout (no custom page). **Activation is required** before Tier 3 user review
  - Use `Award` as the template because it is a simple custom object record page following the same org pattern. Do NOT use `Resume_Builder` or `Ai_Resume_Generator` — those are complex builder pages, not simple record pages
  - The FlexiPage file developer name must match the filename exactly: `Job_Search_Config.flexipage-meta.xml` → developer name `Job_Search_Config`
  - If `Award.flexipage-meta.xml` uses a `<template>` element with a specific layout template name (e.g., `force_recordLayout:Full_Width`), keep it — it controls the page column layout. Only change the object-specific fields
  - If the retrieved `Award` FlexiPage contains `<platformActionlist>` or `<quickActionList>` blocks, retain them — they may be required by the metadata type

---

### TASK 7: Update `Job_Application` FlexiPage — Add `Search_Config__c` Field

- **What:** Retrieve the existing `Job_Application` FlexiPage and add the `Search_Config__c` lookup field to a new "Source" section. The existing FlexiPage uses `force:detailPanel` — the `Search_Config__c` field will be added as an explicit field component alongside the detail panel.
- **Step 1 — Retrieve the FlexiPage:**
  ```bash
  sf project retrieve start \
    --metadata "FlexiPage:Job_Application" \
    --target-org AwesomeOpossumDevHub
  ```
  Output: `force-app/main/default/flexipages/Job_Application.flexipage-meta.xml`
- **Step 2 — Inspect the structure.** Read the retrieved XML and identify:
  - The `<flexiPageRegions>` element(s) — typically `main`, `sidebar`, or a named column
  - Where the `force:detailPanel` or main content component is positioned
  - Whether there is a `sidebar` or secondary region that makes sense for a lookup field

- **Step 3 — Add the Source section.** The approach depends on what's in the retrieved file:

  **If the FlexiPage has a `sidebar` or `right` region:** Add the `Search_Config__c` component to the sidebar region as a `flexipage:fieldSectionItem`.

  **If the FlexiPage is single-region (main only):** Add a new `flexipage:fieldSection` component in the `main` region, appended after the existing components. Example block to add inside the region's `<itemInstances>` list:

  ```xml
  <itemInstances>
      <componentInstance>
          <visibilityRule>
              <booleanFilter/>
              <criteria/>
          </visibilityRule>
          <componentName>flexipage:fieldSection</componentName>
          <componentInstanceProperties>
              <name>title</name>
              <value>Source</value>
          </componentInstanceProperties>
          <componentInstanceProperties>
              <name>useHeading</name>
              <value>true</value>
          </componentInstanceProperties>
          <subComponentInstances>
              <componentInstance>
                  <visibilityRule>
                      <booleanFilter/>
                      <criteria/>
                  </visibilityRule>
                  <componentName>flexipage:fieldSectionItem</componentName>
                  <componentInstanceProperties>
                      <name>field</name>
                      <value>Search_Config__c</value>
                  </componentInstanceProperties>
              </componentInstance>
          </subComponentInstances>
      </componentInstance>
  </itemInstances>
  ```

  > **If the retrieved FlexiPage XML structure does not match the above pattern**, do not guess — match the structure of other existing component blocks in the same file. Copy the pattern of an existing simple field component if one exists; otherwise add the field to the standard layout for `JobApplication__c` instead (see gotcha below).

- **Deploy:**
  ```bash
  sf project deploy start \
    --metadata "FlexiPage:Job_Application" \
    --target-org AwesomeOpossumDevHub --wait 10
  ```
- **Verify:** Open any `JobApplication__c` record → "Source" section appears with the `Search Config` lookup field (blank for existing records — expected)
- **Gotchas:**
  - **Never edit `Job_Application.flexipage-meta.xml` from scratch** — the existing page has LWC components, quick actions, utility items, and section layout that will be lost. Always edit the retrieved version
  - If the FlexiPage uses `force:detailPanel` rendering the standard layout, and the `flexipage:fieldSection` approach fails to deploy (incompatible with template type), **fallback:** retrieve the `JobApplication__c` standard layout, add `Search_Config__c` to it, and deploy the layout instead
  - After this deploy, existing `JobApplication__c` records will show the "Source" section with an empty `Search Config` field — this is expected behavior; only records created by the pipeline after Phase 3 will have it populated
  - `<visibilityRule>` with empty `<booleanFilter/>` and `<criteria/>` means "always visible" — do not remove these elements even though they are empty; the metadata API requires them in some API versions
  - Do NOT add a related list for `Job_Applications` on this FlexiPage per requirements: navigation is one-directional (app → config click-through only)

---

### TASK 8: Create "Active Configs" List View

- **What:** Create a list view for `Job_Search_Config__c` filtered to active records. The pipeline smoke test in Tier 2 E2E uses this view to confirm the correct records are returned.
- **File:** `force-app/main/default/objects/Job_Search_Config__c/listViews/Active_Configs.listView-meta.xml`
- **Create directory:**
  ```bash
  mkdir -p force-app/main/default/objects/Job_Search_Config__c/listViews
  ```
- **File content:**
  ```xml
  <?xml version="1.0" encoding="UTF-8"?>
  <ListView xmlns="http://soap.sforce.com/2006/04/metadata">
      <fullName>Active_Configs</fullName>
      <filterScope>Everything</filterScope>
      <filters>
          <field>Is_Active__c</field>
          <operation>equals</operation>
          <value>1</value>
      </filters>
      <label>Active Configs</label>
      <columns>NAME</columns>
      <columns>Keywords__c</columns>
      <columns>Daily_Limit__c</columns>
      <columns>Schedule_Hour__c</columns>
      <columns>Schedule_Minute__c</columns>
      <columns>Last_Run_At__c</columns>
      <sharedTo>
          <allInternalUsers/>
      </sharedTo>
  </ListView>
  ```
- **Deploy:**
  ```bash
  sf project deploy start \
    --metadata "ListView:Job_Search_Config__c.Active_Configs" \
    --target-org AwesomeOpossumDevHub --wait 10
  ```
- **Validate (dry run):**
  ```bash
  sf project deploy start \
    --metadata "ListView:Job_Search_Config__c.Active_Configs" \
    --target-org AwesomeOpossumDevHub --dry-run --wait 10
  ```
- **Gotchas:**
  - For Checkbox fields, the filter `<value>` for true is `1` (not `true` or `True`) — `1` is the correct Salesforce metadata value for a checkbox "equals true" filter
  - `<filterScope>Everything</filterScope>` means the filter applies across all records (not just "My Records"). This is required for a shared operations-style list view
  - `<sharedTo><allInternalUsers/></sharedTo>` makes the view visible to everyone — if you want it admin-only, use `<sharedTo><roles>...</roles></sharedTo>` instead
  - `NAME` (uppercase, no suffix) is the API name for the standard Name field column in a list view — do NOT use `Name__c`
  - The `<fullName>` must match the filename prefix (`Active_Configs`) and be consistent with the metadata reference in the deploy command

---

## Deployment Sequence Summary

Run in this exact order — each step depends on the prior one:

```
1. TASK 1:   Deploy 3 validation rules
             (depends on: Job_Search_Config__c object + all 11 fields — confirmed from Phase 1)

2. TASK 2:   Deploy Job Search Config Layout
             (depends on: all 11 fields exist in org)

3. TASK 3:   Retrieve Admin profile → add layoutAssignments → deploy Admin profile
             (depends on: Job Search Config Layout deployed in TASK 2)

4. TASK 4:   Deploy Job_Search_Config__c custom tab
             (depends on: object exists)

5. TASK 5:   Retrieve Resume app → add tab → deploy
             (depends on: Job_Search_Config__c tab deployed in TASK 4)

6. TASK 6:   Retrieve Award FlexiPage → create Job_Search_Config FlexiPage → deploy
             (depends on: layout deployed in TASK 2; tab deployed in TASK 4)
             ** MANUAL STEP: Activate FlexiPage in Setup → App Builder after deploy **

7. TASK 7:   Retrieve Job_Application FlexiPage → add Search_Config__c → deploy
             (depends on: Search_Config__c field exists — confirmed from Phase 1)

8. TASK 8:   Deploy Active_Configs list view
             (depends on: Is_Active__c field exists — confirmed from Phase 1)
```

---

## Testing Framework

### Testing Tier Applicability

| Phase Content | Tier 1 (Unit Tests) | Tier 2 (E2E) | Tier 3 (User Review) |
|---|---|---|---|
| Validation Rules, Layout, FlexiPages, Tab, App, List View | SKIP Tier 1 | YES | YES |

**Phase 3 is declarative only** — no Apex classes created or modified. Skip Tier 1 test class generation. Run regression only.

---

### Tier 1: Unit Tests

**Applies to this phase: NO** — All components are declarative (validation rules, layout, FlexiPage, tab, app, list view). No new Apex.

**Regression run (required before Tier 2):**
```bash
sf apex run test --test-level RunLocalTests --target-org AwesomeOpossumDevHub --result-format human --wait 10
```

**Baseline from Phase 2:** 86/88 tests pass. The 2 pre-existing failures in `AIInterviewGuideControllerTest` are expected and unrelated to this feature. Any new failure here indicates a declarative change broke an existing Apex test — investigate before proceeding to Tier 2.

**Gate criteria:** Same as Phase 2 baseline (86/88) or better. Zero new failures.

---

### Tier 2: E2E Testing

Before running E2E scenarios, create the two test records from Appendix C of the requirements:

**Test Record 1 — Salesforce Developer Nightly (Active):**
```bash
sf data create record \
  --sobject Job_Search_Config__c \
  --values "Name='Salesforce Developer Nightly' Keywords__c='Salesforce Developer, Salesforce Engineer, SFDC Developer' Required_Skills__c='Apex;Lightning Web Components;Flow Builder;SOQL;Screen Flows' Bonus_Skills__c='Batch Apex;Queueable Apex;Integration Cloud;CPQ;Experience Cloud' Daily_Limit__c=10 Min_Annual_Salary__c=145000 Days_Back__c=1 Schedule_Hour__c=2 Schedule_Minute__c=30 Is_Active__c=true" \
  --target-org AwesomeOpossumDevHub
```

**Test Record 2 — Salesforce Architect Nightly (Active):**
```bash
sf data create record \
  --sobject Job_Search_Config__c \
  --values "Name='Salesforce Architect Nightly' Keywords__c='Salesforce Architect, Salesforce Solutions Architect, SFDC Architect' Required_Skills__c='Apex;Lightning Web Components;Integration Cloud' Bonus_Skills__c='CPQ;Marketing Cloud;Analytics Cloud;Field Service Lightning' Daily_Limit__c=8 Min_Annual_Salary__c=160000 Days_Back__c=1 Schedule_Hour__c=3 Schedule_Minute__c=0 Is_Active__c=true" \
  --target-org AwesomeOpossumDevHub
```

> If the VR `Keywords_Required_When_Active` deploys correctly, both records above will save without error since both have keywords and `Is_Active__c = true`.

| # | Scenario | Steps | Expected Result | Verification |
|---|---|---|---|---|
| E2E-1 | VR blocks invalid schedule hour | In UI: create record, set `Schedule_Hour__c = 25`, click Save | Error: "Schedule Hour must be between 0 and 23 (UTC)." | UI error message |
| E2E-2 | VR blocks invalid schedule minute | Create record, set `Schedule_Minute__c = 60`, click Save | Error: "Schedule Minute must be between 0 and 59." | UI error message |
| E2E-3 | VR blocks activate without keywords | Create record with `Is_Active__c = true`, leave `Keywords__c` blank, click Save | Error: "Keywords are required before activating a search config." | UI error message |
| E2E-4 | VR allows null schedule values | Create record with `Schedule_Hour__c` blank, `Schedule_Minute__c` blank, `Is_Active__c = false`, click Save | Record saves without error (null is treated as 0 = valid) | Record saved |
| E2E-5 | "Job Search Configs" tab visible in Resume app | Navigate to the Resume Lightning App | "Job Search Configs" tab appears in nav bar | Visual check |
| E2E-6 | Tab opens to `Job_Search_Config__c` object | Click "Job Search Configs" tab | Object home page opens; "Active Configs" list view appears | Visual check |
| E2E-7 | "Active Configs" list view shows only active records | Create 1 inactive record (Is_Active__c = false). Open "Active Configs" list view | Only the 2 active test records are visible; inactive record is not shown | Visual check / count |
| E2E-8 | Pipeline startup SOQL returns active records with all 9 contract fields | `sf data query --query "SELECT Id, Name, Keywords__c, Required_Skills__c, Bonus_Skills__c, Daily_Limit__c, Min_Annual_Salary__c, Schedule_Hour__c, Schedule_Minute__c, Days_Back__c FROM Job_Search_Config__c WHERE Is_Active__c = true ORDER BY Schedule_Hour__c ASC, Schedule_Minute__c ASC" --target-org AwesomeOpossumDevHub` | Returns 2 rows (both active test records) with no error | CLI query output |
| E2E-9 | Pipeline write-back succeeds | `sf data update record --sobject Job_Search_Config__c --record-id <id> --values "Last_Run_At__c='2026-03-27T02:30:00Z' Last_Run_Summary__c='{\"found\":45,\"new\":12,\"pushed\":5}'" --target-org AwesomeOpossumDevHub` | Record updates; `Last_Run_At__c` and `Last_Run_Summary__c` show new values | `sf data get record` query on the record |
| E2E-10 | `Search_Config__c` field visible on `JobApplication__c` record | Open any `JobApplication__c` record | "Source" section with `Search Config` field appears (blank for existing records) | Visual check |
| E2E-11 | `Job_Search_Config` FlexiPage renders all 5 layout sections | Open one of the test records | 5 sections visible: Search Configuration, Skills, Thresholds & Limits, Schedule, Pipeline Feedback | Visual check |

---

### Tier 3: User Review

**Code review checklist:**
- [ ] All 3 VR formulas match requirements: hour range (0-23), minute range (0-59), keywords required when active
- [ ] `<` and `>` are escaped as `&lt;` and `&gt;` in all VR XML files
- [ ] `Last_Run_At__c` and `Last_Run_Summary__c` both have `<behavior>Readonly</behavior>` in the layout
- [ ] Pipeline Feedback section has `<editHeading>false</editHeading>`
- [ ] Tab file uses `<sobjectName>Job_Search_Config__c</sobjectName>`
- [ ] App file has `<tabs>Job_Search_Config__c</tabs>` added without removing existing tabs
- [ ] FlexiPage `<sobjectType>` is `Job_Search_Config__c`
- [ ] List view filter uses `<value>1</value>` for checkbox true
- [ ] `Job_Application` FlexiPage was retrieved before editing (not created from scratch)
- [ ] No related list for `Job_Applications` added to `Job_Application` FlexiPage

**Declarative review checklist:**
- [ ] Setup → Object Manager → Job Search Config → Validation Rules — confirm all 3 rules are Active
- [ ] Setup → Object Manager → Job Search Config → Page Layouts — confirm "Job Search Config Layout" exists
- [ ] Setup → Object Manager → Job Search Config → Lightning Record Pages — confirm `Job Search Config` FlexiPage is present and Activated as Org Default
- [ ] Setup → App Manager → Resume (or equivalent) → confirm "Job Search Configs" is listed as a nav item

**User E2E testing checklist:**
- [ ] Navigate to Resume Lightning App → "Job Search Configs" tab visible
- [ ] Open "Job Search Configs" tab → "Active Configs" list view appears; 2 active test records are shown
- [ ] Open "Salesforce Developer Nightly" record → all 5 layout sections render correctly
- [ ] Verify "Pipeline Feedback" section fields are not editable via inline edit (Last Run At, Last Run Summary are read-only)
- [ ] Attempt to set Is Active = true on a config with no Keywords → VR error fires
- [ ] Set Schedule Hour = 25 → VR error fires
- [ ] Set Schedule Minute = 60 → VR error fires
- [ ] Navigate to any `JobApplication__c` record → "Source" section with `Search Config` field is visible
- [ ] Click the `Search Config` field link on a record that has one populated → navigates to the linked config record

---

## Phase Completion Protocol

When all tasks, Tier 1 regression, and Tier 2/3 tests pass:

1. **Update master plan Phase Registry:** Set Phase 3 status to `Complete`
2. **No regression test classes to add** (no Apex in this phase)
3. **Update Acceptance Criteria** in master plan — mark the following as `Complete`:
   - AC-1: Active configs readable by pipeline SOQL (both test records returned)
   - AC-2: Write-back updates `Last_Run_At__c` and `Last_Run_Summary__c` (verified in E2E-9)
   - AC-4: VRs fire correctly (verified in E2E-1, E2E-2, E2E-3)
   - AC-5: `Job Search Configs` tab visible in Resume Lightning app (verified in E2E-5)
   - AC-6: `Search_Config__c` field visible on `Job_Application` FlexiPage (verified in E2E-10)
   - AC-8: "Active Configs" list view shows only `Is_Active__c = true` records (verified in E2E-7)
4. **Also update Phase 1 status** from `Plan Generated` to `Complete` (Phase 1 was executed but not marked complete)
5. **Write Phase Summary** — add to `Prior Phase Summaries` in master plan:
   ```
   ### Phase 3: UI & Validation — Complete
   - Deployed: 3 validation rules (Schedule_Hour_Range, Schedule_Minute_Range,
     Keywords_Required_When_Active); Job Search Config Layout (5 sections, 11 fields,
     2 read-only); Admin profile layoutAssignment; Job_Search_Config__c custom tab;
     Resume app updated with new tab; Job_Search_Config FlexiPage (manually activated);
     Job_Application FlexiPage updated with Search_Config__c; Active_Configs list view
   - Test records: Salesforce Developer Nightly + Salesforce Architect Nightly (both active)
   - Test classes: none (declarative phase)
   - Key decisions: [note any changes made during implementation, e.g. FlexiPage template used]
   - Known issues: [any issues discovered]
   ```
6. **Commit:**
   ```bash
   /sf-commit
   ```

---

## Feature Complete

Phase 3 is the final phase. When complete, the full `Job Search Config` feature is deployed:

- ✅ **Phase 1 (Data Model):** `Job_Search_Config__c` object + 11 fields + `Search_Config__c` lookup on `JobApplication__c` + Admin FLS
- ✅ **Phase 2 (Security):** `Anthropic_Claude` permission set + assignment + `Althropic_Claude` retired
- ✅ **Phase 3 (UI & Validation):** 3 VRs + layout + tab + app update + FlexiPages + list view

The JobFinder pipeline can now:
1. Read active `Job_Search_Config__c` records at startup via the pipeline SOQL contract
2. Write back `Last_Run_At__c` and `Last_Run_Summary__c` after each run
3. Populate `Search_Config__c` on new `JobApplication__c` records at insert time
