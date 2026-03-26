---
description: "Generate and deploy Salesforce Apex trigger, trigger handler, processor class(es), and test class for a given object — following the TriggerHandlerInterface / RecordProcessorInterface pattern."
argument-hint: [path-to-summary]
---

# SF Implement Trigger

Takes a prior conversation summary describing a Salesforce object, asks targeted questions about business logic, then generates and deploys the full trigger stack: trigger file, trigger handler, processor class(es), and test class.

**Core design principles:**
- One trigger per object — zero logic in the trigger (switch statement only)
- Handler routes/filters records to processors — no record modifications in the handler
- Processors implement business logic — can be multiple per object
- All handlers implement `TriggerHandlerInterface`; all processors implement `RecordProcessorInterface`
- Always scaffold all 7 contexts; always include recursion guard; always generate test class

**Usage:** `/sf-implement-trigger <path-to-summary>` or `/sf-implement-trigger` (will prompt for summary path)

Load `skills/sf-trigger-patterns/SKILL.md` before starting — all templates, patterns, and error references are there.

---

## Phase 0: Pre-flight

1. Confirm org connection:
   ```bash
   sf org display --target-org <alias>
   ```
   If this fails, stop and instruct user to authenticate first.

2. Read the full summary/conversation file passed as argument. Extract:
   - Object API name (e.g. `Lead__c`, `Job_Application__c`)
   - Object purpose and key fields
   - Record types (if any)
   - Parent/child relationships

3. Confirm project structure exists:
   - `force-app/main/default/classes/` — stop if missing
   - `force-app/main/default/triggers/` — stop if missing

4. Check for existing interface classes:
   ```bash
   ls force-app/main/default/classes/ | grep -E "TriggerHandlerInterface|RecordProcessorInterface"
   ```
   If either is missing, create it from the canonical templates in `skills/sf-trigger-patterns/SKILL.md` Section 1, then deploy both before proceeding:
   ```bash
   sf project deploy start \
     --metadata "ApexClass:TriggerHandlerInterface" \
     --metadata "ApexClass:RecordProcessorInterface" \
     --target-org <alias> --wait 10
   ```

5. Check cached context for existing triggers before querying the org:

   a. Read `context/{alias}/objects/{ObjectName__c}.md` if it exists.
      - Look at the **Apex Triggers** section.
      - If a trigger is listed there: **STOP and warn the user.** Do not create a second trigger for the same object.

   b. If no context file exists, or the file has no triggers listed, confirm against the live org:
   ```bash
   sf data query --query "SELECT Id, Name, Status FROM ApexTrigger WHERE Name = '{ObjectName}Trigger'" --target-org <alias>
   ```
   If a trigger exists: **STOP and warn the user.** Do not create a second trigger for the same object.

   c. Also check `context/{alias}/apex/_inventory.md` (if it exists) for any Apex classes matching `{ObjectName}TriggerHandler` or `{ObjectName}Processor` — pre-existing handler/processor classes affect what Phase 4 and Phase 5 should do.

---

## Phase 1: Question Phase (CRITICAL)

After reading the summary, ask ALL of the following questions — grouped by category. Do not skip questions whose answers would determine what gets generated. Note that thorough answers produce better-scaffolded code.

---

### Handler Routing & Processor Structure

1. How many processor classes does this object need? Should all records be handled by one processor, or should records be routed to different processors based on a condition?
   *(e.g. one `LeadProcessor`, or `RetailLeadProcessor` + `EnterpriseLeadProcessor` based on record type)*

2. If multiple processors: what field or condition determines which processor a record is routed to?
   *(Record Type developer name, a Status field value, a Boolean flag, owner type, etc.)*

3. For `beforeUpdate` and `afterUpdate`: which specific fields, when changed, should trigger routing to a processor?
   *(e.g. "only route if Status__c changed" — if none specified, all updates will route)*

4. Should any records be excluded from all processing?
   *(e.g. records created by an integration user, records where Bypass_Trigger__c is true)*

5. Do records need to be filtered differently based on running user profile or permissions?

---

### Before Insert Logic

6. What fields need to be set or defaulted when a new record is created?
   *(e.g. Status = 'New', format a phone number, auto-populate a lookup based on another field)*

7. Are there any validations that must block the save on insert?
   *(e.g. required field not filled in code, duplicate check)*

---

### Before Update Logic

8. What field values need to be recalculated or set when a record is updated?
   *(Only applies when the fields from Q3 change)*

9. Are there any validations that must block the save on update?
   *(e.g. cannot revert Status backwards, cannot change owner if record is closed)*

---

### After Insert Logic

10. What related records need to be created when a new record is saved and has an Id?
    *(e.g. create a Task, create a child record, create an Activity)*

11. Are there notifications, emails, or async/queueable operations needed on insert?

---

### After Update Logic

12. What related records need to be updated or created when this record changes?
    *(e.g. roll up to parent, update child records, sync a field to a related object)*

13. Are there cascading operations on parent or child records when key fields change?

---

### Delete Logic

14. Is there any logic needed on before/after delete?
    *(e.g. prevent deletion of active records via `addError`, archive child records, clean up related data)*

---

### Undelete Logic

15. Is there any logic needed when records are restored via undelete?

---

### Test Scenarios

16. What are the primary happy-path test scenarios for each relevant context?
    *(e.g. "insert a Lead with Record Type = Enterprise, verify X happened")*

17. What edge cases should be tested?
    *(e.g. null fields, 200-record bulk batch, records with no record type, bypass flag set)*

---

After collecting all answers, confirm the plan before generating any files:

```
## Trigger Plan: {ObjectName}

### Processor Structure
- [Single/Multiple] processor(s): [list processor names]
- Routing condition: [describe]

### Handler Filters
- Field change filter (beforeUpdate/afterUpdate): [list fields]
- Exclusion filters: [list bypass conditions]

### Logic Summary
- beforeInsert: [summary of Q6/Q7 answers or "empty stub"]
- beforeUpdate: [summary or "empty stub"]
- afterInsert: [summary or "empty stub"]
- afterUpdate: [summary or "empty stub"]
- beforeDelete: [summary or "empty stub"]
- afterDelete: [summary or "empty stub"]
- afterUndelete: [summary or "empty stub"]

### Test Scenarios
- [list scenarios from Q16/Q17]

Proceed?
```

Wait for user confirmation before generating files.

---

## Phase 2: Verify / Create Interface Classes

Covered in Phase 0. If interface classes were missing and created there, they are already deployed. Skip this phase.

If Phase 0 was not re-run and the files are confirmed missing, create and deploy them now using canonical templates from `skills/sf-trigger-patterns/SKILL.md` Section 1.

---

## Phase 3: Generate Trigger File

**CREATE** `force-app/main/default/triggers/{ObjectName}Trigger.trigger`

Use the trigger template from `skills/sf-trigger-patterns/SKILL.md` Section 2.

- Replace `{ObjectName}` with the object API name (e.g. `Lead__c`, `Job_Application__c`)
- All 7 contexts always included
- No logic in the trigger body — switch and handler calls only

**CREATE** `force-app/main/default/triggers/{ObjectName}Trigger.trigger-meta.xml`

Use the meta XML from `skills/sf-trigger-patterns/SKILL.md` Section 5.

---

## Phase 4: Generate Trigger Handler Class

**CREATE** `force-app/main/default/classes/{ObjectName}TriggerHandler.cls`

Use the handler template from `skills/sf-trigger-patterns/SKILL.md` Section 3 and routing patterns from Section 6.

Apply the following based on Phase 1 answers:

- **Q1/Q2** — Single vs. multi-processor routing (see Section 6: Routing Patterns)
- **Q3** — Add field-change filter in `beforeUpdate` and `afterUpdate` methods
- **Q4** — Add exclusion/bypass filter logic in affected methods
- **Q5** — Add profile/permission checks if specified
- Leave method bodies empty (just `if (hasRun) return;` + processor call) for contexts with no filtering logic

**CREATE** `force-app/main/default/classes/{ObjectName}TriggerHandler.cls-meta.xml`

---

## Phase 5: Generate Processor Class(es)

For each processor identified in Phase 1 (Q1/Q2):

**CREATE** `force-app/main/default/classes/{ObjectName}[Variant]Processor.cls`

Use the processor template from `skills/sf-trigger-patterns/SKILL.md` Section 4.

Apply the following:

- **Q6** — Add `// TODO:` comment in `handleBeforeInsert` describing fields to set/default
- **Q7** — Add `// TODO:` comment describing validation logic (use `rec.addError(...)`)
- **Q8** — Add `// TODO:` comment in `handleBeforeUpdate` for field recalculations
- **Q9** — Add `// TODO:` comment describing update validations
- **Q10** — Add `// TODO:` comment in `handleAfterInsert` for related record creation
- **Q11** — Add `// TODO:` comment for notifications/async work
- **Q12/Q13** — Add `// TODO:` comment in `handleAfterUpdate` for cascading changes
- **Q14** — Add `// TODO:` comment in `handleBeforeDelete` / `handleAfterDelete`
- **Q15** — Add `// TODO:` comment in `handleAfterUndelete`

Only add descriptive `// TODO:` comments where the user described actual logic. Leave empty method bodies for contexts with no described logic.

**CREATE** `force-app/main/default/classes/{ObjectName}[Variant]Processor.cls-meta.xml` for each processor.

---

## Phase 6: Generate Test Class

**CREATE** `force-app/main/default/classes/{ObjectName}TriggerTest.cls`

Use the test class patterns from `skills/sf-trigger-patterns/SKILL.md` Section 12.

Structure:
- `@isTest private class {ObjectName}TriggerTest`
- `@TestSetup` method: creates representative test data based on Q16/Q17 answers; if record types exist, create records for each relevant type
- One `@isTest static void` method per key scenario from Q16
- Edge case methods from Q17
- Always include a bulk test with 200 records
- Each test method: arrange → DML (wrapped in `Test.startTest()` / `Test.stopTest()`) → assert
- Descriptive method names: `testBeforeInsert_DefaultFieldsSet()`, `testAfterInsert_TaskCreated()`, `testBulkInsert_200Records()`, etc.

**CREATE** `force-app/main/default/classes/{ObjectName}TriggerTest.cls-meta.xml`

---

## Phase 7: Deploy

Deploy in dependency order — classes must exist in the org before the trigger can compile.

```bash
# Step 1: Deploy handler, processor(s), and test class
sf project deploy start \
  --metadata "ApexClass:{ObjectName}TriggerHandler" \
  --metadata "ApexClass:{ObjectName}Processor" \
  --metadata "ApexClass:{ObjectName}TriggerTest" \
  --target-org <alias> --wait 10
```

If multiple processors, include each:
```bash
--metadata "ApexClass:{ObjectName}RetailProcessor" \
--metadata "ApexClass:{ObjectName}EnterpriseProcessor" \
```

```bash
# Step 2: Deploy trigger (after handler class is confirmed live)
sf project deploy start \
  --metadata "ApexTrigger:{ObjectName}Trigger" \
  --target-org <alias> --wait 10
```

If any step fails, read the error carefully. Common fixes are documented in `skills/sf-trigger-patterns/SKILL.md` Section 11.

**Do not proceed to Phase 8 until all deploys succeed.**

---

## Phase 8: Validation + Output Report

```bash
# Confirm trigger is active
sf data query --query "SELECT Id, Name, Status FROM ApexTrigger WHERE Name = '{ObjectName}Trigger'" --target-org <alias>

# Confirm classes deployed
sf data query --query "SELECT Id, Name, Status FROM ApexClass WHERE Name LIKE '{ObjectName}%'" --target-org <alias>
```

Produce this summary report:

```
## Trigger Implementation Summary

### Files Created
- ✅ {ObjectName}Trigger.trigger
- ✅ {ObjectName}Trigger.trigger-meta.xml
- ✅ {ObjectName}TriggerHandler.cls
- ✅ {ObjectName}TriggerHandler.cls-meta.xml
- ✅ {ObjectName}Processor.cls  (or list multiple)
- ✅ {ObjectName}Processor.cls-meta.xml
- ✅ {ObjectName}TriggerTest.cls
- ✅ {ObjectName}TriggerTest.cls-meta.xml

### Handler Routing
- Recursion guard: static Boolean hasRun
- Processor(s): [list each processor and the condition that routes to it]
- Field change filters: [list fields checked in beforeUpdate/afterUpdate, or "none"]
- Exclusion filters: [list any bypass conditions, or "none"]

### Processor Stubs
**{ObjectName}Processor** (or name each processor separately)
- handleBeforeInsert: [summary of TODO comment, or "empty stub"]
- handleBeforeUpdate: [summary or "empty stub"]
- handleBeforeDelete: [summary or "empty stub"]
- handleAfterInsert: [summary or "empty stub"]
- handleAfterUpdate: [summary or "empty stub"]
- handleAfterDelete: [summary or "empty stub"]
- handleAfterUndelete: [summary or "empty stub"]

### Test Scenarios Scaffolded
- [list each test method name]

### Deploy Results
- Step 1 (Classes): ✅ Success
- Step 2 (Trigger): ✅ Success

### Next Steps
1. Implement the TODO-commented logic in each processor method
2. Fill in @TestSetup with realistic field values and add System.assertEquals assertions
3. Run tests: sf apex test run --class-names {ObjectName}TriggerTest --target-org <alias>
4. Run /commit to commit generated files to git
```
