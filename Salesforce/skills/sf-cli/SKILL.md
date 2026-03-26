---
name: sf-cli
description: Reference for Salesforce CLI (sf v2) commands used in org introspection, metadata operations, deployment, and data queries. Use when working with any Salesforce org connected via the CLI.
---

# SF CLI v2 — Reference Skill

## 1. Auth & Org Management

```bash
# Authenticate via browser
sf org login web --alias <alias>

# List all connected orgs
sf org list

# Show details of a specific org (confirms auth, returns instanceUrl + apiVersion)
sf org display --target-org <alias>

# Set default org so --target-org can be omitted
sf config set target-org=<alias>
```

---

## 2. Metadata Retrieve

```bash
# Retrieve all custom objects
sf project retrieve start --metadata "CustomObject" --target-org <alias>

# Retrieve a specific object (including its fields)
sf project retrieve start --metadata "CustomObject:MyObject__c" --target-org <alias>

# Retrieve System Administrator profile
sf project retrieve start --metadata "Profile:Admin" --target-org <alias>

# Retrieve all permission sets
sf project retrieve start --metadata "PermissionSet" --target-org <alias>

# Retrieve a specific permission set
sf project retrieve start --metadata "PermissionSet:MyPermSet" --target-org <alias>

# Retrieve all layouts
sf project retrieve start --metadata "Layout" --target-org <alias>

# Retrieve a specific layout
sf project retrieve start --metadata "Layout:MyObject__c-MyObject Layout" --target-org <alias>

# Retrieve FlexiPage
sf project retrieve start --metadata "FlexiPage" --target-org <alias>
sf project retrieve start --metadata "FlexiPage:MyObject_Record_Page" --target-org <alias>
```

### Managed Package Layout Retrieve — Namespace Prefix Required

When retrieving layouts that belong to a managed package, the metadata retrieve command requires the **full namespace-prefixed name**, even though the Tooling API and Salesforce Setup UI may omit the prefix.

**Symptom:** Retrieve returns "Entity not found" or empty results for a layout visible in Setup.

**To find the correct full metadata name — preferred approach:**

Query `LayoutAssignment` via Tooling API to get the exact name as the metadata API expects it:
```bash
sf data query \
  --query "SELECT Layout.Name, Layout.EntityDefinition.QualifiedApiName FROM LayoutAssignment WHERE Layout.EntityDefinition.QualifiedApiName = '<ObjectApiName>'" \
  --use-tooling-api \
  --target-org <alias>
```

**If the Tooling API query is unavailable, trial these patterns in order:**
1. `{Namespace}__{ObjectApiName}-{Namespace}__{Layout Label}` ← most common
   e.g. `AcctSeedERP__Sales_Order__c-AcctSeedERP__Sales Order Layout`
2. `{Namespace}__{ObjectApiName}-{Layout Label}` (object prefix only)
3. `{ObjectApiName}-{Namespace}__{Layout Label}` (layout prefix only)

**Note:** The object portion always uses the full namespaced API name (e.g. `AcctSeedERP__Sales_Order__c`).

**Fully managed / locked layouts:** If retrieve succeeds but deploy fails with a managed package error, the layout is package-locked and cannot be modified. Skip it and document the skip in the Issue Log.

---

## 3. Object & Field Introspection

```bash
# List all custom objects
sf sobject list --sobject-type custom --json --target-org <alias>

# List all standard objects
sf sobject list --sobject-type standard --json --target-org <alias>

# Describe a specific object (fields, types, required, relationships)
sf sobject describe --sobject MyObject__c --json --target-org <alias>
```

---

## 4. Deploy

```bash
# Deploy all metadata from project
sf project deploy start --source-dir force-app --target-org <alias> --wait 10

# Deploy specific metadata types
sf project deploy start --metadata "CustomObject" --target-org <alias> --wait 10
sf project deploy start --metadata "CustomObject:MyObject__c" --target-org <alias> --wait 10
sf project deploy start --metadata "Profile:Admin" --target-org <alias> --wait 10
sf project deploy start --metadata "Layout:MyObject__c-MyObject Layout" --target-org <alias> --wait 10
sf project deploy start --metadata "PermissionSet:MyPermSet" --target-org <alias> --wait 10
sf project deploy start --metadata "FlexiPage:MyObject_Record_Page" --target-org <alias> --wait 10

# Dry run (validate without deploying)
sf project deploy start --source-dir force-app --dry-run --wait 10 --target-org <alias>

# Test levels
--test-level NoTestRun          # scratch orgs / dev only
--test-level RunLocalTests      # sandboxes / production
--test-level RunAllTestsInOrg   # full validation

# Resume or check a deploy in progress
sf project deploy resume --job-id <id>
sf project deploy report --job-id <id>
```

---

## 5. Data Query

```bash
# Standard SOQL query
sf data query --query "SELECT Id, Name FROM Account LIMIT 10" --target-org <alias>

# JSON output
sf data query --query "SELECT Id, Name FROM Account" --json --target-org <alias>

# Tooling API query (metadata objects: ApexClass, FlowDefinition, etc.)
sf data query --query "SELECT Id, DeveloperName FROM CustomObject__c" --use-tooling-api --target-org <alias>
```

---

## 6. Metadata XML Formats

### Custom Object — `ObjectName__c.object-meta.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <deploymentStatus>Deployed</deploymentStatus>
    <label>Object Label</label>
    <pluralLabel>Object Labels</pluralLabel>
    <nameField>
        <label>Name</label>
        <type>Text</type>
    </nameField>
    <sharingModel>ReadWrite</sharingModel>
</CustomObject>
```

- `sharingModel` valid values: `Private`, `Read`, `ReadWrite`, `ControlledByParent`
- `ControlledByParent` is ONLY valid when the object is a Master-Detail child
- `deploymentStatus` must be `Deployed` (not `InDevelopment`) for fields/layouts to work

---

### Custom Field — `FieldName__c.field-meta.xml`

#### Type mapping table

| Spec Type        | XML `<type>` value   | Required sub-elements                                      |
|------------------|----------------------|------------------------------------------------------------|
| Text             | `Text`               | `<length>` (e.g. 255)                                      |
| Text Area        | `TextArea`           | _(none beyond type)_                                       |
| Long Text Area   | `LongTextArea`       | `<length>` (e.g. 32768), `<visibleLines>` (e.g. 5)        |
| Number           | `Number`             | `<precision>` (total digits), `<scale>` (decimal places)   |
| Currency         | `Currency`           | `<precision>`, `<scale>`                                   |
| Percent          | `Percent`            | `<precision>`, `<scale>`                                   |
| Date             | `Date`               | _(none)_                                                   |
| DateTime         | `DateTime`           | _(none)_                                                   |
| Checkbox         | `Checkbox`           | `<defaultValue>` (`true`/`false`)                          |
| Picklist         | `Picklist`           | `<valueSet>` block (see below)                             |
| Multi-Picklist   | `MultiselectPicklist`| `<valueSet>` block, `<visibleLines>`                       |
| Lookup           | `Lookup`             | `<referenceTo>`, `<relationshipName>`, `<relationshipLabel>`|
| Master-Detail    | `MasterDetail`       | `<referenceTo>`, `<relationshipName>`, `<relationshipLabel>`|
| Email            | `Email`              | _(none)_                                                   |
| Phone            | `Phone`              | _(none)_                                                   |
| URL              | `Url`                | _(none)_                                                   |
| Auto Number      | `AutoNumber`         | `<displayFormat>` (e.g. `{0000}`), `<startingNumber>`     |
| Formula          | `Summary` or type    | `<formula>`, `<formulaTreatBlanksAs>`                      |

#### Text field example
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>FieldName__c</fullName>
    <label>Field Label</label>
    <type>Text</type>
    <length>255</length>
    <required>false</required>
</CustomField>
```

#### Picklist field example
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Status__c</fullName>
    <label>Status</label>
    <type>Picklist</type>
    <valueSet>
        <restricted>true</restricted>
        <valueSetDefinition>
            <sorted>false</sorted>
            <value>
                <fullName>Active</fullName>
                <default>true</default>
                <label>Active</label>
            </value>
            <value>
                <fullName>Inactive</fullName>
                <default>false</default>
                <label>Inactive</label>
            </value>
        </valueSetDefinition>
    </valueSet>
</CustomField>
```

#### Lookup field example
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Account__c</fullName>
    <label>Account</label>
    <type>Lookup</type>
    <referenceTo>Account</referenceTo>
    <relationshipName>MyObjects</relationshipName>
    <relationshipLabel>My Objects</relationshipLabel>
    <required>false</required>
</CustomField>
```

---

### Profile — Object Permission Block

```xml
<objectPermissions>
    <allowCreate>true</allowCreate>
    <allowDelete>true</allowDelete>
    <allowEdit>true</allowEdit>
    <allowRead>true</allowRead>
    <modifyAllRecords>true</modifyAllRecords>
    <object>ObjectName__c</object>
    <viewAllRecords>true</viewAllRecords>
</objectPermissions>
```

### Profile — Field Permission Block

```xml
<fieldPermissions>
    <editable>true</editable>
    <field>ObjectName__c.FieldName__c</field>
    <readable>true</readable>
</fieldPermissions>
```

Note: Do NOT add fieldPermissions entries for standard fields (`Name`, `OwnerId`, `CreatedById`, `LastModifiedById`, `IsDeleted`, etc.).

---

### Permission Set — Full Skeleton

```xml
<?xml version="1.0" encoding="UTF-8"?>
<PermissionSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <description>Description of what this permission set grants</description>
    <label>Permission Set Label</label>
    <objectPermissions>
        <allowCreate>true</allowCreate>
        <allowDelete>false</allowDelete>
        <allowEdit>true</allowEdit>
        <allowRead>true</allowRead>
        <modifyAllRecords>false</modifyAllRecords>
        <object>ObjectName__c</object>
        <viewAllRecords>false</viewAllRecords>
    </objectPermissions>
    <fieldPermissions>
        <editable>true</editable>
        <field>ObjectName__c.FieldName__c</field>
        <readable>true</readable>
    </fieldPermissions>
</PermissionSet>
```

---

## 7. Directory Structure Reference

```
force-app/
└── main/
    └── default/
        ├── objects/
        │   └── ObjectName__c/
        │       ├── ObjectName__c.object-meta.xml
        │       └── fields/
        │           ├── FieldOne__c.field-meta.xml
        │           └── FieldTwo__c.field-meta.xml
        ├── profiles/
        │   └── Admin.profile-meta.xml
        ├── layouts/
        │   └── ObjectName__c-ObjectName Layout.layout-meta.xml
        ├── permissionsets/
        │   └── MyPermSet.permissionset-meta.xml
        └── flexipages/
            └── ObjectName_Record_Page.flexipage-meta.xml
```

---

## 8. Filename Conventions

| Type            | Convention                                                      | Example                                              |
|-----------------|-----------------------------------------------------------------|------------------------------------------------------|
| Object          | `{ObjectApiName}.object-meta.xml`                               | `Invoice__c.object-meta.xml`                         |
| Field           | `{FieldApiName}.field-meta.xml`                                 | `Amount__c.field-meta.xml`                           |
| Profile         | `{ProfileName}.profile-meta.xml`                                | `Admin.profile-meta.xml`                             |
| Layout          | `{ObjectApiName}-{LayoutName}.layout-meta.xml`                  | `Invoice__c-Invoice Layout.layout-meta.xml`          |
| PermissionSet   | `{PermSetDeveloperName}.permissionset-meta.xml`                 | `Invoice_Manager.permissionset-meta.xml`             |
| FlexiPage       | `{PageApiName}.flexipage-meta.xml` (underscores, no spaces)    | `Invoice_Record_Page.flexipage-meta.xml`             |

---

## 9. FlexiPage (Lightning Record Page)

### CLI Commands
```bash
# Retrieve
sf project retrieve start --metadata "FlexiPage" --target-org <alias>
sf project retrieve start --metadata "FlexiPage:MyObject_Record_Page" --target-org <alias>

# Deploy
sf project deploy start --metadata "FlexiPage:MyObject_Record_Page" --target-org <alias> --wait 10
```

### Directory
`force-app/main/default/flexipages/`

### Complete XML Template

```xml
<?xml version="1.0" encoding="UTF-8"?>
<FlexiPage xmlns="http://soap.sforce.com/2006/04/metadata">
    <flexiPageRegions>
        <itemInstances>
            <componentInstance>
                <componentInstanceProperties>
                    <name>collapsed</name>
                    <value>false</value>
                </componentInstanceProperties>
                <componentInstanceProperties>
                    <name>numVisibleActions</name>
                    <value>3</value>
                </componentInstanceProperties>
                <componentName>force:highlightsPanel</componentName>
            </componentInstance>
        </itemInstances>
        <name>header</name>
        <type>Region</type>
    </flexiPageRegions>
    <flexiPageRegions>
        <itemInstances>
            <componentInstance>
                <componentName>force:detailPanel</componentName>
            </componentInstance>
        </itemInstances>
        <name>main</name>
        <type>Region</type>
    </flexiPageRegions>
    <masterLabel>ObjectLabel Record Page</masterLabel>
    <sobjectType>ObjectName__c</sobjectType>
    <template>flexipage:recordHomeTemplateDesktop</template>
    <type>RecordPage</type>
</FlexiPage>
```

### Key Fields
- `<template>`: always `flexipage:recordHomeTemplateDesktop`
- `<type>`: always `RecordPage`
- `<sobjectType>`: the custom object API name (e.g. `Invoice__c`)
- `<masterLabel>`: human-readable, e.g. `Invoice Record Page`
- Header region: `force:highlightsPanel` with `collapsed: false`, `numVisibleActions: 3`
- Main region: `force:detailPanel` (no properties needed)

### Post-Deploy Manual Steps (Always Required)
Metadata deploy does NOT activate the page or assign it as org default. After deploy, user must:
1. Setup → Lightning App Builder → find page → click **Activate** → set as **Org Default** for Desktop AND Phone → Save
2. Setup → Tabs → Custom Object Tabs → New → select object → choose Tab Style → Save
3. Setup → App Manager → [app] → Edit → Navigation Items → add tab → Save

---

## 10. Common Error Patterns

| Error                                         | Cause                                                             | Fix                                                                    |
|-----------------------------------------------|-------------------------------------------------------------------|------------------------------------------------------------------------|
| `Unknown property 'FieldPermissions.field'`   | Profile references field that doesn't exist in org yet            | Deploy objects/fields BEFORE deploying profile                         |
| `INVALID_FIELD_FOR_INSERT_UPDATE`             | Field referenced in layout doesn't exist                          | Deploy fields BEFORE deploying layout                                  |
| `sharingModel ControlledByParent invalid`     | Object has no Master-Detail relationship field                    | Use `ReadWrite` or `Private`; only use `ControlledByParent` if MD child|
| `Duplicate value on record`                   | Local file out of sync with org                                   | `sf project retrieve start` to sync, then redeploy                     |
| `duplicate relationshipName`                  | Two Lookup/MD fields share the same `<relationshipName>`          | Make `<relationshipName>` unique across ALL fields on that object       |
| `Required field is missing: fullName`         | `<fullName>` inside XML doesn't match the filename                | Ensure `<fullName>FieldName__c</fullName>` matches `FieldName__c.field-meta.xml` |
| `Entity type not found`                       | Object doesn't exist in org yet                                   | Deploy the object before fields, layout, or profile permissions        |
| `DUPLICATE_VALUE on retrieve`                 | Concurrent retrieve or local conflict                             | Delete local file, re-retrieve                                         |

---

## 11. Useful Flags

| Flag                          | Purpose                                                   |
|-------------------------------|-----------------------------------------------------------|
| `--json`                      | Machine-readable output for all commands                  |
| `--target-org <alias>`        | Target a specific org (overrides config default)          |
| `--wait <minutes>`            | Wait for async operation to complete (default: 33)        |
| `--api-version <version>`     | Override API version (e.g. `59.0`)                        |
| `--dry-run`                   | Validate deploy without committing changes to org         |
| `--source-dir <path>`         | Deploy from a specific directory                          |
| `--metadata <type:name>`      | Deploy/retrieve specific metadata component               |
| `--test-level <level>`        | Test execution level for deploys                          |
| `--concise`                   | Shorter output for deploy results                         |
