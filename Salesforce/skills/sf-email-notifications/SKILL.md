---
name: sf-email-notifications
description: "Reference for Salesforce email and notification metadata — Email Templates, Email Alerts, Custom Notification Types, and notification delivery. Includes API queries and template patterns."
---

# Salesforce Email and Notifications Skill

Reference for querying, retrieving, deploying, and managing Salesforce email templates,
email alerts (workflow alerts), custom notification types, and notification delivery channels.

---

## 1. Email Templates

### Discovery Query (Standard API)

```sql
SELECT Id, Name, DeveloperName, FolderId, Folder.Name, Subject,
       TemplateType, IsActive, Encoding, Body, HtmlValue,
       LastModifiedDate, LastModifiedBy.Name
FROM EmailTemplate
WHERE IsActive = true
ORDER BY Folder.Name, Name
LIMIT 200
```

To include inactive templates:

```sql
SELECT Id, Name, DeveloperName, FolderId, Folder.Name, Subject,
       TemplateType, IsActive,
       LastModifiedDate, LastModifiedBy.Name
FROM EmailTemplate
ORDER BY Folder.Name, Name
LIMIT 200
```

### Template Types

| TemplateType  | Description                                                     |
|---------------|-----------------------------------------------------------------|
| text          | Plain text only — simplest format                               |
| html          | Classic HTML template with letterhead support                   |
| custom        | Lightning Email Template — uses Lightning Web Runtime for rendering |
| visualforce   | Visualforce markup — supports complex logic and iteration       |

### Lightning Email Templates vs Classic

| Feature                  | Lightning (custom)           | Classic (text/html/visualforce) |
|--------------------------|------------------------------|---------------------------------|
| Editor                   | Drag-and-drop builder        | Raw HTML or VF markup           |
| Merge fields             | Handlebars `{{{Recipient.Name}}}` | Classic `{!Contact.Name}`    |
| Enhanced Letterheads     | Yes                          | Classic Letterheads only        |
| Folder support           | Enhanced folders with sharing| Standard folders                |
| Dynamic content          | Limited                      | Full VF logic available         |
| Retrievable via Metadata | Yes                          | Yes                             |

### Merge Field Syntax

Classic merge fields:
```
{!Contact.FirstName}
{!Opportunity.Amount}
{!Organization.Name}
{!Receiving_User.Name}
```

Lightning template merge fields (Handlebars):
```
{{{Recipient.Name}}}
{{{Sender.Name}}}
{{{Opportunity.Amount}}}
```

### Retrieve Command

```bash
sf project retrieve start --metadata "EmailTemplate" --target-org <alias>
```

Retrieve a specific template:

```bash
sf project retrieve start --metadata "EmailTemplate:{FolderName}/{TemplateDeveloperName}" --target-org <alias>
```

### File Path Convention

Classic templates:
```
force-app/main/default/email/{FolderName}/{TemplateDeveloperName}.email
force-app/main/default/email/{FolderName}/{TemplateDeveloperName}.email-meta.xml
```

Lightning email templates:
```
force-app/main/default/email/{FolderName}/{TemplateDeveloperName}.email
force-app/main/default/email/{FolderName}/{TemplateDeveloperName}.email-meta.xml
```

### Email Template XML Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<EmailTemplate xmlns="http://soap.sforce.com/2006/04/metadata">
    <available>true</available>
    <description>Welcome email for new contacts</description>
    <encodingKey>UTF-8</encodingKey>
    <name>Welcome Email</name>
    <subject>Welcome, {!Contact.FirstName}!</subject>
    <type>html</type>
    <textOnly>Plain text fallback content here</textOnly>
</EmailTemplate>
```

The HTML body is stored in the companion `.email` file (not in the XML).

### Email Template Folders

```sql
SELECT Id, Name, DeveloperName, Type, AccessType
FROM Folder
WHERE Type = 'Email'
ORDER BY Name
```

---

## 2. Email Alerts (Workflow Alerts)

### Discovery Query (Tooling API)

```sql
SELECT Id, DeveloperName, Description, SenderType, SenderAddress,
       TemplateName, EntityDefinitionId,
       LastModifiedDate, LastModifiedBy.Name
FROM WorkflowAlert
WHERE NamespacePrefix = null
ORDER BY DeveloperName
LIMIT 200
```

Note: Despite the "Workflow" name, Email Alerts are reusable components referenced by:
- Flow Actions (Send Email Alert element)
- Workflow Rules (legacy)
- Approval Processes (approval/rejection actions)
- Process Builder (legacy)

### SenderType Values

| SenderType       | Description                                      |
|------------------|--------------------------------------------------|
| CurrentUser      | The user who triggered the action                |
| DefaultWorkflow  | Org-wide default workflow sender                 |
| OrgWideEmailAddress | A configured org-wide email address           |

### Retrieve Command

```bash
sf project retrieve start --metadata "WorkflowAlert" --target-org <alias>
```

Retrieve alerts for a specific object:

```bash
sf project retrieve start --metadata "WorkflowAlert:{ObjectApiName}" --target-org <alias>
```

### File Path Convention

Email alerts are stored within the parent object's workflow directory:

```
force-app/main/default/workflows/{ObjectApiName}.workflow-meta.xml
```

The alert definitions are nested inside the workflow XML as `<alerts>` elements.

### Workflow Alert XML Structure

```xml
<alerts>
    <fullName>Case_Escalation_Notification</fullName>
    <description>Notify manager of escalated case</description>
    <protected>false</protected>
    <recipients>
        <field>OwnerId</field>
        <type>owner</type>
    </recipients>
    <recipients>
        <recipient>manager_role@example.com</recipient>
        <type>user</type>
    </recipients>
    <senderAddress>support@example.com</senderAddress>
    <senderType>OrgWideEmailAddress</senderType>
    <template>Support_Templates/Case_Escalation</template>
</alerts>
```

### Recipient Types in Email Alerts

| Type              | Description                                  |
|-------------------|----------------------------------------------|
| owner             | Record owner                                 |
| creator           | Record creator                               |
| role              | Users in a specific role                     |
| roleSubordinates  | Users in a role and all subordinate roles    |
| user              | Specific user by username                    |
| group             | Public group                                 |
| accountTeam       | Account team members                         |
| email             | Email field on the record                    |
| caseTeam          | Case team members                            |
| campaignMemberDerivedOwner | Campaign member derived owner       |

---

## 3. Custom Notification Types

### Discovery Query (Tooling API)

```sql
SELECT Id, DeveloperName, MasterLabel, Description,
       LastModifiedDate, LastModifiedBy.Name
FROM CustomNotificationType
WHERE NamespacePrefix = null
ORDER BY DeveloperName
LIMIT 100
```

### Supported Channels

Custom notifications can be delivered through multiple channels simultaneously:
- **Desktop** — browser notification (Lightning Experience)
- **Mobile** — push notification (Salesforce Mobile App)
- **In-App (Bell)** — notification bell in Lightning header

Channel configuration is done in Setup, not in metadata XML.

### Sending via Apex

```apex
Messaging.CustomNotification notification = new Messaging.CustomNotification();
notification.setTitle('Case Escalated');
notification.setBody('Case #' + caseNumber + ' has been escalated.');
notification.setNotificationTypeId(customNotificationTypeId);
notification.setTargetId(caseId);

Set<String> recipientIds = new Set<String>();
recipientIds.add(managerId);

notification.send(recipientIds);
```

### Sending via Flow

Use the **Send Custom Notification** core action in Flow:
- **Custom Notification Type ID**: The ID of the CustomNotificationType record
- **Recipient IDs**: Collection of User IDs
- **Title**: Notification title text
- **Body**: Notification body text
- **Target Record ID**: Record to navigate to when notification is clicked

### Retrieve Command

```bash
sf project retrieve start --metadata "CustomNotificationType" --target-org <alias>
```

### File Path Convention

```
force-app/main/default/notificationtypes/{DeveloperName}.notiftype-meta.xml
```

### Custom Notification Type XML Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomNotificationType xmlns="http://soap.sforce.com/2006/04/metadata">
    <customNotifTypeName>Case_Escalation</customNotifTypeName>
    <description>Notification for escalated cases</description>
    <desktop>true</desktop>
    <masterLabel>Case Escalation</masterLabel>
    <mobile>true</mobile>
</CustomNotificationType>
```

---

## 4. Notification Delivery Channels and Patterns

### Channel Overview

| Channel    | Mechanism              | Requires                        |
|------------|------------------------|---------------------------------|
| Email      | Email Alert or Apex    | Valid email on recipient        |
| In-App     | Custom Notification    | Lightning Experience enabled    |
| Mobile     | Custom Notification    | Salesforce Mobile App installed |
| Desktop    | Custom Notification    | Browser notification permission |
| Chatter    | Chatter post/mention   | Chatter enabled in org          |
| SMS/Text   | Third-party or custom  | Integration (Twilio, etc.)      |

### Combining Email + In-App Notification

A common pattern is to fire both an Email Alert and a Custom Notification from the same Flow:

1. Flow trigger fires on record change
2. Decision element evaluates criteria
3. **Path A**: Send Email Alert action (for email delivery)
4. **Path B**: Send Custom Notification action (for in-app/mobile/desktop delivery)

### Org-Wide Email Addresses

```sql
SELECT Id, Address, DisplayName, IsAllowAllProfiles, Purpose
FROM OrgWideEmailAddress
ORDER BY DisplayName
```

- `Purpose` values: `UserSelection` (available to users), `AutomatedProcess` (for automated emails)
- Not retrievable via Metadata API — must be configured manually in each org

### Email Deliverability Settings

Not queryable via API. Must verify manually in Setup:
- **Access Level**: No access, System email only, All email
- **Bounce Management**: Enabled/Disabled
- **Compliance BCC**: Optional BCC address for all outbound email

---

## 5. Deployment Patterns and Best Practices

### Deploy Order

1. Email template folders (if using classic folder structure)
2. Email templates (alerts reference them)
3. Email alerts / workflow alerts (flows reference them)
4. Custom notification types (flows and Apex reference them)
5. Flows that use alerts and notifications

### Common Gotchas

- **Template folder permissions**: Enhanced folder sharing is not easily portable between orgs. Document folder sharing requirements separately.
- **Org-wide email addresses**: Not deployable. Must be created manually in target org. If an email alert references an org-wide address that does not exist, deployment will fail.
- **Lightning vs Classic templates**: Lightning templates use different merge field syntax. Mixing types in the same org can cause confusion.
- **Email alert object binding**: Each email alert is bound to a specific object. The alert only has access to merge fields from that object and its related objects.
- **Custom notification type IDs**: IDs differ between orgs. Apex code that hardcodes notification type IDs will break on deploy. Query by DeveloperName instead.
- **Email deliverability in sandboxes**: Sandboxes default to "System email only" — test emails to external addresses will not send unless changed.
- **Daily email limits**: Salesforce enforces daily limits on outbound emails (varies by edition). High-volume alert flows can hit these limits.
- **Recipient limits**: Email alerts support up to 5 recipients per alert. For broader distribution, use public groups.

### Naming Conventions (Typical Patterns)

| Type                     | Convention Example                         |
|--------------------------|--------------------------------------------|
| Email Template           | `Case_Escalation_Notification`             |
| Email Template Folder    | `Support_Templates`, `Sales_Templates`     |
| Email Alert              | `Case_Escalation_Alert`                    |
| Custom Notification Type | `Case_Escalation_Notif`                    |

---

## Context Specification

- metadata_type: EmailTemplate, CustomNotificationType
- context_path: {alias}/email-notifications/
- inventory_file: {alias}/email-notifications/_inventory.md
- detail_file_pattern: {alias}/email-notifications/{ApiName}.md

### Change Detection Queries

**Email Templates** — Uses: Standard API
```sql
SELECT Id, Name, DeveloperName, Folder.Name, TemplateType, IsActive,
       LastModifiedDate, LastModifiedBy.Name
FROM EmailTemplate
WHERE LastModifiedDate > {LAST_SCAN}
ORDER BY LastModifiedDate DESC
LIMIT 50
```

**Email Alerts** — Uses: Tooling API
```sql
SELECT Id, DeveloperName, Description, SenderType,
       LastModifiedDate, LastModifiedBy.Name
FROM WorkflowAlert
WHERE NamespacePrefix = null AND LastModifiedDate > {LAST_SCAN}
ORDER BY LastModifiedDate DESC
LIMIT 50
```

**Custom Notification Types** — Uses: Tooling API
```sql
SELECT Id, DeveloperName, MasterLabel,
       LastModifiedDate, LastModifiedBy.Name
FROM CustomNotificationType
WHERE NamespacePrefix = null AND LastModifiedDate > {LAST_SCAN}
ORDER BY LastModifiedDate DESC
LIMIT 50
```

### Inventory Columns

API Name | Label | Type (Template/Alert/Notification) | Folder | Active | Last Modified | Last Scanned

### Detail File Sections

Identity, Type, Folder, Subject/Description, Merge Fields Used, Referenced Objects, Recipient Configuration, Naming Convention Notes

### Naming Convention Detection

During scan, detect patterns in template/alert/notification names:
- Prefix patterns by object (e.g., `Case_`, `Opportunity_`)
- Folder organization by department or function
- Alert naming relative to template naming
- Record in `_inventory.md` header as `Detected naming pattern: {pattern}`
