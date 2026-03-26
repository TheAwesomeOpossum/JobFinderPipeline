---
name: sf-cpq
description: "Reference for Salesforce CPQ (Configure-Price-Quote) metadata — Product Rules, Price Rules, Quote Templates, Discount Schedules, Price Books, and SBQQ managed package objects. Includes API queries and configuration patterns."
---

# SF CPQ (Configure-Price-Quote) Skill

---

## 1. CPQ Architecture Overview

Salesforce CPQ (SBQQ) extends the standard Opportunity-Product model with a guided quoting experience. The core data model:

```
Product2 (standard)
    ├── PricebookEntry (standard, links Product to Pricebook)
    ├── SBQQ__ProductOption__c (bundle children)
    └── SBQQ__ProductRule__c (configuration / validation rules)

Opportunity (standard)
    └── SBQQ__Quote__c (CPQ Quote — primary or non-primary)
            ├── SBQQ__QuoteLine__c (line items, one per product)
            │       ├── SBQQ__PriceRule__c (pricing calculations)
            │       └── SBQQ__DiscountSchedule__c (volume pricing)
            ├── SBQQ__QuoteDocument__c (generated PDF)
            └── Order (standard, generated from quote)
                    └── OrderItem (standard, generated from quote lines)
```

**Key relationships:**
- An **Opportunity** can have multiple Quotes, but only one is marked **Primary** (`SBQQ__Primary__c = true`)
- **Quote Lines** mirror the Product + PricebookEntry model but add CPQ-specific pricing fields
- **Product Options** define bundle structures — a parent product contains child products
- **Product Rules** enforce configuration constraints (selection, validation, filter, alert)
- **Price Rules** dynamically set pricing fields based on conditions
- **Discount Schedules** apply volume/tiered pricing to products or quote lines
- **Quote Templates** generate PDF output documents

---

## 2. Core CPQ Managed Package Objects (SBQQ__)

All CPQ objects are prefixed with `SBQQ__` and require the Salesforce CPQ managed package.

### 2.1 SBQQ__Quote__c

The main transaction object — represents a quote/proposal.

**Query (Standard API):**
```sql
SELECT Id, Name, SBQQ__Opportunity2__c, SBQQ__Opportunity2__r.Name,
       SBQQ__Account__c, SBQQ__Account__r.Name,
       SBQQ__Primary__c, SBQQ__Status__c,
       SBQQ__StartDate__c, SBQQ__EndDate__c,
       SBQQ__SubscriptionTerm__c, SBQQ__Type__c,
       SBQQ__NetAmount__c, SBQQ__ListAmount__c,
       SBQQ__CustomerDiscount__c,
       SBQQ__PricebookId__c, SBQQ__Pricebook__r.Name,
       LastModifiedDate, LastModifiedBy.Name
FROM SBQQ__Quote__c
ORDER BY CreatedDate DESC
LIMIT 200
```

**Key fields:**
| Field | Type | Description |
|---|---|---|
| `SBQQ__Primary__c` | Boolean | When true, syncs totals back to Opportunity |
| `SBQQ__Status__c` | Picklist | Draft, Approved, Denied, etc. |
| `SBQQ__Type__c` | Picklist | Quote, Renewal, Amendment |
| `SBQQ__StartDate__c` | Date | Contract/subscription start |
| `SBQQ__SubscriptionTerm__c` | Number | Length of subscription in months |
| `SBQQ__NetAmount__c` | Currency | Final calculated price after discounts |

---

### 2.2 SBQQ__QuoteLine__c

Individual line items on a quote.

**Query (Standard API):**
```sql
SELECT Id, Name, SBQQ__Quote__c, SBQQ__Quote__r.Name,
       SBQQ__Product__c, SBQQ__Product__r.Name,
       SBQQ__Quantity__c, SBQQ__ListPrice__c,
       SBQQ__CustomerPrice__c, SBQQ__NetPrice__c,
       SBQQ__NetTotal__c, SBQQ__Discount__c,
       SBQQ__AdditionalDiscount__c, SBQQ__PartnerDiscount__c,
       SBQQ__SubscriptionPricing__c, SBQQ__SubscriptionTerm__c,
       SBQQ__Bundle__c, SBQQ__RequiredBy__c,
       SBQQ__ProductOption__c,
       LastModifiedDate
FROM SBQQ__QuoteLine__c
WHERE SBQQ__Quote__c = '{QuoteId}'
ORDER BY SBQQ__Number__c
```

**Pricing waterfall:**
```
List Price (from PricebookEntry)
  → Partner Discount (SBQQ__PartnerDiscount__c)
    → Customer/Volume Discount (SBQQ__Discount__c)
      → Additional Discount (SBQQ__AdditionalDiscount__c)
        → Net Price (SBQQ__NetPrice__c)
          × Quantity = Net Total (SBQQ__NetTotal__c)
```

---

### 2.3 SBQQ__ProductRule__c

Configuration and validation rules that control product selection and validation.

**Inventory query (Standard API):**
```sql
SELECT Id, Name, SBQQ__Active__c, SBQQ__Type__c,
       SBQQ__Scope__c, SBQQ__ConditionsMet__c,
       SBQQ__ErrorMessage__c, SBQQ__EvaluationEvent__c,
       SBQQ__ErrorCondition__c,
       LastModifiedDate, LastModifiedBy.Name
FROM SBQQ__ProductRule__c
ORDER BY Name
```

**Rule types:**
| Type | Purpose |
|---|---|
| **Validation** | Block save if conditions are met (shows error message) |
| **Selection** | Auto-add, remove, or enable/disable products |
| **Filter** | Restrict which products appear in search results |
| **Alert** | Show a warning message without blocking |

**Scope values:** Product, Quote

**Evaluation events:** Load, Edit, Save, Always

**Child objects:**
- `SBQQ__ErrorCondition__c` — Conditions that trigger the rule
- `SBQQ__ProductAction__c` — Actions executed when rule fires (for Selection rules)
- `SBQQ__LookupQuery__c` — Lookup queries used by actions

---

### 2.4 SBQQ__PriceRule__c

Pricing calculation rules that dynamically set values on quote or quote line fields.

**Inventory query (Standard API):**
```sql
SELECT Id, Name, SBQQ__Active__c, SBQQ__TargetObject__c,
       SBQQ__ConditionsMet__c, SBQQ__EvaluationEvent__c,
       SBQQ__EvaluationOrder__c,
       LastModifiedDate, LastModifiedBy.Name
FROM SBQQ__PriceRule__c
ORDER BY SBQQ__EvaluationOrder__c, Name
```

**Target objects:** Quote Line, Quote

**Child objects:**
- `SBQQ__PriceCondition__c` — When the rule applies
- `SBQQ__PriceAction__c` — What fields to set and to what values

**Price Condition query:**
```sql
SELECT Id, SBQQ__Rule__c, SBQQ__Rule__r.Name,
       SBQQ__Field__c, SBQQ__Operator__c, SBQQ__Value__c,
       SBQQ__FilterType__c, SBQQ__FilterVariable__c
FROM SBQQ__PriceCondition__c
ORDER BY SBQQ__Rule__r.Name
```

**Price Action query:**
```sql
SELECT Id, SBQQ__Rule__c, SBQQ__Rule__r.Name,
       SBQQ__TargetObject__c, SBQQ__Field__c,
       SBQQ__Value__c, SBQQ__Formula__c,
       SBQQ__ValueField__c, SBQQ__SourceVariable__c
FROM SBQQ__PriceAction__c
ORDER BY SBQQ__Rule__r.Name
```

---

### 2.5 SBQQ__QuoteTemplate__c

PDF output templates for generating quote documents.

**Inventory query (Standard API):**
```sql
SELECT Id, Name, SBQQ__Default__c,
       SBQQ__PageOrientation__c, SBQQ__PageSize__c,
       SBQQ__FontFamily__c, SBQQ__FontSize__c,
       SBQQ__TopMargin__c, SBQQ__BottomMargin__c,
       SBQQ__HeaderHeight__c, SBQQ__FooterHeight__c,
       LastModifiedDate, LastModifiedBy.Name
FROM SBQQ__QuoteTemplate__c
ORDER BY Name
```

**Child objects:**
- `SBQQ__TemplateSection__c` — Sections within the template
- `SBQQ__TemplateContent__c` — Content blocks (text, tables, images)
- `SBQQ__LineColumn__c` — Column definitions for line item tables

---

### 2.6 SBQQ__DiscountSchedule__c

Volume/tiered pricing definitions.

**Inventory query (Standard API):**
```sql
SELECT Id, Name, SBQQ__Type__c,
       SBQQ__DiscountUnit__c, SBQQ__AggregationScope__c,
       SBQQ__OverageDiscountUnit__c,
       SBQQ__Pricebook__c, SBQQ__Pricebook__r.Name,
       SBQQ__Product__c, SBQQ__Product__r.Name,
       LastModifiedDate, LastModifiedBy.Name
FROM SBQQ__DiscountSchedule__c
ORDER BY Name
```

**Type values:**
- **Range** — Each tier applies independently (first 10 at $100, next 10 at $90)
- **Slab** — Entire quantity priced at the tier it falls into

**Discount tiers query:**
```sql
SELECT Id, SBQQ__Schedule__c, SBQQ__Schedule__r.Name,
       SBQQ__LowerBound__c, SBQQ__UpperBound__c,
       SBQQ__Discount__c, SBQQ__Price__c
FROM SBQQ__DiscountTier__c
ORDER BY SBQQ__Schedule__r.Name, SBQQ__LowerBound__c
```

---

### 2.7 SBQQ__ProductOption__c

Defines products within a bundle.

**Query (Standard API):**
```sql
SELECT Id, Name, SBQQ__ConfiguredSKU__c, SBQQ__ConfiguredSKU__r.Name,
       SBQQ__OptionalSKU__c, SBQQ__OptionalSKU__r.Name,
       SBQQ__Type__c, SBQQ__Number__c,
       SBQQ__Quantity__c, SBQQ__Required__c,
       SBQQ__Selected__c, SBQQ__Bundled__c,
       SBQQ__DiscountedByPackage__c,
       LastModifiedDate
FROM SBQQ__ProductOption__c
ORDER BY SBQQ__ConfiguredSKU__r.Name, SBQQ__Number__c
```

**Option types:** Component, Accessory, Related Product

---

### 2.8 SBQQ__ConfigurationAttribute__c

Custom attributes displayed during bundle configuration.

**Query (Standard API):**
```sql
SELECT Id, Name, SBQQ__Product__c, SBQQ__Product__r.Name,
       SBQQ__TargetField__c, SBQQ__DisplayOrder__c,
       SBQQ__Required__c, SBQQ__DefaultValue__c,
       SBQQ__ColumnOrder__c, SBQQ__HiddenValues__c,
       SBQQ__ShownValues__c,
       LastModifiedDate
FROM SBQQ__ConfigurationAttribute__c
ORDER BY SBQQ__Product__r.Name, SBQQ__DisplayOrder__c
```

---

## 3. Standard Objects Used by CPQ

### 3.1 Product2

```sql
SELECT Id, Name, ProductCode, Family, Description,
       IsActive, SBQQ__SubscriptionPricing__c,
       SBQQ__SubscriptionTerm__c, SBQQ__SubscriptionType__c,
       SBQQ__BillingFrequency__c, SBQQ__BillingType__c,
       SBQQ__ChargeType__c, SBQQ__ConfigurationType__c,
       SBQQ__HasConfigurationAttributes__c,
       SBQQ__QuantityEditable__c,
       LastModifiedDate, LastModifiedBy.Name
FROM Product2
WHERE IsActive = true
ORDER BY Name
```

**CPQ-specific fields on Product2:**
| Field | Description |
|---|---|
| `SBQQ__SubscriptionPricing__c` | Fixed Price, Percent of Total, Cost Plus Markup |
| `SBQQ__SubscriptionType__c` | Renewable, One-time |
| `SBQQ__ChargeType__c` | One-Time, Recurring, Usage |
| `SBQQ__BillingFrequency__c` | Monthly, Quarterly, Semiannual, Annual |
| `SBQQ__ConfigurationType__c` | Required, Allowed (for bundles) |

### 3.2 Pricebook2 and PricebookEntry

```sql
SELECT Id, Name, IsActive, IsStandard,
       LastModifiedDate, LastModifiedBy.Name
FROM Pricebook2
WHERE IsActive = true
ORDER BY Name
```

```sql
SELECT Id, Pricebook2Id, Pricebook2.Name,
       Product2Id, Product2.Name,
       UnitPrice, IsActive, CurrencyIsoCode
FROM PricebookEntry
WHERE IsActive = true
ORDER BY Pricebook2.Name, Product2.Name
```

---

## 4. CPQ Custom Settings

### 4.1 General Settings

`SBQQ__GeneralSettings__c` — Hierarchy custom setting controlling overall CPQ behavior:

| Key Setting | Description |
|---|---|
| `SBQQ__QuoteCalculatorPlugin__c` | Apex class name for custom pricing logic |
| `SBQQ__QuoteLineEditorPlugin__c` | Apex class name for line editor customization |
| `SBQQ__DefaultQuoteValidityDays__c` | Auto-set expiration date days from creation |
| `SBQQ__RenewalModel__c` | Asset-based or contract-based renewals |

### 4.2 Line Editor Settings

`SBQQ__LineEditorSettings__c` — Controls the quote line editor UI:

| Key Setting | Description |
|---|---|
| `SBQQ__ColumnHeaders__c` | Visible columns in the line editor |
| `SBQQ__GroupFields__c` | Fields used for grouping line items |
| `SBQQ__PageSize__c` | Number of lines displayed per page |

### 4.3 Calculator Settings

`SBQQ__CalculatorSettings__c` — Controls calculation behavior:

| Key Setting | Description |
|---|---|
| `SBQQ__CalculateImmediately__c` | Calculate on every change vs. manual calculate |
| `SBQQ__TriggerCalculation__c` | Enable/disable trigger-based calculation |

---

## 5. CPQ Plugin Architecture

### 5.1 Quote Calculator Plugin (Apex)

Implement the `SBQQ.QuoteCalculatorPlugin` interface for custom pricing logic:

```apex
global class CustomQuoteCalculatorPlugin implements SBQQ.QuoteCalculatorPlugin {

    global Decimal getReservedQuantity(SObject quote, SObject line) {
        // Return reserved quantity for a line
        return 0;
    }

    global Boolean isSelfService(SObject quote) {
        // Return true for self-service context
        return false;
    }

    global void onInit(List<SObject> lines) {
        // Called when calculator initializes
    }

    global void onBeforeCalculate(SObject quote, List<SObject> lines) {
        // Called before pricing calculation
    }

    global void onAfterCalculate(SObject quote, List<SObject> lines) {
        // Called after pricing calculation — set custom fields here
    }

    global void onBeforePriceRules(SObject quote, List<SObject> lines) {
        // Called before price rules execute
    }

    global void onAfterPriceRules(SObject quote, List<SObject> lines) {
        // Called after price rules execute
    }
}
```

Register the plugin in **SBQQ > General Settings > Quote Calculator Plugin**.

### 5.2 JavaScript Quote Calculator Plugin (JQC)

For async/complex calculations, CPQ supports a JavaScript-based plugin using a Custom Script record:

```javascript
export function onInit(quoteLineModels) {
    return Promise.resolve();
}

export function onBeforeCalculate(quoteModel, quoteLineModels) {
    return Promise.resolve();
}

export function onBeforePriceRules(quoteModel, quoteLineModels) {
    return Promise.resolve();
}

export function onAfterPriceRules(quoteModel, quoteLineModels) {
    return Promise.resolve();
}

export function onAfterCalculate(quoteModel, quoteLineModels) {
    // Example: set a custom field based on quantity
    quoteLineModels.forEach(function(line) {
        if (line.record['SBQQ__Quantity__c'] > 100) {
            line.record['Custom_Flag__c'] = true;
        }
    });
    return Promise.resolve();
}

export function isFieldVisible(fieldName, line) {
    return true;
}

export function isFieldEditable(fieldName, line) {
    return true;
}
```

Store JQC code in **SBQQ__CustomScript__c** records.

---

## 6. CPQ Automation Considerations

### 6.1 Performance-Sensitive Areas

| Area | Risk | Recommendation |
|---|---|---|
| **Triggers on SBQQ__QuoteLine__c** | Quote calculation performs bulk DML on quote lines. Heavy triggers cause calculation timeouts. | Use Price Rules instead of triggers for pricing logic. If triggers are necessary, check for `SBQQ__Quote__r.SBQQ__CalculatingQuote__c` to skip during calculation. |
| **Triggers on SBQQ__Quote__c** | Less risky but still called during calculation save. | Keep lightweight. Avoid SOQL on quote lines in the trigger. |
| **Process Builder / Flows on CPQ objects** | Same performance concerns as triggers. | Use CPQ-native rules (Product Rules, Price Rules) instead of Flow for CPQ logic. |
| **Quote-to-Order generation** | Creates Order + OrderItems in bulk. Triggers on Order/OrderItem fire during this process. | Bulkify Order triggers. Test with large quotes (50+ lines). |

### 6.2 CPQ Calculation Context Detection

```apex
// In a trigger, detect if CPQ is currently calculating
Boolean isCalculating = false;
if (Trigger.new[0].getSObjectType() == SBQQ__QuoteLine__c.SObjectType) {
    Id quoteId = (Id)Trigger.new[0].get('SBQQ__Quote__c');
    SBQQ__Quote__c quote = [SELECT SBQQ__CalculatingQuote__c FROM SBQQ__Quote__c WHERE Id = :quoteId];
    isCalculating = quote.SBQQ__CalculatingQuote__c;
}
// Skip heavy logic if CPQ is calculating
if (isCalculating) return;
```

### 6.3 Amendment and Renewal Automation

**Amendments:** When a quote is created as an amendment to an existing contract:
- Type = `Amendment`
- `SBQQ__MasterContract__c` links to the original Contract
- Quote lines carry forward from the contracted quote

**Renewals:** When a renewal opportunity is generated:
- Type = `Renewal`
- `SBQQ__RenewalForecast__c` controls whether renewals auto-generate
- Renewal pricing can uplift from original pricing

---

## 7. CLI Commands for CPQ Metadata

```bash
# Check if CPQ managed package is installed
sf package installed list --target-org <alias>

# Query Product Rules
sf data query \
  --query "SELECT Id, Name, SBQQ__Type__c, SBQQ__Active__c FROM SBQQ__ProductRule__c ORDER BY Name" \
  --target-org <alias> --result-format table

# Query Price Rules
sf data query \
  --query "SELECT Id, Name, SBQQ__Active__c, SBQQ__TargetObject__c FROM SBQQ__PriceRule__c ORDER BY Name" \
  --target-org <alias> --result-format table

# Query Quote Templates
sf data query \
  --query "SELECT Id, Name, SBQQ__Default__c FROM SBQQ__QuoteTemplate__c ORDER BY Name" \
  --target-org <alias> --result-format table

# Query Discount Schedules
sf data query \
  --query "SELECT Id, Name, SBQQ__Type__c FROM SBQQ__DiscountSchedule__c ORDER BY Name" \
  --target-org <alias> --result-format table

# Retrieve custom fields added to CPQ objects
sf project retrieve start \
  --metadata "CustomField:SBQQ__Quote__c.*" \
  --target-org <alias>

# Retrieve Apex classes (for plugin implementations)
sf project retrieve start \
  --metadata "ApexClass:*QuoteCalculator*" \
  --target-org <alias>
```

---

## 8. Gotchas

| Issue | Detail |
|---|---|
| **Managed package dependency** | All SBQQ__ objects require the Salesforce CPQ managed package. Queries will fail with "sObject type not found" if not installed. |
| **Calculation order matters** | Price Rules execute in `SBQQ__EvaluationOrder__c` order. Misordered rules produce incorrect pricing. |
| **Quote line trigger performance** | The CPQ calculator performs bulk DML on quote lines. Triggers on SBQQ__QuoteLine__c are the #1 cause of calculation timeouts. |
| **Primary quote sync** | Only the Primary quote syncs amounts back to the Opportunity. Changing SBQQ__Primary__c triggers recalculation. |
| **Amendment complexity** | Amendment quotes carry forward existing lines. Adding/removing lines on amendments requires careful handling of quantity delta calculations. |
| **Multi-currency** | CPQ respects Salesforce multi-currency but adds complexity to Price Rules and Discount Schedules. Test pricing in all active currencies. |
| **Subscription vs. one-time** | Products can be one-time, recurring, or usage-based. The `SBQQ__ChargeType__c` field controls pricing calculation behavior. Mixing types on one quote is valid but complicates totals. |
| **Custom Script (JQC) debugging** | JavaScript Quote Calculator errors appear in the browser console, not Apex debug logs. Use `console.log()` for debugging. |
| **Contracted pricing** | Contracted prices override standard pricing. Check `SBQQ__ContractedPrice__c` on PricebookEntry if pricing seems wrong. |
| **Twin fields** | CPQ copies standard field values to "twin" custom fields during calculation (e.g., `UnitPrice` to `SBQQ__ListPrice__c`). Do not set twin fields directly. |

---

## Context Specification

- metadata_type: SBQQ__ProductRule__c, SBQQ__PriceRule__c, SBQQ__QuoteTemplate__c, SBQQ__DiscountSchedule__c
- context_path: {alias}/cpq/
- inventory_file: {alias}/cpq/_inventory.md
- detail_file_pattern: _(inventory only)_

### Full Inventory Queries

Uses: standard API

**Note:** These are data object queries (not Tooling API) because CPQ metadata is stored in managed package custom objects, not Salesforce metadata types.

**Product Rules:**
```sql
SELECT Id, Name, SBQQ__Active__c, SBQQ__Type__c,
       SBQQ__Scope__c, SBQQ__ConditionsMet__c,
       SBQQ__ErrorMessage__c, SBQQ__EvaluationEvent__c,
       LastModifiedDate, LastModifiedBy.Name
FROM SBQQ__ProductRule__c
ORDER BY SBQQ__Type__c, Name
```

**Price Rules:**
```sql
SELECT Id, Name, SBQQ__Active__c, SBQQ__TargetObject__c,
       SBQQ__ConditionsMet__c, SBQQ__EvaluationEvent__c,
       SBQQ__EvaluationOrder__c,
       LastModifiedDate, LastModifiedBy.Name
FROM SBQQ__PriceRule__c
ORDER BY SBQQ__EvaluationOrder__c, Name
```

**Quote Templates:**
```sql
SELECT Id, Name, SBQQ__Default__c,
       SBQQ__PageOrientation__c, SBQQ__PageSize__c,
       LastModifiedDate, LastModifiedBy.Name
FROM SBQQ__QuoteTemplate__c
ORDER BY Name
```

**Discount Schedules:**
```sql
SELECT Id, Name, SBQQ__Type__c,
       SBQQ__DiscountUnit__c,
       SBQQ__Product__c, SBQQ__Product__r.Name,
       LastModifiedDate, LastModifiedBy.Name
FROM SBQQ__DiscountSchedule__c
ORDER BY Name
```

### Change Detection Query

Uses: standard API
```sql
SELECT Id, Name, SBQQ__Type__c,
       LastModifiedDate, LastModifiedBy.Name
FROM SBQQ__ProductRule__c
WHERE LastModifiedDate > {LAST_SCAN}
ORDER BY LastModifiedDate DESC
LIMIT 50
```

```sql
SELECT Id, Name, SBQQ__TargetObject__c,
       LastModifiedDate, LastModifiedBy.Name
FROM SBQQ__PriceRule__c
WHERE LastModifiedDate > {LAST_SCAN}
ORDER BY LastModifiedDate DESC
LIMIT 50
```

```sql
SELECT Id, Name,
       LastModifiedDate, LastModifiedBy.Name
FROM SBQQ__QuoteTemplate__c
WHERE LastModifiedDate > {LAST_SCAN}
ORDER BY LastModifiedDate DESC
LIMIT 50
```

```sql
SELECT Id, Name, SBQQ__Type__c,
       LastModifiedDate, LastModifiedBy.Name
FROM SBQQ__DiscountSchedule__c
WHERE LastModifiedDate > {LAST_SCAN}
ORDER BY LastModifiedDate DESC
LIMIT 50
```

### Inventory Columns
Name | Type | Active | Target/Scope | Evaluation Order | Last Modified Date | Last Modified By

### Detail File Sections
_(No per-rule detail files — inventory groups product rules, price rules, quote templates, and discount schedules into a single inventory file.)_

### Naming Convention Detection
Analyze all ProductRule, PriceRule, QuoteTemplate, and DiscountSchedule names and extract:
- **Product Rule naming pattern:** e.g., `{Type}_{Product}_{Condition}`, descriptive labels
- **Price Rule naming pattern:** e.g., `PR_{Target}_{Action}`, numbered evaluation order
- **Template naming pattern:** e.g., customer-facing vs. internal, version-numbered
- **Discount Schedule naming pattern:** e.g., `{Product}_{TierType}`, volume descriptors
- Report findings in the `## Detected Naming Conventions` section at the top of `_inventory.md`
