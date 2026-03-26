---
name: sf-security-advanced
description: "Reference for advanced Salesforce security metadata — Permission Set Groups, Duplicate Rules, Matching Rules, and Field History Tracking. Includes API queries, XML structures, and data quality patterns."
---

# Salesforce Advanced Security Skill

Reference for querying, retrieving, deploying, and managing advanced security and data quality
metadata: Permission Set Groups, Duplicate Rules, Matching Rules, and Field History Tracking.

---

## 1. Permission Set Groups

### Discovery Query (Standard API)

```sql
SELECT Id, DeveloperName, MasterLabel, Description, Status,
       NamespacePrefix, LastModifiedDate, LastModifiedBy.Name
FROM PermissionSetGroup
WHERE NamespacePrefix = null
ORDER BY DeveloperName
LIMIT 200
```

### Relationship to sf-permissions Skill

This skill covers Permission Set Groups — the bundling mechanism. The `sf-permissions` skill
covers individual Permission Sets and their field/object permissions. These two skills complement
each other:

- `sf-permissions`: Individual permission sets, profile permissions, field-level security
- `sf-security-advanced`: Permission set groups (bundles), muting permission sets, group membership

### Permission Set Group Members

Query which permission sets belong to a group:

```sql
SELECT Id, PermissionSetGroupId, PermissionSetId,
       PermissionSet.Name, PermissionSet.Label
FROM PermissionSetGroupComponent
WHERE PermissionSetGroupId = '{groupId}'
ORDER BY PermissionSet.Name
```

### Muting Permission Sets

A muting permission set removes (mutes) specific permissions from a group, even if one of the
member permission sets grants them. This allows reuse of broad permission sets while restricting
specific access per group.

Query muting permission sets:

```sql
SELECT Id, DeveloperName, MasterLabel, PermissionSetGroupId, IsOwnedByProfile
FROM PermissionSet
WHERE IsOwnedByProfile = false AND PermissionSetGroupId != null
ORDER BY DeveloperName
```

### Retrieve Command

```bash
sf project retrieve start --metadata "PermissionSetGroup" --target-org <alias>
```

Retrieve a specific group:

```bash
sf project retrieve start --metadata "PermissionSetGroup:{DeveloperName}" --target-org <alias>
```

### File Path Convention

```
force-app/main/default/permissionsetgroups/{DeveloperName}.permissionsetgroup-meta.xml
```

### Permission Set Group XML Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<PermissionSetGroup xmlns="http://soap.sforce.com/2006/04/metadata">
    <description>All permissions needed for Sales Representatives</description>
    <label>Sales Representative</label>
    <mutingPermissionSets>
        <mutingPermissionSet>Sales_Rep_Muting</mutingPermissionSet>
    </mutingPermissionSets>
    <permissionSets>
        <permissionSet>Sales_Base_Access</permissionSet>
        <permissionSet>Opportunity_Management</permissionSet>
        <permissionSet>Report_Access</permissionSet>
    </permissionSets>
    <status>Updated</status>
</PermissionSetGroup>
```

### Status Values

| Status    | Description                                                       |
|-----------|-------------------------------------------------------------------|
| Updated   | Group has been recalculated and is current                        |
| Updating  | Group is being recalculated (happens after member changes)        |
| Outdated  | Group needs recalculation — member permission sets have changed   |
| Failed    | Recalculation failed — check for conflicts                       |

### Assigning Permission Set Groups to Users

```sql
SELECT Id, AssigneeId, Assignee.Name, PermissionSetGroupId,
       PermissionSetGroup.DeveloperName
FROM PermissionSetAssignment
WHERE PermissionSetGroupId != null
ORDER BY Assignee.Name
```

---

## 2. Duplicate Rules

### Discovery Query (Tooling API)

```sql
SELECT Id, DeveloperName, MasterLabel, SobjectType, IsActive,
       LastModifiedDate, LastModifiedBy.Name
FROM DuplicateRule
WHERE NamespacePrefix = null
ORDER BY SobjectType, DeveloperName
LIMIT 200
```

### Duplicate Rule Actions

| Action  | Description                                                      |
|---------|------------------------------------------------------------------|
| Allow   | Allow save, no alert — record is saved silently                  |
| Alert   | Allow save with warning — user sees duplicate alert but can save |
| Block   | Prevent save — user must resolve duplicates before saving        |
| Report  | Log duplicate to Duplicate Record Set for review                 |

Actions can differ based on whether the record is created vs. edited.

### Retrieve Command

```bash
sf project retrieve start --metadata "DuplicateRule" --target-org <alias>
```

Retrieve for a specific object:

```bash
sf project retrieve start --metadata "DuplicateRule:{ObjectApiName}.{RuleName}" --target-org <alias>
```

### File Path Convention

```
force-app/main/default/duplicateRules/{ObjectApiName}.{RuleDeveloperName}.duplicateRule-meta.xml
```

### Duplicate Rule XML Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<DuplicateRule xmlns="http://soap.sforce.com/2006/04/metadata">
    <actionOnInsert>Allow</actionOnInsert>
    <actionOnUpdate>Allow</actionOnUpdate>
    <alertText>This record might be a duplicate.</alertText>
    <description>Detect duplicate accounts by name and address</description>
    <isActive>true</isActive>
    <masterLabel>Account Duplicate Rule</masterLabel>
    <operationsOnInsert>Alert</operationsOnInsert>
    <operationsOnUpdate>Alert</operationsOnUpdate>
    <securityOption>EnforceSharingRules</securityOption>
    <sortOrder>1</sortOrder>
    <duplicateRuleMatchRules>
        <matchRuleSObjectType>Account</matchRuleSObjectType>
        <matchingRule>Account_Matching_Rule</matchingRule>
        <objectMapping>
            <inputObject>Account</inputObject>
            <mappingFields>
                <inputField>Name</inputField>
                <outputField>Name</outputField>
            </mappingFields>
            <outputObject>Account</outputObject>
        </objectMapping>
    </duplicateRuleMatchRules>
</DuplicateRule>
```

### Duplicate Record Sets and Items

When duplicates are detected and reported, they are stored in:

```sql
SELECT Id, DuplicateRuleId, DuplicateRule.DeveloperName, RecordCount
FROM DuplicateRecordSet
ORDER BY CreatedDate DESC
LIMIT 50
```

```sql
SELECT Id, DuplicateRecordSetId, RecordId
FROM DuplicateRecordItem
WHERE DuplicateRecordSetId = '{setId}'
```

---

## 3. Matching Rules

### Discovery Query (Tooling API)

```sql
SELECT Id, DeveloperName, MasterLabel, SobjectType, IsActive,
       RuleStatus, Description,
       LastModifiedDate, LastModifiedBy.Name
FROM MatchingRule
WHERE NamespacePrefix = null
ORDER BY SobjectType, DeveloperName
LIMIT 200
```

### Matching Methods

| Method          | Description                                         | Use Case                    |
|-----------------|-----------------------------------------------------|-----------------------------|
| Exact           | Field values must match exactly                     | Email, Phone, External ID   |
| Fuzzy: First Name | Phonetic and nickname matching for first names    | Contact/Lead dedup          |
| Fuzzy: Last Name  | Phonetic matching for last names                  | Contact/Lead dedup          |
| Fuzzy: Company Name | Normalized company name comparison              | Account/Lead dedup          |
| Fuzzy: Title    | Title normalization and matching                    | Contact dedup               |
| Fuzzy: Street   | Address normalization and matching                  | Account/Contact dedup       |
| Fuzzy: City     | City name normalization                             | Address matching            |
| Fuzzy: Phone    | Phone number normalization (strips formatting)      | Any phone field             |
| Fuzzy: Zip      | Zip/postal code normalization                       | Address matching            |

### Standard Matching Rules

Salesforce provides standard matching rules for common objects:

| Object  | Standard Rule                              | Fields Matched                    |
|---------|--------------------------------------------|-----------------------------------|
| Account | Standard_Account_Match_Rule_v2             | Name, BillingStreet, BillingCity  |
| Contact | Standard_Contact_Match_Rule_v2             | Name, Email, Phone, MailingStreet |
| Lead    | Standard_Lead_Match_Rule_v2                | Name, Email, Phone, Company      |

Standard rules cannot be edited but can be activated/deactivated.

### Retrieve Command

```bash
sf project retrieve start --metadata "MatchingRules" --target-org <alias>
```

Retrieve for a specific object:

```bash
sf project retrieve start --metadata "MatchingRules:{ObjectApiName}" --target-org <alias>
```

### File Path Convention

```
force-app/main/default/matchingRules/{ObjectApiName}.matchingRule-meta.xml
```

### Matching Rule XML Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<MatchingRules xmlns="http://soap.sforce.com/2006/04/metadata">
    <matchingRules>
        <fullName>Account_Matching_Rule</fullName>
        <label>Account Matching Rule</label>
        <description>Match accounts by name and billing address</description>
        <ruleStatus>Active</ruleStatus>
        <matchingRuleItems>
            <blankValueBehavior>NullNotAllowed</blankValueBehavior>
            <fieldName>Name</fieldName>
            <matchingMethod>Exact</matchingMethod>
        </matchingRuleItems>
        <matchingRuleItems>
            <blankValueBehavior>NullNotAllowed</blankValueBehavior>
            <fieldName>BillingStreet</fieldName>
            <matchingMethod>FuzzyStreet</matchingMethod>
        </matchingRuleItems>
    </matchingRules>
</MatchingRules>
```

### Blank Value Behavior

| Value           | Description                                         |
|-----------------|-----------------------------------------------------|
| NullNotAllowed  | Blank values do not match (stricter)                |
| NullEqualsNull  | Two blank values count as a match (more permissive) |

---

## 4. Field History Tracking

### Configuration

Field history tracking is configured per-field in the object's field metadata XML:

```xml
<fields>
    <fullName>Status__c</fullName>
    <label>Status</label>
    <type>Picklist</type>
    <trackHistory>true</trackHistory>
    <!-- other field properties -->
</fields>
```

The object itself must also have history tracking enabled:

```xml
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <enableHistory>true</enableHistory>
    <!-- other object properties -->
</CustomObject>
```

### Querying Field History

For standard objects, the history object follows the pattern `{Object}History`:

```sql
SELECT Id, ParentId, Field, OldValue, NewValue, CreatedDate, CreatedBy.Name
FROM AccountHistory
WHERE ParentId = '{recordId}'
ORDER BY CreatedDate DESC
LIMIT 100
```

For custom objects, the history object follows the pattern `{Object}__History`:

```sql
SELECT Id, ParentId, Field, OldValue, NewValue, CreatedDate, CreatedBy.Name
FROM MyCustomObject__History
WHERE ParentId = '{recordId}'
ORDER BY CreatedDate DESC
LIMIT 100
```

### Discovering Which Fields Are Tracked

Field history tracking configuration is not directly queryable via SOQL. To discover which
fields have tracking enabled:

1. Retrieve the object metadata and inspect `<trackHistory>` on each field
2. Or query the history object to see which field names appear:

```sql
SELECT Field, COUNT(Id)
FROM AccountHistory
GROUP BY Field
ORDER BY COUNT(Id) DESC
```

### Limits

| Limit                                    | Value |
|------------------------------------------|-------|
| Tracked fields per standard object       | 20    |
| Tracked fields per custom object         | 20    |
| History data retention (default)         | 18 months (then archived) |
| History data retention (with Field Audit Trail) | Up to 10 years |

### Field Audit Trail (Shield)

For orgs with Salesforce Shield, Field Audit Trail extends history tracking:
- Longer retention (up to 10 years via `HistoryRetentionPolicy`)
- Archived data queryable via `FieldHistoryArchive` (Big Object)

```sql
SELECT ParentId, FieldName, OldValue, NewValue, CreatedDate
FROM FieldHistoryArchive
WHERE ParentId = '{recordId}' AND FieldName = 'Status__c'
ORDER BY CreatedDate DESC
```

### History Tracking and Metadata Deployment

When deploying field metadata with `<trackHistory>true</trackHistory>`:
- The object must already have `<enableHistory>true</enableHistory>` set
- Deploying a field with `trackHistory=true` on an object that has not enabled history will fail
- Deploy order: enable object history first, then deploy fields with tracking

---

## 5. Deployment Patterns and Best Practices

### Deploy Order

1. Custom objects with `enableHistory` setting (if using field history)
2. Custom fields with `trackHistory` setting
3. Matching rules (duplicate rules reference them)
4. Duplicate rules (reference matching rules)
5. Permission set groups (reference permission sets — deploy permission sets first)

### Common Gotchas

- **Permission set group recalculation**: After deploying a permission set group, its status may show as `Outdated` until Salesforce recalculates the combined permissions. This happens automatically but may take a few minutes.
- **Muting permission set scope**: A muting permission set only mutes permissions within its group. It does not affect the same permission if granted by a permission set outside the group.
- **Duplicate rule activation order**: Only one duplicate rule per object can be the "first" rule evaluated. Rule `sortOrder` matters — lowest number evaluates first.
- **Matching rule activation limit**: Maximum of 5 active matching rules per object (including standard rules).
- **Matching rule activation delay**: After deploying a matching rule, it may take a few minutes to become active because the matching index needs to build.
- **Field history on formula fields**: Formula fields cannot have history tracking enabled — they are calculated, not stored.
- **Field history on encrypted fields**: Shield Platform Encryption fields can be tracked, but OldValue and NewValue show "Data is encrypted" in history records.
- **Field history tracking count**: The 20-field limit is per object, not per record type. Counts include fields that were previously tracked but are now disabled (until the tracked field list is explicitly updated).
- **Cross-object duplicate rules**: A duplicate rule on Lead can match against Account and Contact objects (cross-object matching). The matching rule on the target object must also be active.

### Naming Conventions (Typical Patterns)

| Type                  | Convention Example                              |
|-----------------------|-------------------------------------------------|
| Permission Set Group  | `Sales_Representative`, `Service_Agent`         |
| Muting Permission Set | `{GroupName}_Muting`                            |
| Duplicate Rule        | `{Object}_Duplicate_Rule`                       |
| Matching Rule         | `{Object}_Matching_Rule`                        |

---

## 6. Useful Supplemental Queries

### All Permission Set Groups with Member Count

```sql
SELECT Id, DeveloperName, MasterLabel, Status,
       (SELECT PermissionSetId, PermissionSet.Name
        FROM PermissionSetGroupComponents)
FROM PermissionSetGroup
WHERE NamespacePrefix = null
ORDER BY DeveloperName
```

### Active Duplicate Rules with Their Matching Rules

Duplicate rules reference matching rules in their XML metadata. To see the relationship,
retrieve the duplicate rule and inspect the `<duplicateRuleMatchRules>` section.

### Objects with History Tracking Enabled

```sql
SELECT QualifiedApiName, DurableId
FROM EntityDefinition
WHERE IsCustomizable = true AND IsQueryable = true
ORDER BY QualifiedApiName
```

Then for each object, check if `{Object}History` or `{Object}__History` is queryable.

### Users Assigned to Permission Set Groups

```sql
SELECT Assignee.Name, Assignee.Username, PermissionSetGroup.DeveloperName
FROM PermissionSetAssignment
WHERE PermissionSetGroupId != null
ORDER BY PermissionSetGroup.DeveloperName, Assignee.Name
```

---

## Context Specification

- metadata_type: PermissionSetGroup, DuplicateRule, MatchingRule
- context_path: {alias}/security-advanced/
- inventory_file: {alias}/security-advanced/_inventory.md
- detail_file_pattern: {alias}/security-advanced/{ApiName}.md

### Change Detection Queries

**Permission Set Groups** — Uses: Standard API
```sql
SELECT Id, DeveloperName, MasterLabel, Status,
       LastModifiedDate, LastModifiedBy.Name
FROM PermissionSetGroup
WHERE NamespacePrefix = null AND LastModifiedDate > {LAST_SCAN}
ORDER BY LastModifiedDate DESC
LIMIT 50
```

**Duplicate Rules** — Uses: Tooling API
```sql
SELECT Id, DeveloperName, MasterLabel, SobjectType, IsActive,
       LastModifiedDate, LastModifiedBy.Name
FROM DuplicateRule
WHERE NamespacePrefix = null AND LastModifiedDate > {LAST_SCAN}
ORDER BY LastModifiedDate DESC
LIMIT 50
```

**Matching Rules** — Uses: Tooling API
```sql
SELECT Id, DeveloperName, MasterLabel, SobjectType, IsActive,
       LastModifiedDate, LastModifiedBy.Name
FROM MatchingRule
WHERE NamespacePrefix = null AND LastModifiedDate > {LAST_SCAN}
ORDER BY LastModifiedDate DESC
LIMIT 50
```

### Inventory Columns

API Name | Label | Type (PSG/DuplicateRule/MatchingRule) | Object | Status/Active | Last Modified | Last Scanned

### Detail File Sections

Identity, Type, Object, Configuration Details, Member List (for PSG), Rule Criteria (for Duplicate/Matching), Naming Convention Notes

### Naming Convention Detection

During scan, detect patterns in permission set group / duplicate rule / matching rule names:
- Permission set group naming relative to roles or personas
- Duplicate rule naming relative to objects
- Record in `_inventory.md` header as `Detected naming pattern: {pattern}`
