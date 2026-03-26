---
name: sf-experience-cloud
description: "Reference for Salesforce Experience Cloud (Communities/Digital Experiences) metadata — Networks, Experience Bundles, Navigation Menus, Audiences, community pages, guest user configuration, and sharing considerations."
---

# SF Experience Cloud (Communities / Digital Experiences) Skill

---

## 1. Experience Cloud Architecture Overview

Experience Cloud provides externally-facing portals and sites built on the Salesforce platform. The architecture layers:

```
Network (Site container)
    ├── Experience Bundle (packaged site content)
    │       ├── Pages (home, detail, list, custom)
    │       ├── Theme / Branding (colors, logo, fonts)
    │       ├── Components (standard + custom LWC)
    │       └── Routes (URL-to-page mappings)
    ├── Navigation Menu (NavigationLinkSet + NavigationMenuItem)
    ├── Audiences (targeted content / personalization)
    ├── Guest User Profile (unauthenticated access)
    ├── Member Profiles / Permission Sets (authenticated access)
    └── Sharing Configuration (sharing sets, share groups, external OWD)
```

**Key concepts:**
- A **Network** is the top-level container for an Experience Cloud site
- Each Network has a **URL path prefix** (e.g., `/customers`, `/partners`)
- The site content is packaged as an **ExperienceBundle** in metadata
- **Two template frameworks exist:** Aura-based (Napili, Customer Service) and LWR (Lightning Web Runtime, Build Your Own)
- Guest users have a dedicated profile with its own object/field permissions
- Sharing for external users uses different mechanisms than internal sharing (sharing sets, share groups)

---

## 2. Core Objects and Metadata

### 2.1 Network (Site)

The Network object represents an Experience Cloud site.

**Inventory query (Standard API):**
```sql
SELECT Id, Name, UrlPathPrefix, Status,
       Description, FirstActivationDate,
       OptionsNicknameDisplayEnabled,
       OptionsPrivateMessagesEnabled,
       OptionsDirectMessagesEnabled,
       OptionsGuestChatterEnabled,
       OptionsInvitationsEnabled,
       OptionsSendWelcomeEmail,
       OptionsSelfRegistrationEnabled,
       LastModifiedDate, LastModifiedBy.Name
FROM Network
ORDER BY Name
```

**Key fields:**
| Field | Type | Description |
|---|---|---|
| `Name` | Text | Site display name |
| `UrlPathPrefix` | Text | URL path after domain (e.g., `customers`) |
| `Status` | Picklist | `Live`, `DownForMaintenance`, `UnderConstruction` |
| `FirstActivationDate` | DateTime | When the site was first published |
| `OptionsSelfRegistrationEnabled` | Boolean | Whether users can self-register |

**Network status values:**
- **Live** — Site is publicly accessible
- **DownForMaintenance** — Shows maintenance page
- **UnderConstruction** — Only accessible to admins

---

### 2.2 ExperienceBundle

The metadata representation of the entire site content, pages, and configuration.

**Tooling API query (limited — most detail is in the retrieved metadata):**
```sql
SELECT Id, DeveloperName, MasterLabel, Type,
       LastModifiedDate, LastModifiedBy.Name
FROM ExperienceBundle
WHERE NamespacePrefix = null
ORDER BY DeveloperName
```

**CLI Retrieve:**
```bash
# Retrieve a specific site's bundle
sf project retrieve start \
  --metadata "ExperienceBundle:{SiteDeveloperName}" \
  --target-org <alias>

# Retrieve all experience bundles
sf project retrieve start \
  --metadata "ExperienceBundle" \
  --target-org <alias>
```

**Retrieved directory structure:**
```
force-app/main/default/experiences/{SiteName}/
    ├── {SiteName}.site-meta.xml        ← Site-level config
    ├── config/                          ← Site settings (language, SEO, etc.)
    ├── routes/                          ← URL-to-page mappings
    ├── views/                           ← Page definitions
    │       ├── home.json
    │       ├── login.json
    │       ├── record-detail.json
    │       └── {custom-page}.json
    ├── themes/                          ← Visual theme configuration
    └── networks/                        ← Network configuration
```

**Important:** ExperienceBundle metadata can be very large (hundreds of files). Retrieve selectively when possible.

---

### 2.3 NavigationLinkSet and NavigationMenuItem

Navigation menus are defined by a **NavigationLinkSet** (the menu container) and **NavigationMenuItem** records (individual links).

**NavigationMenuItem query (Standard API):**
```sql
SELECT Id, Label, Type, Position, Target,
       DefaultListViewId, AccessRestriction,
       NavigationLinkSetId, NavigationLinkSet.DeveloperName,
       ParentId, Status,
       LastModifiedDate, LastModifiedBy.Name
FROM NavigationMenuItem
ORDER BY NavigationLinkSetId, Position
```

**NavigationLinkSet query (Standard API):**
```sql
SELECT Id, DeveloperName, MasterLabel,
       NetworkId, Network.Name,
       LastModifiedDate, LastModifiedBy.Name
FROM NavigationLinkSet
ORDER BY DeveloperName
```

**MenuItem types:**
| Type | Description |
|---|---|
| `SalesforceObject` | Links to a standard/custom object list view |
| `InternalLink` | Links to a page within the site |
| `ExternalLink` | Links to an external URL |
| `Event` | Fires a navigation event |
| `MenuLabel` | Parent menu item (dropdown container) |
| `SystemLink` | System-generated links (Home, etc.) |

**AccessRestriction values:**
- `None` — Visible to all users including guests
- `LoginRequired` — Only visible to authenticated users

---

### 2.4 Audience

Audiences define rules for targeted content and personalization.

**Metadata retrieval:**
```bash
# Retrieve all audiences
sf project retrieve start \
  --metadata "Audience" \
  --target-org <alias>

# Retrieve a specific audience
sf project retrieve start \
  --metadata "Audience:{AudienceName}" \
  --target-org <alias>
```

**Audience metadata XML structure:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Audience xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Partner_Tier_Gold</fullName>
    <description>Gold-tier partner users</description>
    <criteria>
        <criterion>
            <criterionValue>
                <value>Gold</value>
            </criterionValue>
            <operator>Equal</operator>
            <type>FieldBased</type>
        </criterion>
    </criteria>
    <targets>
        <target>{NetworkId}</target>
    </targets>
</Audience>
```

Audiences are used in Experience Builder to show/hide components or page variations based on user attributes.

---

## 3. Site Types and Templates

### 3.1 Aura-Based Templates (Classic)

| Template | Use Case | Key Features |
|---|---|---|
| **Customer Service (Napili)** | Self-service portal | Knowledge, Cases, Q&A, Topics |
| **Partner Central** | Partner portal | Leads, Opportunities, shared records |
| **Help Center** | Public knowledge base | Articles, search, categories |
| **Customer Account Portal** | Account management | Record access, data updates |
| **Aloha** | App launcher page | Single-page app links |

### 3.2 LWR Templates (Lightning Web Runtime)

| Template | Use Case | Key Features |
|---|---|---|
| **Build Your Own (LWR)** | Custom from scratch | Full control, modern CSS, better performance |
| **Microsite (LWR)** | Event/campaign pages | Lightweight, fast loading |
| **Help Center (LWR)** | Knowledge portal (modern) | Enhanced search, article layout |

**LWR vs. Aura differences:**
| Feature | Aura | LWR |
|---|---|---|
| Component framework | Aura components + LWC | LWC only |
| Styling | Limited CSS customization | Full CSS control, enhanced layouts |
| Performance | Heavier JS bundle | Lighter, faster rendering |
| SEO | Limited | Enhanced (SSR support) |
| URL format | Hash-based (`#/`) | Clean URLs |
| Customization | Theme-panel based | CSS variables, advanced theming |

---

## 4. Guest User Security

### 4.1 Guest User Profile

Each site has a dedicated guest user profile: `{SiteName} Profile`

**Query guest user and profile:**
```sql
SELECT Id, Name, ProfileId, Profile.Name, UserType
FROM User
WHERE UserType = 'Guest'
AND Name LIKE '%{SiteName}%'
```

**Guest user profile configuration:**
- Object permissions (CRUD) — typically Read-only on select objects
- Field-level security — restrict sensitive fields
- Apex class access — whitelist specific classes
- Visualforce page access — whitelist specific pages
- Tab settings — which tabs appear

### 4.2 Guest User Security Checklist

| Check | Detail |
|---|---|
| **Object access** | Only grant access to objects the public genuinely needs. Never grant Create/Edit/Delete on sensitive objects. |
| **Field-level security** | Hide PII fields (email, phone, SSN) from guest profile unless explicitly required. |
| **Record access** | Guest users see records shared via sharing rules specifically targeting the guest user or "All Users" group. |
| **Apex controller access** | Only expose `@AuraEnabled` methods that are safe for unauthenticated access. |
| **SOQL injection** | Guest-accessible Apex must use bind variables, never string concatenation for queries. |
| **API access** | Guest users cannot use Salesforce APIs. Verify no API-dependent components on guest pages. |
| **File access** | ContentDocument/ContentVersion sharing to guest users requires explicit configuration. |
| **Secure guest user sharing** | Enable "Secure guest user record access" in Sharing Settings (required since Spring '20). |

### 4.3 Common Security Audit Findings

1. **Overly permissive guest profile** — Guest user has CRUD on objects like Account, Contact, Lead
2. **Missing FLS** — Sensitive fields visible to guest users
3. **Unrestricted Apex** — `@AuraEnabled` methods accessible without proper access checks
4. **Open redirect** — Login/logout URLs not validated, allowing redirect attacks
5. **Self-registration abuse** — No CAPTCHA or rate limiting on self-registration

---

## 5. Custom Components in Experience Cloud

### 5.1 Exposing LWC to Experience Builder

A Lightning Web Component must declare community targets in its meta XML:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<LightningComponentBundle xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>60.0</apiVersion>
    <isExposed>true</isExposed>
    <masterLabel>My Community Component</masterLabel>
    <description>A component for Experience Cloud pages</description>
    <targets>
        <target>lightning__CommunityPage</target>
        <target>lightningCommunity__Page</target>
        <target>lightningCommunity__Default</target>
    </targets>
    <targetConfigs>
        <targetConfig targets="lightningCommunity__Default">
            <property name="title" type="String" label="Title" default="Welcome" />
            <property name="recordId" type="String" label="Record Id" />
        </targetConfig>
    </targetConfigs>
</LightningComponentBundle>
```

**Target values for Experience Cloud:**
| Target | Description |
|---|---|
| `lightning__CommunityPage` | Available on any community page |
| `lightningCommunity__Page` | Available on Aura-based community pages |
| `lightningCommunity__Default` | Default community page region |
| `lightningCommunity__Page_Layout` | Available as a page layout component (LWR) |

### 5.2 Accessing Community Context in LWC

```javascript
import { LightningElement, wire } from 'lwc';
import { CurrentPageReference } from 'lightning/navigation';
import communityId from '@salesforce/community/Id';
import communityBasePath from '@salesforce/community/basePath';
import isGuest from '@salesforce/user/isGuest';
import userId from '@salesforce/user/Id';

export default class MyCommunityComponent extends LightningElement {
    @wire(CurrentPageReference)
    pageRef;

    get isCommunityUser() {
        return communityId != null;
    }

    get isGuestUser() {
        return isGuest;
    }

    get siteBasePath() {
        return communityBasePath;
    }
}
```

### 5.3 Theme and Branding

**Aura sites:** Configure via Experience Builder > Theme panel
- Header/footer components
- Colors (primary, secondary, text)
- Logo and favicon
- Font family

**LWR sites:** Configure via CSS custom properties (design tokens):
```css
:root {
    --dxp-g-brand-primary: #0070d2;
    --dxp-g-brand-secondary: #2e844a;
    --dxp-g-body-font-family: 'Salesforce Sans', Arial, sans-serif;
    --dxp-g-body-font-size: 16px;
}
```

---

## 6. Experience Cloud and Sharing

### 6.1 Sharing Sets

Sharing sets grant record access to community users based on a relationship between the user's profile and the record. Configured in Setup, not deployable via metadata.

**How sharing sets work:**
- Map a user lookup field (e.g., `Contact.AccountId`) to a record lookup field (e.g., `Case.AccountId`)
- When matched, the community user gains access to those records
- Access level: Read Only or Read/Write

**Common sharing set patterns:**
| Object | User Field | Record Field | Access |
|---|---|---|---|
| Case | User.Contact.AccountId | Case.AccountId | Read/Write |
| Order | User.Contact.AccountId | Order.AccountId | Read Only |
| Custom__c | User.Contact.AccountId | Custom__c.Account__c | Read Only |

### 6.2 Share Groups

Share groups automatically include all community users of a specific type (Customer, Partner, etc.). Used in sharing rules.

**Types:**
- **All Customer Portal Users** — Every user with a Customer Community license
- **All Partner Users** — Every user with a Partner Community license
- **All Internal Users** — Every internal user
- **Roles and Subordinates** (Portal) — Includes portal role hierarchy

### 6.3 External Organization-Wide Defaults (OWD)

Experience Cloud uses a **separate external OWD** for objects accessed by community users:

**Query current OWD settings:**
```sql
SELECT SobjectType, DefaultExternalAccess, DefaultInternalAccess
FROM Organization
```

This query does not directly return external OWD. Check via Setup > Sharing Settings.

**Key rules:**
- External OWD can be **more restrictive** than internal OWD, never more permissive
- If internal OWD is Private, external OWD is automatically Private
- If internal OWD is Public Read Only, external OWD can be Private or Public Read Only
- External OWD applies to **all external users** (community, portal, guest)

### 6.4 Login-Based vs. Session-Based Sharing

| Type | Behavior |
|---|---|
| **Login-based (default)** | Sharing calculated at login, cached for the session. Changes to sharing rules take effect on next login. |
| **Session-based** | Sharing recalculated on each page load. More current but slower performance. |

---

## 7. CLI Commands for Experience Cloud

```bash
# List all Networks (sites)
sf data query \
  --query "SELECT Id, Name, UrlPathPrefix, Status FROM Network ORDER BY Name" \
  --target-org <alias> --result-format table

# Retrieve a specific Experience Bundle
sf project retrieve start \
  --metadata "ExperienceBundle:{SiteDeveloperName}" \
  --target-org <alias>

# Retrieve all Experience Bundles
sf project retrieve start \
  --metadata "ExperienceBundle" \
  --target-org <alias>

# Retrieve Network metadata
sf project retrieve start \
  --metadata "Network:{SiteName}" \
  --target-org <alias>

# Retrieve Navigation Menus
sf project retrieve start \
  --metadata "NavigationMenu" \
  --target-org <alias>

# Retrieve Audiences
sf project retrieve start \
  --metadata "Audience" \
  --target-org <alias>

# Deploy an Experience Bundle
sf project deploy start \
  --metadata "ExperienceBundle:{SiteDeveloperName}" \
  --target-org <alias> --wait 10

# Deploy Network changes
sf project deploy start \
  --metadata "Network:{SiteName}" \
  --target-org <alias> --wait 10

# Query guest user profile assignment
sf data query \
  --query "SELECT Id, Name, Profile.Name FROM User WHERE UserType = 'Guest'" \
  --target-org <alias> --result-format table

# Query navigation items for a site
sf data query \
  --query "SELECT Label, Type, Position, Target FROM NavigationMenuItem ORDER BY NavigationLinkSetId, Position" \
  --target-org <alias> --result-format table
```

---

## 8. Gotchas

| Issue | Detail |
|---|---|
| **Must publish after deploy** | Deploying an ExperienceBundle does NOT make changes live. You must publish via Setup UI (Workspaces > Administration > Settings > Publish) or via the `Network` Tooling API. |
| **Guest user security audits** | Salesforce security reviews frequently flag overly permissive guest user profiles. Always apply least-privilege principle. |
| **ExperienceBundle size** | Retrieved bundles can contain hundreds of JSON files. Use selective retrieval and avoid retrieving all bundles at once in large orgs. |
| **Navigation changes need re-publish** | Adding or reordering NavigationMenuItem records requires a site re-publish for changes to appear. |
| **LWR vs. Aura incompatibility** | Components built for Aura communities may not work in LWR sites and vice versa. Check `targets` in component meta XML. |
| **Self-registration configuration** | Self-registration requires: Account for new users, Profile assignment, Apex registration handler, and must be enabled on the Network record. |
| **Multi-language** | Each site can have multiple languages. Translations are managed separately and must be deployed alongside the ExperienceBundle. |
| **SEO metadata** | LWR sites support page-level meta tags and SEO settings. Aura sites have limited SEO capabilities. Sitemap generation is available for LWR sites. |
| **Login page customization** | Custom login pages must be assigned in Workspaces > Administration > Login & Registration. Deploying the page component alone is not enough. |
| **CDN caching** | Experience Cloud uses a CDN for static assets. Changes to CSS/images may not appear immediately due to cache. Clear CDN cache via Setup if needed. |
| **Sharing set limitations** | Sharing sets only support direct lookup relationships, not formula fields or cross-object lookups. For complex sharing, use Apex managed sharing. |
| **Mixed authentication** | Sites can have both guest (unauthenticated) and logged-in pages. Ensure navigation and page permissions are correctly configured for both contexts. |

---

## Context Specification

- metadata_type: Network, ExperienceBundle, NavigationMenuItem
- context_path: {alias}/experience-cloud/
- inventory_file: {alias}/experience-cloud/_inventory.md
- detail_file_pattern: {alias}/experience-cloud/{SiteDeveloperName}.md

### Full Inventory Queries

**Networks (Standard API):**
```sql
SELECT Id, Name, UrlPathPrefix, Status,
       Description, FirstActivationDate,
       OptionsSelfRegistrationEnabled,
       LastModifiedDate, LastModifiedBy.Name
FROM Network
ORDER BY Name
```

**Experience Bundles (Tooling API):**
```sql
SELECT Id, DeveloperName, MasterLabel, Type,
       LastModifiedDate, LastModifiedBy.Name
FROM ExperienceBundle
WHERE NamespacePrefix = null
ORDER BY DeveloperName
```

**Navigation Link Sets (Standard API):**
```sql
SELECT Id, DeveloperName, MasterLabel,
       NetworkId, Network.Name,
       LastModifiedDate, LastModifiedBy.Name
FROM NavigationLinkSet
ORDER BY DeveloperName
```

**Navigation Menu Items (Standard API):**
```sql
SELECT Id, Label, Type, Position, Target,
       AccessRestriction, Status,
       NavigationLinkSetId, NavigationLinkSet.DeveloperName,
       LastModifiedDate, LastModifiedBy.Name
FROM NavigationMenuItem
ORDER BY NavigationLinkSetId, Position
```

### Change Detection Query

Uses: standard API
```sql
SELECT Id, Name, UrlPathPrefix, Status,
       LastModifiedDate, LastModifiedBy.Name
FROM Network
WHERE LastModifiedDate > {LAST_SCAN}
ORDER BY LastModifiedDate DESC
LIMIT 50
```

Uses: tooling API
```sql
SELECT Id, DeveloperName, MasterLabel,
       LastModifiedDate, LastModifiedBy.Name
FROM ExperienceBundle
WHERE NamespacePrefix = null
AND LastModifiedDate > {LAST_SCAN}
ORDER BY LastModifiedDate DESC
LIMIT 50
```

Uses: standard API (SetupAuditTrail for community/site changes)
```sql
SELECT Action, Display, Section, CreatedDate, CreatedBy.Name
FROM SetupAuditTrail
WHERE (Section = 'Networks' OR Section LIKE '%Community%' OR Section LIKE '%Experience%')
AND CreatedDate > {LAST_SCAN}
ORDER BY CreatedDate DESC
LIMIT 50
```

### Inventory Columns
Site Name | URL Prefix | Status | Template Type | Self-Registration | Last Modified Date | Last Modified By

### Detail File Sections
Identity (Name, URL, Status), Template Type, Navigation Menu Structure, Guest User Profile, Sharing Configuration, Custom Components Deployed, Last Scanned

### Naming Convention Detection
Analyze all Network names, ExperienceBundle developer names, and NavigationMenuItem labels and extract:
- **Site naming pattern:** e.g., `{Audience}_{Purpose}`, branded names, internal codenames
- **Navigation label pattern:** e.g., sentence case, title case, abbreviated
- **URL prefix pattern:** e.g., lowercase-hyphenated, abbreviated, audience-based
- Report findings in the `## Detected Naming Conventions` section at the top of `_inventory.md`
