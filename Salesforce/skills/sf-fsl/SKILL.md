---
name: sf-fsl
description: "Reference for Salesforce Field Service Lightning (FSL) metadata — Service Territories, Work Types, Skills, Service Resources, Operating Hours, Scheduling Policies, and FSL-specific custom settings. Includes API queries and configuration patterns."
---

# SF Field Service Lightning (FSL) Skill

---

## 1. FSL Architecture Overview

Field Service Lightning extends Salesforce Service Cloud to manage field operations. The core data model flows through these relationships:

```
Account / Contact
    └── Work Order (service request)
            ├── Work Order Line Item (individual tasks)
            └── Service Appointment (scheduled event)
                    ├── Assigned Resource (ServiceResource)
                    │       ├── ServiceTerritoryMember (territory assignment)
                    │       ├── ResourceAbsence (time off / unavailability)
                    │       └── Skill (capabilities)
                    ├── Service Territory (geographic area)
                    │       └── Operating Hours
                    └── Work Type (type + estimated duration)
```

**Key relationships:**
- A **Work Order** represents a service request tied to an Account/Contact/Asset
- **Work Order Line Items** break a Work Order into individual tasks
- A **Service Appointment** is the schedulable unit — it has a start/end time and is assigned to a **Service Resource**
- **Service Resources** are workers or equipment, linked to a User or Contact record
- **Service Territories** define geographic areas; resources are assigned to territories via **ServiceTerritoryMember**
- **Work Types** define the type of work and estimated duration, used as templates for Service Appointments
- **Operating Hours** define when a territory or resource is available
- **Skills** and **Skill Requirements** match resource capabilities to work requirements

---

## 2. Core FSL Standard Objects

### 2.1 ServiceTerritory

Geographic areas for organizing and assigning service resources.

**Inventory query (Standard API):**
```sql
SELECT Id, Name, OperatingHoursId, OperatingHours.Name,
       IsActive, ParentTerritoryId, ParentTerritory.Name,
       Street, City, State, PostalCode, Country,
       Latitude, Longitude,
       LastModifiedDate, LastModifiedBy.Name
FROM ServiceTerritory
ORDER BY Name
```

**Key fields:**
| Field | Type | Description |
|---|---|---|
| `Name` | Text | Territory name (e.g., "San Francisco Bay Area") |
| `OperatingHoursId` | Lookup | When the territory is active for scheduling |
| `IsActive` | Boolean | Only active territories are used in scheduling |
| `ParentTerritoryId` | Self-lookup | Enables territory hierarchies |
| `Street/City/State/PostalCode/Country` | Address | Physical location of territory center |
| `Latitude/Longitude` | Geolocation | Used for map-based scheduling and travel calculations |

**Territory types (on ServiceTerritoryMember):**
- **Primary** — The resource's main territory
- **Secondary** — Additional territories the resource can serve
- **Relocation** — Temporary territory assignment

---

### 2.2 WorkType

Templates that define the type and estimated duration of work.

**Inventory query (Standard API):**
```sql
SELECT Id, Name, EstimatedDuration, DurationType,
       Description, BlockTimeBeforeAppointment,
       BlockTimeAfterAppointment, TimeframeStart,
       TimeframeEnd, MinimumCrewSize, RecommendedCrewSize,
       LastModifiedDate, LastModifiedBy.Name
FROM WorkType
ORDER BY Name
```

**Key fields:**
| Field | Type | Description |
|---|---|---|
| `Name` | Text | Work type name (e.g., "Annual HVAC Inspection") |
| `EstimatedDuration` | Number | How long the work takes |
| `DurationType` | Picklist | `Hours` or `Minutes` |
| `BlockTimeBeforeAppointment` | Number | Buffer time before the appointment (minutes) |
| `BlockTimeAfterAppointment` | Number | Buffer time after the appointment (minutes) |
| `TimeframeStart/TimeframeEnd` | Number | Days from creation to define scheduling window |
| `MinimumCrewSize` | Number | Minimum resources needed |
| `RecommendedCrewSize` | Number | Ideal number of resources |

**Work Type Groups** (available in later releases) let you group related work types for reporting and scheduling.

---

### 2.3 Skill and SkillRequirement

Skills define resource capabilities; SkillRequirements define what a Work Type or Service Appointment needs.

**Skills inventory (Standard API):**
```sql
SELECT Id, MasterLabel, DeveloperName, Description,
       LastModifiedDate, LastModifiedBy.Name
FROM Skill
ORDER BY MasterLabel
```

**Skill Requirements query (Standard API):**
```sql
SELECT Id, RelatedRecordId, RelatedRecord.Name,
       SkillId, Skill.MasterLabel, SkillLevel,
       LastModifiedDate, LastModifiedBy.Name
FROM SkillRequirement
ORDER BY Skill.MasterLabel
```

**Important:**
- `SkillLevel` is a decimal from 0 to 99.99
- `RelatedRecordId` can point to a WorkType, ServiceAppointment, or WorkOrder
- Skills are defined once globally, then referenced via SkillRequirement junction records
- Service Resources have skills assigned via `ServiceResourceSkill` records

**ServiceResourceSkill query:**
```sql
SELECT Id, ServiceResourceId, ServiceResource.Name,
       SkillId, Skill.MasterLabel, SkillLevel,
       EffectiveStartDate, EffectiveEndDate,
       LastModifiedDate
FROM ServiceResourceSkill
ORDER BY ServiceResource.Name, Skill.MasterLabel
```

---

### 2.4 ServiceResource

Workers or equipment that can be assigned to Service Appointments.

**Inventory query (Standard API):**
```sql
SELECT Id, Name, RelatedRecordId, RelatedRecord.Name,
       ResourceType, IsActive, IsCapacityBased,
       Description, LastModifiedDate, LastModifiedBy.Name
FROM ServiceResource
WHERE IsActive = true
ORDER BY Name
```

**Key fields:**
| Field | Type | Description |
|---|---|---|
| `Name` | Text | Resource display name |
| `RelatedRecordId` | Polymorphic Lookup | Links to User (technician) or Contact (contractor) |
| `ResourceType` | Picklist | `T` (Technician), `D` (Dispatcher), `C` (Crew), `A` (Agent) |
| `IsActive` | Boolean | Only active resources are scheduled |
| `IsCapacityBased` | Boolean | If true, uses capacity-based scheduling instead of time-based |

**Resource types explained:**
- **Technician (T)** — Field workers who travel to service locations
- **Dispatcher (D)** — Users who manage the Gantt/dispatch console
- **Crew (C)** — Groups of resources that work together
- **Agent (A)** — Internal agents (e.g., phone support, not field-based)

---

### 2.5 OperatingHours

Define availability windows for territories, resources, and accounts.

**Inventory query (Standard API):**
```sql
SELECT Id, Name, Description, TimeZone,
       LastModifiedDate, LastModifiedBy.Name
FROM OperatingHours
ORDER BY Name
```

**Time Slots query (Standard API):**
```sql
SELECT Id, OperatingHoursId, OperatingHours.Name,
       DayOfWeek, StartTime, EndTime, Type
FROM TimeSlot
ORDER BY OperatingHoursId, DayOfWeek, StartTime
```

**Key concepts:**
- Operating Hours contain **TimeSlot** child records defining day-by-day availability
- `DayOfWeek` values: `Monday`, `Tuesday`, `Wednesday`, `Thursday`, `Friday`, `Saturday`, `Sunday`
- `Type` is typically `Normal` (regular hours) or `Extended` (overtime availability)
- TimeZone on OperatingHours determines how time slots are interpreted
- A single OperatingHours record can be shared across multiple territories/resources

---

### 2.6 ServiceTerritoryMember

Junction object linking Service Resources to Service Territories.

**Inventory query (Standard API):**
```sql
SELECT Id, ServiceResourceId, ServiceResource.Name,
       ServiceTerritoryId, ServiceTerritory.Name,
       TerritoryType, EffectiveStartDate, EffectiveEndDate,
       Street, City, State, PostalCode, Country,
       Latitude, Longitude, OperatingHoursId,
       LastModifiedDate
FROM ServiceTerritoryMember
ORDER BY ServiceTerritory.Name, ServiceResource.Name
```

**TerritoryType values:**
- `P` — Primary (resource's home territory)
- `S` — Secondary (additional coverage area)
- `R` — Relocation (temporary assignment)

Each resource should have exactly one Primary territory at any given time. Scheduling policies use territory type to prioritize resource assignment.

---

### 2.7 ServiceAppointment

The schedulable unit — represents a specific service visit with a time window.

**Query (Standard API):**
```sql
SELECT Id, AppointmentNumber, Subject, Status,
       ParentRecordId, ParentRecord.Name,
       WorkTypeId, WorkType.Name,
       ServiceTerritoryId, ServiceTerritory.Name,
       EarliestStartTime, DueDate,
       SchedStartTime, SchedEndTime,
       ActualStartTime, ActualEndTime,
       Duration, DurationType,
       Street, City, State, PostalCode, Country,
       Latitude, Longitude,
       LastModifiedDate, LastModifiedBy.Name
FROM ServiceAppointment
ORDER BY SchedStartTime DESC
LIMIT 200
```

**Standard status values:** None, Scheduled, Dispatched, In Progress, Completed, Canceled

**Custom statuses** can be added via Setup > Field Service > Service Appointment Statuses.

---

### 2.8 WorkOrder and WorkOrderLineItem

**WorkOrder query (Standard API):**
```sql
SELECT Id, WorkOrderNumber, Subject, Status, Priority,
       AccountId, Account.Name, ContactId, Contact.Name,
       AssetId, Asset.Name, WorkTypeId, WorkType.Name,
       ServiceTerritoryId, ServiceTerritory.Name,
       StartDate, EndDate,
       LastModifiedDate, LastModifiedBy.Name
FROM WorkOrder
ORDER BY CreatedDate DESC
LIMIT 200
```

**WorkOrderLineItem query (Standard API):**
```sql
SELECT Id, LineItemNumber, Subject, Status,
       WorkOrderId, WorkOrder.WorkOrderNumber,
       WorkTypeId, WorkType.Name,
       StartDate, EndDate, Duration, DurationType,
       LastModifiedDate
FROM WorkOrderLineItem
ORDER BY WorkOrderId, LineItemNumber
LIMIT 200
```

---

## 3. FSL Managed Package Objects

These objects require the **Field Service managed package** (`FSL`) to be installed. They are prefixed with `FSL__`.

### 3.1 Scheduling Policies

```sql
SELECT Id, Name, FSL__Description__c,
       FSL__Daily_Optimization__c, FSL__Fix_Overlaps__c,
       LastModifiedDate, LastModifiedBy.Name
FROM FSL__Scheduling_Policy__c
ORDER BY Name
```

Scheduling Policies contain **Work Rules** and **Service Objectives** that control how the optimizer assigns appointments.

### 3.2 Work Rules (FSL__Scheduling_Policy_Work_Rule__c)

Junction between Scheduling Policies and Work Rule definitions:
```sql
SELECT Id, FSL__Scheduling_Policy__c, FSL__Scheduling_Policy__r.Name,
       FSL__Service_Work_Rule__c, FSL__Service_Work_Rule__r.Name
FROM FSL__Scheduling_Policy_Work_Rule__c
ORDER BY FSL__Scheduling_Policy__r.Name
```

Common work rule types:
- **Match Territory** — Resource must be in the appointment's territory
- **Match Skills** — Resource must have required skills
- **Working Hours** — Respect operating hours
- **Maximum Travel From Home** — Limit travel distance
- **Resource Availability** — Check for absences

### 3.3 Service Goals (FSL__Service_Goal__c)

Optimization objectives assigned to scheduling policies:
```sql
SELECT Id, Name, FSL__Type__c, FSL__Object_Group_Field__c,
       LastModifiedDate
FROM FSL__Service_Goal__c
ORDER BY Name
```

Goal types: Minimize Travel, Minimize Overtime, Maximize Priority, ASAP, Resource Priority, Custom

### 3.4 Polygons (FSL__Polygon__c)

Geographic boundaries used for territory mapping and map layers:
```sql
SELECT Id, Name, FSL__KML__c, FSL__Color__c,
       FSL__Service_Territory__c, FSL__Service_Territory__r.Name,
       LastModifiedDate
FROM FSL__Polygon__c
ORDER BY Name
```

**Note:** Query managed package custom fields with their full API name including the `FSL__` namespace prefix. If the managed package is not installed, these queries will fail with "sObject type not found."

---

## 4. FSL Custom Settings and Configuration

### 4.1 FSL Customization Settings

`FSL__Customization__c` is a hierarchy custom setting controlling FSL behavior:

```sql
SELECT Id, SetupOwnerId, FSL__Enable_Drip_Feed__c,
       FSL__Enable_Predictive_Travel__c,
       FSL__Enable_Scheduling__c, FSL__Enable_Street_Level_Routing__c,
       FSL__Ga_Enabled__c, FSL__Optimization_Enabled__c
FROM FSL__Customization__c
```

### 4.2 Field Service Settings (Setup UI)

Access via: **Setup > Field Service > Field Service Settings**

Key settings configured via UI:
- **Auto-create Service Appointments from Work Orders** — Automatically generates SA records
- **Service Appointment default status flow**
- **Geolocation tracking settings** for mobile workers
- **Inventory management** enable/disable
- **Scheduling horizon** — How far in the future the optimizer looks

### 4.3 Connected App (FSL Mobile)

The Field Service mobile app connects via a Connected App. Key settings:
- Mobile app field sets on ServiceAppointment, WorkOrder, WorkOrderLineItem
- Offline data configuration (which objects/fields are cached on device)
- Mobile flow definitions for guided workflows

---

## 5. Dispatcher Console (Gantt)

### 5.1 Gantt Chart Configuration

The Dispatcher Console is a Lightning component (`FSL:GanttComponent`) that provides:
- Drag-and-drop scheduling
- Resource calendar view
- Map integration
- Optimization triggers

**Configure via:** Setup > Field Service > Dispatcher Console UI

Key configuration areas:
- **Palettes** — Color-coding service appointments by status or custom fields
- **Filters** — What appointments appear on the Gantt
- **Match resources** — Quick-match resources to appointments based on skills/territory
- **Candidates** — Suggested time slots when scheduling manually

### 5.2 Service Report Templates

Templates for generating PDF reports after service completion:
- Configured in Setup > Field Service > Service Report Templates
- Contain sections for customer signature, parts used, work performed
- Rendered on mobile app and can be emailed to customers

---

## 6. FSL Triggers and Automation Considerations

### 6.1 Common Trigger Points

**ServiceAppointment triggers (most common):**
- Status change automation (e.g., notify customer when Dispatched)
- Auto-populate fields from parent Work Order
- Validate scheduling window constraints
- Calculate travel time or update related records

**WorkOrder triggers:**
- Auto-create Service Appointments when Work Order is created
- Status rollup from child Work Order Line Items
- SLA/entitlement calculations

**ResourceAbsence triggers:**
- Notify dispatchers of newly created absences
- Auto-reschedule affected appointments

### 6.2 Automation Best Practices

| Practice | Detail |
|---|---|
| **Avoid heavy triggers on ServiceAppointment** | The FSL optimizer performs bulk DML on ServiceAppointment records. Heavy triggers cause optimization timeouts. |
| **Use async processing** | For complex logic triggered by status changes, use Platform Events or Queueable Apex instead of synchronous triggers |
| **Check for FSL context** | The managed package sets certain fields during optimization. Use `FSL.SchedulingHelper` methods to detect optimizer context if available |
| **Respect the scheduling lifecycle** | Status values flow: None > Scheduled > Dispatched > In Progress > Completed. Don't skip statuses without understanding downstream effects |
| **Resource Absence handling** | When an absence is created, the optimizer can auto-reschedule affected appointments. Avoid duplicate rescheduling logic in triggers |

### 6.3 FSL-Specific Apex Utilities

If the managed package is installed, these are available:
- `FSL.GanttBookingService` — Book appointments programmatically
- `FSL.AppointmentBookingService` — Get candidate time slots
- `FSL.ScheduleService` — Run optimization programmatically

```apex
// Example: Get scheduling candidates for a Service Appointment
FSL.AppointmentBookingService service = new FSL.AppointmentBookingService();
List<FSL.AppointmentBookingSlot> slots = service.getSlots(
    serviceAppointmentId,
    schedulingPolicyId
);
```

---

## 7. CLI Commands for FSL Metadata

```bash
# Retrieve all Service Territories
sf data query \
  --query "SELECT Id, Name, IsActive FROM ServiceTerritory ORDER BY Name" \
  --target-org <alias> --result-format table

# Retrieve Work Types
sf data query \
  --query "SELECT Id, Name, EstimatedDuration, DurationType FROM WorkType ORDER BY Name" \
  --target-org <alias> --result-format table

# Retrieve Operating Hours with Time Slots
sf data query \
  --query "SELECT Id, Name, TimeZone FROM OperatingHours ORDER BY Name" \
  --target-org <alias> --result-format table

# Check FSL managed package version
sf package installed list --target-org <alias>

# Retrieve FSL-related custom fields on standard objects
sf project retrieve start \
  --metadata "CustomField:ServiceAppointment.*" \
  --target-org <alias>

sf project retrieve start \
  --metadata "CustomField:WorkOrder.*" \
  --target-org <alias>
```

---

## 8. Gotchas

| Issue | Detail |
|---|---|
| **Managed package required** | FSL__* objects only exist after installing the Field Service managed package. Core objects (WorkOrder, ServiceAppointment, ServiceTerritory) are standard but have limited functionality without the package. |
| **Optimizer bulk DML** | The scheduling optimizer performs bulk inserts/updates on ServiceAppointment. Triggers must be bulkified and performant or optimization will timeout. |
| **Geolocation accuracy** | Scheduling quality depends heavily on accurate address/geolocation data on ServiceTerritory, ServiceAppointment, and ServiceResource records. |
| **Status transitions** | Service Appointment statuses have a defined flow. Skipping statuses (e.g., None directly to Completed) may break reporting and mobile app behavior. |
| **Territory hierarchy** | Child territories inherit operating hours from parent unless explicitly overridden. This can cause unexpected scheduling windows. |
| **Crew scheduling** | Crew-based scheduling (multiple resources per appointment) adds complexity. Ensure MinimumCrewSize and RecommendedCrewSize are set on WorkType. |
| **Mobile offline sync** | Changes made offline on the mobile app sync when connectivity returns. Triggers must handle out-of-order updates gracefully. |
| **Permission sets** | FSL requires specific permission sets: `FSL_Admin_Permissions`, `FSL_Dispatcher_Permissions`, `FSL_Resource_Permissions`, `FSL_Community_Dispatcher`, etc. |
| **Multi-day appointments** | Appointments spanning multiple days require special handling in scheduling policies and triggers. |

---

## Context Specification

- metadata_type: ServiceTerritory, WorkType, SkillRequirement, ServiceResource, OperatingHours
- context_path: {alias}/fsl/
- inventory_file: {alias}/fsl/_inventory.md
- detail_file_pattern: _(inventory only)_

### Full Inventory Queries

Uses: standard API

**Service Territories:**
```sql
SELECT Id, Name, OperatingHoursId, OperatingHours.Name,
       IsActive, ParentTerritoryId, ParentTerritory.Name,
       LastModifiedDate, LastModifiedBy.Name
FROM ServiceTerritory
ORDER BY Name
```

**Work Types:**
```sql
SELECT Id, Name, EstimatedDuration, DurationType,
       Description, LastModifiedDate, LastModifiedBy.Name
FROM WorkType
ORDER BY Name
```

**Skills:**
```sql
SELECT Id, MasterLabel, DeveloperName, Description,
       LastModifiedDate, LastModifiedBy.Name
FROM Skill
ORDER BY MasterLabel
```

**Service Resources:**
```sql
SELECT Id, Name, RelatedRecordId, ResourceType,
       IsActive, LastModifiedDate, LastModifiedBy.Name
FROM ServiceResource
WHERE IsActive = true
ORDER BY Name
```

**Operating Hours:**
```sql
SELECT Id, Name, Description, TimeZone,
       LastModifiedDate, LastModifiedBy.Name
FROM OperatingHours
ORDER BY Name
```

### Change Detection Query

Uses: standard API
```sql
SELECT Id, Name, LastModifiedDate, LastModifiedBy.Name
FROM ServiceTerritory
WHERE LastModifiedDate > {LAST_SCAN}
ORDER BY LastModifiedDate DESC
LIMIT 50
```

```sql
SELECT Id, Name, LastModifiedDate, LastModifiedBy.Name
FROM WorkType
WHERE LastModifiedDate > {LAST_SCAN}
ORDER BY LastModifiedDate DESC
LIMIT 50
```

```sql
SELECT Id, Name, LastModifiedDate, LastModifiedBy.Name
FROM ServiceResource
WHERE LastModifiedDate > {LAST_SCAN}
ORDER BY LastModifiedDate DESC
LIMIT 50
```

Uses: standard API (SetupAuditTrail for FSL settings changes)
```sql
SELECT Action, Display, Section, CreatedDate, CreatedBy.Name
FROM SetupAuditTrail
WHERE Section LIKE '%Field Service%'
AND CreatedDate > {LAST_SCAN}
ORDER BY CreatedDate DESC
LIMIT 50
```

### Inventory Columns
Name | Type | Active | Operating Hours / Duration | Last Modified Date | Last Modified By

### Detail File Sections
_(No per-record detail files — inventory groups territories, work types, skills, resources, and operating hours into a single inventory file.)_

### Naming Convention Detection
Analyze all ServiceTerritory names, WorkType names, and Skill labels and extract:
- **Territory naming pattern:** e.g., geographic region, city-based, zone-numbered
- **Work Type naming pattern:** e.g., `{Service}_{Duration}`, descriptive labels
- **Skill naming pattern:** e.g., certification-based, tool-based, trade-based
- Report findings in the `## Detected Naming Conventions` section at the top of `_inventory.md`
