# Apex Triggers Inventory — AwesomeOpossumDevHub

_Last scanned: 2026-03-26T17:37:00Z_
_Source: sf-init-project_
_Skill: sf-trigger-patterns_

## Detected Naming Conventions

- **Trigger naming:** `{ObjectName}Trigger` (e.g., `AccountTrigger`, `JobApplicationTrigger`)
- **Handler naming:** `{ObjectName}TriggerHandler`
- **Processor naming:** `{ObjectName}Processor`
- **Test naming:** `{ObjectName}TriggerTest`
- **Interfaces used:** `TriggerHandlerInterface`, `RecordProcessorInterface`
- **Pattern:** Single trigger per object → delegates to handler → delegates to processor(s)

## Trigger Inventory

| Trigger Name | Object | Status | API Version | Last Modified |
|---|---|---|---|---|
| AccountTrigger | Account | Active | v66 | 2026-03-13 |
| ExperienceTrigger | Experience__c | Active | v66 | 2026-03-19 |
| InterviewTrigger | Interview__c | Active | v66 | 2026-03-16 |
| JobApplicationTrigger | JobApplication__c | Active | v62 | 2026-03-08 |
| JobTrigger | Job__c | Active | v60 | 2024-02-26 |

## Handler / Processor Class Map

| Object | Trigger | Handler | Processor(s) | Test Class |
|---|---|---|---|---|
| Account | AccountTrigger | AccountTriggerHandler | AccountProcessor | AccountSearchControllerTest |
| Experience__c | ExperienceTrigger | ExperienceTriggerHandler | ExperienceProcessor | ExperienceTriggerTest |
| Interview__c | InterviewTrigger | InterviewTriggerHandler | InterviewProcessor | InterviewTriggerTest |
| JobApplication__c | JobApplicationTrigger | _(unknown — check org)_ | _(unknown)_ | _(unknown)_ |
| Job__c | JobTrigger | JobTriggerHandler | _(JobHelper)_ | _(unknown)_ |
