# Apex Classes Inventory — AwesomeOpossumDevHub

_Last scanned: 2026-03-26T17:37:00Z_
_Source: sf-init-project_
_Skill: sf-apex-classes_

## Detected Naming Conventions

- **Controllers:** `{Feature}Controller` suffix (e.g., `AIResumeGeneratorController`, `CoverLetterController`)
- **Test classes:** `{ClassName}Test` suffix (e.g., `ResumeControllerTest`, `InterviewTriggerTest`)
- **Trigger handlers:** `{Object}TriggerHandler` pattern (e.g., `AccountTriggerHandler`, `InterviewTriggerHandler`)
- **Processors:** `{Object}Processor` suffix (e.g., `AccountProcessor`, `ExperienceProcessor`)
- **Interfaces:** PascalCase ending in `Interface` (e.g., `TriggerHandlerInterface`, `RecordProcessorInterface`)
- **Helpers/Utils:** `{Domain}Helper` suffix (e.g., `JobHelper`, `ResumePDFHelper`)
- **Community/Standard templates:** `Communities*`, `Site*`, `Lightning*`, `Microbatch*` prefixes (Salesforce-generated)
- **Test data:** `TestDataFactory`, `TestDataFactoryTests`
- **No namespace prefix** on any class

## Inventory

| Name | Status | API Version | Category | Last Modified |
|---|---|---|---|---|
| AccountListControllerLwc | Active | v63 | Controller (LWC) | 2025-03-20 |
| AccountProcessor | Active | v66 | Processor | 2026-03-13 |
| AccountSearchController | Active | v62 | Controller | 2026-03-10 |
| AccountSearchControllerTest | Active | v62 | Test | 2026-03-10 |
| AccountTriggerHandler | Active | v66 | Trigger Handler | 2026-03-13 |
| AIInterviewGuideController | Active | v62 | Controller (AI) | 2026-03-16 |
| AIInterviewGuideControllerTest | Active | v62 | Test | 2026-03-16 |
| AIResumeGeneratorController | Active | v62 | Controller (AI) | 2026-03-07 |
| AIResumeGeneratorControllerTest | Active | v62 | Test | 2026-03-07 |
| ChangePasswordController | Active | v63 | Controller (Community) | 2026-03-02 |
| ChangePasswordControllerTest | Active | v63 | Test | 2026-03-02 |
| CommunitiesLandingController | Active | v63 | Controller (Community) | 2026-03-02 |
| CommunitiesLandingControllerTest | Active | v63 | Test | 2026-03-02 |
| CommunitiesLoginController | Active | v63 | Controller (Community) | 2026-03-02 |
| CommunitiesLoginControllerTest | Active | v63 | Test | 2026-03-02 |
| CommunitiesSelfRegConfirmController | Active | v63 | Controller (Community) | 2026-03-02 |
| CommunitiesSelfRegConfirmControllerTest | Active | v63 | Test | 2026-03-02 |
| CommunitiesSelfRegController | Active | v63 | Controller (Community) | 2026-03-02 |
| CommunitiesSelfRegControllerTest | Active | v63 | Test | 2026-03-02 |
| ContactMeController | Active | v62 | Controller | 2026-03-02 (est.) |
| CoverLetterController | Active | v62 | Controller | 2026-03-02 (est.) |
| ExperienceProcessor | Active | v66 | Processor | 2026-03-19 (est.) |
| ExperienceTriggerHandler | Active | v66 | Trigger Handler | 2026-03-19 (est.) |
| ExperienceTriggerTest | Active | v66 | Test | 2026-03-19 (est.) |
| ForgotPasswordController | Active | v63 | Controller (Community) | 2026-03-02 |
| ForgotPasswordControllerTest | Active | v63 | Test | 2026-03-02 |
| InterviewProcessor | Active | v66 | Processor | 2026-03-16 (est.) |
| InterviewTriggerHandler | Active | v66 | Trigger Handler | 2026-03-16 |
| InterviewTriggerTest | Active | v66 | Test | 2026-03-16 |
| JobHelper | Active | v59 | Helper | 2024-02-26 (est.) |
| JobTriggerHandler | Active | v59 | Trigger Handler | 2024-02-26 (est.) |
| LightningForgotPasswordController | Active | v63 | Controller (Community) | 2026-03-02 |
| LightningForgotPasswordControllerTest | Active | v63 | Test | 2026-03-02 |
| LightningLoginFormController | Active | v63 | Controller (Community) | 2026-03-02 |
| LightningLoginFormControllerTest | Active | v63 | Test | 2026-03-02 |
| LightningSelfRegisterController | Active | v63 | Controller (Community) | 2026-03-02 |
| LightningSelfRegisterControllerTest | Active | v63 | Test | 2026-03-02 |
| ManagedContentController | Active | v62 | Controller | 2026-03-02 (est.) |
| MicrobatchSelfRegController | Active | v63 | Controller (Community) | 2026-03-02 |
| MicrobatchSelfRegControllerTest | Active | v63 | Test | 2026-03-02 |
| MyProfilePageController | Active | v63 | Controller (Community) | 2026-03-02 |
| MyProfilePageControllerTest | Active | v63 | Test | 2026-03-02 |
| RecordProcessorInterface | Active | v66 | Interface | 2026-03-19 (est.) |
| ResumeController | Active | v62 | Controller | 2026-03-07 (est.) |
| ResumeControllerTest | Active | v62 | Test | 2026-03-07 (est.) |
| ResumeExperienceController | Active | v59 | Controller | 2024-02-26 (est.) |
| ResumePDFHelper | Active | v59 | Helper | 2024-02-26 (est.) |
| ResumeWizardController | Active | v62 | Controller | 2026-03-07 (est.) |
| ResumeWizardControllerTest | Active | v62 | Test | 2026-03-07 (est.) |
| SiteLoginController | Active | v63 | Controller (Community) | 2026-03-02 |
| SiteLoginControllerTest | Active | v63 | Test | 2026-03-02 |
| SiteRegisterController | Active | v63 | Controller (Community) | 2026-03-02 |
| SiteRegisterControllerTest | Active | v63 | Test | 2026-03-02 |
| TestDataFactory | Active | v59 | Test Utility | 2024-02-26 (est.) |
| TestDataFactoryTests | Active | v59 | Test | 2024-02-26 (est.) |
| TriggerHandlerInterface | Active | v66 | Interface | 2026-03-19 (est.) |
