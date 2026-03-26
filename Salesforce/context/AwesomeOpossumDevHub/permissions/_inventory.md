# Permissions Inventory — AwesomeOpossumDevHub

_Last scanned: 2026-03-26T17:37:00Z_
_Source: sf-init-project_
_Skill: sf-permissions_

## Detected Naming Conventions

- **Custom permission sets:** `{Feature}_{Role}` or descriptive PascalCase (e.g., `Experience_Profile_Manager`, `Althropic_Claude`)
- **System permission sets:** Salesforce-generated `SubscriptionManagement*` sets (11 total — not org-built)

## Permission Sets (org-built)

| API Name | Label | Notes |
|---|---|---|
| Althropic_Claude | Althropic Claude | Likely grants access to Anthropic/Claude AI features (note: typo in name) |
| Experience_Profile_Manager | Experience Profile Manager | Manages Experience object profiles |
| Live_Agent_Setup_Flow | Chat Setup Flow | Live Agent setup access |

## Permission Sets (system/standard)

| API Name | Label |
|---|---|
| SubscriptionManagementBillingAdmin | SubscriptionManagementBillingAdmin |
| SubscriptionManagementBillingOperations | SubscriptionManagementBillingOperations |
| SubscriptionManagementBuyerIntegrationUser | SubscriptionManagementBuyerIntegrationUser |
| SubscriptionManagementCollections | SubscriptionManagementCollections |
| SubscriptionManagementCreditMemoAdjustmentsOperations | SubscriptionManagementCreditMemoAdjustmentsOperations |
| SubscriptionManagementPaymentAdministrator | SubscriptionManagementPaymentAdministrator |
| SubscriptionManagementPaymentOperations | SubscriptionManagementPaymentOperations |
| SubscriptionManagementProductAndPricingAdmin | SubscriptionManagementProductAndPricingAdmin |
| SubscriptionManagementSalesOperationsRep | SubscriptionManagementSalesOperationsRep |
| SubscriptionManagementSalesRep | SubscriptionManagementSalesRep |
| SubscriptionManagementTaxAdmin | SubscriptionManagementTaxAdmin |

## Profiles (47 total — key profiles)

| Profile Name | Notes |
|---|---|
| System Administrator | Standard admin |
| Standard User | Standard |
| Standard Platform User | Standard |
| LWR Portfolio Profile | Custom — LWR Experience site |
| William Roach-Barrette Portfolio Profile | Custom — Portfolio site |
| Awesome Opossum Guest Profile | Custom — Guest access |
| HelloWorld Profile | Custom |
| Custom: Sales Profile | Custom standard |
| Custom: Marketing Profile | Custom standard |
| Custom: Support Profile | Custom standard |
| _(+ 37 standard/community profiles)_ | |

## Permission Set Groups

_(None found)_
