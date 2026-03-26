---
name: sf-layouts
description: "Reference for Salesforce page layouts, Lightning record pages (FlexiPages), compact layouts, and path settings. Includes Tooling API queries, XML structures, and deployment patterns."
---

# SF Layouts Skill

---

## 1. Page Layouts

### Purpose

Page layouts control the arrangement of fields, sections, related lists, buttons, and actions on a record detail page. They are assigned per profile and optionally per record type.

### Query — Tooling API

```sql
SELECT Id, Name, EntityDefinitionId, EntityDefinition.QualifiedApiName,
       LastModifiedDate, LastModifiedBy.Name
FROM Layout
WHERE EntityDefinition.NamespacePrefix = null
ORDER BY EntityDefinition.QualifiedApiName, Name
```

### File Path

```
force-app/main/default/layouts/{ObjectName}-{LayoutName}.layout-meta.xml
```

**Naming rule:** The filename is `{ObjectApiName}-{Layout Label}.layout-meta.xml`. Spaces in the layout label are preserved in the filename. Example: `Account-Account Layout.layout-meta.xml`.

### XML Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Layout xmlns="http://soap.sforce.com/2006/04/metadata">
    <layoutSections>
        <customLabel>false</customLabel>
        <detailHeading>false</detailHeading>
        <editHeading>true</editHeading>
        <label>Information</label>
        <layoutColumns>
            <layoutItems>
                <behavior>Required</behavior>
                <field>Name</field>
            </layoutItems>
            <layoutItems>
                <behavior>Edit</behavior>
                <field>Status__c</field>
            </layoutItems>
        </layoutColumns>
        <layoutColumns>
            <layoutItems>
                <behavior>Edit</behavior>
                <field>Phone</field>
            </layoutItems>
        </layoutColumns>
        <style>TwoColumnsTopToBottom</style>
    </layoutSections>
    <layoutSections>
        <customLabel>true</customLabel>
        <detailHeading>true</detailHeading>
        <editHeading>true</editHeading>
        <label>Custom Section</label>
        <layoutColumns>
            <layoutItems>
                <behavior>Edit</behavior>
                <field>Custom_Field__c</field>
            </layoutItems>
        </layoutColumns>
        <layoutColumns/>
        <style>TwoColumnsLeftToRight</style>
    </layoutSections>
    <relatedLists>
        <fields>FULL_NAME</fields>
        <fields>CONTACT.TITLE</fields>
        <fields>CONTACT.PHONE1</fields>
        <relatedList>RelatedContactList</relatedList>
    </relatedLists>
    <quickActionList>
        <quickActionListItems>
            <quickActionName>FeedItem.TextPost</quickActionName>
        </quickActionListItems>
        <quickActionListItems>
            <quickActionName>NewContact</quickActionName>
        </quickActionListItems>
    </quickActionList>
</Layout>
```

### Layout Section Styles

| Style | Description |
|---|---|
| `TwoColumnsTopToBottom` | Two columns, fields fill top to bottom in each column |
| `TwoColumnsLeftToRight` | Two columns, fields fill left to right across columns |
| `OneColumn` | Single column, full width |
| `CustomLinks` | Section for custom links (legacy) |

### Layout Item Behaviors

| Behavior | Description |
|---|---|
| `Required` | Field is required on this layout (layout-level required, not schema-level) |
| `Edit` | Field is editable |
| `Readonly` | Field is visible but not editable on this layout |

### CLI Commands

```bash
# Retrieve a specific layout
sf project retrieve start \
  --metadata "Layout:{ObjectName__c}-{Layout Name}" \
  --target-org <alias>

# Retrieve all layouts for an object
sf project retrieve start \
  --metadata "Layout:{ObjectName__c}" \
  --target-org <alias>

# Deploy a specific layout
sf project deploy start \
  --metadata "Layout:{ObjectName__c}-{Layout Name}" \
  --target-org <alias> --wait 10

# Deploy all layouts
sf project deploy start \
  --source-dir force-app/main/default/layouts \
  --target-org <alias> --wait 10
```

### Important: Always Retrieve Before Editing

**Never build a layout XML from scratch.** Layouts contain hundreds of lines of metadata including all related lists, quick actions, and platform-managed sections. Always:

1. Retrieve the layout from the org
2. Edit the retrieved XML
3. Deploy the modified XML

Building from scratch will result in missing sections, lost related lists, and broken page configurations.

---

## 2. FlexiPages (Lightning Record Pages)

### Purpose

FlexiPages are Lightning record pages, app pages, and home pages built in Lightning App Builder. They define the component layout for Lightning Experience and can contain standard and custom Lightning components.

### Query — Tooling API

```sql
SELECT Id, DeveloperName, MasterLabel, EntityDefinitionId,
       EntityDefinition.QualifiedApiName, Type,
       LastModifiedDate
FROM FlexiPage
WHERE NamespacePrefix = null
ORDER BY Type, DeveloperName
```

_Note: `LastModifiedBy.Name` is NOT available on the `FlexiPage` Tooling API object — omit it._

### File Path

```
force-app/main/default/flexipages/{DeveloperName}.flexipage-meta.xml
```

### FlexiPage Types

| Type | Description |
|---|---|
| `RecordPage` | Lightning record page for a specific object |
| `AppPage` | Standalone Lightning app page |
| `HomePage` | Lightning home page |
| `UtilityBar` | Utility bar configuration |
| `FlowPage` | Flow screen page |

### XML Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<FlexiPage xmlns="http://soap.sforce.com/2006/04/metadata">
    <flexiPageRegions>
        <itemInstances>
            <componentInstance>
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
        <itemInstances>
            <componentInstance>
                <componentName>c:myCustomComponent</componentName>
                <componentInstanceProperties>
                    <name>recordId</name>
                    <value>{!Record.Id}</value>
                </componentInstanceProperties>
            </componentInstance>
        </itemInstances>
        <name>main</name>
        <type>Region</type>
    </flexiPageRegions>
    <flexiPageRegions>
        <itemInstances>
            <componentInstance>
                <componentName>force:relatedListContainer</componentName>
            </componentInstance>
        </itemInstances>
        <name>sidebar</name>
        <type>Region</type>
    </flexiPageRegions>
    <masterLabel>My Record Page</masterLabel>
    <sobjectType>My_Object__c</sobjectType>
    <template>
        <name>flexipage:defaultPageTemplate</name>
    </template>
    <type>RecordPage</type>
</FlexiPage>
```

### Common Standard Components

| Component Name | Purpose |
|---|---|
| `force:highlightsPanel` | Compact layout / highlights panel at top of record |
| `force:detailPanel` | Record detail section (renders the page layout) |
| `force:relatedListContainer` | All related lists |
| `force:relatedListSingleContainer` | A specific related list |
| `runtime_sales_activities:activityPanel` | Activity timeline |
| `force:recordDetailWithInlineEdit` | Record detail with inline editing |
| `flexipage:richText` | Rich text area |
| `c:{componentName}` | Custom LWC or Aura component |

### Page Templates

| Template | Description |
|---|---|
| `flexipage:defaultPageTemplate` | Header + Main + Sidebar (standard 3-region) |
| `flexipage:defaultPageTemplateTwo` | Header + Full-width Main |
| `flexipage:defaultPageTemplateThree` | Header + Left + Right (two equal columns) |

### CLI Commands

```bash
# Retrieve a specific FlexiPage
sf project retrieve start \
  --metadata "FlexiPage:{DeveloperName}" \
  --target-org <alias>

# Retrieve all FlexiPages
sf project retrieve start \
  --metadata "FlexiPage" \
  --target-org <alias>

# Deploy a specific FlexiPage
sf project deploy start \
  --metadata "FlexiPage:{DeveloperName}" \
  --target-org <alias> --wait 10
```

### Activation

FlexiPages must be **activated** after deployment to be visible to users. Activation can be done:

- **Org default:** All users see this page for the object
- **App default:** Users see this page only in a specific Lightning app
- **App + Record Type + Profile:** Most granular assignment

**Activation is NOT deployable via metadata API in most cases.** After deploying a FlexiPage, you must manually activate it in Lightning App Builder (Setup → Lightning App Builder → Edit → Activation).

**Exception:** You can deploy activation assignments via `objectTranslations` or by including the `flexipageAccess` in app metadata, but this is fragile and not commonly used.

### Important: Always Retrieve Before Editing

Like page layouts, FlexiPages should always be retrieved before editing. They contain complex region and component structures that are difficult to build from scratch correctly.

---

## 3. Compact Layouts

### Purpose

Compact Layouts define which fields appear in:
- The highlights panel at the top of a record page
- Mobile record views
- Lookup card hovers
- Einstein activity capture

### Query — Tooling API

```sql
SELECT Id, DeveloperName, FullName, SobjectType,
       LastModifiedDate, LastModifiedBy.Name
FROM CompactLayout
WHERE NamespacePrefix = null
ORDER BY SobjectType, DeveloperName
```

### File Path

```
force-app/main/default/objects/{Object}/compactLayouts/{Name}.compactLayout-meta.xml
```

### XML Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CompactLayout xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>My_Compact_Layout</fullName>
    <fields>Name</fields>
    <fields>Status__c</fields>
    <fields>Owner.Name</fields>
    <fields>Priority__c</fields>
    <fields>CreatedDate</fields>
    <label>My Compact Layout</label>
</CompactLayout>
```

### Key Rules

- Maximum **10 fields** per compact layout.
- The **first field** is used as the record title in the highlights panel.
- The first field should generally be the `Name` field or a meaningful identifier.
- Compact layout assignment (which compact layout is the primary) is set in the object XML under `<compactLayoutAssignment>`.

### Object-Level Assignment

In the object's `-meta.xml` file, the primary compact layout is specified:

```xml
<compactLayoutAssignment>My_Compact_Layout</compactLayoutAssignment>
```

### CLI Commands

```bash
# Retrieve compact layouts for an object
sf project retrieve start \
  --metadata "CompactLayout:{ObjectName__c}" \
  --target-org <alias>

# Deploy compact layouts
sf project deploy start \
  --metadata "CompactLayout:{ObjectName__c}" \
  --target-org <alias> --wait 10
```

---

## 4. Path Settings (Path Assistant)

### Purpose

Path (formerly Sales Path) provides a visual guide showing the stages/steps of a process (typically tied to a picklist field like Stage or Status). It displays coaching content at each step and can include key fields.

### Query

Path settings are **not directly queryable via Tooling API SOQL**. They must be retrieved via metadata API.

### Retrieve

```bash
# Retrieve all path settings
sf project retrieve start \
  --metadata "PathAssistant" \
  --target-org <alias>
```

### File Path

```
force-app/main/default/pathAssistants/{PathName}.pathAssistant-meta.xml
```

### XML Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<PathAssistant xmlns="http://soap.sforce.com/2006/04/metadata">
    <active>true</active>
    <entityName>Opportunity</entityName>
    <fieldName>StageName</fieldName>
    <masterLabel>Default Sales Path</masterLabel>
    <pathAssistantSteps>
        <fieldNames>Amount</fieldNames>
        <fieldNames>CloseDate</fieldNames>
        <info><![CDATA[<p>Confirm the prospect has a real need and budget.</p>]]></info>
        <picklistValueName>Qualification</picklistValueName>
    </pathAssistantSteps>
    <pathAssistantSteps>
        <fieldNames>Amount</fieldNames>
        <fieldNames>NextStep</fieldNames>
        <info><![CDATA[<p>Send the proposal and schedule follow-up.</p>]]></info>
        <picklistValueName>Proposal</picklistValueName>
    </pathAssistantSteps>
    <recordTypeName>Standard_Sales</recordTypeName>
</PathAssistant>
```

### Key Rules

- Path is tied to a specific picklist field on the object.
- Each step can have coaching content (rich text) and key fields.
- Path can be scoped to a specific record type via `recordTypeName`.
- Path must be activated after deployment (similar to FlexiPage activation).

---

## 5. Layout Assignment (Profile → Layout → Record Type)

### How Layout Assignments Work

Layout assignments are defined in the **profile** XML, not in the layout XML itself. Each profile specifies which layout to use for each object, and optionally per record type.

### Profile XML — Layout Assignments Section

```xml
<layoutAssignments>
    <layout>Account-Account Layout</layout>
</layoutAssignments>
<layoutAssignments>
    <layout>Account-Partner Account Layout</layout>
    <recordType>Account.Partner</recordType>
</layoutAssignments>
<layoutAssignments>
    <layout>Case-Case Layout</layout>
</layoutAssignments>
<layoutAssignments>
    <layout>Case-Support Case Layout</layout>
    <recordType>Case.Support</recordType>
</layoutAssignments>
```

### Assignment Logic

1. If a profile has a layout assignment with NO `recordType`, that layout is the default for that object.
2. If a profile has a layout assignment WITH a `recordType`, that layout is used when the record has that record type.
3. If no assignment exists for an object, Salesforce uses the system default layout.

### CLI — Retrieve Profile Layout Assignments

```bash
# Retrieve a profile (includes layout assignments)
sf project retrieve start \
  --metadata "Profile:{ProfileName}" \
  --target-org <alias>
```

### Gotchas

- Layout assignments live in the profile, so editing them requires retrieving + redeploying the profile.
- Permission sets do NOT have layout assignments — only profiles do.
- When deploying a new layout, you must also update the profile to assign it.
- The layout name in the assignment must exactly match the layout's full name (e.g., `Account-Account Layout`).

---

## 6. Deployment Order for Layout-Related Metadata

```
1. Objects + Fields       (fields must exist before layouts reference them)
2. Record Types           (record types must exist before layout assignments reference them)
3. Page Layouts           (layouts must exist before profiles reference them)
4. Compact Layouts        (can deploy alongside page layouts)
5. FlexiPages             (depend on objects and optionally custom LWC)
6. Profiles               (layout assignments reference layouts + record types)
7. Path Assistants        (depend on objects, picklist values, record types)
8. FlexiPage Activation   (manual step in Setup after FlexiPage deployment)
```

---

## 7. Common Gotchas

| Issue | Detail |
|---|---|
| **Layout filename must match** | The filename `{Object}-{Layout Label}.layout-meta.xml` must match the layout's full name exactly, including spaces. |
| **FlexiPage activation is manual** | Deploying a FlexiPage does NOT activate it. You must activate it via Lightning App Builder in Setup. |
| **Compact layout 10-field limit** | Compact layouts support a maximum of 10 fields. Attempting to add more will cause a deployment error. |
| **Related list field API names** | Related list field references in layout XML use special format for standard fields (e.g., `FULL_NAME`, `CONTACT.TITLE`) — always retrieve, never build from memory. |
| **Profile layout assignments are additive** | Deploying a profile with layout assignments only ADDS/UPDATES assignments — it does not remove existing assignments not in the XML. |
| **Never build layouts from scratch** | Page layouts and FlexiPages contain complex, platform-managed sections. Always retrieve from the org first, then modify. |
| **Quick action ordering** | The order of `quickActionListItems` in the layout XML determines the display order of actions. |
| **Blank columns matter** | Empty `<layoutColumns/>` elements in layout XML are significant — they define the empty column in a two-column layout. Removing them changes the layout structure. |

---

## Context Specification

- metadata_type: Layout, FlexiPage, CompactLayout
- context_path: {alias}/layouts/
- inventory_file: {alias}/layouts/_inventory.md
- detail_file_pattern: _(inventory only — no per-item detail files)_

### Full Inventory Queries

**Layouts** — Uses: tooling API
```sql
SELECT Id, Name, EntityDefinitionId, EntityDefinition.QualifiedApiName,
       LastModifiedDate, LastModifiedBy.Name
FROM Layout
WHERE EntityDefinition.NamespacePrefix = null
ORDER BY EntityDefinition.QualifiedApiName, Name
```

**FlexiPages** — Uses: tooling API
```sql
SELECT Id, DeveloperName, MasterLabel, EntityDefinitionId,
       EntityDefinition.QualifiedApiName, Type,
       LastModifiedDate
FROM FlexiPage
WHERE NamespacePrefix = null
ORDER BY Type, DeveloperName
```

_Note: `LastModifiedBy.Name` is NOT available on the `FlexiPage` Tooling API object — omit it._

**Compact Layouts** — Uses: tooling API
```sql
SELECT Id, DeveloperName, FullName, SobjectType,
       LastModifiedDate, LastModifiedBy.Name
FROM CompactLayout
WHERE NamespacePrefix = null
ORDER BY SobjectType, DeveloperName
```

### Change Detection Queries

**Layouts** — Uses: tooling API
```sql
SELECT Id, Name, EntityDefinitionId, EntityDefinition.QualifiedApiName,
       LastModifiedDate, LastModifiedBy.Name
FROM Layout
WHERE LastModifiedDate > {LAST_SCAN}
AND EntityDefinition.NamespacePrefix = null
ORDER BY LastModifiedDate DESC
LIMIT 50
```

**FlexiPages** — Uses: tooling API
```sql
SELECT Id, DeveloperName, MasterLabel, Type,
       LastModifiedDate
FROM FlexiPage
WHERE LastModifiedDate > {LAST_SCAN}
AND NamespacePrefix = null
ORDER BY LastModifiedDate DESC
LIMIT 50
```

_Note: `LastModifiedBy.Name` is NOT a valid relation on `FlexiPage` in Tooling API — omit it._

### Inventory Columns
Type | Object | Name/Developer Name | Label | Last Modified Date | Last Modified By

### Detail File Sections
_(No per-item detail files — inventory groups items by type. Retrieve full XML with `sf project retrieve start --metadata "Layout:{ObjectName}"` or `sf project retrieve start --metadata "FlexiPage:{DeveloperName}"`)_

### Naming Convention Detection
Analyze all discovered items and extract:
- **Layout naming:** `{Object}-{Description} Layout` vs `{Object}-{RecordType} Layout` patterns
- **FlexiPage naming:** `{Object}_Record_Page` vs `{Object}_{RecordType}_Page` patterns
- **Compact layout naming:** `{Object}_Compact` vs descriptive patterns
- Report findings in the `## Detected Naming Conventions` section at the top of `_inventory.md`
