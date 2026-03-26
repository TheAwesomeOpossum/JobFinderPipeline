---
name: sf-reporting
description: "Reference for Salesforce reporting metadata — Reports, Dashboards, List Views, and custom Report Types. Includes API queries, metadata structure, and deployment patterns."
---

# Salesforce Reporting Skill

Reference for querying, retrieving, deploying, and managing Salesforce reporting metadata:
Reports, Dashboards, List Views, and custom Report Types.

---

## 1. Reports

### Discovery Query (Standard API)

```sql
SELECT Id, Name, DeveloperName, FolderName, Format, Description,
       LastRunDate, LastModifiedDate, LastModifiedBy.Name
FROM Report
WHERE IsDeleted = false
ORDER BY FolderName, Name
LIMIT 200
```

### Report Formats

| Format   | Description                                          |
|----------|------------------------------------------------------|
| TABULAR  | Flat list of rows — no groupings                     |
| SUMMARY  | Grouped rows with subtotals (up to 3 grouping levels)|
| MATRIX   | Rows grouped on two axes (row + column groupings)    |
| JOINED   | Multiple report blocks side-by-side in one report    |

### Retrieve Command

```bash
sf project retrieve start --metadata "Report:{FolderName}/{ReportName}" --target-org <alias>
```

To retrieve all reports in a folder:

```bash
sf project retrieve start --metadata "Report:{FolderName}" --target-org <alias>
```

To retrieve every report in the org (use sparingly — can be very large):

```bash
sf project retrieve start --metadata "Report" --target-org <alias>
```

### File Path Convention

```
force-app/main/default/reports/{FolderName}/{ReportDeveloperName}.report-meta.xml
```

### Report XML Structure (key elements)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Report xmlns="http://soap.sforce.com/2006/04/metadata">
    <name>Open Opportunities This Quarter</name>
    <reportType>Opportunity</reportType>
    <format>Summary</format>
    <groupingsDown>
        <dateGranularity>Day</dateGranularity>
        <field>ACCOUNT_NAME</field>
        <sortOrder>Asc</sortOrder>
    </groupingsDown>
    <columns>
        <field>OPPORTUNITY_NAME</field>
    </columns>
    <columns>
        <field>AMOUNT</field>
    </columns>
    <filter>
        <criteriaItems>
            <column>STAGE_NAME</column>
            <isUnlocked>true</isUnlocked>
            <operator>notEqual</operator>
            <value>Closed Won,Closed Lost</value>
        </criteriaItems>
    </filter>
    <timeFrameFilter>
        <dateColumn>CLOSE_DATE</dateColumn>
        <interval>INTERVAL_CURQ</interval>
    </timeFrameFilter>
</Report>
```

### Report Folders

Report folders control visibility. Query folders via:

```sql
SELECT Id, Name, DeveloperName, Type, AccessType
FROM Folder
WHERE Type = 'Report'
ORDER BY Name
```

- `AccessType` values: `Public`, `Hidden`, `Shared`
- Enhanced folder sharing uses `FolderShare` object (not queryable via SOQL — use Metadata API)

---

## 2. Dashboards

### Discovery Query (Standard API)

```sql
SELECT Id, Title, DeveloperName, FolderName, Description,
       RunningUserId, LastModifiedDate, LastModifiedBy.Name
FROM Dashboard
WHERE IsDeleted = false
ORDER BY FolderName, Title
LIMIT 200
```

### Running User

Dashboards run as either:
- **Specified user** — all viewers see the same data (set via `RunningUserId`)
- **Logged-in user** — each viewer sees their own data (Dynamic Dashboards)
- Dynamic dashboards count against org limits

### Retrieve Command

```bash
sf project retrieve start --metadata "Dashboard:{FolderName}/{DashboardName}" --target-org <alias>
```

### File Path Convention

```
force-app/main/default/dashboards/{FolderName}/{DashboardDeveloperName}.dashboard-meta.xml
```

### Dashboard Component Types

| Component Type    | Description                                |
|-------------------|--------------------------------------------|
| Chart             | Bar, line, pie, donut, funnel, scatter     |
| Table             | Tabular data from a source report          |
| Metric            | Single grand total number                  |
| Gauge             | Value against a defined range              |
| Rich Text         | Static text or images (Lightning only)     |
| Custom Lightning  | Embedded LWC component                     |

### Dashboard XML Structure (key elements)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Dashboard xmlns="http://soap.sforce.com/2006/04/metadata">
    <title>Sales Performance</title>
    <runningUser>admin@example.com</runningUser>
    <dashboardType>SpecifiedUser</dashboardType>
    <leftSection>
        <columnSize>Medium</columnSize>
        <components>
            <componentType>Chart</componentType>
            <report>unfiled$public/Open_Pipeline_Report</report>
            <chartAxisRange>Auto</chartAxisRange>
        </components>
    </leftSection>
</Dashboard>
```

---

## 3. List Views

### Discovery Query (Standard API)

```sql
SELECT Id, Name, DeveloperName, SobjectType, IsSOQLCompatible,
       LastModifiedDate, LastModifiedBy.Name
FROM ListView
WHERE SobjectType != null
ORDER BY SobjectType, DeveloperName
LIMIT 500
```

To filter to a specific object:

```sql
SELECT Id, Name, DeveloperName, SobjectType
FROM ListView
WHERE SobjectType = 'Account'
ORDER BY DeveloperName
```

### Retrieve Command

List views are retrieved as part of their parent object metadata:

```bash
sf project retrieve start --metadata "ListView:{ObjectName}.{ListViewName}" --target-org <alias>
```

Or retrieve all list views for an object:

```bash
sf project retrieve start --metadata "CustomObject:{ObjectName}" --target-org <alias>
```

### File Path Convention

```
force-app/main/default/objects/{ObjectApiName}/listViews/{ListViewDeveloperName}.listView-meta.xml
```

### List View XML Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ListView xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>My_Open_Cases</fullName>
    <label>My Open Cases</label>
    <filterScope>Mine</filterScope>
    <filters>
        <field>CASES.STATUS</field>
        <operation>notEqual</operation>
        <value>Closed</value>
    </filters>
    <columns>CASES.CASE_NUMBER</columns>
    <columns>CASES.SUBJECT</columns>
    <columns>CASES.STATUS</columns>
    <columns>CASES.PRIORITY</columns>
    <columns>CASES.CREATED_DATE</columns>
</ListView>
```

### Filter Scope Values

| Scope           | Description                          |
|-----------------|--------------------------------------|
| Everything      | All records visible to the user      |
| Mine            | Records owned by the running user    |
| MineAndMyGroups | Records owned by user or their groups|
| Queue           | Records in a specific queue          |
| Delegated       | Delegated records                    |
| MyTerritory     | Records in the user's territory      |
| MyTeamTerritory | Records in the user's team territory |

---

## 4. Custom Report Types

### Important: NOT Queryable via SOQL

Custom Report Types cannot be discovered via Standard or Tooling API SOQL.
You must retrieve them via the Metadata API.

### Retrieve Command

Retrieve all custom report types:

```bash
sf project retrieve start --metadata "ReportType" --target-org <alias>
```

Retrieve a specific report type:

```bash
sf project retrieve start --metadata "ReportType:{DeveloperName}" --target-org <alias>
```

### File Path Convention

```
force-app/main/default/reportTypes/{DeveloperName}.reportType-meta.xml
```

### Report Type XML Structure (key elements)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ReportType xmlns="http://soap.sforce.com/2006/04/metadata">
    <baseObject>Account</baseObject>
    <category>accounts</category>
    <deployed>true</deployed>
    <description>Accounts with related Contacts</description>
    <label>Accounts with Contacts</label>
    <join>
        <outerJoin>false</outerJoin>
        <relationship>Contacts</relationship>
        <join>
            <outerJoin>true</outerJoin>
            <relationship>Cases</relationship>
        </join>
    </join>
    <sections>
        <columns>
            <checkedByDefault>true</checkedByDefault>
            <field>Account.Name</field>
            <table>Account</table>
        </columns>
    </sections>
</ReportType>
```

### Join Types

- **Inner join** (`outerJoin = false`): Primary "with" related — only records that have child records
- **Outer join** (`outerJoin = true`): Primary "with or without" related — includes records missing child records
- Up to 4 objects can be chained in a single report type (A → B → C → D)

---

## 5. Deployment Patterns and Best Practices

### Deploy Order

1. Custom objects and fields (reports reference them)
2. Custom report types (reports reference them)
3. Report folders (reports live inside them)
4. Reports (dashboards reference them)
5. Dashboard folders
6. Dashboards

### Common Gotchas

- **Large result sets**: The `Report` and `ListView` queries can return hundreds of records. Always use `LIMIT` and filter by folder or object when possible.
- **Folder permissions**: Report/Dashboard folder sharing is managed via `FolderShare` metadata, not SOQL. Must retrieve separately.
- **Report type dependencies**: A report type must exist in the org before any report that uses it can be deployed. Deploy report types first.
- **Cross-object report types**: If a custom report type references custom objects, those objects must exist before the report type is deployed.
- **List view visibility**: List views with `filterScope = Queue` reference Queue IDs that differ between orgs. Use Queue DeveloperName references where possible.
- **Dashboard running user**: If a dashboard specifies a `runningUser`, that user must exist in the target org. Consider using logged-in user mode for portability.
- **Joined reports**: Cannot be created via the API in older API versions. Retrieve-only in some orgs.
- **Report chart on page layout**: Stored in layout metadata, not report metadata.
- **Enhanced analytics (CRM Analytics / Tableau CRM)**: Completely separate metadata type — not covered by this skill.

### Naming Conventions (Typical Patterns)

| Type        | Convention Example                     |
|-------------|----------------------------------------|
| Report      | `Open_Opportunities_This_Quarter`      |
| Dashboard   | `Sales_Performance_Dashboard`          |
| List View   | `All_Open_Cases` or `My_Open_Cases`    |
| Report Type | `Accounts_with_Contacts`               |
| Folder      | `Sales_Reports`, `Service_Dashboards`  |

---

## 6. Useful Supplemental Queries

### Recently Modified Reports

```sql
SELECT Id, Name, DeveloperName, FolderName, Format,
       LastModifiedDate, LastModifiedBy.Name
FROM Report
WHERE LastModifiedDate > LAST_N_DAYS:30
ORDER BY LastModifiedDate DESC
LIMIT 50
```

### Reports by Report Type

```sql
SELECT Id, Name, DeveloperName, FolderName, Format
FROM Report
WHERE ReportTypeApiName = 'Opportunity'
ORDER BY Name
```

### Dashboard Components Referencing a Report

Dashboards reference reports by name in their XML. To find which dashboards use a specific report,
retrieve all dashboards and search the XML for the report's folder-qualified name.

### List Views with Specific Columns

List view column configuration is not queryable via SOQL. Retrieve the list view XML and inspect
the `<columns>` elements.

---

## Context Specification

- metadata_type: Report, Dashboard, ListView
- context_path: {alias}/reporting/
- inventory_file: {alias}/reporting/_inventory.md
- detail_file_pattern: {alias}/reporting/{ApiName}.md

### Change Detection Queries

**Reports** — Uses: Standard API
```sql
SELECT Id, Name, DeveloperName, FolderName, Format,
       LastModifiedDate, LastModifiedBy.Name
FROM Report
WHERE LastModifiedDate > {LAST_SCAN} AND IsDeleted = false
ORDER BY LastModifiedDate DESC
LIMIT 50
```

**Dashboards** — Uses: Standard API
```sql
SELECT Id, Title, DeveloperName, FolderName,
       LastModifiedDate, LastModifiedBy.Name
FROM Dashboard
WHERE LastModifiedDate > {LAST_SCAN} AND IsDeleted = false
ORDER BY LastModifiedDate DESC
LIMIT 50
```

**List Views** — Uses: Standard API
```sql
SELECT Id, Name, DeveloperName, SobjectType,
       LastModifiedDate, LastModifiedBy.Name
FROM ListView
WHERE LastModifiedDate > {LAST_SCAN}
ORDER BY LastModifiedDate DESC
LIMIT 50
```

### Inventory Columns

API Name | Label/Title | Type | Folder/Object | Format | Last Modified | Last Scanned

### Detail File Sections

Identity, Format/Type, Folder, Filters, Columns/Components, Referenced Objects, Naming Convention Notes

### Naming Convention Detection

During scan, detect patterns in report/dashboard/list view names:
- Prefix patterns (e.g., `Sales_`, `Service_`)
- Folder organization patterns
- List view naming consistency per object
- Record in `_inventory.md` header as `Detected naming pattern: {pattern}`
