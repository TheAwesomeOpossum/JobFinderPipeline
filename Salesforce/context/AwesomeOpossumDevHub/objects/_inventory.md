# Objects Inventory — AwesomeOpossumDevHub

_Last scanned: 2026-03-26T17:37:00Z_
_Source: sf-init-project_

## Detected Managed Packages

_(None — this is a clean org with no managed packages)_

## Detected Naming Conventions

- **Primary style:** PascalCase with underscores for multi-word names (e.g., `JobApplication__c`, `CoverLetter__c`)
- **Junction pattern:** `Resume_{EntityName}__c` for resume join objects (Resume_Award__c, Resume_Education__c, Resume_Experience__c, Resume_Strength__c)
- **No namespace prefix detected** — all objects are org-built
- **Custom metadata types:** PascalCase + `__mdt` suffix (e.g., `AIPromptConfig__mdt`, `ResumeOwnerConfig__mdt`)

## Custom Object Inventory

| Object API Name | Namespace | Org-Built | Notes |
|---|---|---|---|
| AIPromptConfig__mdt | _(none)_ | Yes | Custom Metadata Type — AI prompt configuration |
| AboutMe__c | _(none)_ | Yes | Resume profile section |
| AnthropicSettings__c | _(none)_ | Yes | Anthropic/AI integration settings |
| Award__c | _(none)_ | Yes | Award data for resume |
| CoverLetter__c | _(none)_ | Yes | Cover letter generation |
| Education__c | _(none)_ | Yes | Education history for resume |
| Experience__c | _(none)_ | Yes | Work experience for resume |
| InterviewContact__c | _(none)_ | Yes | Junction — Interview to Contact |
| Interview__c | _(none)_ | Yes | Interview tracking |
| JobApplication__c | _(none)_ | Yes | Job application tracking |
| Job__c | _(none)_ | Yes | Job listing data |
| ResumeOwnerConfig__mdt | _(none)_ | Yes | Custom Metadata Type — resume owner config |
| Resume_Award__c | _(none)_ | Yes | Junction — Resume to Award |
| Resume_Education__c | _(none)_ | Yes | Junction — Resume to Education |
| Resume_Experience__c | _(none)_ | Yes | Junction — Resume to Experience |
| Resume_Strength__c | _(none)_ | Yes | Junction — Resume to Strength |
| Resume__c | _(none)_ | Yes | Resume master record |
| Strength__c | _(none)_ | Yes | Strengths/skills for resume |
