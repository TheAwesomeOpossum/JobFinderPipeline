---
name: sf-data-architecture
description: "Reference for Salesforce data architecture metadata — Record Types, Custom Metadata Types (__mdt), Custom Settings, Custom Labels, Global Value Sets, Field Sets, Platform Events (__e), and Business Processes. Includes Tooling API queries, XML structures, and usage patterns."
---

# SF Data Architecture Skill

---

## 1. Record Types

### Purpose

Record Types allow a single object to support multiple business processes, each with its own:
- Page layout assignment
- Picklist value subset
- Business process (for Opportunity, Case, Lead)
- Default values and validation rule behavior (via `$RecordType.DeveloperName`)

Record Types are fundamental to multi-process orgs — they separate different workflows on the same object without duplicating schema.

### Query — Standard API

```sql
SELECT Id, Name, DeveloperName, SobjectType, IsActive, Description,
       BusinessProcessId, IsPersonType
FROM RecordType
WHERE IsActive = true
ORDER BY SobjectType, DeveloperName
```

### Query — Tooling API (for LastModifiedDate)

```sql
SELECT Id, Name, DeveloperName, EntityDefinitionId,
       EntityDefinition.QualifiedApiName, IsActive, Description,
       LastModifiedDate, LastModifiedBy.Name
FROM RecordType
WHERE EntityDefinition.NamespacePrefix = null
ORDER BY EntityDefinition.QualifiedApiName, DeveloperName
```

### File Path

```
force-app/main/default/objects/{Object}/recordTypes/{RecordTypeName}.recordType-meta.xml
```

### XML Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<RecordType xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>My_Record_Type</fullName>
    <active>true</active>
    <businessProcess>My Business Process</businessProcess>
    <description>Description of this record type.</description>
    <label>My Record Type</label>
    <picklistValues>
        <picklist>Status__c</picklist>
        <values>
            <fullName>New</fullName>
            <default>true</default>
        </values>
        <values>
            <fullName>In Progress</fullName>
            <default>false</default>
        </values>
    </picklistValues>
</RecordType>
```

### CLI Commands

```bash
# Retrieve all record types for an object
sf project retrieve start \
  --metadata "RecordType:{ObjectName__c}" \
  --target-org <alias>

# Retrieve a single record type
sf project retrieve start \
  --metadata "RecordType:{ObjectName__c}.{RecordTypeDeveloperName}" \
  --target-org <alias>

# Deploy record types
sf project deploy start \
  --metadata "RecordType:{ObjectName__c}" \
  --target-org <alias> --wait 10
```

### Key Interactions

| Interaction | Detail |
|---|---|
| **Page Layouts** | Each profile can have a different layout per record type. Assigned in profile XML under `layoutAssignments`. |
| **Picklist Values** | Record types can restrict which picklist values are available. Configured in the record type XML `picklistValues` section. |
| **Business Processes** | Opportunity (Sales Process), Case (Support Process), and Lead (Lead Process) record types reference a BusinessProcess. |
| **Profiles** | Record type availability and default record type are set per profile. |
| **Permission Sets** | Permission sets cannot set a default record type — only profiles can. Permission sets can grant record type visibility. |
| **Formulas / VR** | Use `$RecordType.DeveloperName` in validation rules and formula fields to apply logic per record type. |

### Gotchas

- Record type DeveloperName cannot be changed after creation via metadata API — you must delete and recreate.
- The `Master` record type always exists but is not returned by default in all queries.
- Deploying record type picklist values does NOT create the picklist values themselves — the values must already exist on the field.
- Business process must exist before deploying a record type that references it.

---

## 2. Custom Metadata Types (__mdt)

### Purpose

Custom Metadata Types store application configuration data that is:
- Deployable via metadata API (unlike Custom Settings data)
- Queryable in SOQL without counting against governor limits
- Usable in validation rules, formula fields, and flows
- Package-safe for ISV distribution

Think of CMDTs as "configuration tables" that travel with your metadata deployments.

### Discover CMDTs — Tooling API

```sql
SELECT QualifiedApiName, DeveloperName, Label, Description,
       LastModifiedDate, LastModifiedBy.Name
FROM EntityDefinition
WHERE QualifiedApiName LIKE '%__mdt'
AND NamespacePrefix = null
ORDER BY QualifiedApiName
```

### Query CMDT Records — Standard API

```sql
SELECT DeveloperName, Label, MasterLabel, {custom_fields}
FROM {CMDT_Name}__mdt
ORDER BY DeveloperName
```

### File Paths

**Type definition:**
```
force-app/main/default/objects/{TypeName}__mdt/
  {TypeName}__mdt.object-meta.xml
  fields/{FieldName}__c.field-meta.xml
```

**Record data:**
```
force-app/main/default/customMetadata/{TypeName}.{RecordDeveloperName}.md-meta.xml
```

### XML Structure — Type Definition

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>My Config Type</label>
    <pluralLabel>My Config Types</pluralLabel>
    <visibility>Public</visibility>
</CustomObject>
```

### XML Structure — Record

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomMetadata xmlns="http://soap.sforce.com/2006/04/metadata"
                xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                xmlns:xsd="http://www.w3.org/2001/XMLSchema">
    <label>My Config Record</label>
    <protected>false</protected>
    <values>
        <field>Field_One__c</field>
        <value xsi:type="xsd:string">SomeValue</value>
    </values>
    <values>
        <field>Field_Two__c</field>
        <value xsi:type="xsd:boolean">true</value>
    </values>
</CustomMetadata>
```

### CLI Commands

```bash
# Retrieve CMDT type + all records
sf project retrieve start \
  --metadata "CustomObject:{TypeName}__mdt" \
  --metadata "CustomMetadata:{TypeName}" \
  --target-org <alias>

# Deploy CMDT records
sf project deploy start \
  --metadata "CustomMetadata:{TypeName}" \
  --target-org <alias> --wait 10
```

### CMDT vs Custom Settings

| Feature | Custom Metadata Types | Custom Settings |
|---|---|---|
| Deployable data | Yes | No (data is org-specific) |
| SOQL governor limits | Does not count | Counts against limits |
| Usable in formulas / VR | Yes (`$CustomMetadata`) | Yes (`$Setup` for Hierarchy) |
| Apex access | SOQL query | `getInstance()` / `getAll()` |
| Suitable for | App config, mapping tables, routing rules | User/org preferences, feature flags |

### Apex Usage

```apex
// Query CMDT records in Apex
List<My_Config__mdt> configs = [
    SELECT DeveloperName, Field_One__c, Field_Two__c
    FROM My_Config__mdt
    WHERE IsActive__c = true
];

// Or use the getInstance pattern
My_Config__mdt config = My_Config__mdt.getInstance('Record_Name');
```

---

## 3. Custom Settings

### Purpose

Custom Settings store org-specific or user-specific data. Two types:

- **Hierarchy Settings** — Values cascade: Org Default → Profile → User. Great for feature flags, thresholds, and per-user configuration.
- **List Settings** — A flat list of records, similar to a custom object but cached and available without SOQL.

### Discover Custom Settings — Tooling API

```sql
SELECT QualifiedApiName, DeveloperName, Label, Description,
       LastModifiedDate, LastModifiedBy.Name
FROM EntityDefinition
WHERE IsCustomSetting = true
AND NamespacePrefix = null
ORDER BY QualifiedApiName
```

### File Path

```
force-app/main/default/objects/{SettingName}__c/
  {SettingName}__c.object-meta.xml
  fields/{FieldName}__c.field-meta.xml
```

### XML Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <customSettingsType>Hierarchy</customSettingsType>
    <enableFeeds>false</enableFeeds>
    <label>My App Settings</label>
    <visibility>Public</visibility>
</CustomObject>
```

### Apex Access Patterns

```apex
// Hierarchy Settings — returns the most specific value for the running user
My_App_Settings__c settings = My_App_Settings__c.getInstance();
Boolean featureEnabled = settings.Enable_Feature__c;

// Hierarchy — get org default explicitly
My_App_Settings__c orgDefault = My_App_Settings__c.getOrgDefaults();

// List Settings — get all records
Map<String, My_List_Setting__c> allSettings = My_List_Setting__c.getAll();
My_List_Setting__c specificRecord = My_List_Setting__c.getInstance('RecordName');
```

### When to Use Custom Settings vs CMDT

- Use **CMDT** when the configuration should be deployable across orgs (e.g., field mappings, routing rules, integration endpoints).
- Use **Custom Settings** when values differ per org/user and should NOT travel with deployments (e.g., feature flags per environment, user preferences).
- **Hierarchy settings** are ideal for feature toggles and bypass flags (e.g., `Disable_Validation__c` checked for integration users).

---

## 4. Custom Labels

### Purpose

Custom Labels store text strings that can be:
- Translated for multi-language orgs
- Referenced in Apex, Visualforce, LWC, and Aura
- Deployed via metadata API

### Query — Tooling API

The Tooling API object for Custom Labels is `ExternalString`:

```sql
SELECT Id, Name, Value, Category, Language, IsProtected,
       LastModifiedDate, LastModifiedBy.Name
FROM ExternalString
WHERE NamespacePrefix = null
ORDER BY Name
```

### File Path

All custom labels are stored in a single file:
```
force-app/main/default/labels/CustomLabels.labels-meta.xml
```

### XML Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomLabels xmlns="http://soap.sforce.com/2006/04/metadata">
    <labels>
        <fullName>Error_Required_Field</fullName>
        <categories>Error,Validation</categories>
        <language>en_US</language>
        <protected>false</protected>
        <shortDescription>Error Required Field</shortDescription>
        <value>This field is required. Please enter a value before saving.</value>
    </labels>
    <labels>
        <fullName>Success_Record_Created</fullName>
        <categories>Success</categories>
        <language>en_US</language>
        <protected>false</protected>
        <shortDescription>Success Record Created</shortDescription>
        <value>Record created successfully.</value>
    </labels>
</CustomLabels>
```

### Usage Patterns

```apex
// Apex
String msg = System.Label.Error_Required_Field;
```

```javascript
// LWC
import errorLabel from '@salesforce/label/c.Error_Required_Field';
import successLabel from '@salesforce/label/c.Success_Record_Created';

export default class MyComponent extends LightningElement {
    labels = {
        error: errorLabel,
        success: successLabel
    };
}
```

```html
<!-- Visualforce -->
{!$Label.c.Error_Required_Field}
```

### CLI Commands

```bash
# Retrieve all custom labels
sf project retrieve start \
  --metadata "CustomLabel" \
  --target-org <alias>

# Deploy custom labels
sf project deploy start \
  --metadata "CustomLabel" \
  --target-org <alias> --wait 10
```

### Gotchas

- All labels are in ONE file — merge conflicts are common in team environments.
- The `categories` field is a comma-separated string, not a picklist.
- Label `fullName` cannot contain spaces — use underscores.
- Maximum label value length is 1,000 characters.
- Translations are stored separately in translation files, not in the labels file.

---

## 5. Global Value Sets

### Purpose

Global Value Sets define picklist values that can be shared across multiple objects and fields. Instead of defining the same picklist values on each field, a Global Value Set is defined once and referenced by multiple fields.

### Query — Tooling API

```sql
SELECT Id, DeveloperName, MasterLabel, Description,
       LastModifiedDate, LastModifiedBy.Name
FROM GlobalValueSet
WHERE NamespacePrefix = null
ORDER BY DeveloperName
```

### File Path

```
force-app/main/default/globalValueSets/{Name}.globalValueSet-meta.xml
```

### XML Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<GlobalValueSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <customValue>
        <fullName>High</fullName>
        <default>false</default>
        <label>High</label>
    </customValue>
    <customValue>
        <fullName>Medium</fullName>
        <default>true</default>
        <label>Medium</label>
    </customValue>
    <customValue>
        <fullName>Low</fullName>
        <default>false</default>
        <label>Low</label>
    </customValue>
    <description>Priority levels used across multiple objects.</description>
    <masterLabel>Priority</masterLabel>
    <sorted>false</sorted>
</GlobalValueSet>
```

### CLI Commands

```bash
# Retrieve all global value sets
sf project retrieve start \
  --metadata "GlobalValueSet" \
  --target-org <alias>

# Deploy a specific global value set
sf project deploy start \
  --metadata "GlobalValueSet:{DeveloperName}" \
  --target-org <alias> --wait 10
```

### Referencing in a Field

When a picklist field uses a Global Value Set, the field XML references it via `<valueSet>`:

```xml
<fields>
    <fullName>Priority__c</fullName>
    <label>Priority</label>
    <type>Picklist</type>
    <valueSet>
        <valueSetName>Priority</valueSetName>
    </valueSet>
</fields>
```

### Gotchas

- Adding values to a Global Value Set immediately makes them available on ALL fields that reference it.
- Removing/deactivating values affects all referencing fields — check impact first.
- Record types can still restrict which values from a Global Value Set are available.
- You cannot convert a field-level picklist to a Global Value Set via metadata API — this must be done in Setup UI.
- **When deploying a new GVS value, always deploy the GVS and every RecordType that restricts its visible values in the same operation.** If a RecordType's allowed value list is not updated to include the new value, the value exists in the GVS but remains invisible to records using that RecordType. Retrieve the affected RecordType(s), add the new value to their `<picklistValues>` section, and include them in the same deployment.

---

## 6. Field Sets

### Purpose

Field Sets are groups of fields that can be dynamically referenced in Visualforce pages, Lightning components, and Apex code. They allow admins to add/remove fields from a page without code changes.

### Query — Tooling API

```sql
SELECT Id, DeveloperName, MasterLabel, EntityDefinitionId,
       EntityDefinition.QualifiedApiName, Description,
       LastModifiedDate, LastModifiedBy.Name
FROM FieldSet
WHERE NamespacePrefix = null
ORDER BY EntityDefinition.QualifiedApiName, DeveloperName
```

### File Path

```
force-app/main/default/objects/{Object}/fieldSets/{FieldSetName}.fieldSet-meta.xml
```

### XML Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<FieldSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>My_Field_Set</fullName>
    <availableFields>
        <field>Optional_Field__c</field>
        <isFieldManaged>false</isFieldManaged>
        <isRequired>false</isRequired>
    </availableFields>
    <displayedFields>
        <field>Required_Field__c</field>
        <isFieldManaged>false</isFieldManaged>
        <isRequired>true</isRequired>
    </displayedFields>
    <description>Fields displayed on the intake form.</description>
    <label>My Field Set</label>
</FieldSet>
```

### Apex Usage

```apex
// Get all fields in a field set
List<Schema.FieldSetMember> fields =
    Schema.SObjectType.Account.fieldSets.getMap()
        .get('My_Field_Set').getFields();

// Iterate and build dynamic SOQL
String query = 'SELECT ';
for (Schema.FieldSetMember f : fields) {
    query += f.getFieldPath() + ', ';
}
query = query.removeEnd(', ') + ' FROM Account';
```

### Visualforce Usage

```html
<apex:repeat value="{!$ObjectType.Account.FieldSets.My_Field_Set}" var="f">
    <apex:inputField value="{!account[f.fieldPath]}" required="{!f.required}"/>
</apex:repeat>
```

### CLI Commands

```bash
# Retrieve field sets for an object
sf project retrieve start \
  --metadata "FieldSet:{ObjectName__c}" \
  --target-org <alias>

# Deploy field sets
sf project deploy start \
  --metadata "FieldSet:{ObjectName__c}" \
  --target-org <alias> --wait 10
```

---

## 7. Platform Events (__e)

### Purpose

Platform Events enable event-driven architecture in Salesforce. They are used for:
- Real-time integration with external systems
- Decoupled communication between Salesforce components
- Near-real-time processing of asynchronous operations
- Change Data Capture (CDC) style notifications

### Discover Platform Events — Tooling API

```sql
SELECT QualifiedApiName, DeveloperName, Label, Description,
       LastModifiedDate, LastModifiedBy.Name
FROM EntityDefinition
WHERE QualifiedApiName LIKE '%__e'
AND NamespacePrefix = null
ORDER BY QualifiedApiName
```

### File Path

```
force-app/main/default/objects/{EventName}__e/
  {EventName}__e.object-meta.xml
  fields/{FieldName}__c.field-meta.xml
```

### XML Structure — Event Definition

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <deploymentStatus>Deployed</deploymentStatus>
    <eventType>HighVolume</eventType>
    <label>My Platform Event</label>
    <pluralLabel>My Platform Events</pluralLabel>
    <publishBehavior>PublishAfterCommit</publishBehavior>
</CustomObject>
```

### Publish Behaviors

| Behavior | Description |
|---|---|
| `PublishAfterCommit` | Event is published only after the transaction commits successfully. Use for most business events. |
| `PublishImmediately` | Event is published immediately, even if the transaction rolls back. Use for logging/audit. |

### Apex — Publish

```apex
// Publish a single event
My_Event__e event = new My_Event__e(
    Record_Id__c = recordId,
    Action__c = 'Created',
    Payload__c = JSON.serialize(data)
);
Database.SaveResult sr = EventBus.publish(event);
if (!sr.isSuccess()) {
    for (Database.Error err : sr.getErrors()) {
        System.debug('Error: ' + err.getMessage());
    }
}

// Publish multiple events
List<My_Event__e> events = new List<My_Event__e>();
// ... populate events
List<Database.SaveResult> results = EventBus.publish(events);
```

### Apex — Subscribe (Trigger)

```apex
trigger MyEventTrigger on My_Event__e (after insert) {
    for (My_Event__e event : Trigger.New) {
        // Process event
        String recordId = event.Record_Id__c;
        String action = event.Action__c;
    }
}
```

### Subscribe via Flow

- Use a Platform Event-Triggered Flow
- Flow type: "Platform Event — Triggered Flow"
- Set the platform event as the trigger object
- Process each event record in the flow

### CLI Commands

```bash
# Retrieve a platform event definition
sf project retrieve start \
  --metadata "CustomObject:{EventName}__e" \
  --target-org <alias>

# Deploy a platform event
sf project deploy start \
  --metadata "CustomObject:{EventName}__e" \
  --target-org <alias> --wait 10
```

### Gotchas

- Platform Event triggers run under the Automated Process user, not the publishing user.
- Platform Events do not support all field types — no formula fields, no lookup fields.
- High-Volume events do not appear in Setup → Platform Events for monitoring; use Event Monitoring.
- `EventBus.publish()` is not subject to the normal DML governor limit — it has its own limit.
- Platform Event triggers can be retried by the platform — design for idempotency.

---

## 8. Business Processes

### Purpose

Business Processes define the picklist value subsets available for:
- **Opportunity** → Sales Process (Stage values)
- **Case** → Support Process (Status values)
- **Lead** → Lead Process (Status values)
- **Solution** → Solution Process (Status values)

Record types reference a business process to control which stage/status values are available.

### Query — Standard API

```sql
SELECT Id, Name, TableEnumOrId, IsActive, Description
FROM BusinessProcess
ORDER BY TableEnumOrId, Name
```

### File Path

Business processes are embedded in the object's XML, not standalone files:
```
force-app/main/default/objects/{Object}/businessProcesses/{ProcessName}.businessProcess-meta.xml
```

### XML Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<BusinessProcess xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Standard Sales Process</fullName>
    <isActive>true</isActive>
    <values>
        <fullName>Prospecting</fullName>
        <default>true</default>
    </values>
    <values>
        <fullName>Qualification</fullName>
        <default>false</default>
    </values>
    <values>
        <fullName>Proposal</fullName>
        <default>false</default>
    </values>
    <values>
        <fullName>Closed Won</fullName>
        <default>false</default>
    </values>
    <values>
        <fullName>Closed Lost</fullName>
        <default>false</default>
    </values>
</BusinessProcess>
```

### Key Rules

- A business process must exist BEFORE deploying a record type that references it.
- The `TableEnumOrId` value indicates which object the process belongs to: `Opportunity`, `Case`, `Lead`, or `Solution`.
- Each record type for these objects MUST reference a business process.
- Business process values must be a subset of the picklist values on the controlling field (Stage, Status, etc.).

### CLI Commands

```bash
# Retrieve business processes for an object
sf project retrieve start \
  --metadata "BusinessProcess:{ObjectName}" \
  --target-org <alias>

# Deploy business processes
sf project deploy start \
  --metadata "BusinessProcess:{ObjectName}" \
  --target-org <alias> --wait 10
```

---

## 9. Deployment Order for Data Architecture Metadata

When deploying data architecture components, follow this order to avoid dependency errors:

```
1. Global Value Sets          (picklist values must exist first)
2. Custom Metadata Type defs  (type definition before records)
3. Custom Settings defs       (object definition before data)
4. Platform Event defs        (event definition before triggers)
5. Custom Labels              (labels before code that references them)
6. Objects + Fields           (fields before record types that filter them)
7. Business Processes         (must exist before record types reference them)
8. Record Types               (depend on business processes + picklist values)
9. Field Sets                 (depend on fields existing)
10. Custom Metadata records   (depend on CMDT type definition)
```

---

## Context Specification

- metadata_type: RecordType, CustomMetadataType, CustomSetting, CustomLabel, GlobalValueSet, FieldSet, PlatformEvent
- context_path: {alias}/data-architecture/
- inventory_file: {alias}/data-architecture/_inventory.md
- detail_file_pattern: _(inventory only — no per-item detail files)_

### Full Inventory Queries

**Record Types** — Uses: standard API
```sql
SELECT Id, Name, DeveloperName, SobjectType, IsActive, Description,
       BusinessProcessId
FROM RecordType
WHERE IsActive = true
ORDER BY SobjectType, DeveloperName
```

**Custom Metadata Types** — Uses: tooling API
```sql
SELECT QualifiedApiName, DeveloperName, Label, Description,
       LastModifiedDate, LastModifiedBy.Name
FROM EntityDefinition
WHERE QualifiedApiName LIKE '%__mdt'
AND NamespacePrefix = null
ORDER BY QualifiedApiName
```

**Custom Settings** — Uses: tooling API
```sql
SELECT QualifiedApiName, DeveloperName, Label, Description,
       LastModifiedDate, LastModifiedBy.Name
FROM EntityDefinition
WHERE IsCustomSetting = true
AND NamespacePrefix = null
ORDER BY QualifiedApiName
```

**Custom Labels** — Uses: tooling API
```sql
SELECT Id, Name, Value, Category, Language, IsProtected,
       LastModifiedDate, LastModifiedBy.Name
FROM ExternalString
WHERE NamespacePrefix = null
ORDER BY Name
```

**Global Value Sets** — Uses: tooling API
```sql
SELECT Id, DeveloperName, MasterLabel, Description,
       LastModifiedDate, LastModifiedBy.Name
FROM GlobalValueSet
WHERE NamespacePrefix = null
ORDER BY DeveloperName
```

**Field Sets** — Uses: tooling API
```sql
SELECT Id, DeveloperName, MasterLabel, EntityDefinitionId,
       EntityDefinition.QualifiedApiName, Description,
       LastModifiedDate, LastModifiedBy.Name
FROM FieldSet
WHERE NamespacePrefix = null
ORDER BY EntityDefinition.QualifiedApiName, DeveloperName
```

**Platform Events** — Uses: tooling API
```sql
SELECT QualifiedApiName, DeveloperName, Label, Description,
       LastModifiedDate, LastModifiedBy.Name
FROM EntityDefinition
WHERE QualifiedApiName LIKE '%__e'
AND NamespacePrefix = null
ORDER BY QualifiedApiName
```

### Change Detection Queries

**Record Types** — Uses: standard API
```sql
SELECT Id, Name, DeveloperName, SobjectType, IsActive,
       LastModifiedDate, LastModifiedById
FROM RecordType
WHERE LastModifiedDate > {LAST_SCAN}
ORDER BY LastModifiedDate DESC
LIMIT 50
```

**Custom Labels** — Uses: tooling API
```sql
SELECT Id, Name, Value, Category, Language,
       LastModifiedDate, LastModifiedBy.Name
FROM ExternalString
WHERE LastModifiedDate > {LAST_SCAN}
AND NamespacePrefix = null
ORDER BY LastModifiedDate DESC
LIMIT 50
```

**Global Value Sets** — Uses: tooling API
```sql
SELECT Id, DeveloperName, MasterLabel,
       LastModifiedDate, LastModifiedBy.Name
FROM GlobalValueSet
WHERE LastModifiedDate > {LAST_SCAN}
AND NamespacePrefix = null
ORDER BY LastModifiedDate DESC
LIMIT 50
```

### Inventory Columns
Sub-Type | Object/Name | Developer Name | Active/Value | Last Modified Date | Last Modified By

### Detail File Sections
_(No per-item detail files — inventory groups items by sub-type. Retrieve full XML with appropriate `sf project retrieve start --metadata` commands per type.)_

### Naming Convention Detection
Analyze all discovered items and extract:
- **Record type naming:** `{Object}_{Process}` vs `{Descriptive_Name}` patterns
- **CMDT naming:** suffix patterns (`_Config__mdt`, `_Mapping__mdt`, `_Setting__mdt`)
- **Custom label categories:** comma-separated category values and naming prefixes (e.g., `Error_`, `Success_`, `UI_`)
- **Platform event naming:** suffix or domain patterns (e.g., `{Domain}_Event__e`)
- **Global value set naming:** descriptive names, object-prefixed names
- Report findings in the `## Detected Naming Conventions` section at the top of `_inventory.md`
