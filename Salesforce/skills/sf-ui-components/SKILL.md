---
name: sf-ui-components
description: "Reference for Salesforce UI component metadata — Lightning Web Components (LWC), Aura Components, Visualforce Pages/Components, Custom Tabs, Quick Actions, and Lightning Applications. Includes Tooling API queries, file structures, and development patterns."
---

# Salesforce UI Components Skill

This skill provides comprehensive reference for all Salesforce UI component metadata types,
including file structures, Tooling API queries, development patterns, and deployment commands.

---

## 1. Lightning Web Components (LWC)

Lightning Web Components is the primary modern UI framework for Salesforce development.
LWC uses standard web technologies (HTML, JavaScript, CSS) with a thin layer of
Salesforce-specific services.

### File Structure

Each LWC lives in its own folder under `force-app/main/default/lwc/`:

```
force-app/main/default/lwc/{componentName}/
  {componentName}.html          ← Template markup
  {componentName}.js            ← JavaScript controller
  {componentName}.css           ← Component styles (optional)
  {componentName}.js-meta.xml   ← Metadata configuration (required)
  __tests__/                    ← Jest unit tests (optional)
    {componentName}.test.js
```

### Meta XML Structure

The `.js-meta.xml` file controls where and how the component can be used:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<LightningComponentBundle xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>62.0</apiVersion>
    <isExposed>true</isExposed>
    <masterLabel>My Component Label</masterLabel>
    <description>Description shown in Lightning App Builder</description>
    <targets>
        <target>lightning__RecordPage</target>
        <target>lightning__AppPage</target>
        <target>lightning__HomePage</target>
        <target>lightning__FlowScreen</target>
        <target>lightning__Tab</target>
        <target>lightning__UtilityBar</target>
        <target>lightningCommunity__Page</target>
        <target>lightningCommunity__Default</target>
    </targets>
    <targetConfigs>
        <targetConfig targets="lightning__RecordPage">
            <objects>
                <object>Account</object>
                <object>Custom_Object__c</object>
            </objects>
            <property name="title" type="String" label="Card Title"
                      default="Default Title" description="Title displayed on the card" />
            <property name="recordsPerPage" type="Integer" label="Records Per Page"
                      default="10" />
            <property name="showHeader" type="Boolean" label="Show Header"
                      default="true" />
        </targetConfig>
        <targetConfig targets="lightning__FlowScreen">
            <property name="inputValue" type="String" label="Input Value"
                      role="inputOnly" />
            <property name="outputValue" type="String" label="Output Value"
                      role="outputOnly" />
        </targetConfig>
    </targetConfigs>
</LightningComponentBundle>
```

### Available Targets

| Target | Description |
|---|---|
| `lightning__RecordPage` | Record detail pages in Lightning Experience |
| `lightning__AppPage` | App pages (custom Lightning pages) |
| `lightning__HomePage` | Home page in Lightning Experience |
| `lightning__FlowScreen` | Screen flows |
| `lightning__Tab` | Custom tab (standalone page) |
| `lightning__UtilityBar` | Utility bar items |
| `lightning__Inbox` | Outlook/Gmail integration |
| `lightningCommunity__Page` | Experience Cloud pages |
| `lightningCommunity__Default` | Experience Cloud with default properties |
| `lightningSnapin__ChatMessage` | Embedded Service chat |
| `lightningSnapin__Minimized` | Embedded Service minimized |
| `lightningSnapin__PreChat` | Embedded Service pre-chat |
| `lightningSnapin__ChatHeader` | Embedded Service chat header |

### Tooling API Query

```sql
SELECT Id, DeveloperName, MasterLabel, ApiVersion,
       LastModifiedDate, LastModifiedBy.Name
FROM LightningComponentBundle
WHERE NamespacePrefix = null
ORDER BY DeveloperName
```

**API:** Tooling API (not standard REST/SOAP)

### Component Lifecycle Hooks

LWC components have defined lifecycle hooks that fire at specific points:

```javascript
import { LightningElement, api, wire, track } from 'lwc';

export default class MyComponent extends LightningElement {

    // --- Reactive Properties ---
    @api recordId;            // Public property, set by parent or record page
    @api objectApiName;       // Public property, set by record page
    @track items = [];        // Tracked for reactivity (arrays/objects)
    label = 'default';        // Reactive primitive (no decorator needed)

    // --- Lifecycle Hooks ---

    constructor() {
        super();
        // Fires first. Cannot access DOM or public properties yet.
        // Use for initializing non-reactive state only.
    }

    connectedCallback() {
        // Fires when component is inserted into DOM.
        // Public properties (@api) are available here.
        // Use for initialization logic, event listeners, imperative data fetching.
        // Can fire more than once if component is removed and re-inserted.
    }

    renderedCallback() {
        // Fires after every render cycle.
        // Use for DOM manipulation (this.template.querySelector).
        // CAUTION: Runs frequently — guard against infinite loops.
        // Always use a flag to prevent repeated execution.
    }

    disconnectedCallback() {
        // Fires when component is removed from DOM.
        // Use for cleanup: remove event listeners, cancel subscriptions.
    }

    errorCallback(error, stack) {
        // Fires when a descendant component throws an error.
        // Use for error boundaries / fallback UI.
    }
}
```

### Wire Service

The `@wire` decorator connects components to Salesforce data and metadata reactively:

```javascript
import { LightningElement, wire, api } from 'lwc';
import { getRecord, getFieldValue } from 'lightning/uiRecordApi';
import { getObjectInfo } from 'lightning/uiObjectInfoApi';
import ACCOUNT_NAME from '@salesforce/schema/Account.Name';
import ACCOUNT_INDUSTRY from '@salesforce/schema/Account.Industry';

export default class WireExample extends LightningElement {
    @api recordId;

    // Wire to a record
    @wire(getRecord, { recordId: '$recordId', fields: [ACCOUNT_NAME, ACCOUNT_INDUSTRY] })
    account;

    // Access wired data
    get accountName() {
        return getFieldValue(this.account.data, ACCOUNT_NAME);
    }

    // Wire to a function for more control
    @wire(getRecord, { recordId: '$recordId', fields: [ACCOUNT_NAME] })
    wiredAccount({ error, data }) {
        if (data) {
            this.processData(data);
        } else if (error) {
            this.handleError(error);
        }
    }

    // Wire to object metadata
    @wire(getObjectInfo, { objectApiName: 'Account' })
    objectInfo;
}
```

### Imperative Apex Calls

For non-reactive or on-demand data fetching, use imperative Apex:

```javascript
import { LightningElement, api } from 'lwc';
import getRelatedRecords from '@salesforce/apex/MyController.getRelatedRecords';
import saveRecords from '@salesforce/apex/MyController.saveRecords';

export default class ImperativeExample extends LightningElement {
    @api recordId;
    records = [];
    error;
    isLoading = false;

    connectedCallback() {
        this.loadRecords();
    }

    async loadRecords() {
        this.isLoading = true;
        try {
            this.records = await getRelatedRecords({ parentId: this.recordId });
            this.error = undefined;
        } catch (error) {
            this.error = error;
            this.records = [];
        } finally {
            this.isLoading = false;
        }
    }

    async handleSave() {
        try {
            await saveRecords({ records: this.records });
            // Show success toast
        } catch (error) {
            // Handle error
        }
    }
}
```

### Event Communication Patterns

LWC supports several communication patterns depending on component relationships:

**Child-to-Parent: Custom Events**

```javascript
// Child component dispatches event
this.dispatchEvent(new CustomEvent('select', {
    detail: { recordId: this.item.Id },
    bubbles: false,    // default: false (only parent receives)
    composed: false    // default: false (does not cross shadow DOM)
}));

// Parent component handles event in template
// <c-child-component onselect={handleSelect}></c-child-component>
handleSelect(event) {
    const selectedId = event.detail.recordId;
}
```

**Parent-to-Child: Public Properties and Methods**

```javascript
// Child exposes public API
@api recordId;

@api
refresh() {
    this.loadData();
}

// Parent sets property in template
// <c-child-component record-id={selectedId}></c-child-component>

// Parent calls public method imperatively
this.template.querySelector('c-child-component').refresh();
```

**Unrelated Components: Lightning Message Service (LMS)**

```javascript
import { publish, subscribe, unsubscribe, MessageContext } from 'lightning/messageService';
import MY_CHANNEL from '@salesforce/messageChannel/MyMessageChannel__c';

// Publishing component
@wire(MessageContext) messageContext;

handlePublish() {
    publish(this.messageContext, MY_CHANNEL, {
        recordId: this.selectedId,
        source: 'componentA'
    });
}

// Subscribing component
@wire(MessageContext) messageContext;
subscription = null;

connectedCallback() {
    this.subscription = subscribe(
        this.messageContext,
        MY_CHANNEL,
        (message) => this.handleMessage(message)
    );
}

disconnectedCallback() {
    unsubscribe(this.subscription);
    this.subscription = null;
}
```

### LWC Naming Rules

| Context | Convention | Example |
|---|---|---|
| Folder name | camelCase | `myCustomComponent` |
| JS class name | PascalCase | `MyCustomComponent` |
| In HTML markup | kebab-case with namespace | `<c-my-custom-component>` |
| In Aura markup | camelCase with namespace | `<c:myCustomComponent>` |

Naming constraints:
- Must begin with a lowercase letter
- Must contain only alphanumeric characters
- Cannot contain hyphens or underscores in the folder/file name
- Cannot contain two consecutive uppercase letters
- Cannot end with an underscore
- Cannot contain a reserved word (e.g., `slot`, `template`, `part`)

### Common LWC Patterns

**Lightning Data Table:**
```html
<template>
    <lightning-datatable
        key-field="Id"
        data={records}
        columns={columns}
        onrowaction={handleRowAction}
        hide-checkbox-column
        show-row-number-column>
    </lightning-datatable>
</template>
```

**Lightning Record Form (Fastest Way to Build Record CRUD):**
```html
<!-- View mode -->
<lightning-record-view-form record-id={recordId} object-api-name="Account">
    <lightning-output-field field-name="Name"></lightning-output-field>
    <lightning-output-field field-name="Industry"></lightning-output-field>
</lightning-record-view-form>

<!-- Edit mode -->
<lightning-record-edit-form record-id={recordId} object-api-name="Account"
                            onsuccess={handleSuccess}>
    <lightning-input-field field-name="Name"></lightning-input-field>
    <lightning-input-field field-name="Industry"></lightning-input-field>
    <lightning-button type="submit" label="Save"></lightning-button>
</lightning-record-edit-form>

<!-- Automatic mode (view/edit toggle) -->
<lightning-record-form
    record-id={recordId}
    object-api-name="Account"
    fields={fields}
    mode="view">
</lightning-record-form>
```

**Navigation:**
```javascript
import { NavigationMixin } from 'lightning/navigation';

export default class NavExample extends NavigationMixin(LightningElement) {

    navigateToRecord(recordId) {
        this[NavigationMixin.Navigate]({
            type: 'standard__recordPage',
            attributes: {
                recordId: recordId,
                objectApiName: 'Account',
                actionName: 'view'
            }
        });
    }

    navigateToList() {
        this[NavigationMixin.Navigate]({
            type: 'standard__objectPage',
            attributes: {
                objectApiName: 'Account',
                actionName: 'list'
            },
            state: {
                filterName: 'Recent'
            }
        });
    }
}
```

### Deploy LWC

```bash
sf project deploy start \
  --source-dir force-app/main/default/lwc/{componentName} \
  --target-org <alias>
```

---

## 2. Aura Components (Legacy Lightning Framework)

Aura is the original Lightning component framework. Salesforce recommends LWC for all
new development. Use Aura only for maintaining existing components or for the few features
not yet available in LWC.

### File Structure

```
force-app/main/default/aura/{ComponentName}/
  {ComponentName}.cmp              ← Markup (required)
  {ComponentName}Controller.js     ← Client-side controller
  {ComponentName}Helper.js         ← Reusable helper functions
  {ComponentName}.css              ← Styles
  {ComponentName}.cmp-meta.xml     ← Metadata
  {ComponentName}.design           ← App Builder design attributes
  {ComponentName}.svg              ← Custom icon
  {ComponentName}Renderer.js       ← Custom renderer (rare)
```

### Tooling API Query

```sql
SELECT Id, DeveloperName, MasterLabel, ApiVersion,
       LastModifiedDate, LastModifiedBy.Name
FROM AuraDefinitionBundle
WHERE NamespacePrefix = null
ORDER BY DeveloperName
```

**API:** Tooling API

### Aura Component Example

```xml
<!-- {ComponentName}.cmp -->
<aura:component implements="flexipage:availableForRecordHome,force:hasRecordId"
                access="global"
                controller="MyApexController">

    <aura:attribute name="recordId" type="String" />
    <aura:attribute name="items" type="List" default="[]" />

    <aura:handler name="init" value="{!this}" action="{!c.doInit}" />

    <lightning:card title="My Aura Component">
        <aura:iteration items="{!v.items}" var="item">
            <p>{!item.Name}</p>
        </aura:iteration>
    </lightning:card>
</aura:component>
```

### Aura-LWC Interoperability

- LWC components CAN be used inside Aura components
- Aura components CANNOT be used inside LWC components
- Migration path: replace Aura components with LWC one at a time, bottom-up

### Deploy Aura

```bash
sf project deploy start \
  --source-dir force-app/main/default/aura/{ComponentName} \
  --target-org <alias>
```

---

## 3. Visualforce Pages

Visualforce is a legacy server-side rendering framework. Use only when required for
specific scenarios: PDF rendering, classic email templates, specific page overrides,
or certain connected app frontends.

### File Structure

```
force-app/main/default/pages/
  {PageName}.page              ← Markup
  {PageName}.page-meta.xml     ← Metadata
```

### Meta XML

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ApexPage xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>62.0</apiVersion>
    <availableInTouch>false</availableInTouch>
    <confirmationTokenRequired>false</confirmationTokenRequired>
    <label>My Page</label>
</ApexPage>
```

### Tooling API Query

```sql
SELECT Id, Name, ApiVersion, MasterLabel,
       LastModifiedDate, LastModifiedBy.Name
FROM ApexPage
WHERE NamespacePrefix = null
ORDER BY Name
```

**API:** Tooling API

### Common Use Cases

| Use Case | Why VF |
|---|---|
| PDF rendering | `renderAs="pdf"` attribute — no LWC equivalent |
| Classic email templates | VF email templates render server-side |
| Service Cloud console sidebar | Some legacy console integrations |
| Custom button overrides (Classic) | Required in orgs still on Classic |

### Deploy Visualforce Pages

```bash
sf project deploy start \
  --source-dir force-app/main/default/pages/{PageName}.page \
  --source-dir force-app/main/default/pages/{PageName}.page-meta.xml \
  --target-org <alias>
```

---

## 4. Visualforce Components

Reusable Visualforce markup blocks, used within Visualforce Pages.

### File Structure

```
force-app/main/default/components/
  {ComponentName}.component              ← Markup
  {ComponentName}.component-meta.xml     ← Metadata
```

### Tooling API Query

```sql
SELECT Id, Name, ApiVersion,
       LastModifiedDate, LastModifiedBy.Name
FROM ApexComponent
WHERE NamespacePrefix = null
ORDER BY Name
```

**API:** Tooling API

### Deploy Visualforce Components

```bash
sf project deploy start \
  --source-dir force-app/main/default/components/{ComponentName}.component \
  --source-dir force-app/main/default/components/{ComponentName}.component-meta.xml \
  --target-org <alias>
```

---

## 5. Custom Tabs

Custom Tabs surface custom objects, Visualforce pages, LWC components, web URLs,
or Lightning pages in the Salesforce navigation.

### Tooling API Query

```sql
SELECT Id, DeveloperName, MasterLabel, SobjectName, Type,
       Url, LastModifiedDate, LastModifiedBy.Name
FROM CustomTab
WHERE NamespacePrefix = null
ORDER BY DeveloperName
```

**API:** Tooling API

### Tab Types

| Type | Description | Typical Use |
|---|---|---|
| CustomObject | Tab for a custom object | Standard for any custom object |
| Web | External URL tab | Link to external systems |
| Visualforce | Tab hosting a VF page | Legacy custom UI |
| LightningComponent | Tab hosting an Aura or LWC component | Modern custom UI |
| FlexiPage | Tab hosting a Lightning Page | App Builder pages |

### File Structure

```
force-app/main/default/tabs/
  {TabName}.tab-meta.xml
```

### Tab Meta XML Example

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomTab xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>My Custom Tab</label>
    <customObject>true</customObject>
    <motif>Custom68: Wrench</motif>
    <mobileReady>true</mobileReady>
</CustomTab>
```

For LWC-based tab:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomTab xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>My LWC Tab</label>
    <lwcComponent>myComponentName</lwcComponent>
    <motif>Custom70: Laptop</motif>
    <mobileReady>true</mobileReady>
</CustomTab>
```

### Deploy Custom Tabs

```bash
sf project deploy start \
  --source-dir force-app/main/default/tabs/{TabName}.tab-meta.xml \
  --target-org <alias>
```

---

## 6. Quick Actions

Quick Actions provide streamlined UI for common tasks. They appear on record pages,
global actions menu, list views, and Chatter feeds.

### Tooling API Query

```sql
SELECT Id, DeveloperName, SobjectType, Type, Label,
       TargetObject, LastModifiedDate, LastModifiedBy.Name
FROM QuickActionDefinition
WHERE NamespacePrefix = null
ORDER BY SobjectType, DeveloperName
```

**API:** Tooling API

### Action Types

| Type | Description |
|---|---|
| Create | Create a new record |
| Update | Update fields on the current record |
| LogACall | Log a call activity |
| SendEmail | Send an email |
| Flow | Launch a screen flow |
| LightningWebComponent | Display a custom LWC |
| VisualforcePage | Display a Visualforce page |
| CustomAction | Custom Aura component |

### Global vs Object-Specific Actions

- **Global actions:** Not tied to any object. Appear in the global actions menu.
  - File path: `force-app/main/default/quickActions/{ActionName}.quickAction-meta.xml`
- **Object-specific actions:** Tied to a specific object. Appear on that object's record page.
  - File path: `force-app/main/default/quickActions/{ObjectName}.{ActionName}.quickAction-meta.xml`

### Quick Action Meta XML Example

```xml
<?xml version="1.0" encoding="UTF-8"?>
<QuickAction xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>Create Follow-Up Task</label>
    <optionsCreateFeedItem>false</optionsCreateFeedItem>
    <quickActionLayout>
        <layoutSectionStyle>TwoColumnsLeftToRight</layoutSectionStyle>
        <quickActionLayoutColumns>
            <quickActionLayoutItems>
                <emptySpace>false</emptySpace>
                <field>Subject</field>
                <uiBehavior>Required</uiBehavior>
            </quickActionLayoutItems>
            <quickActionLayoutItems>
                <emptySpace>false</emptySpace>
                <field>ActivityDate</field>
                <uiBehavior>Edit</uiBehavior>
            </quickActionLayoutItems>
        </quickActionLayoutColumns>
    </quickActionLayout>
    <targetObject>Task</targetObject>
    <type>Create</type>
</QuickAction>
```

### LWC Quick Action Example

```xml
<?xml version="1.0" encoding="UTF-8"?>
<QuickAction xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>Custom LWC Action</label>
    <lightningWebComponent>myQuickActionComponent</lightningWebComponent>
    <optionsCreateFeedItem>false</optionsCreateFeedItem>
    <type>LightningWebComponent</type>
    <height>400</height>
</QuickAction>
```

When using LWC in a Quick Action, the component must handle its own header and footer:

```javascript
import { LightningElement, api } from 'lwc';
import { CloseActionScreenEvent } from 'lightning/actions';

export default class MyQuickAction extends LightningElement {
    @api recordId;

    handleCancel() {
        this.dispatchEvent(new CloseActionScreenEvent());
    }

    handleSave() {
        // Perform save logic
        this.dispatchEvent(new CloseActionScreenEvent());
    }
}
```

### Deploy Quick Actions

```bash
sf project deploy start \
  --source-dir force-app/main/default/quickActions/ \
  --target-org <alias>
```

---

## 7. Lightning Applications

Lightning Applications define the top-level navigation, tabs, branding, and utility bar
configuration for a Lightning Experience app.

### Tooling API Query

```sql
SELECT Id, DeveloperName, MasterLabel,
       LastModifiedDate, LastModifiedBy.Name
FROM CustomApplication
WHERE NamespacePrefix = null
ORDER BY DeveloperName
```

**API:** Tooling API

Note: The Tooling API object is `CustomApplication`, not `LightningApplication`.
This query returns both Classic and Lightning apps. Check the `UiType` field if available
to distinguish between them.

### App Types

| Type | Description |
|---|---|
| Lightning (Standard) | Tabbed navigation in Lightning Experience |
| Lightning (Console) | Split-view console navigation for service/support |
| Classic | Salesforce Classic app (legacy) |

### File Structure

```
force-app/main/default/applications/
  {AppName}.app-meta.xml
```

### App Meta XML Example

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomApplication xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>My Custom App</label>
    <formFactors>
        <formFactor>Large</formFactor>
        <formFactor>Small</formFactor>
    </formFactors>
    <navType>Standard</navType>
    <uiType>Lightning</uiType>
    <tabs>
        <tab>standard-home</tab>
        <tab>Account</tab>
        <tab>Contact</tab>
        <tab>My_Custom_Object__c</tab>
    </tabs>
    <utilityBar>
        <utilityBarItems>
            <element>
                <componentName>flexipage:reportChart</componentName>
                <label>Reports</label>
            </element>
        </utilityBarItems>
    </utilityBar>
</CustomApplication>
```

### Deploy Lightning Applications

```bash
sf project deploy start \
  --source-dir force-app/main/default/applications/{AppName}.app-meta.xml \
  --target-org <alias>
```

---

## 8. UI Framework Decision Guide

| Framework | Use When | Status | Performance |
|---|---|---|---|
| LWC | New development, custom UI, record pages, flows | Active, recommended | Best (native web standards) |
| Aura | Legacy maintenance, features not yet in LWC | Legacy, maintenance only | Good (proprietary framework) |
| Visualforce | PDF rendering, classic email templates, specific overrides | Legacy | Slower (server-side rendering) |

### Decision Tree

1. **Is this new development?** -> Use LWC
2. **Does it need PDF rendering?** -> Use Visualforce with `renderAs="pdf"`
3. **Is it modifying an existing Aura component?** -> Maintain in Aura, plan LWC migration
4. **Does it need a feature only in Aura?** -> Use Aura (rare — check LWC docs first)
5. **Is it a Classic-only org?** -> Use Visualforce

### Feature Comparison

| Feature | LWC | Aura | Visualforce |
|---|---|---|---|
| Lightning App Builder | Yes | Yes | Via tab/iframe |
| Flow Screens | Yes | Yes | No |
| Experience Cloud | Yes | Yes | Limited |
| Mobile (Salesforce app) | Yes | Yes | Limited |
| PDF Rendering | No | No | Yes |
| Server-side rendering | No | No | Yes |
| Standard web APIs | Yes | Limited | No |
| Jest testing | Yes | No | No |

---

## 9. Gotchas and Common Pitfalls

### LWC Naming

- **Folder name must be camelCase:** `myComponent` (not `MyComponent`, `my-component`, or `my_component`)
- **In HTML markup, use kebab-case with `c-` prefix:** `<c-my-component>`
- **In Aura markup, use camelCase with `c:` namespace:** `<c:myComponent>`
- Two consecutive uppercase letters are NOT allowed: `myHTTPComponent` is invalid, use `myHttpComponent`

### Aura to LWC Migration

- Migrate bottom-up: convert leaf components first, then containers
- LWC can nest inside Aura; Aura cannot nest inside LWC
- Aura events do NOT cross into LWC — use LMS for cross-framework communication
- `$A.get()`, `$A.createComponent()` have no LWC equivalent — use standard DOM APIs

### Visualforce Limitations

- VF pages cannot use Lightning Design System (SLDS) natively without manual inclusion
- VF pages in Lightning Experience run inside an iframe — limited communication with Lightning
- ViewState limits (170 KB) can cause issues on complex pages
- Governor limits on controller methods apply server-side

### Quick Action Constraints

- Quick Action type determines which UI framework can be used:
  - `Create` / `Update` types: standard layout editor only
  - `LightningWebComponent` type: custom LWC only
  - `VisualforcePage` type: custom VF page only
  - `Flow` type: screen flow only
- LWC Quick Actions require the component to implement its own action bar (Save/Cancel buttons)
- Maximum height for LWC Quick Actions: configurable in metadata

### Lightning App Considerations

- Console apps have different navigation behavior than standard apps
- Utility bar items persist across pages in Lightning Experience
- App visibility is controlled by profiles and permission sets, not the app metadata itself
- Custom apps must be assigned to profiles/permission sets before users can see them

### General Deployment Notes

- Deploy LWC and Aura components BEFORE deploying FlexiPages that reference them
- Deploy Quick Actions BEFORE deploying page layouts that include them
- Deploy Custom Tabs BEFORE deploying apps that reference them
- Message Channels must be deployed before LWC components that import them

---

## 10. Useful CLI Commands

### List all LWC in an org

```bash
sf data query --query "SELECT DeveloperName, MasterLabel, ApiVersion FROM LightningComponentBundle WHERE NamespacePrefix = null ORDER BY DeveloperName" --target-org <alias> --use-tooling-api
```

### Retrieve all LWC from org

```bash
sf project retrieve start --metadata "LightningComponentBundle" --target-org <alias>
```

### Retrieve specific LWC

```bash
sf project retrieve start --metadata "LightningComponentBundle:myComponentName" --target-org <alias>
```

### Retrieve all Quick Actions for an object

```bash
sf project retrieve start --metadata "QuickAction:Account.*" --target-org <alias>
```

### Retrieve all Visualforce Pages

```bash
sf project retrieve start --metadata "ApexPage" --target-org <alias>
```

### Retrieve a Lightning App

```bash
sf project retrieve start --metadata "CustomApplication:My_App" --target-org <alias>
```

### Create a new LWC via CLI

```bash
sf lightning generate component --name myComponent --type lwc --output-dir force-app/main/default/lwc
```

---

## Context Specification

- metadata_type: LightningComponentBundle, AuraDefinitionBundle, ApexPage, QuickAction, CustomTab
- context_path: {alias}/ui-components/
- inventory_file: {alias}/ui-components/_inventory.md
- detail_file_pattern: {alias}/ui-components/{ApiName}.md

### Change Detection Queries

**Lightning Web Components**
Uses: tooling API
```sql
SELECT DeveloperName, MasterLabel, ApiVersion,
       LastModifiedDate, LastModifiedBy.Name
FROM LightningComponentBundle
WHERE NamespacePrefix = null
  AND LastModifiedDate > {LAST_SCAN}
ORDER BY LastModifiedDate DESC
LIMIT 50
```

**Aura Components**
Uses: tooling API
```sql
SELECT DeveloperName, MasterLabel, ApiVersion,
       LastModifiedDate, LastModifiedBy.Name
FROM AuraDefinitionBundle
WHERE NamespacePrefix = null
  AND LastModifiedDate > {LAST_SCAN}
ORDER BY LastModifiedDate DESC
LIMIT 50
```

**Visualforce Pages**
Uses: tooling API
```sql
SELECT Name, MasterLabel, ApiVersion,
       LastModifiedDate, LastModifiedBy.Name
FROM ApexPage
WHERE NamespacePrefix = null
  AND LastModifiedDate > {LAST_SCAN}
ORDER BY LastModifiedDate DESC
LIMIT 50
```

**Quick Actions**
Uses: tooling API
```sql
SELECT DeveloperName, SobjectType, Type, Label,
       LastModifiedDate, LastModifiedBy.Name
FROM QuickActionDefinition
WHERE NamespacePrefix = null
  AND LastModifiedDate > {LAST_SCAN}
ORDER BY LastModifiedDate DESC
LIMIT 50
```

**Custom Tabs**
Uses: tooling API
```sql
SELECT DeveloperName, MasterLabel, SobjectName, Type,
       LastModifiedDate, LastModifiedBy.Name
FROM CustomTab
WHERE NamespacePrefix = null
  AND LastModifiedDate > {LAST_SCAN}
ORDER BY LastModifiedDate DESC
LIMIT 50
```

### Inventory Columns

| Type | API Name | Label | Framework | Object | Last Modified | Modified By |
|---|---|---|---|---|---|---|

### Naming Convention Detection

- **LWC:** camelCase folder names (e.g., `accountList`, `customRecordForm`)
- **Aura:** PascalCase folder names (e.g., `AccountList`, `CustomRecordForm`)
- **Visualforce Pages:** Mixed conventions; often PascalCase or underscore-separated
- **Quick Actions:** `{Object}.{ActionName}` for object-specific; `{ActionName}` for global
- **Custom Tabs:** Matches the object or component API name; `{Name}` tab

### Detail File Sections

- Identity (API Name, Label, Type/Framework, API Version)
- Configuration (Targets, Target Configs, Exposed, Object Associations)
- Dependencies (Apex Controllers, Message Channels, Static Resources, Other Components)
- Last Scanned Timestamp
