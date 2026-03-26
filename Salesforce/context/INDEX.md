# Org Context Registry

This file is the master registry of all connected orgs. It is populated automatically when `/sf-init-project` or `/sf-get-existing-org-object-context` is run.

**Do not hand-edit this file.** It is written and updated by commands.

---

## Connected Orgs

| Alias | Org ID | Instance URL | Username | Last Full Scan | Last Freshness Check | Context Path |
|---|---|---|---|---|---|---|
| AwesomeOpossumDevHub | 00Dal000000VGdNEAW | https://your-org.develop.my.salesforce.com | your-sf-user@example.com | 2026-03-26T17:37:00Z | _(not yet run)_ | context/AwesomeOpossumDevHub/ |

---

## Metadata Inventory Summary

_Populated on first scan. Shows counts per metadata type per org._

| Alias | Objects | Apex Classes | Triggers | Flows | Validation Rules | PermSets | Profiles | Layouts | LWC | Aura | VF Pages |
|---|---|---|---|---|---|---|---|---|---|---|---|

---

## Object Inventory Summary

_Populated on first scan. One row per org per object._

| Alias | Object API Name | Label | Fields (count) | Last Modified in Org | In Local Files |
|---|---|---|---|---|---|

---

## Notes

- Context directories are located at `context/{alias}/`
- Scan timestamps are in UTC ISO-8601 format
- "Last Freshness Check" is when `sf-check-context-freshness` was last run (not when the org was last changed)
- A blank "Last Full Scan" means no context has been gathered yet for that alias
- Cloud-specific skills (FSL, CPQ, Experience Cloud) are skipped if not installed in the org
