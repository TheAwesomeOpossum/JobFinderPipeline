# Phase 2: Security

**Feature:** Job Search Config
**Org:** AwesomeOpossumDevHub
**Phase:** 2 of 3
**Master Plan:** `projects/AwesomeOpossumDevHub/job-search-config/master-plan.md`
**Generated:** 2026-03-26

---

## Prior Phase Summary

> ⚠️ **Phase 1 has not yet been marked Complete.** The Prior Phase Summaries section in the master plan is still empty — update it after Phase 1 is verified, before executing Phase 2.

### Phase 1: Data Model — Plan Generated (not yet executed)

Planned deliverables (pending completion):
- `Job_Search_Config__c` object (Private sharing, field history enabled)
- 11 custom fields on `Job_Search_Config__c` (including `Required_Skills__c` and `Bonus_Skills__c` referencing `Skills` GVS)
- `Search_Config__c` Lookup field on `JobApplication__c` (`deleteConstraint=SetNull`, nullable)
- Admin profile FLS for all 12 new fields + object-level CRUD for `Job_Search_Config__c`

**Phase 2 dependency:** All 12 fields above must exist in the org before deploying the `Anthropic_Claude` permission set. `PermissionSet` XML that references fields not yet in the org will fail to deploy with a `FIELD_INTEGRITY_EXCEPTION`. Confirm Phase 1 is complete before starting TASK 2.

---

## Phase Goals

- Retrieve the existing `Althropic_Claude` permission set to capture current permissions before migration
- Create a replacement `Anthropic_Claude` permission set with all prior permissions plus new access to `Job_Search_Config__c` fields
- Assign `Anthropic_Claude` to the integration user (`your-sf-user@example.com`)
- Verify the integration user has the required access before removing the old perm set
- Remove the `Althropic_Claude` assignment and delete the perm set from the org

---

## Success Criteria

| # | Criterion | Verification Method | Tier |
|---|---|---|---|
| SC-1 | `Anthropic_Claude` perm set exists in org with correct OLS and FLS | `sf data query --query "SELECT Id, Name, Label FROM PermissionSet WHERE Name = 'Anthropic_Claude'" --target-org AwesomeOpossumDevHub` | Tier 2 (E2E) |
| SC-2 | `Anthropic_Claude` grants Read + Create + Edit (no Delete) on `Job_Search_Config__c` | Setup → Permission Sets → Anthropic Claude → Object Settings | Tier 2 (E2E) |
| SC-3 | `Anthropic_Claude` grants readable + editable FLS on all 11 `Job_Search_Config__c` fields | Setup → Permission Sets → Anthropic Claude → Field Permissions | Tier 2 (E2E) |
| SC-4 | `Anthropic_Claude` grants readable + editable FLS on `JobApplication__c.Search_Config__c` | Same as SC-3 for JobApplication fields | Tier 2 (E2E) |
| SC-5 | `Anthropic_Claude` assigned to `your-sf-user@example.com` | `sf data query --query "SELECT PermissionSet.Name FROM PermSetAssignment WHERE Assignee.Username = 'your-sf-user@example.com' AND PermissionSet.Name = 'Anthropic_Claude'" --target-org AwesomeOpossumDevHub` | Tier 2 (E2E) |
| SC-6 | `Althropic_Claude` is no longer assigned to the integration user | `sf data query --query "SELECT PermissionSet.Name FROM PermSetAssignment WHERE Assignee.Username = 'your-sf-user@example.com' AND PermissionSet.Name = 'Althropic_Claude'" --target-org AwesomeOpossumDevHub` returns 0 rows | Tier 2 (E2E) |
| SC-7 | `Althropic_Claude` perm set no longer exists in org | `sf data query --query "SELECT Id, Name FROM PermissionSet WHERE Name = 'Althropic_Claude'" --target-org AwesomeOpossumDevHub` returns 0 rows | Tier 2 (E2E) |
| SC-8 | Integration user can query `Job_Search_Config__c` via pipeline SOQL | Run pipeline startup query as integration user | Tier 3 (User Review) |
| SC-9 | Regression — all existing Apex tests still pass | `sf apex run test --test-level RunLocalTests` | Tier 1 (regression-only) |

---

## Skill & Context References

Load these before executing:
- `skills/sf-permissions/SKILL.md` — PermissionSet XML skeleton (Section 4), CLI introspection queries (Section 9), best practices (Section 11)
- `skills/sf-cli/SKILL.md` — retrieve/deploy commands, metadata delete pattern
- `context/AwesomeOpossumDevHub/permissions/_inventory.md` — confirms `Althropic_Claude` is the existing integration perm set

---

## Task List

---

### TASK 1: Retrieve Existing `Althropic_Claude` Permission Set

- **What:** Retrieve the current `Althropic_Claude` permission set XML from the org. This captures all existing permissions before migration — do NOT create `Anthropic_Claude` without first reading what `Althropic_Claude` currently grants.
- **Retrieve:**
  ```bash
  sf project retrieve start \
    --metadata "PermissionSet:Althropic_Claude" \
    --target-org AwesomeOpossumDevHub
  ```
- **Output file:** `force-app/main/default/permissionsets/Althropic_Claude.permissionset-meta.xml`
- **What to inspect:** Read the retrieved file and note:
  - All `<objectPermissions>` blocks (which objects and access levels are granted)
  - All `<fieldPermissions>` blocks (which fields are readable/editable)
  - All `<userPermissions>` blocks (any system permissions like API Enabled, View All Data, etc.)
  - All `<tabSettings>` and `<applicationVisibilities>` blocks if present
- **Gotchas:**
  - If the retrieve returns nothing (empty XML), the perm set may have been created but never saved with a description — it still exists. Check Setup → Permission Sets → `Althropic_Claude` manually to verify it has content.
  - Do NOT deploy `Althropic_Claude.permissionset-meta.xml` — this file is for reference only. All edits go into the new `Anthropic_Claude` file.

---

### TASK 2: Create `Anthropic_Claude` Permission Set File

- **What:** Create the new permission set XML file. Start by copying the full content of the retrieved `Althropic_Claude` file, then add the new `Job_Search_Config__c` and `JobApplication__c.Search_Config__c` permissions.
- **File:** `force-app/main/default/permissionsets/Anthropic_Claude.permissionset-meta.xml`
- **Create the directory if it does not exist:**
  ```bash
  mkdir -p force-app/main/default/permissionsets
  ```

**Step 1 — Base file (copy from Althropic_Claude, then change label/description):**

Use the XML structure from the retrieved `Althropic_Claude` file as the starting point. Replace only the `<label>` and `<description>` elements:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<PermissionSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>Anthropic Claude</label>
    <description>Integration user permission set for the JobFinder Python pipeline. Grants read/create/edit access to Job_Search_Config__c and JobApplication__c. Replaces the typo'd Althropic_Claude perm set.</description>

    <!-- === COPY ALL BLOCKS FROM Althropic_Claude HERE === -->
    <!-- Include all <objectPermissions>, <fieldPermissions>, <userPermissions>, etc. from the retrieved file -->

    <!-- === NEW BLOCKS ADDED FOR PHASE 2 (append below existing content) === -->

    <!-- Job_Search_Config__c object-level access -->
    <objectPermissions>
        <allowCreate>true</allowCreate>
        <allowDelete>false</allowDelete>
        <allowEdit>true</allowEdit>
        <allowRead>true</allowRead>
        <modifyAllRecords>false</modifyAllRecords>
        <object>Job_Search_Config__c</object>
        <viewAllRecords>false</viewAllRecords>
    </objectPermissions>

    <!-- Job_Search_Config__c field-level access (all 11 fields — read + edit) -->
    <fieldPermissions>
        <editable>true</editable>
        <field>Job_Search_Config__c.Keywords__c</field>
        <readable>true</readable>
    </fieldPermissions>
    <fieldPermissions>
        <editable>true</editable>
        <field>Job_Search_Config__c.Required_Skills__c</field>
        <readable>true</readable>
    </fieldPermissions>
    <fieldPermissions>
        <editable>true</editable>
        <field>Job_Search_Config__c.Bonus_Skills__c</field>
        <readable>true</readable>
    </fieldPermissions>
    <fieldPermissions>
        <editable>true</editable>
        <field>Job_Search_Config__c.Daily_Limit__c</field>
        <readable>true</readable>
    </fieldPermissions>
    <fieldPermissions>
        <editable>true</editable>
        <field>Job_Search_Config__c.Min_Annual_Salary__c</field>
        <readable>true</readable>
    </fieldPermissions>
    <fieldPermissions>
        <editable>true</editable>
        <field>Job_Search_Config__c.Days_Back__c</field>
        <readable>true</readable>
    </fieldPermissions>
    <fieldPermissions>
        <editable>true</editable>
        <field>Job_Search_Config__c.Schedule_Hour__c</field>
        <readable>true</readable>
    </fieldPermissions>
    <fieldPermissions>
        <editable>true</editable>
        <field>Job_Search_Config__c.Schedule_Minute__c</field>
        <readable>true</readable>
    </fieldPermissions>
    <fieldPermissions>
        <editable>true</editable>
        <field>Job_Search_Config__c.Is_Active__c</field>
        <readable>true</readable>
    </fieldPermissions>
    <fieldPermissions>
        <editable>true</editable>
        <field>Job_Search_Config__c.Last_Run_At__c</field>
        <readable>true</readable>
    </fieldPermissions>
    <fieldPermissions>
        <editable>true</editable>
        <field>Job_Search_Config__c.Last_Run_Summary__c</field>
        <readable>true</readable>
    </fieldPermissions>

    <!-- JobApplication__c.Search_Config__c lookup field — read + edit so pipeline can populate at insert -->
    <fieldPermissions>
        <editable>true</editable>
        <field>JobApplication__c.Search_Config__c</field>
        <readable>true</readable>
    </fieldPermissions>

</PermissionSet>
```

- **Gotchas:**
  - **Do NOT add `fieldPermissions` for standard fields** (e.g. `Name`, `OwnerId`, `CreatedById`, `LastModifiedById` on `Job_Search_Config__c`) — they are auto-visible and adding blocks for them causes deploy errors on some API versions.
  - **Check for duplicate blocks** — if `Althropic_Claude` already had a `JobApplication__c` `objectPermissions` block, do NOT add a second one. Merge access levels into a single block.
  - If `Althropic_Claude` has a `<userPermissions>` block for `ApiEnabled`, carry it over exactly — the integration user must retain API access.
  - `allowDelete=false` on `Job_Search_Config__c` is intentional per requirements (integration user should not be able to delete config records).
  - **`viewAllRecords=false`** is correct — the integration user (`your-sf-user@example.com`) is the System Administrator and already has visibility via profile; `viewAll` on the perm set would be redundant and over-permissioned.

---

### TASK 3: Deploy `Anthropic_Claude` Permission Set

- **What:** Deploy the new perm set to the org. Verify Phase 1 is complete before this step — all referenced fields must exist.
- **Pre-deploy check:**
  ```bash
  sf data query \
    --query "SELECT Id, QualifiedApiName FROM EntityDefinition WHERE QualifiedApiName = 'Job_Search_Config__c'" \
    --target-org AwesomeOpossumDevHub
  ```
  Confirms `Job_Search_Config__c` exists. If 0 rows returned, stop — Phase 1 fields are not yet deployed.
- **Dry-run first:**
  ```bash
  sf project deploy start \
    --metadata "PermissionSet:Anthropic_Claude" \
    --target-org AwesomeOpossumDevHub --dry-run --wait 10
  ```
- **Deploy:**
  ```bash
  sf project deploy start \
    --metadata "PermissionSet:Anthropic_Claude" \
    --target-org AwesomeOpossumDevHub --wait 10
  ```
- **Verify:**
  ```bash
  sf data query \
    --query "SELECT Id, Name, Label FROM PermissionSet WHERE Name = 'Anthropic_Claude'" \
    --target-org AwesomeOpossumDevHub
  ```
- **Gotchas:**
  - Deploy will fail with `FIELD_INTEGRITY_EXCEPTION` if any referenced field does not exist in the org. Confirm all Phase 1 fields are deployed.
  - If deploy fails on `Job_Search_Config__c` fields only (not on existing Althropic_Claude fields), Phase 1 is incomplete — stop and complete Phase 1 first.

---

### TASK 4: Assign `Anthropic_Claude` to Integration User

- **What:** Look up the integration user's ID and assign the new perm set. This must happen before removing the old perm set assignment.
- **Step 1 — Get integration user ID:**
  ```bash
  sf data query \
    --query "SELECT Id, Username FROM User WHERE Username = 'your-sf-user@example.com'" \
    --target-org AwesomeOpossumDevHub
  ```
  Note the `Id` value (format: `005xxxxxxxxxxxx`).

- **Step 2 — Get `Anthropic_Claude` perm set ID:**
  ```bash
  sf data query \
    --query "SELECT Id, Name FROM PermissionSet WHERE Name = 'Anthropic_Claude'" \
    --target-org AwesomeOpossumDevHub
  ```
  Note the `Id` value (format: `0PSxxxxxxxxxxxx`).

- **Step 3 — Create the perm set assignment:**
  ```bash
  sf data create record \
    --sobject PermSetAssignment \
    --values "AssigneeId='<UserId>' PermissionSetId='<PermSetId>'" \
    --target-org AwesomeOpossumDevHub
  ```
  Replace `<UserId>` and `<PermSetId>` with the IDs from Steps 1 and 2.

- **Verify assignment exists:**
  ```bash
  sf data query \
    --query "SELECT Id, PermissionSet.Name, Assignee.Username FROM PermSetAssignment WHERE Assignee.Username = 'your-sf-user@example.com' AND PermissionSet.Name = 'Anthropic_Claude'" \
    --target-org AwesomeOpossumDevHub
  ```
  Must return 1 row before proceeding to TASK 5.

- **Gotchas:**
  - Do NOT remove `Althropic_Claude` until this assignment is confirmed. An access gap would immediately break the pipeline's ability to authenticate or read configs.

---

### TASK 5: Verify Integration User Access (Gate Before Removal)

- **What:** Before touching the old perm set, confirm the integration user can access `Job_Search_Config__c` using only `Anthropic_Claude`. This is the safety gate that prevents accidental access loss.
- **Verify pipeline SOQL works with new perm set:**
  ```bash
  sf data query \
    --query "SELECT Id, Name, Keywords__c, Required_Skills__c, Bonus_Skills__c, Daily_Limit__c, Min_Annual_Salary__c, Schedule_Hour__c, Schedule_Minute__c, Days_Back__c FROM Job_Search_Config__c WHERE Is_Active__c = true ORDER BY Schedule_Hour__c ASC, Schedule_Minute__c ASC" \
    --target-org AwesomeOpossumDevHub
  ```
  This query runs as the authenticated user (System Admin). For a true integration-user-level test, check from the Setup UI:
  - Setup → Users → `your-sf-user@example.com` → Permission Sets — confirm `Anthropic Claude` appears in the list

- **Gotchas:**
  - The CLI session authenticates as the default/authenticated org user. The integration user (`your-sf-user@example.com`) in this org is the same as the System Administrator, so the CLI SOQL test is equivalent. In a multi-user org, a distinct integration user would need to be tested separately via login-as.

---

### TASK 6: Remove `Althropic_Claude` Assignment from Integration User

- **What:** Find and delete the `PermSetAssignment` record that links `Althropic_Claude` to the integration user. This un-assigns the perm set — does NOT delete the perm set yet.
- **Step 1 — Get the assignment record ID:**
  ```bash
  sf data query \
    --query "SELECT Id, PermissionSet.Name, Assignee.Username FROM PermSetAssignment WHERE Assignee.Username = 'your-sf-user@example.com' AND PermissionSet.Name = 'Althropic_Claude'" \
    --target-org AwesomeOpossumDevHub
  ```
  Note the `Id` value (format: `0a3xxxxxxxxxxxx`).

- **Step 2 — Delete the assignment:**
  ```bash
  sf data delete record \
    --sobject PermSetAssignment \
    --record-id <AssignmentId> \
    --target-org AwesomeOpossumDevHub
  ```

- **Verify removal:**
  ```bash
  sf data query \
    --query "SELECT Id FROM PermSetAssignment WHERE PermissionSet.Name = 'Althropic_Claude'" \
    --target-org AwesomeOpossumDevHub
  ```
  Must return 0 rows before proceeding to TASK 7. If any rows remain, there are other users still assigned — investigate before deleting the perm set.

---

### TASK 7: Delete `Althropic_Claude` Permission Set

- **What:** Permanently delete the `Althropic_Claude` permission set from the org. No users should be assigned at this point (verified in TASK 6).

**Option A — Via destructiveChanges (recommended):**

1. Create a temporary directory for the destructive deploy:
   ```bash
   mkdir -p /tmp/destruct-cleanup
   ```

2. Create `destructiveChanges.xml`:
   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <Package xmlns="http://soap.sforce.com/2006/04/metadata">
       <types>
           <members>Althropic_Claude</members>
           <name>PermissionSet</name>
       </types>
       <version>62.0</version>
   </Package>
   ```

3. Create an empty `package.xml` alongside it (required by the deploy API):
   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <Package xmlns="http://soap.sforce.com/2006/04/metadata">
       <version>62.0</version>
   </Package>
   ```

4. Deploy the destructive change:
   ```bash
   sf project deploy start \
     --manifest /tmp/destruct-cleanup/package.xml \
     --post-destructive-changes /tmp/destruct-cleanup/destructiveChanges.xml \
     --target-org AwesomeOpossumDevHub --wait 10
   ```

**Option B — Via Setup UI (safe fallback):**
- Setup → Permission Sets → Find `Althropic Claude` → Delete
- Use this if the destructiveChanges deploy fails or if you prefer manual control

- **Verify deletion:**
  ```bash
  sf data query \
    --query "SELECT Id, Name FROM PermissionSet WHERE Name = 'Althropic_Claude'" \
    --target-org AwesomeOpossumDevHub
  ```
  Must return 0 rows.

- **Gotchas:**
  - The delete will fail if any user is still assigned to `Althropic_Claude`. Verify TASK 6 zero-row check before attempting deletion.
  - The destructiveChanges API will also fail if the perm set is part of a Permission Set Group — check Setup → Permission Set Groups first (org has none per context scan, but verify).
  - **Do NOT delete the local `force-app/main/default/permissionsets/Althropic_Claude.permissionset-meta.xml` file from the filesystem until after the org deletion is confirmed** — it serves as a rollback reference.
  - After confirming deletion from org, the local `Althropic_Claude.permissionset-meta.xml` file can be deleted from the repo.

---

## Deployment Sequence Summary

Run in this exact order — each step is a gate for the next:

```
1. TASK 1: Retrieve Althropic_Claude → inspect current permissions
2. TASK 2: Create Anthropic_Claude.permissionset-meta.xml (copy + extend)
3. TASK 3: Deploy Anthropic_Claude to org
4. TASK 4: Assign Anthropic_Claude to your-sf-user@example.com
   VERIFY: Confirm assignment exists before proceeding
5. TASK 5: Verify integration user has correct access
   GATE: Do NOT proceed until access is confirmed
6. TASK 6: Remove Althropic_Claude assignment from integration user
   VERIFY: 0 rows returned for Althropic_Claude assignment before proceeding
7. TASK 7: Delete Althropic_Claude from org
```

---

## Testing Framework

### Tier 1: Unit Tests

**Applies to this phase: NO** — Phase 2 is declarative only (permission set deploy + data operations). No Apex classes created or modified.

**Regression run (still required):**
```bash
sf apex run test --test-level RunLocalTests --target-org AwesomeOpossumDevHub --result-format human --wait 10
```
Gate: All existing tests pass. A perm set deploy should not break Apex tests, but run this to confirm the Phase 1 declarative changes also caused no regressions.

---

### Tier 2: E2E Testing

| # | Scenario | Steps | Expected Result | Verification |
|---|---|---|---|---|
| E2E-1 | `Anthropic_Claude` exists in org | Query PermissionSet WHERE Name = 'Anthropic_Claude' | 1 row returned, Label = 'Anthropic Claude' | `sf data query --query "SELECT Id, Name, Label FROM PermissionSet WHERE Name = 'Anthropic_Claude'" --target-org AwesomeOpossumDevHub` |
| E2E-2 | `Anthropic_Claude` has correct OLS on `Job_Search_Config__c` | Setup → Permission Sets → Anthropic Claude → Object Settings → Job Search Config | Read=✓ Create=✓ Edit=✓ Delete=✗ | Setup UI inspection |
| E2E-3 | `Anthropic_Claude` has FLS on all 11 `Job_Search_Config__c` fields | Setup → Permission Sets → Anthropic Claude → Field Permissions → filter by Job Search Config | All 11 fields listed as readable + editable | Setup UI inspection |
| E2E-4 | `Anthropic_Claude` has FLS on `JobApplication__c.Search_Config__c` | Setup → Permission Sets → Anthropic Claude → Field Permissions → filter by Job Application | `Search Config` field readable + editable | Setup UI inspection |
| E2E-5 | `Anthropic_Claude` assigned to integration user | Query PermSetAssignment WHERE Username = 'your-sf-user@example.com' AND PermSetName = 'Anthropic_Claude' | 1 row returned | `sf data query --query "SELECT Id FROM PermSetAssignment WHERE Assignee.Username = 'your-sf-user@example.com' AND PermissionSet.Name = 'Anthropic_Claude'" --target-org AwesomeOpossumDevHub` |
| E2E-6 | `Althropic_Claude` is unassigned from integration user | Query PermSetAssignment WHERE Username = 'your-sf-user@example.com' AND PermSetName = 'Althropic_Claude' | 0 rows returned | Same query pattern as E2E-5 with Althropic_Claude |
| E2E-7 | `Althropic_Claude` perm set deleted from org | Query PermissionSet WHERE Name = 'Althropic_Claude' | 0 rows returned | `sf data query --query "SELECT Id FROM PermissionSet WHERE Name = 'Althropic_Claude'" --target-org AwesomeOpossumDevHub` |
| E2E-8 | Pipeline SOQL runs correctly | Run the startup query against `Job_Search_Config__c` | No INSUFFICIENT_ACCESS errors; query completes | `sf data query --query "SELECT Id, Name, Keywords__c FROM Job_Search_Config__c WHERE Is_Active__c = true" --target-org AwesomeOpossumDevHub` |

---

### Tier 3: User Review

**Code review checklist:**
- [ ] `Anthropic_Claude.permissionset-meta.xml` — label is `Anthropic Claude` (not `Althropic_Claude`)
- [ ] All `objectPermissions` from `Althropic_Claude` are present in `Anthropic_Claude` (nothing dropped)
- [ ] `Job_Search_Config__c` OLS: `allowCreate=true`, `allowDelete=false`, `allowEdit=true`, `allowRead=true`, `modifyAllRecords=false`, `viewAllRecords=false`
- [ ] All 11 `Job_Search_Config__c` field permissions are present (readable + editable)
- [ ] `JobApplication__c.Search_Config__c` field permission is present (readable + editable)
- [ ] No standard field FLS blocks (e.g. no `fieldPermissions` for `Job_Search_Config__c.Name`)
- [ ] No duplicate `objectPermissions` blocks for any single object

**User E2E testing checklist:**
- [ ] Open Setup → Permission Sets → confirm `Anthropic Claude` exists (not `Althropic Claude`)
- [ ] Open Setup → Permission Sets → Anthropic Claude → Object Settings — verify `Job Search Config` row shows Read/Create/Edit checked, Delete unchecked
- [ ] Open Setup → Permission Sets → Anthropic Claude → Assigned Users — verify `your-sf-user@example.com` is listed
- [ ] Open Setup → Permission Sets → confirm `Althropic Claude` no longer appears in the list
- [ ] Open Setup → Users → `your-sf-user@example.com` → Permission Sets — confirm `Althropic Claude` is absent, `Anthropic Claude` is present
- [ ] Log in as integration user (or use System Admin) → navigate to Job Search Configs tab — can create a new record

---

## Phase Completion Protocol

When all tasks and E2E/user review tests pass:

1. **Update master plan Phase Registry:** Set Phase 2 status to `Complete`
2. **No regression test classes to add** (no Apex in this phase)
3. **Write Phase Summary** — add to `Prior Phase Summaries` in master plan:
   ```
   ### Phase 2: Security — Complete
   - Deployed: Anthropic_Claude permission set (OLS + FLS for Job_Search_Config__c and
     JobApplication__c.Search_Config__c, plus all prior Althropic_Claude permissions)
   - Data operations: Assigned Anthropic_Claude to your-sf-user@example.com;
     removed Althropic_Claude assignment; deleted Althropic_Claude from org
   - Test classes: none (declarative + data operation phase)
   - Key decisions: [note which existing permissions were in Althropic_Claude and carried over]
   - Known issues: [any issues discovered]
   ```
4. **Delete local `Althropic_Claude` file from repo:**
   ```bash
   rm force-app/main/default/permissionsets/Althropic_Claude.permissionset-meta.xml
   ```
5. **Update Acceptance Criteria:** Mark AC-7 as `Complete` (`Anthropic_Claude` grants correct access; `Althropic_Claude` removed)
6. **Commit:**
   ```bash
   /sf-commit
   ```
7. **Next step:** Run `/sf-plan-feature --next job-search-config` to generate the Phase 3 plan.

---

## Phase Retrospective

**Completed:** 2026-03-27
**Executed by:** Claude

### Implementation Summary

- Tasks completed: 7/7
- Components deployed: `Anthropic_Claude` (PermissionSet)
- Data operations: PermissionSetAssignment created (`Anthropic_Claude` → `your-sf-user@example.com`); PermissionSetAssignment deleted (`Althropic_Claude` → `your-sf-user@example.com`); `Althropic_Claude` deleted from org via destructiveChanges
- Test classes: none (declarative + data operation phase)

### Issues Encountered & Resolutions

| # | Tier | Issue | Root Cause | Resolution | Attempts |
|---|---|---|---|---|---|
| 1 | Implement | `sf data create record` failed for PermSetAssignment | CLI data API does not support `PermSetAssignment` sObject via that command | Used anonymous Apex `insert PermissionSetAssignment` instead | 1 |
| 2 | Tier 1 | 2 test failures: `AIInterviewGuideControllerTest` | Pre-existing failures unrelated to perm set changes | Confirmed by user as pre-existing; documented, not fixed | 0 |

### Autonomous Decisions Made

- Used `PermissionSetAssignment` (correct Apex sObject name) after `PermSetAssignment` caused a compile failure on first attempt
- Discovered SFDX project root is `JobFinderSF/` subdirectory, not the `Salesforce/` workspace root — all deploy commands run from there

### Test Results

| Tier | Result | Details |
|---|---|---|
| Tier 1 (Regression) | PASSED | 86/88 tests passed; 2 pre-existing failures in `AIInterviewGuideControllerTest` (unrelated to this phase) |
| Tier 2 (E2E) | PASSED | 8/8 scenarios verified |
| Tier 3 (User Review) | APPROVED | Record creation deferred to Phase 3 (requires tab/layout); all other checklist items confirmed |
