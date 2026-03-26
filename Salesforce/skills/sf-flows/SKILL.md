---
name: sf-flows
description: "Reference for Salesforce Flow types, Tooling API queries, Flow metadata XML structure, element types, trigger configurations, best practices, and common patterns."
---

# SF Flows — Reference Skill

This skill provides comprehensive reference for Salesforce Flows — understanding, scanning, creating, modifying, and deploying Flows via metadata XML and CLI commands.

---

## 1. Flow Types Reference

### ProcessType Values

| ProcessType | UI Name | Has UI? | Notes |
|---|---|---|---|
| `AutoLaunchedFlow` | Autolaunched Flow | No | Runs in background; invoked by triggers, other flows, Apex, REST, or processes |
| `Flow` | Screen Flow | Yes | Contains `<screens>` elements; user-facing guided interaction |
| `Workflow` | Process Builder | No | **DEPRECATED** — Salesforce is retiring Process Builder. Migrate to Record-Triggered Flows. |
| `CustomEvent` | Platform Event-Triggered Flow | No | Fires when a platform event message is published |
| `InvocableProcess` | Autolaunched Flow (Invocable) | No | Legacy process type; treat as AutoLaunchedFlow |
| `ContactRequestFlow` | Contact Request Flow | Yes | Specialized screen flow for contact request channels |
| `CheckoutFlow` | Checkout Flow (Commerce) | Yes | Commerce-specific checkout flow |
| `Orchestration` | Orchestration | No | Multi-step orchestration across flows |
| `RoutingFlow` | Routing Flow | No | Omni-Channel skill-based routing |

### TriggerType Values (Record-Triggered Flows)

Record-triggered flows use `processType = AutoLaunchedFlow` combined with a `triggerType` in the `<start>` element.

| TriggerType | When It Fires | Key Characteristics |
|---|---|---|
| `RecordBeforeSave` | Before the record is saved to the database | Can modify the triggering record directly without DML; most efficient for field updates on the same record; cannot create/update/delete other records |
| `RecordAfterSave` | After the record is committed to the database | Record has an Id; use for creating/updating/deleting related records; supports scheduled paths |
| `RecordBeforeDelete` | Before the record is deleted | Use to validate or prevent deletion; cannot create/update other records |

### RecordTriggerType Values

These appear in the `<start>` element and control which DML operations fire the flow.

| RecordTriggerType | Description |
|---|---|
| `Create` | Flow fires only on record insert |
| `Update` | Flow fires only on record update |
| `CreateAndUpdate` | Flow fires on both insert and update |
| `Delete` | Flow fires on record delete (used with `RecordBeforeDelete` triggerType) |

---

## 2. CLI Commands

### Query Active Flows

```bash
# List all active flows (custom only, no managed packages)
sf data query \
  --query "SELECT Id, Definition.DeveloperName, VersionNumber, Status, ProcessType, TriggerType, Description, LastModifiedDate, LastModifiedBy.Name FROM Flow WHERE Status = 'Active' AND Definition.NamespacePrefix = null ORDER BY Definition.DeveloperName" \
  --use-tooling-api --target-org <alias>
```

### Query Flow Definitions (Active vs Latest Version)

```bash
# Shows which version is active and which is latest — useful to detect draft versions
sf data query \
  --query "SELECT DeveloperName, ActiveVersionId, LatestVersionId, LastModifiedDate FROM FlowDefinition WHERE NamespacePrefix = null ORDER BY DeveloperName" \
  --use-tooling-api --target-org <alias>
```

### Query Record-Triggered Flows Only

```bash
# Find all record-triggered flows with their trigger details
sf data query \
  --query "SELECT Id, Definition.DeveloperName, VersionNumber, ProcessType, TriggerType, TriggerObjectOrEvent.QualifiedApiName, RecordTriggerType, Description, LastModifiedDate FROM Flow WHERE Status = 'Active' AND TriggerType IN ('RecordBeforeSave','RecordAfterSave','RecordBeforeDelete') AND Definition.NamespacePrefix = null ORDER BY TriggerObjectOrEvent.QualifiedApiName, Definition.DeveloperName" \
  --use-tooling-api --target-org <alias>
```

### Query Flows for a Specific Object

```bash
# All active flows that trigger on a specific object
sf data query \
  --query "SELECT Id, Definition.DeveloperName, TriggerType, RecordTriggerType, Description FROM Flow WHERE Status = 'Active' AND TriggerObjectOrEvent.QualifiedApiName = '<ObjectApiName>' AND Definition.NamespacePrefix = null" \
  --use-tooling-api --target-org <alias>
```

### Retrieve and Deploy

```bash
# Retrieve a specific flow by developer name
sf project retrieve start \
  --metadata "Flow:<DeveloperName>" \
  --target-org <alias>

# Retrieve all flows
sf project retrieve start \
  --metadata "Flow" \
  --target-org <alias>

# Deploy a specific flow
sf project deploy start \
  --metadata "Flow:<DeveloperName>" \
  --target-org <alias> --wait 10

# Deploy a flow from source directory
sf project deploy start \
  --source-dir force-app/main/default/flows/<DeveloperName>.flow-meta.xml \
  --target-org <alias> --wait 10

# Deploy all flows in the project
sf project deploy start \
  --metadata "Flow" \
  --target-org <alias> --wait 10
```

### Check for Existing Flows Before Creating

Always check for existing flows on an object before creating a new one. Multiple record-triggered flows on the same object with the same trigger type can cause execution order issues.

```bash
sf data query \
  --query "SELECT Definition.DeveloperName, TriggerType, RecordTriggerType FROM Flow WHERE Status = 'Active' AND TriggerObjectOrEvent.QualifiedApiName = '<ObjectApiName>' AND Definition.NamespacePrefix = null" \
  --use-tooling-api --target-org <alias>
```

---

## 3. File Path and XML Structure

### Canonical File Path

```
force-app/main/default/flows/{DeveloperName}.flow-meta.xml
```

**Naming rule:** The filename (without `.flow-meta.xml`) must exactly match the `<DeveloperName>` of the flow definition. No spaces — use underscores.

### High-Level XML Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Flow xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>62.0</apiVersion>
    <description>Human-readable description of the flow purpose.</description>
    <label>My Flow Label</label>
    <processType>AutoLaunchedFlow</processType>
    <status>Active</status>
    <interviewLabel>My_Flow-{!$Flow.CurrentDateTime}</interviewLabel>

    <!-- Start element (required) -->
    <start>
        <locationX>50</locationX>
        <locationY>0</locationY>
        <connector>
            <targetReference>First_Element_Name</targetReference>
        </connector>
        <!-- Record-triggered flow fields (omit for screen/autolaunched flows) -->
        <object>Account</object>
        <recordTriggerType>CreateAndUpdate</recordTriggerType>
        <triggerType>RecordAfterSave</triggerType>
        <filterLogic>and</filterLogic>
        <filters>
            <field>Status__c</field>
            <operator>EqualTo</operator>
            <value>
                <stringValue>Active</stringValue>
            </value>
        </filters>
        <!-- Scheduled paths (after-save only) -->
        <scheduledPaths>
            <name>Run_3_Days_Later</name>
            <connector>
                <targetReference>Some_Element</targetReference>
            </connector>
            <label>3 Days After Created</label>
            <offsetNumber>3</offsetNumber>
            <offsetUnit>Days</offsetUnit>
            <recordField>CreatedDate</recordField>
            <timeSource>RecordField</timeSource>
        </scheduledPaths>
    </start>

    <!-- Flow elements (order in XML does not matter — connectors define execution order) -->
    <decisions>...</decisions>
    <assignments>...</assignments>
    <recordCreates>...</recordCreates>
    <recordUpdates>...</recordUpdates>
    <recordDeletes>...</recordDeletes>
    <recordLookups>...</recordLookups>
    <subflows>...</subflows>
    <screens>...</screens>
    <actionCalls>...</actionCalls>
    <loops>...</loops>
    <formulas>...</formulas>
    <variables>...</variables>
    <constants>...</constants>
    <textTemplates>...</textTemplates>
    <waits>...</waits>

    <!-- Environment (controls run mode) -->
    <environments>Default</environments>
    <runInMode>DefaultMode</runInMode>
</Flow>
```

### Start Element — Entry Conditions (Filters)

Entry conditions control which records fire the flow. Only records matching all filters will enter the flow.

```xml
<start>
    <locationX>50</locationX>
    <locationY>0</locationY>
    <connector>
        <targetReference>Check_Conditions</targetReference>
    </connector>
    <object>Case</object>
    <recordTriggerType>CreateAndUpdate</recordTriggerType>
    <triggerType>RecordAfterSave</triggerType>
    <filterLogic>and</filterLogic>
    <filters>
        <field>Status</field>
        <operator>EqualTo</operator>
        <value>
            <stringValue>Closed</stringValue>
        </value>
    </filters>
    <filters>
        <field>Type</field>
        <operator>NotEqualTo</operator>
        <value>
            <stringValue>Administrative</stringValue>
        </value>
    </filters>
</start>
```

**Filter operators:** `EqualTo`, `NotEqualTo`, `GreaterThan`, `GreaterThanOrEqualTo`, `LessThan`, `LessThanOrEqualTo`, `Contains`, `StartsWith`, `EndsWith`, `IsNull`, `IsChanged`

**filterLogic values:** `and`, `or`, `1 AND (2 OR 3)` (custom logic using 1-indexed filter positions)

---

## 4. Flow Element Types Reference

### Data Elements

| XML Element | UI Name | Description | Key Fields |
|---|---|---|---|
| `recordLookups` | Get Records | Query records from the database (SOQL equivalent) | `object`, `filters`, `queriedFields`, `sortField`, `sortOrder`, `limit`, `getFirstRecordOnly`, `storeOutputAutomatically` |
| `recordCreates` | Create Records | Insert new records | `object`, `inputAssignments`, `storeOutputAutomatically` |
| `recordUpdates` | Update Records | Update existing records | `object`, `filters`, `inputAssignments` or `inputReference` |
| `recordDeletes` | Delete Records | Delete records | `object`, `filters` |

### Logic Elements

| XML Element | UI Name | Description | Key Fields |
|---|---|---|---|
| `decisions` | Decision | Branch logic (if/then/else) with one or more outcomes | `rules` (outcomes with conditions), `defaultConnector` |
| `loops` | Loop | Iterate over a collection variable | `collectionReference`, `iterationOrder`, `nextValueConnector`, `noMoreValuesConnector` |
| `waits` | Wait | Pause the flow until a condition is met or time elapses | `waitEvents` |
| `collectionProcessors` | Collection processors | Sort, filter, or aggregate a collection | `collectionProcessorType`, `collectionReference` |

### Interaction Elements

| XML Element | UI Name | Description | Key Fields |
|---|---|---|---|
| `screens` | Screen | Display UI to the user (Screen Flows only) | `fields` (screen components), `showHeader`, `showFooter` |
| `actionCalls` | Action | Invoke an action (Apex, email alert, quick action, custom notification, etc.) | `actionName`, `actionType`, `inputParameters`, `outputParameters` |
| `subflows` | Subflow | Call another flow | `flowName`, `inputAssignments`, `outputAssignments` |

### Resource Elements (no execution — define data containers)

| XML Element | UI Name | Description | Key Fields |
|---|---|---|---|
| `variables` | Variable | Store data during flow execution | `name`, `dataType`, `isCollection`, `isInput`, `isOutput`, `objectType` |
| `constants` | Constant | Static values | `name`, `dataType`, `value` |
| `formulas` | Formula | Calculated values (evaluated when referenced) | `name`, `dataType`, `expression` |
| `textTemplates` | Text Template | Text with merge fields | `name`, `text`, `isViewedAsPlainText` |
| `assignments` | Assignment | Set variable values | `assignmentItems` (variable, operator, value) |
| `choices` | Choice | Single choice option for screen components | `choiceText`, `dataType`, `value` |
| `dynamicChoiceSets` | Dynamic Choice Set | Choices populated from a record query | `dataType`, `object`, `displayField`, `valueField` |

---

## 5. Element XML Examples

### Decision Element

```xml
<decisions>
    <name>Check_Status</name>
    <label>Check Status</label>
    <locationX>314</locationX>
    <locationY>278</locationY>
    <defaultConnector>
        <targetReference>End_Element</targetReference>
    </defaultConnector>
    <defaultConnectorLabel>Default Outcome</defaultConnectorLabel>
    <rules>
        <name>Is_Active</name>
        <conditionLogic>and</conditionLogic>
        <conditions>
            <leftValueReference>$Record.Status__c</leftValueReference>
            <operator>EqualTo</operator>
            <rightValue>
                <stringValue>Active</stringValue>
            </rightValue>
        </conditions>
        <connector>
            <targetReference>Update_Related_Records</targetReference>
        </connector>
        <label>Is Active</label>
    </rules>
</decisions>
```

### Record Lookup (Get Records)

```xml
<recordLookups>
    <name>Get_Related_Contacts</name>
    <label>Get Related Contacts</label>
    <locationX>314</locationX>
    <locationY>398</locationY>
    <connector>
        <targetReference>Loop_Contacts</targetReference>
    </connector>
    <filterLogic>and</filterLogic>
    <filters>
        <field>AccountId</field>
        <operator>EqualTo</operator>
        <value>
            <elementReference>$Record.Id</elementReference>
        </value>
    </filters>
    <getFirstRecordOnly>false</getFirstRecordOnly>
    <object>Contact</object>
    <queriedFields>Id</queriedFields>
    <queriedFields>FirstName</queriedFields>
    <queriedFields>LastName</queriedFields>
    <queriedFields>Email</queriedFields>
    <storeOutputAutomatically>true</storeOutputAutomatically>
</recordLookups>
```

### Record Create

```xml
<recordCreates>
    <name>Create_Task</name>
    <label>Create Follow-Up Task</label>
    <locationX>314</locationX>
    <locationY>518</locationY>
    <connector>
        <targetReference>Next_Element</targetReference>
    </connector>
    <inputAssignments>
        <field>Subject</field>
        <value>
            <stringValue>Follow up on case</stringValue>
        </value>
    </inputAssignments>
    <inputAssignments>
        <field>WhatId</field>
        <value>
            <elementReference>$Record.Id</elementReference>
        </value>
    </inputAssignments>
    <inputAssignments>
        <field>OwnerId</field>
        <value>
            <elementReference>$Record.OwnerId</elementReference>
        </value>
    </inputAssignments>
    <inputAssignments>
        <field>ActivityDate</field>
        <value>
            <elementReference>fx_DueDate</elementReference>
        </value>
    </inputAssignments>
    <object>Task</object>
    <storeOutputAutomatically>true</storeOutputAutomatically>
</recordCreates>
```

### Record Update (Update Triggering Record — Before Save)

```xml
<recordUpdates>
    <name>Set_Default_Fields</name>
    <label>Set Default Fields</label>
    <locationX>314</locationX>
    <locationY>278</locationY>
    <inputAssignments>
        <field>Priority__c</field>
        <value>
            <stringValue>Medium</stringValue>
        </value>
    </inputAssignments>
    <inputReference>$Record</inputReference>
</recordUpdates>
```

### Record Update (Update Other Records — After Save)

```xml
<recordUpdates>
    <name>Update_Parent_Account</name>
    <label>Update Parent Account</label>
    <locationX>314</locationX>
    <locationY>398</locationY>
    <connector>
        <targetReference>Next_Element</targetReference>
    </connector>
    <filterLogic>and</filterLogic>
    <filters>
        <field>Id</field>
        <operator>EqualTo</operator>
        <value>
            <elementReference>$Record.AccountId</elementReference>
        </value>
    </filters>
    <inputAssignments>
        <field>Last_Case_Date__c</field>
        <value>
            <elementReference>$Flow.CurrentDate</elementReference>
        </value>
    </inputAssignments>
    <object>Account</object>
</recordUpdates>
```

### Assignment

```xml
<assignments>
    <name>Set_Variables</name>
    <label>Set Variables</label>
    <locationX>314</locationX>
    <locationY>158</locationY>
    <connector>
        <targetReference>Check_Status</targetReference>
    </connector>
    <assignmentItems>
        <assignToReference>var_Counter</assignToReference>
        <operator>Add</operator>
        <value>
            <numberValue>1.0</numberValue>
        </value>
    </assignmentItems>
    <assignmentItems>
        <assignToReference>var_RecordCollection</assignToReference>
        <operator>Add</operator>
        <value>
            <elementReference>loop_CurrentItem</elementReference>
        </value>
    </assignmentItems>
</assignments>
```

### Loop

```xml
<loops>
    <name>Loop_Contacts</name>
    <label>Loop Contacts</label>
    <locationX>314</locationX>
    <locationY>518</locationY>
    <collectionReference>Get_Related_Contacts</collectionReference>
    <iterationOrder>Asc</iterationOrder>
    <nextValueConnector>
        <targetReference>Assign_Values</targetReference>
    </nextValueConnector>
    <noMoreValuesConnector>
        <targetReference>Update_Records</targetReference>
    </noMoreValuesConnector>
</loops>
```

### Formula Resource

```xml
<formulas>
    <name>fx_DueDate</name>
    <dataType>Date</dataType>
    <expression>{!$Flow.CurrentDate} + 7</expression>
</formulas>
```

### Variable Resource

```xml
<variables>
    <name>var_RecordCollection</name>
    <dataType>SObject</dataType>
    <isCollection>true</isCollection>
    <isInput>false</isInput>
    <isOutput>false</isOutput>
    <objectType>Contact</objectType>
</variables>
```

### Subflow

```xml
<subflows>
    <name>Call_Notification_Flow</name>
    <label>Send Notification</label>
    <locationX>314</locationX>
    <locationY>638</locationY>
    <connector>
        <targetReference>Next_Element</targetReference>
    </connector>
    <flowName>Send_Custom_Notification</flowName>
    <inputAssignments>
        <name>recordId</name>
        <value>
            <elementReference>$Record.Id</elementReference>
        </value>
    </inputAssignments>
</subflows>
```

### Action Call (Send Email Alert)

```xml
<actionCalls>
    <name>Send_Email_Alert</name>
    <label>Send Email Alert</label>
    <locationX>314</locationX>
    <locationY>398</locationY>
    <connector>
        <targetReference>Next_Element</targetReference>
    </connector>
    <actionName>Case.Case_Closed_Notification</actionName>
    <actionType>emailAlert</actionType>
    <inputParameters>
        <name>SObjectRowId</name>
        <value>
            <elementReference>$Record.Id</elementReference>
        </value>
    </inputParameters>
</actionCalls>
```

### Action Call (Invoke Apex)

```xml
<actionCalls>
    <name>Call_Apex_Action</name>
    <label>Calculate Pricing</label>
    <locationX>314</locationX>
    <locationY>398</locationY>
    <connector>
        <targetReference>Next_Element</targetReference>
    </connector>
    <actionName>CalculatePricingAction</actionName>
    <actionType>apex</actionType>
    <inputParameters>
        <name>recordIds</name>
        <value>
            <elementReference>var_RecordIds</elementReference>
        </value>
    </inputParameters>
    <outputParameters>
        <assignToReference>var_CalculatedPrice</assignToReference>
        <name>totalPrice</name>
    </outputParameters>
</actionCalls>
```

---

## 6. Flow Variable References

### System Variables

| Reference | Description |
|---|---|
| `$Record` | The triggering record (record-triggered flows) |
| `$Record__Prior` | The record values before the update (update-triggered flows only) |
| `$Flow.CurrentDate` | Today's date (Date type) |
| `$Flow.CurrentDateTime` | Current date/time (DateTime type) |
| `$Flow.CurrentStage` | Current stage in an orchestration |
| `$Flow.InterviewGuid` | Unique identifier for this flow interview |
| `$Flow.FaultMessage` | Error message from a failed element |
| `$Flow.ActiveStages` | Active stages in an orchestration |
| `$User.Id` | Running user's Id |
| `$User.FirstName` | Running user's first name |
| `$User.LastName` | Running user's last name |
| `$User.Email` | Running user's email |
| `$Organization.Id` | Org Id |
| `$Api.Session_ID` | Session Id for API calls |
| `$Profile.Name` | Running user's profile name |

### Merge Field Syntax

- Reference a flow variable: `{!var_MyVariable}`
- Reference a record field: `{!$Record.FieldName__c}`
- Reference prior value: `{!$Record__Prior.FieldName__c}`
- Reference formula: `{!fx_MyFormula}`
- Reference a lookup field on the record: `{!$Record.Account.Name}` (dot notation through relationships)

---

## 7. Record-Triggered Flow Best Practices

### Before-Save vs After-Save Decision Guide

| Criterion | Before Save | After Save |
|---|---|---|
| Modify the triggering record | Yes — direct field assignment, no DML | No — record is read-only |
| Create related records | No | Yes |
| Update other records | No | Yes |
| Delete records | No | Yes |
| Send notifications | No | Yes |
| Call subflows | Limited (no DML in called flow) | Yes |
| Invoke Apex | Limited (no DML) | Yes |
| Performance | Most efficient — no additional DML | Requires DML for any record changes |
| Scheduled paths | Not available | Available |
| Access to record Id | No (not yet assigned on insert) | Yes |

### Run Mode: System vs User

| Run Mode | Behavior |
|---|---|
| System Mode without Sharing | Full access to all records; bypasses sharing rules, field-level security, and CRUD checks. **Use with caution.** |
| System Mode with Sharing | Full field access but respects sharing rules. |
| User Mode with Sharing | Respects CRUD, FLS, and sharing rules. **Recommended for most flows.** |
| Default Mode | System context for record-triggered and autolaunched flows; user context for screen flows. |

In XML, run mode is controlled by:
```xml
<runInMode>DefaultMode</runInMode>
<!-- or -->
<runInMode>SystemModeWithSharing</runInMode>
```

### Entry Conditions Best Practices

- **Always add entry conditions** on record-triggered flows to limit which records trigger the flow. Flows without entry conditions fire on every record save, wasting resources.
- **Use `IsChanged` operator** for update-triggered flows to only fire when relevant fields change.
- Entry conditions use the same filter operators as `recordLookups` filters.
- For "Only when a record is updated to meet the condition" behavior, set `doesRequireRecordChangedToMeetCriteria` to `true` in the `<start>` element.

```xml
<start>
    <doesRequireRecordChangedToMeetCriteria>true</doesRequireRecordChangedToMeetCriteria>
    <!-- ... filters ... -->
</start>
```

### Avoid Recursion

- After-save record-triggered flows can re-trigger themselves if they update the triggering record's object.
- Salesforce limits recursion: the same flow can fire up to **2 additional times** in the same transaction for after-save flows (3 total executions).
- Before-save flows do NOT cause recursion because they do not perform DML.
- To prevent recursion: add entry conditions that exclude records already processed (e.g., check a checkbox field that the flow sets).

### Bulkification

- Flows process records **one at a time** through the flow path — there is no batching within a single flow interview.
- However, Salesforce **batches DML operations** across interviews: if 200 records trigger the flow, Salesforce executes 200 flow interviews but combines the DML into bulk operations.
- For record lookups (`Get Records`), each interview issues its own SOQL query — **this can hit SOQL limits in bulk operations.** Mitigate by using before-save flows (which don't need queries to update the triggering record) or by consolidating logic.
- Governor limits are shared across the entire transaction (all triggers, flows, processes, and Apex in the same save operation).

---

## 8. Salesforce Order of Execution

Understanding where flows execute in the save order is critical for troubleshooting and design.

| Step | What Executes |
|---|---|
| 1 | System validation rules (required fields, field formats, field length) |
| 2 | **Before-save record-triggered flows** |
| 3 | Before triggers (Apex) |
| 4 | Custom validation rules |
| 5 | Duplicate rules |
| 6 | Record saved to database (not yet committed) |
| 7 | After triggers (Apex) |
| 8 | Assignment rules, auto-response rules |
| 9 | Workflow rules (legacy — being retired) |
| 10 | Workflow field updates (re-fires before/after triggers if field updates occur) |
| 11 | **After-save record-triggered flows** |
| 12 | Entitlement rules |
| 13 | Roll-up summary field calculations |
| 14 | Cross-object formula field calculations |
| 15 | Criteria-based sharing rule evaluation |
| 16 | DML operation committed to database |
| 17 | Post-commit logic (sending email, enqueuing async Apex) |

**Key implications:**
- Before-save flows run **before** Apex before triggers and **before** custom validation rules — so a before-save flow can set field values that validation rules then check.
- After-save flows run **after** Apex after triggers — so trigger logic executes first.
- If an after-save flow updates the triggering record, the entire save cycle re-executes (steps 1-16) for that update.
- Process Builder workflows (legacy) execute before after-save flows.

---

## 9. Common Flow Patterns

### Pattern 1: Auto-Populate Fields on Record Creation (Before Save)

Set default field values when a record is created. Most efficient — no DML needed.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Flow xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>62.0</apiVersion>
    <label>Case - Set Defaults on Create</label>
    <processType>AutoLaunchedFlow</processType>
    <status>Active</status>
    <start>
        <locationX>50</locationX>
        <locationY>0</locationY>
        <connector>
            <targetReference>Set_Default_Priority</targetReference>
        </connector>
        <object>Case</object>
        <recordTriggerType>Create</recordTriggerType>
        <triggerType>RecordBeforeSave</triggerType>
    </start>
    <recordUpdates>
        <name>Set_Default_Priority</name>
        <label>Set Default Priority</label>
        <locationX>176</locationX>
        <locationY>158</locationY>
        <inputAssignments>
            <field>Priority</field>
            <value>
                <stringValue>Medium</stringValue>
            </value>
        </inputAssignments>
        <inputReference>$Record</inputReference>
    </recordUpdates>
    <environments>Default</environments>
</Flow>
```

### Pattern 2: Create Related Record After Insert (After Save)

Create a child record after the parent is inserted.

Key elements:
- `triggerType`: `RecordAfterSave`
- `recordTriggerType`: `Create`
- Use `$Record.Id` to link the new child record to the parent
- Use `recordCreates` element

### Pattern 3: Field Change Notification (After Save)

Send a notification when a specific field changes. Use entry conditions with `IsChanged` to only fire when the field actually changes.

```xml
<start>
    <connector>
        <targetReference>Send_Notification</targetReference>
    </connector>
    <doesRequireRecordChangedToMeetCriteria>true</doesRequireRecordChangedToMeetCriteria>
    <filterLogic>and</filterLogic>
    <filters>
        <field>Status</field>
        <operator>EqualTo</operator>
        <value>
            <stringValue>Closed</stringValue>
        </value>
    </filters>
    <object>Case</object>
    <recordTriggerType>Update</recordTriggerType>
    <triggerType>RecordAfterSave</triggerType>
</start>
```

### Pattern 4: Scheduled Path for Follow-Up (After Save)

Run logic at a future time relative to a field on the record. Only available on after-save flows.

```xml
<start>
    <connector>
        <targetReference>Immediate_Actions</targetReference>
    </connector>
    <object>Opportunity</object>
    <recordTriggerType>Create</recordTriggerType>
    <triggerType>RecordAfterSave</triggerType>
    <scheduledPaths>
        <name>Three_Days_After_Close</name>
        <connector>
            <targetReference>Send_Followup_Email</targetReference>
        </connector>
        <label>3 Days After Close Date</label>
        <offsetNumber>3</offsetNumber>
        <offsetUnit>Days</offsetUnit>
        <recordField>CloseDate</recordField>
        <timeSource>RecordField</timeSource>
    </scheduledPaths>
</start>
```

### Pattern 5: Loop and Collect Pattern (Avoid DML in Loops)

When iterating over records, collect updates in a collection variable, then perform a single bulk update after the loop.

Flow structure:
1. `recordLookups` — Get records to process
2. `loops` — Iterate over the collection
3. Inside loop: `assignments` — Add modified record to a collection variable
4. After loop: `recordUpdates` — Update all collected records in one DML

### Pattern 6: Subflow for Reusable Logic

Extract common logic into a separate autolaunched flow and call it from multiple parent flows using the `subflows` element. Pass data in via `inputAssignments` and receive results via `outputAssignments`.

### Pattern 7: Screen Flow for Guided Data Entry

Use `screens` elements with input components to collect user data, then create/update records based on user input. Screen flows use `processType = Flow`.

---

## 10. Flow vs Apex Trigger Decision Guide

| Criterion | Flow | Apex Trigger |
|---|---|---|
| **Complexity** | Simple to moderate logic; branching, field updates, basic record operations | Complex business logic, multi-step transactions, algorithmic processing |
| **Maintainability** | Admin-maintainable; visual builder | Requires developer; code-based |
| **Bulkification** | Automatic DML batching, but SOQL is per-interview | Full control over bulkification |
| **Callouts** | Limited (Apex actions or HTTP callout actions) | Full callout support with `@future` or `Queueable` |
| **Performance** | Good for simple operations; degrades with complex logic or many elements | Best performance for complex operations |
| **Testing** | No unit test requirement (but should be tested) | Requires 75% code coverage |
| **Error handling** | Fault paths (limited) | Full try/catch/finally |
| **Transaction control** | Limited | Full control (`Database.setSavepoint()`, `Database.rollback()`) |
| **Recursion control** | Automatic (2 additional executions max) | Manual (`static Boolean` flags) |
| **Multi-object in one transaction** | Multiple DML elements but no transaction grouping | Single transaction with savepoints |
| **Reuse** | Subflows | Classes and methods |

**Rule of thumb:**
- Use **Flows** for: field defaulting, simple notifications, basic related record creation, admin-owned logic, scheduled paths.
- Use **Apex Triggers** for: complex validation across many records, callouts, bulk data processing, operations requiring precise error handling, performance-critical paths.
- **Avoid mixing** both on the same object/trigger point when possible — it creates execution order dependencies that are hard to debug.

---

## 11. Gotchas and Limits

| Issue | Detail |
|---|---|
| **2,000 element limit** | A single flow interview can execute at most 2,000 elements. Flows with large loops can hit this. Mitigate by processing in batches or using Apex. |
| **Governor limits shared** | Flows share the same governor limits as Apex in the transaction: 150 DML statements, 100 SOQL queries, etc. A flow with a Get Records inside a loop will hit the 100 SOQL limit at 100 iterations. |
| **Before-save cannot DML** | Before-save flows can only modify `$Record` — they cannot create, update, or delete other records. Any attempt results in a runtime error. |
| **Screen flow data loss** | Screen flow interview data is lost if the user navigates away or the session times out. There is no auto-save. |
| **One active version** | Only one version of a flow can be active at a time. Activating a new version automatically deactivates the previous one. |
| **Process Builder + Flow conflicts** | If both Process Builder and record-triggered flows exist on the same object, Process Builder runs first. This can cause confusing behavior. Migrate Process Builders to flows. |
| **Flow recursion limit** | After-save flows can re-trigger themselves up to 2 additional times (3 total). Exceeding this causes the transaction to fail. |
| **Null handling** | Flow treats null and empty string as different values (unlike Apex SOQL). Use `IsNull` checks in decisions to handle null references safely. |
| **No SOQL aggregate** | Flows cannot perform aggregate SOQL queries (COUNT, SUM, AVG). Use Apex invocable actions for aggregation. |
| **Cross-object field references** | In record-triggered flows, you can reference fields on parent records via `$Record.ParentLookup__r.FieldName__c`, but only for the triggering record's direct parent — not grandparent or deeper. |
| **Scheduled path limitations** | Scheduled paths are only available on after-save record-triggered flows. The scheduled time is evaluated once — if the record changes after scheduling, the path still runs at the originally scheduled time (unless the record no longer meets entry conditions at execution time). |
| **Deploy with Active status** | Deploying a flow with `<status>Active</status>` will immediately activate it. Deploy as `Draft` first and activate manually if you want to review. |
| **DML order** | Multiple DML elements in the same flow execute in the order they appear in the flow path. If a Create fails, subsequent elements are skipped (unless a fault path is defined). |
| **Custom metadata in filters** | Flow entry conditions cannot reference custom metadata types or custom settings directly. Use a Get Records element or an Apex action to fetch those values. |
| **Version numbering** | Flow versions are auto-incremented. You cannot set a specific version number. Each deploy creates a new version. |
| **Deleting flows** | You cannot delete a flow definition that has an active version. Deactivate all versions first, then delete. Use `sf data query` on FlowDefinition to check. |

---

## 12. Common Deploy Errors

| Error | Cause | Fix |
|---|---|---|
| `The flow version can't be activated because it hasn't been validated` | Flow has errors (missing connectors, invalid references) | Open the flow in Flow Builder to see errors; fix missing connectors or invalid field references |
| `An error occurred while trying to save the flow: UNKNOWN_EXCEPTION` | XML structure issue, often a missing connector or reference to a deleted element | Validate that all `<targetReference>` values point to existing elements in the flow |
| `The flow references an unknown element` | A connector references an element name that doesn't exist in the XML | Check all `<targetReference>` values match element `<name>` values exactly |
| `The flow can't be saved because it contains a loop` | Circular connector path detected | Ensure no element connects back to itself or creates an infinite loop path |
| `Insufficient access rights on object: ObjectName` | Flow run mode doesn't have access to the object | Check run mode (System vs User) and ensure profile/permission set grants access |
| `The record couldn't be saved because it failed to trigger a flow` | Runtime error in an active flow | Check debug logs for the specific flow error; common causes: null reference, DML on wrong object in before-save |
| `You can't create or update records in a before-save triggered flow` | Before-save flow contains a Create Records or Update Records (on a different object) element | Move DML elements to an after-save flow or use an Apex action |
| `FLOW_ELEMENT_LIMIT_EXCEEDED` | Flow interview exceeded the 2,000 executed element limit | Reduce loop iterations, simplify logic, or move complex processing to Apex |
| `There are multiple flows defined on this object` | Warning when multiple record-triggered flows exist for the same trigger point | Not an error — but review execution order in Flow Trigger Explorer |

---

## 13. Flow Trigger Explorer

When multiple flows exist on the same object and trigger type, use Flow Trigger Explorer (Setup > Flow Trigger Explorer) to understand and control execution order. In the API, you cannot directly set execution order — it is managed through the Setup UI.

To query all flows on a given object for awareness:

```bash
sf data query \
  --query "SELECT Definition.DeveloperName, TriggerType, RecordTriggerType, Status FROM Flow WHERE Status = 'Active' AND TriggerObjectOrEvent.QualifiedApiName = '<ObjectApiName>' AND Definition.NamespacePrefix = null ORDER BY TriggerType" \
  --use-tooling-api --target-org <alias>
```

---

## 14. Testing Flows

### Test via CLI

```bash
# Insert a record to trigger a record-triggered flow
sf data create record \
  --sobject Case \
  --values "Subject='Test Flow' Status='New' Priority='High'" \
  --target-org <alias>

# Query to verify flow results
sf data query \
  --query "SELECT Id, Subject, Custom_Field__c FROM Case WHERE Subject = 'Test Flow' ORDER BY CreatedDate DESC LIMIT 1" \
  --target-org <alias>
```

### Test via Apex (for unit testing flows indirectly)

Record-triggered flows fire automatically when Apex test methods insert/update/delete records. No special setup needed — just assert on the expected outcomes.

```apex
@isTest
static void testRecordTriggeredFlow_SetsDefaultPriority() {
    Case c = new Case(Subject = 'Test', Status = 'New');
    Test.startTest();
    insert c;
    Test.stopTest();

    Case result = [SELECT Priority FROM Case WHERE Id = :c.Id];
    System.assertEquals('Medium', result.Priority, 'Flow should set default priority to Medium');
}
```

### Debug Flows

```bash
# Enable flow debug logging
sf data query \
  --query "SELECT Id, Definition.DeveloperName, InterviewStatus, CurrentElement, CreatedDate FROM FlowInterview WHERE Definition.DeveloperName = '<FlowDeveloperName>' ORDER BY CreatedDate DESC LIMIT 5" \
  --use-tooling-api --target-org <alias>
```

Check debug logs (Setup > Debug Logs) for `FLOW_START_INTERVIEWS`, `FLOW_ELEMENT_BEGIN`, `FLOW_ELEMENT_END`, and `FLOW_ELEMENT_ERROR` events.

---

## Context Specification

- metadata_type: Flow
- context_path: {alias}/flows/
- inventory_file: {alias}/flows/_inventory.md
- detail_file_pattern: {alias}/flows/{DeveloperName}.md

### Full Inventory Query
Uses: tooling API
```sql
SELECT Id, Definition.DeveloperName, VersionNumber, Status, ProcessType,
       Description, LastModifiedDate, LastModifiedBy.Name
FROM Flow
WHERE Status = 'Active'
AND Definition.NamespacePrefix = null
ORDER BY Definition.DeveloperName
```

_Note: `TriggerType` is NOT a valid column on the `Flow` object in Tooling API v66+. To get trigger type, use a separate query on `FlowDefinition` or inspect the flow XML._

### Change Detection Query
Uses: tooling API
```sql
SELECT Definition.DeveloperName, VersionNumber, Status, ProcessType,
       LastModifiedDate, LastModifiedBy.Name
FROM Flow
WHERE LastModifiedDate > {LAST_SCAN}
AND Definition.NamespacePrefix = null
ORDER BY LastModifiedDate DESC
LIMIT 50
```

### Inventory Columns
Developer Name | Label | Process Type | Trigger Type | Trigger Object | Status | Version | Last Modified Date | Last Modified By

### Detail File Sections (record-triggered flows only)
Identity (DeveloperName, Label, Description), Trigger Configuration (Object, TriggerType, RecordTriggerType, Entry Conditions), Element Summary (count by element type: decisions, assignments, recordCreates, recordUpdates, recordDeletes, recordLookups, subflows, screens, actionCalls, loops), Version History

### Naming Convention Detection
Analyze all Flow DeveloperName values and extract:
- **Prefix patterns:** e.g., `RT_`, `Screen_`, `Auto_`, `Scheduled_`
- **Separator style:** underscores vs camelCase vs mixed
- **Verb placement:** `Create_Invoice` vs `Invoice_Create` vs `Invoice_Creation_Flow`
- **Object inclusion:** whether object name is embedded in flow name
- Report findings in `## Detected Naming Conventions` at the top of `_inventory.md`
