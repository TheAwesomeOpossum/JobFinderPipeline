---
name: sf-automation-legacy
description: "Reference for legacy Salesforce automation — Workflow Rules, Workflow Field Updates, Workflow Alerts, and Approval Processes. Includes Tooling API queries, XML structures, and migration guidance to Flow."
---

# SF Automation Legacy Skill

---

## Important: Legacy Automation Deprecation Notice

Salesforce is actively deprecating Workflow Rules and Process Builder. As of Spring '23, Workflow Rules and Process Builder can no longer be created in new orgs. Existing rules continue to function but should be migrated to Flow.

**All findings from this skill should be flagged as "Legacy — consider migration to Flow."**

**New automation should ALWAYS use Flows** (record-triggered flows, scheduled flows, platform event-triggered flows, etc.).

Approval Processes are the **exception** — they remain actively supported and are NOT deprecated.

---

## 1. Workflow Rules

### Purpose

Workflow Rules evaluate record criteria and trigger automated actions when records are created or edited. They are one of the oldest automation tools in Salesforce.

### Query — Tooling API

```sql
SELECT Id, Name, TableEnumOrId, LastModifiedDate, LastModifiedBy.Name
FROM WorkflowRule
WHERE NamespacePrefix = null
ORDER BY TableEnumOrId, Name
```

### File Path

```
force-app/main/default/workflows/{ObjectName}.workflow-meta.xml
```

**Note:** All workflow rules, field updates, and alerts for an object are stored in a SINGLE workflow file per object, not as individual files.

### XML Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Workflow xmlns="http://soap.sforce.com/2006/04/metadata">
    <rules>
        <fullName>Set_Status_Active</fullName>
        <actions>
            <name>Update_Status_Active</name>
            <type>FieldUpdate</type>
        </actions>
        <active>true</active>
        <criteriaItems>
            <field>MyObject__c.Stage__c</field>
            <operation>equals</operation>
            <value>Approved</value>
        </criteriaItems>
        <description>Sets Status to Active when Stage is Approved.</description>
        <triggerType>onCreateOrTriggeringUpdate</triggerType>
    </rules>
</Workflow>
```

### Evaluation Criteria (triggerType)

| Value | Description |
|---|---|
| `onCreateOnly` | Evaluate only when a record is created. |
| `onCreateOrTriggeringUpdate` | Evaluate when created AND every time the record is edited to meet the criteria. |
| `onAllChanges` | Evaluate when created AND every time the record is edited (regardless of criteria). |

### Criteria Items

```xml
<criteriaItems>
    <field>MyObject__c.Status__c</field>
    <operation>equals</operation>
    <value>Active</value>
</criteriaItems>
<criteriaItems>
    <field>MyObject__c.Amount__c</field>
    <operation>greaterThan</operation>
    <value>1000</value>
</criteriaItems>
```

**Operations:** `equals`, `notEqual`, `greaterThan`, `lessThan`, `greaterOrEqual`, `lessOrEqual`, `contains`, `notContain`, `startsWith`, `includes`, `excludes`

### Formula Criteria

Instead of `criteriaItems`, rules can use a formula:

```xml
<formula>AND(ISPICKVAL(Stage__c, &quot;Approved&quot;), Amount__c &gt; 1000)</formula>
```

### Workflow Actions

A workflow rule can trigger multiple types of actions:

| Action Type | XML `type` Value | Description |
|---|---|---|
| Field Update | `FieldUpdate` | Modify a field value on the record or a related parent record |
| Email Alert | `Alert` | Send an email using an email template |
| Outbound Message | `OutboundMessage` | Send a SOAP message to an external endpoint |
| Task | `Task` | Create a task assigned to a user, role, or record owner |

### Time-Dependent Actions

Workflow rules can schedule actions to execute at a future time:

```xml
<workflowTimeTriggers>
    <actions>
        <name>Send_Reminder_Email</name>
        <type>Alert</type>
    </actions>
    <offsetFromField>MyObject__c.Due_Date__c</offsetFromField>
    <timeLength>-3</timeLength>
    <workflowTimeTriggerUnit>Days</workflowTimeTriggerUnit>
</workflowTimeTriggers>
```

This schedules the alert 3 days BEFORE the Due Date. Negative values = before, positive = after.

---

## 2. Workflow Field Updates

### Purpose

Field Updates modify a field value on the current record or a parent record (via lookup) when triggered by a workflow rule, approval process, or flow.

### Query — Tooling API

```sql
SELECT Id, Name, FieldDefinitionId, SourceTableEnumOrId,
       Operation, LiteralValue, Formula,
       LastModifiedDate, LastModifiedBy.Name
FROM WorkflowFieldUpdate
WHERE NamespacePrefix = null
ORDER BY SourceTableEnumOrId, Name
```

### XML Structure (within workflow file)

```xml
<fieldUpdates>
    <fullName>Update_Status_Active</fullName>
    <description>Sets Status to Active.</description>
    <field>Status__c</field>
    <literalValue>Active</literalValue>
    <name>Update Status Active</name>
    <notifyAssignee>false</notifyAssignee>
    <operation>Literal</operation>
    <protected>false</protected>
    <reevaluateOnChange>true</reevaluateOnChange>
</fieldUpdates>
```

### Operations

| Operation | Description | Key Attributes |
|---|---|---|
| `Literal` | Set to a specific value | `literalValue` contains the value |
| `Formula` | Set via a formula expression | `formula` contains the expression |
| `Null` | Clear the field value | No additional attributes |
| `PreviousValue` | Revert to the previous value | No additional attributes |
| `LookupValue` | Set from a lookup field | `lookupValue` and `lookupValueType` |

### Formula Operation Example

```xml
<fieldUpdates>
    <fullName>Set_Closed_Date_Today</fullName>
    <field>Closed_Date__c</field>
    <formula>TODAY()</formula>
    <name>Set Closed Date Today</name>
    <notifyAssignee>false</notifyAssignee>
    <operation>Formula</operation>
    <protected>false</protected>
</fieldUpdates>
```

### Re-evaluation on Change

The `<reevaluateOnChange>true</reevaluateOnChange>` flag is critical:
- When `true`, a field update can cause other workflow rules on the same object to re-fire.
- This creates a second pass through workflow rules — a common source of unexpected behavior.
- Maximum of one re-evaluation cycle (no infinite loops, but two passes can produce confusing results).

### Cross-Object Field Updates

Field updates can modify a field on a parent record (via lookup):

```xml
<fieldUpdates>
    <fullName>Update_Parent_Status</fullName>
    <field>Status__c</field>
    <literalValue>Has Children</literalValue>
    <name>Update Parent Status</name>
    <notifyAssignee>false</notifyAssignee>
    <operation>Literal</operation>
    <protected>false</protected>
    <targetObject>Parent_Object__c</targetObject>
</fieldUpdates>
```

---

## 3. Workflow Alerts (Email Alerts)

### Purpose

Email Alerts send email notifications using an email template. While originally designed for Workflow Rules, Email Alerts can also be invoked from:
- Flows
- Approval Processes
- Apex (`Messaging.SingleEmailMessage` with `setTemplateId`)

### Query — Tooling API

```sql
SELECT Id, DeveloperName, Description, SenderType, SenderAddress,
       TemplateName, EntityDefinitionId,
       LastModifiedDate, LastModifiedBy.Name
FROM WorkflowAlert
WHERE NamespacePrefix = null
ORDER BY EntityDefinition.QualifiedApiName, DeveloperName
```

### XML Structure (within workflow file)

```xml
<alerts>
    <fullName>Send_Approval_Notification</fullName>
    <description>Send notification when record is approved.</description>
    <protected>false</protected>
    <recipients>
        <type>owner</type>
    </recipients>
    <recipients>
        <recipient>admin@example.com</recipient>
        <type>user</type>
    </recipients>
    <senderAddress>noreply@example.com</senderAddress>
    <senderType>OrgWideEmailAddress</senderType>
    <template>unfiled$public/Approval_Notification</template>
</alerts>
```

### Recipient Types

| Type | Description | Recipient Value |
|---|---|---|
| `owner` | Record owner | _(none needed)_ |
| `creator` | Record creator | _(none needed)_ |
| `user` | Specific user | User email or ID |
| `role` | All users in a role | Role DeveloperName |
| `roleSubordinates` | Role and subordinates | Role DeveloperName |
| `group` | Public group members | Group DeveloperName |
| `accountTeam` | Account team members | Account team role |
| `email` | Email field on record | Field API name |
| `caseTeam` | Case team members | Case team role |

### Sender Types

| Type | Description |
|---|---|
| `CurrentUser` | Send from the user who triggered the rule |
| `DefaultWorkflowUser` | Send from the org's default workflow user |
| `OrgWideEmailAddress` | Send from a specific org-wide email address |

### Note on Reusability

Email Alerts are reusable across Workflow Rules, Flows, and Approval Processes. When migrating workflow rules to flows, the same Email Alert can be referenced — no need to recreate them.

---

## 4. Approval Processes

### Purpose

Approval Processes define multi-step approval workflows with:
- Entry criteria (which records enter the process)
- Approval steps with assigned approvers
- Approval / rejection actions at each step and final
- Email notifications to approvers
- Record locking during approval

**Approval Processes are NOT deprecated** — they remain the primary tool for structured approval workflows in Salesforce.

### Query

Approval Processes are **NOT directly queryable via Tooling API SOQL**. You must retrieve them via metadata API.

### ProcessInstance Query (Runtime Data)

To query approval history at runtime:

```sql
SELECT Id, TargetObjectId, Status, CreatedDate, CompletedDate,
       LastActorId, LastActor.Name
FROM ProcessInstance
WHERE TargetObject.Type = '{ObjectApiName}'
ORDER BY CreatedDate DESC
```

```sql
SELECT Id, ProcessInstanceId, StepStatus, ActorId, Actor.Name,
       Comments, CreatedDate
FROM ProcessInstanceStep
WHERE ProcessInstance.TargetObject.Type = '{ObjectApiName}'
ORDER BY CreatedDate DESC
```

### CLI — Retrieve

```bash
# Retrieve all approval processes
sf project retrieve start \
  --metadata "ApprovalProcess" \
  --target-org <alias>

# Retrieve approval processes for a specific object
sf project retrieve start \
  --metadata "ApprovalProcess:{ObjectApiName}" \
  --target-org <alias>
```

### File Path

```
force-app/main/default/approvalProcesses/{ObjectName}.{ProcessName}.approvalProcess-meta.xml
```

### XML Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ApprovalProcess xmlns="http://soap.sforce.com/2006/04/metadata">
    <active>true</active>
    <allowRecall>true</allowRecall>
    <allowedSubmitters>
        <type>allInternalUsers</type>
    </allowedSubmitters>
    <approvalPageFields>
        <field>Name</field>
        <field>Owner.Name</field>
        <field>Amount__c</field>
        <field>Status__c</field>
    </approvalPageFields>
    <approvalStep>
        <allowDelegate>true</allowDelegate>
        <assignedApprover>
            <approver>
                <name>Manager</name>
                <type>relatedUserField</type>
            </approver>
        </assignedApprover>
        <label>Manager Approval</label>
        <name>Manager_Approval</name>
    </approvalStep>
    <approvalStep>
        <allowDelegate>false</allowDelegate>
        <assignedApprover>
            <approver>
                <name>VP_Sales</name>
                <type>user</type>
            </approver>
        </assignedApprover>
        <entryCriteria>
            <criteriaItems>
                <field>MyObject__c.Amount__c</field>
                <operation>greaterThan</operation>
                <value>50000</value>
            </criteriaItems>
        </entryCriteria>
        <label>VP Approval</label>
        <name>VP_Approval</name>
        <rejectBehavior>
            <type>BackToPrevious</type>
        </rejectBehavior>
    </approvalStep>
    <description>Standard approval process for high-value records.</description>
    <emailTemplate>unfiled$public/Approval_Request</emailTemplate>
    <entryCriteria>
        <criteriaItems>
            <field>MyObject__c.Status__c</field>
            <operation>equals</operation>
            <value>Pending Approval</value>
        </criteriaItems>
    </entryCriteria>
    <finalApprovalActions>
        <action>
            <name>Update_Status_Approved</name>
            <type>FieldUpdate</type>
        </action>
        <action>
            <name>Send_Approval_Notification</name>
            <type>Alert</type>
        </action>
    </finalApprovalActions>
    <finalApprovalRecordLock>true</finalApprovalRecordLock>
    <finalRejectionActions>
        <action>
            <name>Update_Status_Rejected</name>
            <type>FieldUpdate</type>
        </action>
    </finalRejectionActions>
    <finalRejectionRecordLock>false</finalRejectionRecordLock>
    <initialSubmissionActions>
        <action>
            <name>Update_Status_In_Review</name>
            <type>FieldUpdate</type>
        </action>
    </initialSubmissionActions>
    <label>Standard Approval</label>
    <recordEditability>AdminOrCurrentApprover</recordEditability>
    <showApprovalHistory>true</showApprovalHistory>
</ApprovalProcess>
```

### Approver Types

| Type | Description |
|---|---|
| `user` | Specific user by username |
| `relatedUserField` | User lookup field on the record (e.g., `Manager`) |
| `queue` | A Salesforce queue |
| `role` | Users in a specific role |
| `roleSubordinates` | Users in a role and its subordinates |

### Reject Behavior

| Type | Description |
|---|---|
| `RejectRequest` | Final rejection — stops the process |
| `BackToPrevious` | Returns to the previous approval step |

### Apex — Submit for Approval

```apex
Approval.ProcessSubmitRequest req = new Approval.ProcessSubmitRequest();
req.setComments('Submitting for approval.');
req.setObjectId(recordId);
req.setProcessDefinitionNameOrId('Standard_Approval');
req.setNextApproverIds(new List<Id>{approverId});

Approval.ProcessResult result = Approval.process(req);
```

### Apex — Approve/Reject

```apex
Approval.ProcessWorkitemRequest workItem = new Approval.ProcessWorkitemRequest();
workItem.setComments('Approved.');
workItem.setAction('Approve'); // or 'Reject'
workItem.setWorkitemId(workItemId);

Approval.ProcessResult result = Approval.process(workItem);
```

---

## 5. Migration Guide: Workflow Rules to Flow

### Salesforce Migrate to Flow Tool

Salesforce provides a built-in migration tool:
1. Navigate to **Setup → Migrate to Flow**
2. Select the workflow rule to migrate
3. Review the generated flow
4. Activate the flow and deactivate the workflow rule

### Manual Migration Patterns

| Workflow Component | Flow Equivalent |
|---|---|
| Workflow Rule (criteria) | Record-Triggered Flow with entry conditions |
| Workflow Field Update | Assignment element + Update Records element |
| Workflow Email Alert | Action element (Send Email Alert) |
| Workflow Outbound Message | Action element (custom invocable action) |
| Workflow Task | Create Records element |
| Time-Dependent Action | Scheduled Path on record-triggered flow |

### Migration Steps (Manual)

1. **Document the workflow rule:** criteria, actions, time-dependent actions.
2. **Create a record-triggered flow** on the same object.
3. **Set entry conditions** matching the workflow rule criteria.
4. **Choose the trigger:** "A record is created" / "A record is created or updated" / "A record is updated" (maps to `triggerType`).
5. **Add flow elements** for each workflow action:
   - Field Update → Assignment + Update Records (or use "After Save" with `$Record` updates)
   - Email Alert → Send Email Alert action (reuse the existing email alert)
   - Task → Create Records element
6. **For time-dependent actions:** Add a Scheduled Path with the appropriate time offset.
7. **Test the flow** thoroughly before deactivating the workflow rule.
8. **Deactivate the workflow rule** (do not delete immediately — keep as reference).

### Key Differences to Watch

| Concern | Workflow Rules | Record-Triggered Flows |
|---|---|---|
| **Execution order** | After before-triggers, after after-triggers | Before-save: before after-triggers. After-save: after workflow rules |
| **Recursion** | One re-evaluation cycle max | Configurable: run once or allow re-entry |
| **Bulkification** | Automatic | Must be designed — avoid loops with DML |
| **Cross-object updates** | Supported via field updates | Supported via Update Records element |
| **Error handling** | Minimal (fails silently or shows generic error) | Fault paths for explicit error handling |
| **Governor limits** | Workflow-specific limits | Standard Apex-style governor limits |

---

## 6. Order of Execution Impact

Understanding where legacy automation falls in Salesforce's order of execution is critical for debugging:

```
1.  System validation rules (required fields, field formats)
2.  Before-triggers (Apex)
3.  Custom validation rules
4.  After-triggers (Apex)
5.  Assignment rules
6.  Auto-response rules
7.  ─── WORKFLOW RULES fire here ───
8.  Workflow field updates execute
9.  If field updates with reevaluateOnChange → repeat steps 2-8 ONCE
10. ─── AFTER-SAVE RECORD-TRIGGERED FLOWS fire here ───
11. Escalation rules
12. Entitlement rules
13. Roll-up summary field calculations
14. Cross-object workflow field updates
15. Criteria-based sharing evaluation
16. DML operation commits
```

### Common Bugs from Mixed Automation

- **Workflow + Flow on same object:** Workflow rules fire BEFORE after-save flows. If both modify the same field, the flow "wins" because it runs later.
- **Field update re-evaluation:** A workflow field update with `reevaluateOnChange = true` causes before-triggers to fire again. If the trigger modifies the same field, it can create unexpected loops (capped at one re-evaluation).
- **Before-save flow + workflow field update:** Before-save flows run early (step 2 area), workflow field updates run later. The field update can overwrite what the before-save flow set.

### Debugging Tip

When debugging an org with mixed automation (triggers + workflow rules + flows), check the debug log for these markers:
- `WF_RULE_EVAL` — workflow rule evaluation
- `WF_FIELD_UPDATE` — workflow field update execution
- `WF_EMAIL_ALERT` — email alert execution
- `FLOW_START_INTERVIEWS` — flow execution
- `CODE_UNIT_STARTED` — trigger execution

---

## 7. CLI Commands Summary

```bash
# Retrieve all workflow rules for an object
sf project retrieve start \
  --metadata "Workflow:{ObjectName__c}" \
  --target-org <alias>

# Retrieve all approval processes
sf project retrieve start \
  --metadata "ApprovalProcess" \
  --target-org <alias>

# Retrieve approval processes for a specific object
sf project retrieve start \
  --metadata "ApprovalProcess:{ObjectApiName}" \
  --target-org <alias>

# Deploy workflow changes
sf project deploy start \
  --metadata "Workflow:{ObjectName__c}" \
  --target-org <alias> --wait 10

# Deploy approval process
sf project deploy start \
  --metadata "ApprovalProcess:{ObjectName}.{ProcessName}" \
  --target-org <alias> --wait 10
```

---

## Context Specification

- metadata_type: WorkflowRule, WorkflowFieldUpdate, WorkflowAlert
- context_path: {alias}/automation-legacy/
- inventory_file: {alias}/automation-legacy/_inventory.md
- detail_file_pattern: _(inventory only — no per-item detail files)_

### Full Inventory Queries

**Workflow Rules** — Uses: tooling API
```sql
SELECT Id, Name, TableEnumOrId, LastModifiedDate, LastModifiedBy.Name
FROM WorkflowRule
WHERE NamespacePrefix = null
ORDER BY TableEnumOrId, Name
```

**Workflow Field Updates** — Uses: tooling API
```sql
SELECT Id, Name, FieldDefinitionId, SourceTableEnumOrId,
       Operation, LiteralValue, Formula,
       LastModifiedDate, LastModifiedBy.Name
FROM WorkflowFieldUpdate
WHERE NamespacePrefix = null
ORDER BY SourceTableEnumOrId, Name
```

**Workflow Alerts** — Uses: tooling API
```sql
SELECT Id, DeveloperName, Description, SenderType,
       EntityDefinitionId, EntityDefinition.QualifiedApiName,
       LastModifiedDate, LastModifiedBy.Name
FROM WorkflowAlert
WHERE NamespacePrefix = null
ORDER BY EntityDefinition.QualifiedApiName, DeveloperName
```

### Change Detection Queries

**Workflow Rules** — Uses: tooling API
```sql
SELECT Id, Name, TableEnumOrId,
       LastModifiedDate, LastModifiedBy.Name
FROM WorkflowRule
WHERE LastModifiedDate > {LAST_SCAN}
AND NamespacePrefix = null
ORDER BY LastModifiedDate DESC
LIMIT 50
```

**Workflow Field Updates** — Uses: tooling API
```sql
SELECT Id, Name, SourceTableEnumOrId, Operation,
       LastModifiedDate, LastModifiedBy.Name
FROM WorkflowFieldUpdate
WHERE LastModifiedDate > {LAST_SCAN}
AND NamespacePrefix = null
ORDER BY LastModifiedDate DESC
LIMIT 50
```

**Workflow Alerts** — Uses: tooling API
```sql
SELECT Id, DeveloperName, Description,
       LastModifiedDate, LastModifiedBy.Name
FROM WorkflowAlert
WHERE LastModifiedDate > {LAST_SCAN}
AND NamespacePrefix = null
ORDER BY LastModifiedDate DESC
LIMIT 50
```

**Approval Processes (via SetupAuditTrail)** — Uses: standard API
```sql
SELECT Id, Action, Section, Display, CreatedDate, CreatedBy.Name
FROM SetupAuditTrail
WHERE Section = 'Approval Process'
AND CreatedDate > {LAST_SCAN}
ORDER BY CreatedDate DESC
LIMIT 50
```

### Inventory Columns
Sub-Type | Object | Name/Developer Name | Operation/Status | Description | Last Modified Date | Last Modified By

### Detail File Sections
_(No per-item detail files — inventory groups items by sub-type: Workflow Rules, Field Updates, Email Alerts. Retrieve full XML with `sf project retrieve start --metadata "Workflow:{ObjectName__c}"`)_

### Naming Convention Detection
Analyze all discovered items and extract:
- **Workflow rule naming:** `{Verb}_{Object}_{Condition}` vs `{Object}_{Action}` patterns
- **Field update naming:** prefix patterns (`FU_`, `Update_`, `Set_`)
- **Email alert naming:** prefix patterns (`EA_`, `Alert_`, `Notify_`)
- **Approval process naming:** `{Object}_{Process}` vs `{Descriptive_Name}` patterns
- Report findings in the `## Detected Naming Conventions` section at the top of `_inventory.md`
