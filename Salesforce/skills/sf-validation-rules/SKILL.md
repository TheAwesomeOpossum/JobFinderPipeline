---
name: sf-validation-rules
description: "Reference for Salesforce ValidationRule metadata XML, CLI deploy/retrieve commands, formula functions, common patterns by field type, and deploy gotchas."
---

# SF Validation Rules Skill

---

## 1. File Path + XML Skeleton

**Canonical path:**
```
force-app/main/default/objects/{Obj__c}/validationRules/{RuleName}.validationRule-meta.xml
```

**Full XML skeleton (all 6 required elements):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<ValidationRule xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>RuleName</fullName>
    <active>true</active>
    <description>One-sentence description of what this rule enforces.</description>
    <errorConditionFormula>
        /* Formula evaluates TRUE when the save is BLOCKED (inverted logic) */
        ISBLANK(Field__c)
    </errorConditionFormula>
    <errorMessage>Human-readable error message shown to the user.</errorMessage>
    <errorDisplayField>Field__c</errorDisplayField>
</ValidationRule>
```

**Key rule:** The formula must return `TRUE` when the save **should be blocked**. This is inverted from what most developers expect — think "when should this fail?" not "when is this valid?"

- `<fullName>` must exactly match the filename (no spaces, no `.validationRule-meta.xml`)
- `<errorDisplayField>` is optional — if omitted, error appears at the top of the page
- `<active>true</active>` — set to `false` to deploy but leave inactive

---

## 2. CLI Commands

```bash
# Deploy a single validation rule
sf project deploy start \
  --metadata "ValidationRule:{ObjectName__c}.{RuleName}" \
  --target-org <alias> --wait 10

# Deploy all validation rules for an object
sf project deploy start \
  --metadata "ValidationRule:{ObjectName__c}" \
  --target-org <alias> --wait 10

# Retrieve all validation rules for an object
sf project retrieve start \
  --metadata "ValidationRule:{ObjectName__c}" \
  --target-org <alias>

# Retrieve a single validation rule
sf project retrieve start \
  --metadata "ValidationRule:{ObjectName__c}.{RuleName}" \
  --target-org <alias>

# List all validation rules on an object (SOQL)
sf data query \
  --query "SELECT Id, ValidationName, Active, Description FROM ValidationRule WHERE EntityDefinition.QualifiedApiName = '{ObjectName__c}'" \
  --target-org <alias>
```

---

## 3. Formula Function Reference

| Function | Syntax | Use Case |
|---|---|---|
| `ISPICKVAL` | `ISPICKVAL(Field__c, "Value")` | Test picklist value equality |
| `ISBLANK` | `ISBLANK(Field__c)` | True if text/lookup is blank (preferred over ISNULL for text) |
| `ISNULL` | `ISNULL(Field__c)` | True if number/date/currency is null |
| `ISCHANGED` | `ISCHANGED(Field__c)` | True if field value changed on this save (always false on insert) |
| `ISNEW` | `ISNEW()` | True if this is a new record insert |
| `PRIORVALUE` | `PRIORVALUE(Field__c)` | Value of field before this save (use with ISCHANGED) |
| `AND` | `AND(expr1, expr2, ...)` | All conditions must be true |
| `OR` | `OR(expr1, expr2, ...)` | Any condition must be true |
| `NOT` | `NOT(expr)` | Inverts a boolean expression |
| `TEXT` | `TEXT(Field__c)` | Convert picklist/number to text for comparison |
| `LEN` | `LEN(Field__c)` | Length of a text string |
| `TODAY` | `TODAY()` | Current date (Date type) |
| `NOW` | `NOW()` | Current datetime (DateTime type) |

---

## 4. Common Patterns by Scenario

### Pattern 1: Conditional Required Field
Block save when a picklist is a certain value but a dependent field is blank.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ValidationRule xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Require_Resolution_Notes_When_Closed</fullName>
    <active>true</active>
    <description>Resolution Notes is required when Status is Closed.</description>
    <errorConditionFormula>
        AND(
            ISPICKVAL(Status__c, "Closed"),
            ISBLANK(Resolution_Notes__c)
        )
    </errorConditionFormula>
    <errorMessage>Resolution Notes is required when Status is Closed.</errorMessage>
    <errorDisplayField>Resolution_Notes__c</errorDisplayField>
</ValidationRule>
```

---

### Pattern 2: Date Range (End Must Be After Start)
```xml
<?xml version="1.0" encoding="UTF-8"?>
<ValidationRule xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>End_Date_After_Start_Date</fullName>
    <active>true</active>
    <description>End Date must be on or after Start Date.</description>
    <errorConditionFormula>
        AND(
            NOT(ISNULL(Start_Date__c)),
            NOT(ISNULL(End_Date__c)),
            End_Date__c < Start_Date__c
        )
    </errorConditionFormula>
    <errorMessage>End Date must be on or after Start Date.</errorMessage>
    <errorDisplayField>End_Date__c</errorDisplayField>
</ValidationRule>
```

---

### Pattern 3: Future Date Enforcement
```xml
<?xml version="1.0" encoding="UTF-8"?>
<ValidationRule xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Scheduled_Date_Must_Be_Future</fullName>
    <active>true</active>
    <description>Scheduled Date must be today or in the future.</description>
    <errorConditionFormula>
        AND(
            NOT(ISNULL(Scheduled_Date__c)),
            Scheduled_Date__c &lt; TODAY()
        )
    </errorConditionFormula>
    <errorMessage>Scheduled Date must be today or a future date.</errorMessage>
    <errorDisplayField>Scheduled_Date__c</errorDisplayField>
</ValidationRule>
```

---

### Pattern 4: Picklist Dependency
Block a child picklist value unless a parent picklist has the right value.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ValidationRule xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Sub_Type_Requires_Correct_Type</fullName>
    <active>true</active>
    <description>Sub Type "Electrical" is only valid when Type is "HVAC".</description>
    <errorConditionFormula>
        AND(
            ISPICKVAL(Sub_Type__c, "Electrical"),
            NOT(ISPICKVAL(Type__c, "HVAC"))
        )
    </errorConditionFormula>
    <errorMessage>Sub Type "Electrical" is only valid when Type is "HVAC".</errorMessage>
    <errorDisplayField>Sub_Type__c</errorDisplayField>
</ValidationRule>
```

---

### Pattern 5: Status Transition Lock (PRIORVALUE + ISCHANGED)
Prevent moving backward in a workflow (e.g., can't reopen a Closed record).

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ValidationRule xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Cannot_Reopen_Closed_Record</fullName>
    <active>true</active>
    <description>Status cannot be changed away from Closed once set.</description>
    <errorConditionFormula>
        AND(
            NOT(ISNEW()),
            ISCHANGED(Status__c),
            ISPICKVAL(PRIORVALUE(Status__c), "Closed"),
            NOT(ISPICKVAL(Status__c, "Closed"))
        )
    </errorConditionFormula>
    <errorMessage>This record is Closed and cannot be reopened.</errorMessage>
    <errorDisplayField>Status__c</errorDisplayField>
</ValidationRule>
```

---

### Pattern 6: Numeric Range
```xml
<?xml version="1.0" encoding="UTF-8"?>
<ValidationRule xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Quantity_Must_Be_Positive</fullName>
    <active>true</active>
    <description>Quantity must be greater than zero.</description>
    <errorConditionFormula>
        AND(
            NOT(ISNULL(Quantity__c)),
            Quantity__c &lt;= 0
        )
    </errorConditionFormula>
    <errorMessage>Quantity must be greater than 0.</errorMessage>
    <errorDisplayField>Quantity__c</errorDisplayField>
</ValidationRule>
```

---

### Pattern 7: Immutable Field After Creation
Prevent editing a field after the record has been saved once (e.g., a locked reference number).

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ValidationRule xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Reference_Number_Immutable</fullName>
    <active>true</active>
    <description>Reference Number cannot be changed after the record is created.</description>
    <errorConditionFormula>
        AND(
            NOT(ISNEW()),
            ISCHANGED(Reference_Number__c)
        )
    </errorConditionFormula>
    <errorMessage>Reference Number cannot be changed after the record is created.</errorMessage>
    <errorDisplayField>Reference_Number__c</errorDisplayField>
</ValidationRule>
```

---

### Pattern 8: Cross-Object Validation (Dot Notation on Lookup)
Validate against a field on a parent record via a lookup relationship.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ValidationRule xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Cannot_Create_If_Parent_Inactive</fullName>
    <active>true</active>
    <description>Cannot create a child record if the parent Account is inactive.</description>
    <errorConditionFormula>
        AND(
            NOT(ISBLANK(Account__c)),
            NOT(Account__r.IsActive)
        )
    </errorConditionFormula>
    <errorMessage>Cannot associate with an inactive Account.</errorMessage>
    <errorDisplayField>Account__c</errorDisplayField>
</ValidationRule>
```

**Cross-object syntax:** `LookupFieldName__r.TargetField__c`
- Use the relationship name (the `__r` form), not the lookup field's `__c` form
- Standard lookups use the relationship name configured in the field metadata

---

## 5. Gotchas

| Issue | Detail |
|---|---|
| **100-rule limit** | Each object can have at most 100 active validation rules. Plan accordingly for complex objects. |
| **Compound fields unsupported** | Cannot use compound fields (e.g., `BillingAddress`) directly in formulas; reference sub-fields (`BillingCity`, `BillingState`) instead. |
| **ISCHANGED always false on insert** | `ISCHANGED()` returns false for new records. Always wrap with `NOT(ISNEW())` when using ISCHANGED to avoid unexpected behavior. |
| **Formula character limit** | Error condition formula max is 3,900 characters (Salesforce limit). Break complex logic into helper formula fields if needed. |
| **Workflows/Flows can bypass rules** | Validation rules are bypassed by system context (e.g., `System.runAs()` in Apex with `AllowFieldTruncation`, or `Database.insert()` with `allOrNone=false` in some contexts). Flows set to "Run in System Mode without Sharing" bypass validation rules. |
| **XML special characters** | In formulas, use `&lt;` for `<` and `&gt;` for `>` — raw angle brackets break XML parsing. |
| **fullName must match filename** | `<fullName>My_Rule</fullName>` → filename must be `My_Rule.validationRule-meta.xml`. No spaces allowed in fullName. |

---

## Context Specification

- metadata_type: ValidationRule
- context_path: {alias}/validation-rules/
- inventory_file: {alias}/validation-rules/_inventory.md
- detail_file_pattern: _(inventory only)_

### Full Inventory Query
Uses: tooling API
```sql
SELECT ValidationName, EntityDefinition.QualifiedApiName, Active, Description,
       ErrorMessage, LastModifiedDate, LastModifiedBy.Name
FROM ValidationRule
WHERE EntityDefinition.NamespacePrefix = null
ORDER BY EntityDefinition.QualifiedApiName, ValidationName
```

### Change Detection Query
Uses: tooling API
```sql
SELECT ValidationName, EntityDefinition.QualifiedApiName, Active, Description,
       LastModifiedDate, LastModifiedBy.Name
FROM ValidationRule
WHERE LastModifiedDate > {LAST_SCAN}
AND EntityDefinition.NamespacePrefix = null
ORDER BY LastModifiedDate DESC
LIMIT 50
```

### Inventory Columns
Object | Rule Name | Active | Description | Last Modified Date | Last Modified By

### Detail File Sections
_(No per-rule detail files — inventory is grouped by object. Retrieve full rule XML with `sf project retrieve start --metadata "ValidationRule:{ObjectName__c}"`)_

### Naming Convention Detection
Analyze all ValidationRule names and extract:
- **Prefix patterns:** e.g., `VR_`, `Require_`, `Prevent_`, `Enforce_`
- **Naming structure:** `{Verb}_{Object}_{Field}` vs `{Object}_{Condition}` vs plain descriptive
- **Description conventions:** sentence style, included field references
- Report findings in the `## Detected Naming Conventions` section at the top of `_inventory.md`
