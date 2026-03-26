# Data Architecture Inventory — AwesomeOpossumDevHub

_Last scanned: 2026-03-26T17:37:00Z_
_Source: sf-init-project_
_Skill: sf-data-architecture_

## Detected Naming Conventions

- **Record types:** PascalCase with underscores for spaces (e.g., `Work_Experience`, `Personal_Experience`)
- **CMDT:** PascalCase + `__mdt` (e.g., `AIPromptConfig__mdt`, `ResumeOwnerConfig__mdt`)
- **Global Value Sets:** PascalCase singular nouns (e.g., `Skills`)

## Record Types — 3 total

| Object | Developer Name | Active | Notes |
|---|---|---|---|
| Experience__c | Internship | Yes | Internship experience type |
| Experience__c | Personal_Experience | Yes | Personal project/experience |
| Experience__c | Work_Experience | Yes | Professional work experience |

## Custom Metadata Types — 2 total

| API Name | Notes |
|---|---|
| AIPromptConfig__mdt | AI prompt templates/configuration |
| ResumeOwnerConfig__mdt | Resume owner settings/config |

## Global Value Sets — 1 total

| Developer Name | Notes |
|---|---|
| Skills | Skill picklist values shared across objects |

## Custom Settings

_(None found)_

## Platform Events

_(None found)_

## Field Sets

_(Not queried — check org if needed)_
