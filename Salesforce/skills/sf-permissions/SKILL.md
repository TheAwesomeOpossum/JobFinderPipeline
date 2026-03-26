---
name: sf-permissions
description: "Reference for Salesforce permissions architecture: OLS/FLS/RLS model, OWD values, Profile XML, Permission Set XML, Sharing Rule XML, role hierarchy, public groups, CLI introspection queries, org permissions memory format, and best practices."
---

# SF Permissions Skill

---

## 1. Three-Layer Model

Salesforce enforces access through three layers applied in order. If a higher layer denies access, lower layers cannot grant it.

| Layer | Controls | Where Configured |
|---|---|---|
| **OLS** (Object-Level Security) | Whether a user can see/edit records of an object type at all | Profile objectPermissions, Permission Set objectPermissions |
| **FLS** (Field-Level Security) | Which specific fields a user can read or edit | Profile fieldPermissions, Permission Set fieldPermissions |
| **RLS** (Record-Level Security) | Which specific records a user can see/edit within the objects they have OLS access to | OWD, Role Hierarchy, Sharing Rules, Manual Sharing, Teams |

**Precedence rule:** If OLS denies access to an object, FLS and RLS are irrelevant — the user cannot see any records or fields. OLS must be granted first.

---

## 2. OWD (Organization-Wide Default) Values

OWD sets the baseline record visibility before role hierarchy and sharing rules are applied.

| Value | Who Can See Records | Who Can Edit Records | Best For |
|---|---|---|---|
| **Private** | Owner + users above in role hierarchy + System Admin | Owner + System Admin | Sensitive data; controlled sharing via explicit rules |
| **Read** | All users in org | Owner + System Admin | Reference data users need to look up but not change |
| **ReadWrite** | All users in org | All users in org | Collaborative objects; no need to restrict record access |
| **ControlledByParent** | Determined by parent record's OWD | Determined by parent record's OWD | Master-Detail children only |

**GOTCHA:** `ControlledByParent` is **only valid** for objects that have a Master-Detail relationship field. Setting it on an object with only Lookup fields will cause a deploy error.

**GOTCHA:** Changing OWD on objects with existing data triggers a sharing recalculation job. On large orgs this can take minutes to hours. Warn the user before changing OWD in production.

---

## 3. Profile XML (Reference)

Profiles are large files retrieved from the org. Always retrieve before editing; never overwrite the full file.

```xml
<!-- Object-level access block inside Admin.profile-meta.xml -->
<objectPermissions>
    <allowCreate>true</allowCreate>
    <allowDelete>true</allowDelete>
    <allowEdit>true</allowEdit>
    <allowRead>true</allowRead>
    <modifyAllRecords>true</modifyAllRecords>
    <object>ObjectName__c</object>
    <viewAllRecords>true</viewAllRecords>
</objectPermissions>

<!-- Field-level access block -->
<fieldPermissions>
    <editable>true</editable>
    <field>ObjectName__c.FieldName__c</field>
    <readable>true</readable>
</fieldPermissions>
```

Always append new blocks just before the closing `</Profile>` tag.

---

## 4. Permission Set XML (Full Skeleton)

**Path:** `force-app/main/default/permissionsets/{PermSetName}.permissionset-meta.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<PermissionSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <!-- Human-readable label shown in Salesforce Setup -->
    <label>Permission Set Label</label>
    <!-- Optional description documenting intended users/purpose -->
    <description>What this permission set grants and who it is for.</description>

    <!-- One objectPermissions block per object -->
    <objectPermissions>
        <allowCreate>true</allowCreate>       <!-- Can create new records -->
        <allowDelete>false</allowDelete>      <!-- Can delete records -->
        <allowEdit>true</allowEdit>           <!-- Can edit existing records -->
        <allowRead>true</allowRead>           <!-- Can view records (required for any access) -->
        <modifyAllRecords>false</modifyAllRecords>  <!-- Bypass sharing: edit all records -->
        <object>ObjectName__c</object>
        <viewAllRecords>false</viewAllRecords>      <!-- Bypass sharing: view all records -->
    </objectPermissions>

    <!-- One fieldPermissions block per custom field -->
    <fieldPermissions>
        <editable>true</editable>    <!-- false = read-only -->
        <field>ObjectName__c.FieldName__c</field>
        <readable>true</readable>    <!-- must be true if editable is true -->
    </fieldPermissions>
</PermissionSet>
```

**Access level reference table:**

| Access Level | allowRead | allowCreate | allowEdit | allowDelete | viewAll | modifyAll |
|---|---|---|---|---|---|---|
| Read Only | true | false | false | false | false | false |
| Read + Edit | true | false | true | false | false | false |
| Full CRUD | true | true | true | true | false | false |
| Full Admin | true | true | true | true | true | true |

**GOTCHA:** `modifyAllRecords` and `viewAllRecords` bypass all sharing rules and role hierarchy. Only grant these when truly required (e.g., admin-like support roles). Never grant as a convenience shortcut.

---

## 5. Permission Set Groups (Concept)

Permission Set Groups bundle multiple permission sets together so users receive one assignment instead of many. They are configured in Setup → Permission Set Groups and **cannot be deployed via CLI metadata** — they must be created manually in each org's Setup UI.

Use Permission Set Groups when a persona (e.g., "Field Technician") needs a combination of several focused permission sets. Document the intended groupings in memory for manual setup.

---

## 6. Sharing Rule XML

**Path:** `force-app/main/default/sharingRules/{ObjectName__c}.sharingRules-meta.xml`

**IMPORTANT:** A single file holds ALL sharing rules for one object. Always retrieve the existing file before editing; never overwrite.

### Owner-Based Sharing Rule
Shares records owned by members of one group with members of another group.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<SharingRules xmlns="http://soap.sforce.com/2006/04/metadata">
    <sharingOwnerRules>
        <fullName>Share_Owned_By_Field_Techs_With_Dispatchers</fullName>
        <accessLevel>Read</accessLevel>          <!-- Read or ReadWrite -->
        <description>Share field tech records with dispatchers for visibility.</description>
        <label>Share Field Tech Records with Dispatchers</label>
        <sharedTo>
            <group>Dispatchers</group>           <!-- Public Group API name -->
        </sharedTo>
        <sharedFrom>
            <group>Field_Technicians</group>     <!-- Records owned by this group -->
        </sharedFrom>
    </sharingOwnerRules>
</SharingRules>
```

### Criteria-Based Sharing Rule
Shares records that match field criteria with a group.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<SharingRules xmlns="http://soap.sforce.com/2006/04/metadata">
    <sharingCriteriaRules>
        <fullName>Share_Priority_High_With_Managers</fullName>
        <accessLevel>ReadWrite</accessLevel>
        <description>Share high-priority records with the Management group.</description>
        <label>Share High Priority Records with Managers</label>
        <booleanFilter>1</booleanFilter>         <!-- Optional: combine filters with AND/OR logic -->
        <criteriaItems>
            <field>ObjectName__c.Priority__c</field>
            <operation>equals</operation>        <!-- equals, notEqual, lessThan, greaterThan, lessOrEqual, greaterOrEqual, contains, notContain, startsWith, includes, excludes -->
            <value>High</value>
        </criteriaItems>
        <sharedTo>
            <group>Management</group>
        </sharedTo>
    </sharingCriteriaRules>
</SharingRules>
```

**Valid `accessLevel` values:** `Read`, `ReadWrite`
**Valid `operation` values for criteriaItems:** `equals`, `notEqual`, `lessThan`, `greaterThan`, `lessOrEqual`, `greaterOrEqual`, `contains`, `notContain`, `startsWith`, `includes` (picklist), `excludes` (picklist)

**Valid `sharedTo` targets:**
- `<group>GroupApiName</group>` — Public Group
- `<role>RoleName</role>` — Role
- `<roleAndSubordinates>RoleName</roleAndSubordinates>` — Role + all subordinate roles
- `<allInternalUsers/>` — All internal (non-portal) users

**GOTCHA:** Public Groups referenced in `<sharedTo>` or `<sharedFrom>` must already exist in the org before the sharing rule is deployed. If the group doesn't exist, the deploy will fail with a "Group not found" error.

---

## 7. Role Hierarchy (Concept)

Role hierarchy provides **implicit upward sharing**: users in higher roles automatically see records owned by users in lower roles (when OWD is Private or Read). This works without explicit sharing rules.

Role hierarchy is configured in Setup → Roles and **cannot be deployed as metadata** — it must be created manually in each org. Document the intended role structure in memory for manual setup guidance.

---

## 8. Public Groups

Public Groups are org-level collections of users, roles, or other groups used as sharing targets. They are created in Setup → Public Groups and **cannot be deployed as metadata**.

Key points:
- Groups must exist in the org **before** deploying sharing rules that reference them
- Group API names are case-sensitive in sharing rule XML
- Verify group existence before deploying: Setup → Public Groups → confirm the API name

---

## 9. CLI Introspection Queries

Use these to understand the existing permissions landscape before creating new configuration.

```bash
# 1. List all permission sets in the org
sf data query \
  --query "SELECT Id, Name, Label, Description FROM PermissionSet WHERE IsOwnedByProfile = false ORDER BY Name" \
  --target-org <alias>

# 2. Retrieve OWD (sharingModel) for a specific object — check the XML after retrieve
sf project retrieve start \
  --metadata "CustomObject:{ObjectName__c}" \
  --target-org <alias>
# Then read force-app/main/default/objects/{ObjectName__c}/{ObjectName__c}.object-meta.xml
# and look for the <sharingModel> element

# 3. Query permission set assignments for a specific user
sf data query \
  --query "SELECT PermissionSet.Name, PermissionSet.Label FROM PermSetAssignment WHERE AssigneeId = '{UserId}'" \
  --target-org <alias>

# 4. Retrieve all permission sets for local inspection
sf project retrieve start \
  --metadata "PermissionSet" \
  --target-org <alias>

# 5. Retrieve all sharing rules for a specific object
sf project retrieve start \
  --metadata "SharingRules:{ObjectName__c}" \
  --target-org <alias>
```

---

## 10. Org Permissions Memory Format

When writing or updating the `## Salesforce Org Permissions Layout` section in `~/.claude/projects/-home-your-username/memory/MEMORY.md`, use this exact structure:

```markdown
## Salesforce Org Permissions Layout

_Last updated: {YYYY-MM-DD} during {project/command name}_

### OWD (Organization-Wide Defaults)

| Object | Sharing Model | Notes |
|---|---|---|
| {ObjectName__c} | {Private/Read/ReadWrite/ControlledByParent} | {any relevant context} |

### Permission Sets

#### {PermSetName} — {label}
- **Intended users:** {description of who gets this}
- **Objects:** {ObjectName__c} — {access level}
- **Key fields editable:** {list of field API names or "all"}
- **Key fields read-only:** {list of field API names or "none"}
- **ViewAll/ModifyAll:** {yes/no per object}
- **Deployed:** {yes/no} | **Session:** {date/project}

### Sharing Rules

#### {ObjectName__c}
- `{RuleName}` — {owner-based/criteria-based} — shares with `{group}` — access: {Read/ReadWrite}
  - Criteria: {field = value, or "owner in {group}"}

### Role Hierarchy Notes
{Prose notes about intended role structure if discussed, or "Not configured / not discussed"}

### Public Groups
| Group Name | API Name | Members | Purpose |
|---|---|---|---|
| {label} | {api name} | {description} | {what it's used for} |
```

**Rules for updating this section:**
- Always append new rows/entries — never delete prior sessions' data
- If the section doesn't exist in MEMORY.md, add it at the end
- If a phase was skipped: record only the OWD of new objects (from Phase 1) and note "Only System Administrator configured in this session"
- Update the `_Last updated_` line each time

---

## Context Specification

- metadata_type: Profile, PermissionSet
- context_path: {alias}/permissions/
- inventory_file: {alias}/permissions/_permsets.md
- detail_file_pattern: _(inventory files only — detail is in local retrieved XML files)_

### Change Detection Query
Uses: standard API
```sql
SELECT Id, Name, Label, Description, LastModifiedDate, LastModifiedBy.Name
FROM PermissionSet
WHERE IsOwnedByProfile = false
AND LastModifiedDate > {LAST_SCAN}
ORDER BY LastModifiedDate DESC
LIMIT 50
```

Also run for Profiles:
```sql
SELECT Id, Name, LastModifiedDate, LastModifiedBy.Name
FROM Profile
WHERE LastModifiedDate > {LAST_SCAN}
ORDER BY LastModifiedDate DESC
LIMIT 25
```

### Inventory Columns (PermSets)
API Name | Label | Description | Last Modified Date | Last Modified By

### Inventory Columns (Profiles — written to `_profiles.md`)
Profile Name | Last Modified Date | Last Modified By

### Detail File Sections
_(No per-permset detail files — use `sf project retrieve start --metadata "PermissionSet:{Name}"` to get detail)_

---

## 11. Best Practices

| Practice | Rationale |
|---|---|
| **Minimal profiles** | Give profiles only the minimum they need. Use permission sets for everything additional. Profiles are hard to diff and maintain. |
| **Modular permission sets** | One permission set per feature/persona (e.g., "Read Work Orders", "Edit Work Orders") rather than one giant permission set per role. Combine with Permission Set Groups. |
| **Least privilege** | Start with Read-only; add Create/Edit/Delete only when there's a specific use case. Never grant ModifyAll as a convenience shortcut. |
| **Avoid `modifyAll` unless required** | ModifyAll bypasses all sharing rules. It is appropriate for admin support roles but dangerous on general-use permission sets. Document every ModifyAll grant with a reason. |
| **Deploy sharing rules last** | Sharing rules depend on objects existing in the org and public groups existing in Setup. Always deploy in order: Objects → Permission Sets → Sharing Rules. |
| **Retrieve before edit** | Always retrieve the current state of profiles, permission sets, and sharing rule files before editing. Never overwrite with a stale local copy. |
