---
name: sf-assignment-rules
description: "Reference for Salesforce assignment automation — Lead Assignment Rules, Case Assignment Rules, Auto-Response Rules, and Case Escalation Rules. Includes Metadata API retrieval patterns and XML structures."
---

# Salesforce Assignment Rules Skill

Reference for retrieving, deploying, and managing Salesforce assignment automation metadata:
Lead Assignment Rules, Case Assignment Rules, Auto-Response Rules, and Case Escalation Rules.

---

## Important: API Limitations

These rule types are **NOT queryable via Standard or Tooling API SOQL**. There are no SOQL-accessible
objects for AssignmentRule, AutoResponseRule, or EscalationRule metadata.

All discovery and retrieval must go through the **Metadata API** (sf project retrieve).

Change detection uses **SetupAuditTrail** to detect when rules have been modified.

---

## 1. Lead Assignment Rules

### Purpose

Lead Assignment Rules automatically route new leads to specific users or queues based on
criteria such as lead source, industry, geography, or any other lead field.

### Retrieve Command

```bash
sf project retrieve start --metadata "AssignmentRules:Lead" --target-org <alias>
```

### File Path Convention

```
force-app/main/default/assignmentRules/Lead.assignmentRules-meta.xml
```

### XML Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<AssignmentRules xmlns="http://soap.sforce.com/2006/04/metadata">
    <assignmentRule>
        <fullName>Standard Lead Assignment</fullName>
        <active>true</active>
        <ruleEntry>
            <assignedTo>west_coast_sales</assignedTo>
            <assignedToType>Queue</assignedToType>
            <criteriaItems>
                <field>Lead.State</field>
                <operation>equals</operation>
                <value>CA,OR,WA,NV,AZ</value>
            </criteriaItems>
            <criteriaItems>
                <field>Lead.LeadSource</field>
                <operation>equals</operation>
                <value>Web</value>
            </criteriaItems>
            <template>Lead_Assignment_Notification</template>
        </ruleEntry>
        <ruleEntry>
            <assignedTo>east_coast_sales</assignedTo>
            <assignedToType>Queue</assignedToType>
            <criteriaItems>
                <field>Lead.State</field>
                <operation>equals</operation>
                <value>NY,NJ,CT,MA,PA</value>
            </criteriaItems>
            <template>Lead_Assignment_Notification</template>
        </ruleEntry>
        <ruleEntry>
            <assignedTo>default_lead_queue</assignedTo>
            <assignedToType>Queue</assignedToType>
        </ruleEntry>
    </assignmentRule>
</AssignmentRules>
```

### Key Behaviors

- **Only one active rule at a time**: Multiple assignment rules can exist for the Lead object,
  but only one can be active. Activating a new rule deactivates the previous one.
- **First match wins**: Rule entries are evaluated top-to-bottom. The first entry whose criteria
  match is used; subsequent entries are not evaluated.
- **Default entry**: The last rule entry typically has no criteria — it acts as a catch-all
  default assignment.
- **Email notification**: Each rule entry can optionally reference an email template to notify
  the assigned user.
- **Trigger behavior**: Assignment rules fire when leads are created (and optionally when
  updated, if the "Use active assignment rules" checkbox is selected in the API request).

### AssignedToType Values

| Value | Description                                    |
|-------|------------------------------------------------|
| Queue | Assign to a Queue (by Queue DeveloperName)     |
| User  | Assign to a specific User (by Username)        |

---

## 2. Case Assignment Rules

### Purpose

Case Assignment Rules route cases to specific users or queues based on case attributes such as
origin, type, priority, record type, or any other case field.

### Retrieve Command

```bash
sf project retrieve start --metadata "AssignmentRules:Case" --target-org <alias>
```

### File Path Convention

```
force-app/main/default/assignmentRules/Case.assignmentRules-meta.xml
```

### XML Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<AssignmentRules xmlns="http://soap.sforce.com/2006/04/metadata">
    <assignmentRule>
        <fullName>Standard Case Assignment</fullName>
        <active>true</active>
        <ruleEntry>
            <assignedTo>tier2_support</assignedTo>
            <assignedToType>Queue</assignedToType>
            <criteriaItems>
                <field>Case.Priority</field>
                <operation>equals</operation>
                <value>High</value>
            </criteriaItems>
            <criteriaItems>
                <field>Case.Type</field>
                <operation>equals</operation>
                <value>Problem</value>
            </criteriaItems>
            <template>Case_Assignment_Notification</template>
        </ruleEntry>
        <ruleEntry>
            <assignedTo>tier1_support</assignedTo>
            <assignedToType>Queue</assignedToType>
            <template>Case_Assignment_Notification</template>
        </ruleEntry>
    </assignmentRule>
</AssignmentRules>
```

### Differences from Lead Assignment Rules

- Same XML structure and behavior as Lead assignment rules
- Applies to the Case object instead of Lead
- Case assignment rules are also triggered by Email-to-Case and Web-to-Case
- Case assignment rules can reassign cases on update (if configured via API options)

---

## 3. Auto-Response Rules

### Purpose

Auto-Response Rules send automatic email replies when leads are captured via Web-to-Lead or
cases are created via Web-to-Case or Email-to-Case. The response email uses an email template
and is sent to the lead/case contact's email address.

### Retrieve Commands

For Lead auto-response rules:

```bash
sf project retrieve start --metadata "AutoResponseRules:Lead" --target-org <alias>
```

For Case auto-response rules:

```bash
sf project retrieve start --metadata "AutoResponseRules:Case" --target-org <alias>
```

### File Path Convention

```
force-app/main/default/autoResponseRules/Lead.autoResponseRules-meta.xml
force-app/main/default/autoResponseRules/Case.autoResponseRules-meta.xml
```

### XML Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<AutoResponseRules xmlns="http://soap.sforce.com/2006/04/metadata">
    <autoResponseRule>
        <fullName>Standard Case Auto-Response</fullName>
        <active>true</active>
        <ruleEntry>
            <criteriaItems>
                <field>Case.Origin</field>
                <operation>equals</operation>
                <value>Email</value>
            </criteriaItems>
            <criteriaItems>
                <field>Case.Priority</field>
                <operation>equals</operation>
                <value>High</value>
            </criteriaItems>
            <template>Support_Templates/High_Priority_Auto_Response</template>
            <senderEmail>support@example.com</senderEmail>
            <senderName>Support Team</senderName>
        </ruleEntry>
        <ruleEntry>
            <template>Support_Templates/Standard_Auto_Response</template>
            <senderEmail>support@example.com</senderEmail>
            <senderName>Support Team</senderName>
        </ruleEntry>
    </autoResponseRule>
</AutoResponseRules>
```

### Key Behaviors

- **Only one active rule at a time** per object (Lead or Case)
- **First match wins**: Same as assignment rules — entries evaluated top-to-bottom
- **Template reference**: Each entry must reference an email template (folder/template format)
- **Sender configuration**: Each entry can specify sender email and sender name. If not
  specified, uses the default org-wide email address or the automated process user.
- **Triggered only on create**: Auto-response rules fire only when the record is first created
  via web/email channels. They do not fire on record updates.

---

## 4. Escalation Rules (Case Only)

### Purpose

Escalation Rules automatically escalate cases that have not been resolved within a defined
time period. Escalation actions include reassigning the case, notifying users, or both.

### Retrieve Command

```bash
sf project retrieve start --metadata "EscalationRules:Case" --target-org <alias>
```

### File Path Convention

```
force-app/main/default/escalationRules/Case.escalationRules-meta.xml
```

### XML Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<EscalationRules xmlns="http://soap.sforce.com/2006/04/metadata">
    <escalationRule>
        <fullName>Standard Case Escalation</fullName>
        <active>true</active>
        <ruleEntry>
            <criteriaItems>
                <field>Case.Priority</field>
                <operation>equals</operation>
                <value>High</value>
            </criteriaItems>
            <escalationAction>
                <assignedTo>support_manager@example.com</assignedTo>
                <assignedToType>User</assignedToType>
                <minutesToEscalation>240</minutesToEscalation>
                <notifyCaseOwner>true</notifyCaseOwner>
                <notifyTo>support_manager@example.com</notifyTo>
                <notifyToTemplate>Support_Templates/Case_Escalation_Alert</notifyToTemplate>
            </escalationAction>
            <escalationAction>
                <assignedTo>support_director@example.com</assignedTo>
                <assignedToType>User</assignedToType>
                <minutesToEscalation>480</minutesToEscalation>
                <notifyCaseOwner>true</notifyCaseOwner>
                <notifyTo>support_director@example.com</notifyTo>
                <notifyToTemplate>Support_Templates/Case_Escalation_Critical</notifyToTemplate>
            </escalationAction>
        </ruleEntry>
    </escalationRule>
</EscalationRules>
```

### Escalation Action Properties

| Property              | Description                                              |
|-----------------------|----------------------------------------------------------|
| minutesToEscalation   | Time in minutes after which the escalation action fires  |
| assignedTo            | User or Queue to reassign the case to                    |
| assignedToType        | `User` or `Queue`                                        |
| notifyCaseOwner       | Whether to notify the current case owner                 |
| notifyTo              | Additional user to notify (by username)                  |
| notifyToTemplate      | Email template for the notification                      |

### Key Behaviors

- **Only one active rule at a time** for the Case object
- **Multiple escalation actions per entry**: A single rule entry can have multiple escalation
  actions that fire at different time intervals (e.g., 4 hours, 8 hours, 24 hours)
- **Business hours**: Escalation timers respect the org's Business Hours settings. Time outside
  business hours does not count toward the escalation threshold.
- **Escalation clock start**: The timer starts when the case is created (or when it re-enters
  matching criteria after being reset)
- **Escalation stops when**: The case is closed, the case owner changes (if configured), or the
  case no longer matches the rule entry criteria

### Business Hours Consideration

Escalation rules use the Business Hours configured in Setup. Verify business hours are set correctly:

```sql
SELECT Id, Name, IsDefault, IsActive, MondayStartTime, MondayEndTime,
       TuesdayStartTime, TuesdayEndTime, TimeZoneSidKey
FROM BusinessHours
WHERE IsActive = true
ORDER BY Name
```

---

## 5. Rule Entry Criteria Operators

All four rule types (Assignment, Auto-Response, Escalation) use the same criteria operators:

| Operation          | Description                          |
|--------------------|--------------------------------------|
| equals             | Exact match                          |
| notEqual           | Not equal to                         |
| lessThan           | Less than (numeric/date)             |
| greaterThan        | Greater than (numeric/date)          |
| lessOrEqual        | Less than or equal                   |
| greaterOrEqual     | Greater than or equal                |
| contains           | Contains substring                   |
| notContain         | Does not contain substring           |
| startsWith         | Starts with string                   |
| includes           | Includes value (multi-select)        |
| excludes           | Excludes value (multi-select)        |

### Multi-Value Criteria

For `equals` and `notEqual`, multiple values are comma-separated in the `<value>` element:

```xml
<criteriaItems>
    <field>Lead.State</field>
    <operation>equals</operation>
    <value>CA,OR,WA</value>
</criteriaItems>
```

---

## 6. Deployment Patterns and Best Practices

### Deploy Order

1. Queues (assignment rules reference them by DeveloperName)
2. Email templates (rules reference them for notifications)
3. Assignment rules
4. Auto-response rules
5. Escalation rules

### Common Gotchas

- **Only one active rule per type per object**: Deploying a rule with `<active>true</active>` will
  deactivate any previously active rule. Be careful when deploying to production.
- **Queue references**: Assignment rules reference queues by DeveloperName. If the queue does not
  exist in the target org, deployment will fail. Ensure queues are deployed or created first.
- **Email template references**: Rules reference email templates by folder-qualified name
  (e.g., `Support_Templates/Case_Assignment_Notification`). The template must exist in the target org.
- **User references**: Rules that assign to specific users reference them by username. Usernames
  differ between production and sandbox orgs (sandboxes append `.sandboxname`).
- **Rule entry order matters**: Entries are evaluated top-to-bottom. The order in the XML file
  determines evaluation order. Changing entry order changes business logic.
- **Cannot partially deploy**: The entire rule (all entries) deploys as a single unit. You cannot
  deploy a single rule entry within a rule.
- **Escalation business hours**: If business hours differ between source and target org, escalation
  timing will behave differently. Verify business hours configuration after deployment.
- **Web-to-Lead/Case dependency**: Auto-response rules only fire for records created via web capture
  or email channels. Records created via the UI or API do not trigger auto-response rules (unless
  the API request specifies `useDefaultRule = true`).
- **No version history**: Changes to these rules are not tracked in the same way as Apex or Flows.
  Use SetupAuditTrail to detect changes.

### Testing Assignment Rules

After deploying, test by creating records through the appropriate channel:
- **Lead assignment**: Create a lead via Web-to-Lead form or API with assignment rule header
- **Case assignment**: Create a case via Email-to-Case, Web-to-Case, or API with assignment rule header
- **Auto-response**: Create via Web-to-Lead/Case and verify email received
- **Escalation**: Create a matching case and wait for the escalation timer (use short intervals in sandbox)

To trigger assignment rules via the Salesforce CLI:

```bash
sf data create record --sobject Lead --values "LastName='Test' FirstName='Assignment' Company='Test Co'" --use-default-rule --target-org <alias>
```

---

## 7. Queues (Related Metadata)

Assignment rules commonly route to queues. Query existing queues:

```sql
SELECT Id, Name, DeveloperName, Type
FROM Group
WHERE Type = 'Queue'
ORDER BY Name
```

Queue members:

```sql
SELECT Id, GroupId, Group.Name, UserOrGroupId
FROM GroupMember
WHERE Group.Type = 'Queue'
ORDER BY Group.Name
```

Queue-supported objects:

```sql
SELECT Id, QueueId, Queue.DeveloperName, SobjectType
FROM QueueSobject
ORDER BY Queue.DeveloperName, SobjectType
```

---

## Context Specification

- metadata_type: AssignmentRule, AutoResponseRule, EscalationRule
- context_path: {alias}/assignment-rules/
- inventory_file: {alias}/assignment-rules/_inventory.md
- detail_file_pattern: {alias}/assignment-rules/{ApiName}.md

### Change Detection Query

These metadata types are not directly queryable. Change detection uses SetupAuditTrail.

Uses: Standard API
```sql
SELECT CreatedDate, CreatedBy.Name, Action, Section, Display
FROM SetupAuditTrail
WHERE CreatedDate > {LAST_SCAN}
  AND Section IN ('AssignmentRule','AutoResponseRule','EscalationRule')
ORDER BY CreatedDate DESC
LIMIT 25
```

### Full Inventory Method

Full inventory requires Metadata API retrieval and XML parsing:

1. Retrieve all assignment rules: `sf project retrieve start --metadata "AssignmentRules" --target-org <alias>`
2. Retrieve all auto-response rules: `sf project retrieve start --metadata "AutoResponseRules" --target-org <alias>`
3. Retrieve all escalation rules: `sf project retrieve start --metadata "EscalationRules" --target-org <alias>`
4. Parse retrieved XML to build inventory

### Inventory Columns

Rule Name | Type (Assignment/AutoResponse/Escalation) | Object (Lead/Case) | Active | Entry Count | Last Audit Trail Change | Last Scanned

### Detail File Sections

Identity, Type, Object, Active Status, Rule Entries (ordered), Criteria per Entry, Assigned To, Email Templates Referenced, Escalation Timers (if applicable), Naming Convention Notes

### Naming Convention Detection

During scan, detect patterns in rule and rule entry names:
- Rule naming by object or team
- Queue naming patterns referenced by rules
- Record in `_inventory.md` header as `Detected naming pattern: {pattern}`
