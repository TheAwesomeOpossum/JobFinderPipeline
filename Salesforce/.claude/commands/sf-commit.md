---
description: "Create a Salesforce-aware git commit. Categorizes changed files by metadata type, auto-generates descriptive commit messages, and groups related files. Understands force-app/ directory structure."
argument-hint: [-m "message"]
---

# sf-commit

Create a Salesforce-aware git commit with auto-categorized metadata types and descriptive commit messages.

---

## Phase 0: Pre-Flight

### 0.1 Verify Git Repository

```bash
git rev-parse --is-inside-work-tree
```

- If the command fails (not a git repo):
  > "This directory is not a git repository. Initialize one? (yes/no)"
  - If yes: `git init`
  - If no: stop.

### 0.2 Check for Changes

```bash
git status
```

- If working tree is clean and nothing staged:
  > "Nothing to commit. Working tree clean."
  Stop.

---

## Phase 1: Analyze Changes

### 1.1 Gather Changed Files

Run `git status` to collect all modified, untracked, and deleted files.

Separate into three lists:
- **Staged** (already in index)
- **Modified** (tracked but unstaged)
- **Untracked** (new files not yet tracked)

### 1.2 Categorize by Salesforce Metadata Type

Map each file path to a metadata category using these patterns:

| Path Pattern | Category |
|---|---|
| `force-app/**/objects/**/*.object-meta.xml` | Custom Objects |
| `force-app/**/objects/**/fields/*.field-meta.xml` | Custom Fields |
| `force-app/**/objects/**/validationRules/*` | Validation Rules |
| `force-app/**/objects/**/recordTypes/*` | Record Types |
| `force-app/**/objects/**/listViews/*` | List Views |
| `force-app/**/objects/**/compactLayouts/*` | Compact Layouts |
| `force-app/**/classes/*.cls` | Apex Classes |
| `force-app/**/classes/*.cls-meta.xml` | Apex Classes (meta) |
| `force-app/**/triggers/*.trigger` | Apex Triggers |
| `force-app/**/triggers/*.trigger-meta.xml` | Apex Triggers (meta) |
| `force-app/**/profiles/*` | Profiles |
| `force-app/**/permissionsets/*` | Permission Sets |
| `force-app/**/layouts/*` | Layouts |
| `force-app/**/flexipages/*` | FlexiPages |
| `force-app/**/lwc/**` | LWC Components |
| `force-app/**/aura/**` | Aura Components |
| `force-app/**/flows/*` | Flows |
| `force-app/**/sharingRules/*` | Sharing Rules |
| `force-app/**/tabs/*` | Custom Tabs |
| `force-app/**/applications/*` | Custom Applications |
| `force-app/**/staticresources/*` | Static Resources |
| `force-app/**/customMetadata/*` | Custom Metadata |
| `force-app/**/labels/*` | Custom Labels |
| `context/**` | Context Cache |
| `projects/**` | Requirements & Implementation Plans |
| Other | Uncategorized |

### 1.3 Group Related Files

Combine companion files into single logical units:
- `.cls` + `.cls-meta.xml` = one Apex Class
- `.trigger` + `.trigger-meta.xml` = one Apex Trigger
- LWC bundle files (`*.html`, `*.js`, `*.css`, `*.js-meta.xml`) = one LWC Component
- Aura bundle files = one Aura Component

Count unique logical units per category, not raw file count.

### 1.4 Build Category Summary

For each category with changes, list:
- Number of logical units
- API names of changed items (extracted from file paths)

---

## Phase 2: Generate Commit Message

### 2.1 Check for User-Provided Message

If `$ARGUMENTS` contains `-m "..."` or `-m '...'`:
- Use the provided message as the commit subject line.
- Still append the metadata summary as the commit body.

### 2.2 Auto-Generate Message

If no message provided, generate one automatically.

**Select tag** based on the primary change category:

| Condition | Tag |
|---|---|
| New custom objects or fields present | `feat` |
| New triggers, flows, or Apex classes (new feature logic) | `feat` |
| Changes to existing Apex (bug fixes, updates) | `fix` |
| Profile or permission set changes only | `security` |
| Layout or FlexiPage changes only | `ui` |
| Context cache updates only | `chore` |
| Requirements or plans only | `docs` |
| Mixed categories | Use tag for the most significant change |

**Detect phase context:**
Check if the commit is being made during a PIV loop phase by looking for:
- Recently modified `projects/**/master-plan.md` files
- Phase plan file referenced in recent sf-execute output
If a phase context is detected, include the phase in the commit message.

**Generate subject line:**
```
{tag}({phase-scope}): {concise description of primary change}
```

If no phase context: omit the scope parenthetical.

Examples:
- `feat(phase-1): add Equipment__c object with 12 custom fields`
- `security(phase-2): update Admin profile for Work_Order__c permissions`
- `feat(phase-3): add WorkOrderTrigger with status validation processor`
- `ui(phase-4): update Work_Order__c layout with scheduling section`
- `chore: update context cache after equipment deployment`
- `feat: add Equipment__c object with 12 custom fields` (no phase context)

**Generate body:**
```
Metadata:
- Custom Objects: Equipment__c, Work_Order__c
- Custom Fields: Equipment__c.Serial_Number__c, Equipment__c.Status__c
- Apex Classes: WorkOrderTriggerHandler, StatusValidationProcessor
- Profiles: Admin
```

### 2.3 Compose Full Commit Message

```
{tag}: {subject line}

Metadata:
- {Category}: {item list}
- {Category}: {item list}
...
```

---

## Phase 3: Stage and Commit

### 3.1 Present Proposed Commit

Display the full proposal for user review:

```
Proposed commit:

  {full commit message}

Files ({N} total, {M} logical units):
  Custom Objects: {list}
  Custom Fields: {list}
  Apex Classes: {list}
  Profiles: {list}
  ...

Proceed? (yes / edit message / select files / cancel)
```

### 3.2 Handle User Response

- **yes**: proceed to staging and commit.
- **edit message**: ask user for new message, then re-display proposal.
- **select files**: show numbered file list, let user pick which to include, then re-display proposal.
- **cancel**: stop without committing.

### 3.3 Stage Files

Stage specific files by name. Never use `git add .` or `git add -A`.

```bash
git add {file1} {file2} {file3} ...
```

**Never stage these files/directories:**
- `.env`
- `.env.*`
- `credentials.json`
- `*.key`
- `*.pem`
- `.sf/`
- `.sfdx/`
- `node_modules/`

**Always stage these files (if changed):**
- `context/**` files (intended to be version-controlled and shared)
- `force-app/**` files (Salesforce metadata)
- `projects/**` files (requirements docs and implementation plans)

If any file in the staging list matches a "never stage" pattern, warn the user:
> "Skipping {filename} — matches sensitive file pattern. Stage it manually if intended."

### 3.4 Create Commit

```bash
git commit -m "{full commit message}"
```

### 3.5 Confirm

```bash
git log --oneline -1
```

Display the result to confirm the commit was created.

---

## Phase 4: Post-Commit

### 4.1 Report

> "Committed {N} files across {M} metadata categories."

List the categories and counts:
```
  Custom Objects: 2
  Custom Fields: 12
  Apex Classes: 4
  Profiles: 1
  Total: 19 files
```

### 4.2 Offer Push

Check if a remote is configured and the branch tracks an upstream:

```bash
git remote -v
git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null
```

- If remote exists and branch tracks upstream:
  > "Push to remote? (yes/no)"
  - If yes: `git push`
  - If no: skip.
- If no remote configured: do nothing (no prompt).

---

## Notes

- This command replaces generic `/commit` with Salesforce-specific metadata awareness.
- Never stages sensitive files — warns the user if they appear in the changeset.
- Groups companion files (`.cls` + `.cls-meta.xml`) so commit messages reflect logical units, not raw file counts.
- Always asks for user confirmation before committing — no auto-commits.
- Context cache files are always eligible for staging since they are designed to be shared.
- If the user provides `-m "message"`, the metadata summary is still appended as the commit body for traceability.
