---
name: sf-trigger-patterns
description: Reference library for Salesforce Apex trigger patterns — canonical interface templates, trigger/handler/processor skeletons, meta XML formats, routing patterns, bulkification, recursion prevention, and common deploy errors.
---

# SF Trigger Patterns — Reference Skill

This skill is referenced by `.claude/commands/sf-implement-trigger.md`. Contains all canonical templates and patterns.

---

## 1. Canonical Interface Templates

### `TriggerHandlerInterface.cls`

```apex
public interface TriggerHandlerInterface {
    void beforeInsert(List<SObject> newList);
    void beforeUpdate(List<SObject> newList, Map<Id, SObject> oldMap);
    void beforeDelete(Map<Id, SObject> oldMap);
    void afterInsert(List<SObject> newList, Map<Id, SObject> newMap);
    void afterUpdate(List<SObject> newList, Map<Id, SObject> newMap, Map<Id, SObject> oldMap);
    void afterDelete(Map<Id, SObject> oldMap);
    void afterUndelete(List<SObject> newList, Map<Id, SObject> newMap);
}
```

### `RecordProcessorInterface.cls`

```apex
public interface RecordProcessorInterface {
    void handleBeforeInsert(List<SObject> newList);
    void handleBeforeUpdate(List<SObject> newList, Map<Id, SObject> oldMap);
    void handleBeforeDelete(List<SObject> newList, Map<Id, SObject> oldMap);
    void handleAfterInsert(List<SObject> newList, Map<Id, SObject> newMap);
    void handleAfterUpdate(List<SObject> newList, Map<Id, SObject> newMap, Map<Id, SObject> oldMap);
    void handleAfterDelete(List<SObject> newList, Map<Id, SObject> oldMap);
    void handleAfterUndelete(List<SObject> newList, Map<Id, SObject> newMap);
}
```

---

## 2. Trigger Template

`force-app/main/default/triggers/{ObjectName}Trigger.trigger`

```apex
trigger {ObjectName}Trigger on {ObjectName} (before insert, before update, before delete, after insert, after update, after delete, after undelete) {

    switch on Trigger.operationType
    {
        when BEFORE_INSERT {
            {ObjectName}TriggerHandler.beforeInsert(Trigger.new);
        }
        when BEFORE_UPDATE {
            {ObjectName}TriggerHandler.beforeUpdate(Trigger.new, Trigger.oldMap);
        }
        when BEFORE_DELETE {
            {ObjectName}TriggerHandler.beforeDelete(Trigger.oldMap);
        }
        when AFTER_INSERT {
            {ObjectName}TriggerHandler.afterInsert(Trigger.new, Trigger.oldMap);
        }
        when AFTER_UPDATE {
            {ObjectName}TriggerHandler.afterUpdate(Trigger.new, Trigger.newMap, Trigger.oldMap);
        }
        when AFTER_DELETE {
            {ObjectName}TriggerHandler.afterDelete(Trigger.oldMap);
        }
        when AFTER_UNDELETE {
            {ObjectName}TriggerHandler.afterUndelete(Trigger.new, Trigger.newMap);
        }
    }

}
```

**Rules:**
- All 7 contexts always included — never omit contexts even if currently unused
- Zero logic in the trigger body — only the switch statement and handler calls
- `afterInsert` passes `Trigger.oldMap` (which is null) to match handler signature

---

## 3. Handler Template

`force-app/main/default/classes/{ObjectName}TriggerHandler.cls`

```apex
public with sharing class {ObjectName}TriggerHandler implements TriggerHandlerInterface {

    // Recursion guard — prevents re-entry if trigger fires during a DML inside a processor
    public static Boolean hasRun = false;

    public static void beforeInsert(List<SObject> newList) {
        if (hasRun) return;
        // Filter: [describe any exclusion conditions here, e.g. bypass flag check]
        {ObjectName}Processor.handleBeforeInsert(newList);
    }

    public static void beforeUpdate(List<SObject> newList, Map<Id, SObject> oldMap) {
        if (hasRun) return;
        // Filter: [describe field-change conditions here, e.g. only route if Status__c changed]
        {ObjectName}Processor.handleBeforeUpdate(newList, oldMap);
    }

    public static void beforeDelete(Map<Id, SObject> oldMap) {
        if (hasRun) return;
        {ObjectName}Processor.handleBeforeDelete(null, oldMap);
    }

    public static void afterInsert(List<SObject> newList, Map<Id, SObject> newMap) {
        if (hasRun) return;
        {ObjectName}Processor.handleAfterInsert(newList, newMap);
    }

    public static void afterUpdate(List<SObject> newList, Map<Id, SObject> newMap, Map<Id, SObject> oldMap) {
        if (hasRun) return;
        // Filter: [describe field-change conditions here]
        {ObjectName}Processor.handleAfterUpdate(newList, newMap, oldMap);
    }

    public static void afterDelete(Map<Id, SObject> oldMap) {
        if (hasRun) return;
        {ObjectName}Processor.handleAfterDelete(null, oldMap);
    }

    public static void afterUndelete(List<SObject> newList, Map<Id, SObject> newMap) {
        if (hasRun) return;
        {ObjectName}Processor.handleAfterUndelete(newList, newMap);
    }
}
```

**Rules:**
- `public static Boolean hasRun = false;` — class-level, not instance-level
- All 7 methods implemented as `public static void` even if body is empty
- Handler filters/routes; it does NOT modify records
- Do not set `hasRun = true` in the handler — set it inside the processor if recursion prevention is needed for that specific operation

---

## 4. Processor Template

`force-app/main/default/classes/{ObjectName}Processor.cls`

```apex
public with sharing class {ObjectName}Processor implements RecordProcessorInterface {

    public static void handleBeforeInsert(List<SObject> newList) {
        List<{ObjectName}> records = (List<{ObjectName}>) newList;
        // TODO: [describe logic here]
    }

    public static void handleBeforeUpdate(List<SObject> newList, Map<Id, SObject> oldMap) {
        List<{ObjectName}> records = (List<{ObjectName}>) newList;
        // TODO: [describe logic here]
    }

    public static void handleBeforeDelete(List<SObject> newList, Map<Id, SObject> oldMap) {
        // TODO: [describe logic here]
    }

    public static void handleAfterInsert(List<SObject> newList, Map<Id, SObject> newMap) {
        List<{ObjectName}> records = (List<{ObjectName}>) newList;
        // TODO: [describe logic here]
    }

    public static void handleAfterUpdate(List<SObject> newList, Map<Id, SObject> newMap, Map<Id, SObject> oldMap) {
        List<{ObjectName}> records = (List<{ObjectName}>) newList;
        // TODO: [describe logic here]
    }

    public static void handleAfterDelete(List<SObject> newList, Map<Id, SObject> oldMap) {
        // TODO: [describe logic here]
    }

    public static void handleAfterUndelete(List<SObject> newList, Map<Id, SObject> newMap) {
        List<{ObjectName}> records = (List<{ObjectName}>) newList;
        // TODO: [describe logic here]
    }
}
```

**Rules:**
- Cast `List<SObject>` to the typed list at the top of each method that accesses typed fields
- For `beforeDelete` and `afterDelete`, `newList` is null — use `oldMap` to access records
- Empty method bodies are valid — implement them as empty stubs, not omitted

---

## 5. Meta XML Templates

### Trigger meta — `{ObjectName}Trigger.trigger-meta.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ApexTrigger xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>66.0</apiVersion>
    <status>Active</status>
</ApexTrigger>
```

### Class meta — `{ClassName}.cls-meta.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>66.0</apiVersion>
    <status>Active</status>
</ApexClass>
```

Use this meta XML for every `.cls` file: interfaces, handlers, processors, and test classes.

---

## 6. Routing Patterns

### Single Processor (all records go to one processor)

```apex
public static void beforeInsert(List<SObject> newList) {
    if (hasRun) return;
    {ObjectName}Processor.handleBeforeInsert(newList);
}
```

### Multi-Processor by Record Type

```apex
public static void beforeInsert(List<SObject> newList) {
    if (hasRun) return;

    List<{ObjectName}> typeARecords = new List<{ObjectName}>();
    List<{ObjectName}> typeBRecords = new List<{ObjectName}>();

    Map<String, Schema.RecordTypeInfo> rtMap =
        Schema.SObjectType.{ObjectName}.getRecordTypeInfosByDeveloperName();
    Id typeAId = rtMap.get('TypeA_Developer_Name').getRecordTypeId();
    Id typeBId = rtMap.get('TypeB_Developer_Name').getRecordTypeId();

    for ({ObjectName} rec : ({List<{ObjectName}>}) newList) {
        if (rec.RecordTypeId == typeAId) {
            typeARecords.add(rec);
        } else if (rec.RecordTypeId == typeBId) {
            typeBRecords.add(rec);
        }
    }

    if (!typeARecords.isEmpty()) {
        TypeAProcessor.handleBeforeInsert(typeARecords);
    }
    if (!typeBRecords.isEmpty()) {
        TypeBProcessor.handleBeforeInsert(typeBRecords);
    }
}
```

### Multi-Processor by Field Value

```apex
public static void beforeInsert(List<SObject> newList) {
    if (hasRun) return;

    List<{ObjectName}> retailRecords = new List<{ObjectName}>();
    List<{ObjectName}> enterpriseRecords = new List<{ObjectName}>();

    for ({ObjectName} rec : (List<{ObjectName}>) newList) {
        if (rec.Segment__c == 'Retail') {
            retailRecords.add(rec);
        } else if (rec.Segment__c == 'Enterprise') {
            enterpriseRecords.add(rec);
        }
    }

    if (!retailRecords.isEmpty()) {
        RetailProcessor.handleBeforeInsert(retailRecords);
    }
    if (!enterpriseRecords.isEmpty()) {
        EnterpriseProcessor.handleBeforeInsert(enterpriseRecords);
    }
}
```

### Field Change Filter (beforeUpdate / afterUpdate)

```apex
public static void beforeUpdate(List<SObject> newList, Map<Id, SObject> oldMap) {
    if (hasRun) return;

    List<{ObjectName}> changedRecords = new List<{ObjectName}>();
    for ({ObjectName} rec : (List<{ObjectName}>) newList) {
        {ObjectName} oldRec = ({ObjectName}) oldMap.get(rec.Id);
        if (rec.Status__c != oldRec.Status__c) {
            changedRecords.add(rec);
        }
    }

    if (!changedRecords.isEmpty()) {
        {ObjectName}Processor.handleBeforeUpdate(changedRecords, oldMap);
    }
}
```

### Bypass / Exclusion Filter

```apex
public static void beforeInsert(List<SObject> newList) {
    if (hasRun) return;

    List<SObject> filtered = new List<SObject>();
    for ({ObjectName} rec : (List<{ObjectName}>) newList) {
        // Skip records with bypass flag or created by integration user
        if (rec.Bypass_Trigger__c == true) continue;
        filtered.add(rec);
    }

    if (!filtered.isEmpty()) {
        {ObjectName}Processor.handleBeforeInsert(filtered);
    }
}
```

---

## 7. Before vs After Reference

| Context | Records Available | Can Modify Records | Can DML | Common Uses |
|---|---|---|---|---|
| `beforeInsert` | `Trigger.new` (no Ids yet) | Yes — set fields directly | No | Default values, field formatting, validation |
| `beforeUpdate` | `Trigger.new`, `Trigger.oldMap` | Yes — set fields directly | No | Recalculate derived fields, validation |
| `beforeDelete` | `Trigger.oldMap` | No | No | Prevent deletion via `addError` |
| `afterInsert` | `Trigger.new`, `Trigger.newMap` (Ids exist) | No — use DML | Yes | Create related records, send notifications |
| `afterUpdate` | `Trigger.new`, `Trigger.newMap`, `Trigger.oldMap` | No — use DML | Yes | Update related records, cascade changes |
| `afterDelete` | `Trigger.oldMap` | No | Yes | Clean up related records |
| `afterUndelete` | `Trigger.new`, `Trigger.newMap` | No — use DML | Yes | Restore related records, re-link data |

**Key rules:**
- Before context: modify fields directly on `Trigger.new` records — no DML needed
- After context: never modify `Trigger.new` — use DML (`update`, `insert`) for any changes
- `addError()` is only meaningful in before contexts (and beforeDelete)

---

## 8. Bulkification Patterns

### Collect → Query Once → Collect Updates → DML Once

```apex
// BAD — SOQL in a loop
for ({ObjectName} rec : records) {
    List<RelatedObject__c> related = [SELECT Id FROM RelatedObject__c WHERE Parent__c = :rec.Id];
}

// GOOD — bulk pattern
// Step 1: collect
Set<Id> parentIds = new Set<Id>();
for ({ObjectName} rec : records) {
    parentIds.add(rec.Id);
}

// Step 2: query once
Map<Id, List<RelatedObject__c>> relatedByParent = new Map<Id, List<RelatedObject__c>>();
for (RelatedObject__c related : [SELECT Id, Parent__c FROM RelatedObject__c WHERE Parent__c IN :parentIds]) {
    if (!relatedByParent.containsKey(related.Parent__c)) {
        relatedByParent.put(related.Parent__c, new List<RelatedObject__c>());
    }
    relatedByParent.get(related.Parent__c).add(related);
}

// Step 3: process
List<RelatedObject__c> toUpdate = new List<RelatedObject__c>();
for ({ObjectName} rec : records) {
    List<RelatedObject__c> children = relatedByParent.get(rec.Id);
    if (children != null) {
        for (RelatedObject__c child : children) {
            child.SomeField__c = rec.SomeField__c;
            toUpdate.add(child);
        }
    }
}

// Step 4: DML once
if (!toUpdate.isEmpty()) {
    update toUpdate;
}
```

**Rules:**
- Never query inside a for loop
- Never DML inside a for loop
- Collect all records to process first, then do one query, then one DML
- Triggers fire in batches of up to 200 records — always write as if the list has 200 records

---

## 9. Recursion Prevention Patterns

### Static Boolean (prevents all re-entry)

```apex
// In handler class:
public static Boolean hasRun = false;

// In each handler method:
public static void afterInsert(List<SObject> newList, Map<Id, SObject> newMap) {
    if (hasRun) return;
    {ObjectName}Processor.handleAfterInsert(newList, newMap);
}

// In processor, if this method does DML that would re-fire the trigger:
public static void handleAfterInsert(List<SObject> newList, Map<Id, SObject> newMap) {
    {ObjectName}TriggerHandler.hasRun = true;
    // ... DML that would re-fire trigger ...
    {ObjectName}TriggerHandler.hasRun = false; // Reset if future calls in same transaction are valid
}
```

### Static Set<Id> (prevents re-entry only for already-processed records)

```apex
// In handler class:
public static Set<Id> processedIds = new Set<Id>();

public static void afterUpdate(List<SObject> newList, Map<Id, SObject> newMap, Map<Id, SObject> oldMap) {
    List<SObject> unprocessed = new List<SObject>();
    for (SObject rec : newList) {
        if (!processedIds.contains(rec.Id)) {
            processedIds.add(rec.Id);
            unprocessed.add(rec);
        }
    }
    if (!unprocessed.isEmpty()) {
        {ObjectName}Processor.handleAfterUpdate(unprocessed, newMap, oldMap);
    }
}
```

Use `Set<Id>` when you need fine-grained control (some records can be re-processed, others cannot). Use `Boolean` when any re-entry should be blocked entirely.

---

## 10. Record Type Lookup (No SOQL)

```apex
// Get record type Id by developer name — zero SOQL
Map<String, Schema.RecordTypeInfo> rtMap =
    Schema.SObjectType.{ObjectName}.getRecordTypeInfosByDeveloperName();

Id retailRtId   = rtMap.get('Retail').getRecordTypeId();
Id enterpriseRtId = rtMap.get('Enterprise').getRecordTypeId();

// Safely handle missing record type
Schema.RecordTypeInfo rtInfo = rtMap.get('DeveloperName');
if (rtInfo != null) {
    Id rtId = rtInfo.getRecordTypeId();
}
```

**Rules:**
- Always use `getRecordTypeInfosByDeveloperName()` — not by label (labels can change, developer names cannot)
- Never query `RecordType` object in a trigger — it counts against SOQL limits and fails in bulk
- Developer name is the API name without `__c` (e.g. object `Lead`, developer name `Enterprise` not `Enterprise__c`)

---

## 11. Common Deploy Errors

| Error | Cause | Fix |
|---|---|---|
| `Interface method must be implemented: void beforeInsert(...)` | Handler class missing one of the 7 interface methods | Add all 7 methods to the handler class |
| `Method does not override or implement a method` | Method signature doesn't exactly match interface | Check parameter types — `List<SObject>` not `List<{ObjectName}>` in signature |
| `Variable does not exist: Trigger.oldMap` (in afterInsert) | `Trigger.oldMap` is null in afterInsert context | Pass null or `Trigger.oldMap` (null is fine — just don't dereference it in processor) |
| `Compile error: Return type of an overriding method must be the same` | Interface signature mismatch | Match return type and parameter types exactly from `TriggerHandlerInterface` |
| `Test coverage insufficient` | Test class doesn't cover enough of handler/processor | Add test methods that exercise each non-empty method in the processor |
| `CANNOT_INSERT_UPDATE_ACTIVATE_ENTITY` | Trigger itself has a compile error | Read the nested error; fix the referenced class, then redeploy trigger |
| `Dependent class is invalid and needs recompilation` | Class compiled against an old version of its dependency | Redeploy the dependency class first, then the dependent class |
| `Entity type 'Trigger' has duplicate trigger` | Trigger already exists for that object | Query `ApexTrigger` to find existing trigger — do not create a second one |
| `trigger event ... not valid` | Typo in trigger event list | Valid events: `before insert`, `before update`, `before delete`, `after insert`, `after update`, `after delete`, `after undelete` |
| `SObject row was retrieved via SOQL without querying...` | Accessing a field not in SELECT clause | Add field to SOQL query |

---

## Context Specification

- metadata_type: ApexClass, ApexTrigger
- context_path: {alias}/apex/
- inventory_file: {alias}/apex/_inventory.md
- detail_file_pattern: _(inventory only — no per-class detail files)_

### Change Detection Query
Uses: tooling API
```sql
SELECT Name, Status, LastModifiedDate, LastModifiedBy.Name, ApiVersion
FROM ApexClass
WHERE LastModifiedDate > {LAST_SCAN}
AND (Name LIKE '%TriggerHandler%' OR Name LIKE '%Processor%' OR Name LIKE '%Trigger%')
ORDER BY LastModifiedDate DESC
LIMIT 50
```

Also run for triggers:
```sql
SELECT Name, Status, LastModifiedDate, LastModifiedBy.Name
FROM ApexTrigger
WHERE LastModifiedDate > {LAST_SCAN}
ORDER BY LastModifiedDate DESC
LIMIT 50
```

### Inventory Columns
Class/Trigger Name | Type (Class/Trigger) | Status | API Version | Last Modified Date | Last Modified By

### Detail File Sections
_(No per-class detail files — the inventory file is sufficient for pre-flight context)_

---

## 12. Test Class Patterns

### Minimal test class skeleton

```apex
@isTest
private class {ObjectName}TriggerTest {

    @TestSetup
    static void setupTestData() {
        // Create representative test records
        // For each record type if applicable
        // Insert parent/related records needed by tested logic
    }

    @isTest
    static void testBeforeInsert_DefaultFieldsSet() {
        // Arrange
        {ObjectName} rec = new {ObjectName}(/* required fields */);

        // Act
        Test.startTest();
        insert rec;
        Test.stopTest();

        // Assert
        {ObjectName} result = [{SELECT fields FROM {ObjectName} WHERE Id = :rec.Id}];
        System.assertEquals('Expected Value', result.SomeField__c, 'Field should be set on insert');
    }

    @isTest
    static void testAfterInsert_RelatedRecordCreated() {
        // Arrange + Act
        {ObjectName} rec = new {ObjectName}(/* required fields */);
        Test.startTest();
        insert rec;
        Test.stopTest();

        // Assert
        List<RelatedObject__c> related = [SELECT Id FROM RelatedObject__c WHERE Parent__c = :rec.Id];
        System.assertEquals(1, related.size(), 'Should create one related record on insert');
    }

    @isTest
    static void testBulkInsert_200Records() {
        List<{ObjectName}> records = new List<{ObjectName}>();
        for (Integer i = 0; i < 200; i++) {
            records.add(new {ObjectName}(/* required fields */));
        }

        Test.startTest();
        insert records;
        Test.stopTest();

        // Assert no governor limit exceptions and expected outcomes
        System.assertEquals(200, [SELECT COUNT() FROM {ObjectName}], 'All 200 records should be inserted');
    }

    @isTest
    static void testBypassFlag_SkipsProcessing() {
        {ObjectName} rec = new {ObjectName}(Bypass_Trigger__c = true /* + required fields */);

        Test.startTest();
        insert rec;
        Test.stopTest();

        // Assert that processing was skipped (check that no side effects occurred)
    }

    @isTest
    static void testAfterDelete_CleanupOccurred() {
        // Arrange — query a record created in @TestSetup
        {ObjectName} rec = [{SELECT Id FROM {ObjectName} LIMIT 1}];

        // Act
        Test.startTest();
        delete rec;
        Test.stopTest();

        // Assert — verify expected cleanup behavior (e.g., related records removed, parent field updated)
        // TODO: replace with assertions specific to handleAfterDelete logic
    }

    @isTest
    static void testAfterUndelete_RestorationOccurred() {
        // Arrange — query and delete a record first to set up undelete scenario
        {ObjectName} rec = [{SELECT Id FROM {ObjectName} LIMIT 1}];
        delete rec;

        // Act
        Test.startTest();
        undelete rec;
        Test.stopTest();

        // Assert — verify expected restoration behavior (e.g., related records re-linked, parent field restored)
        // TODO: replace with assertions specific to handleAfterUndelete logic
    }
}
```

**Rules:**
- Always wrap DML in `Test.startTest()` / `Test.stopTest()` — this resets governor limits and executes async operations
- Each test method tests one scenario — not multiple unrelated behaviors
- Assert with descriptive messages (third parameter to `System.assertEquals`)
- Always include a bulk test (200 records) to verify no SOQL/DML in loops
- `@TestSetup` data is re-inserted fresh for each test method (rolled back between tests)
- Always include `testAfterDelete_*` and `testAfterUndelete_*` stubs even if the processor has empty implementations for those contexts — they ensure coverage and serve as placeholders when logic is added later
