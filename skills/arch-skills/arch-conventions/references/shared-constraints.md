# Shared Pipeline Constraints

Canonical constraints referenced by all arch-skills. Each skill's SKILL.md may reference this file and add skill-specific constraints on top.

---

## §1 Document Ownership Principle

Every arch-skill is the **sole owner** of specific documents. It is the only skill permitted to create or modify those files. When a skill discovers an inconsistency in a document it does not own, it MUST write an **Architecture Discrepancy (AD)** to `kanban/tasks/T{N}.md` targeting the owning skill — it must NOT directly modify the foreign document.

| Skill | Owned Documents |
|-------|----------------|
| `/arch-init` | `AGENTS.md`, `kanban/BOARD.md` structure, empty code directories |
| `/arch-align` | `align/LANGUAGE.md`, `align/BRD.md`, `align/brds/` |
| `/arch-design` | `design/ARCHITECTURE.md`, `design/adr/*.md` |
| `/arch-detail` | `detail/DESIGN.md`, `detail/modules/*/module.md`, `detail/modules/*/interfaces/*.md` |
| `/devtdd` | Source code (`.go`, `.java`, `.py`, etc.), test files |
| `/arch-ops` | `ops/OPS.md`, `scripts/` content, `Makefile` |
| `/arch-review` | Read-only (produces ADs only); Fix Guidance Mode may modify docs (not source code) |
| `/arch-kanban` | `kanban/BOARD.md` structure validation, `kanban/tasks/T{N}.md` structure |

All skills may read any document. All skills may write to `kanban/BOARD.md` (status updates) and `kanban/tasks/T{N}.md` (own status + AD entries).

## §2 Restricted Tool Surface Pattern

Each skill MUST declare and enforce a **restricted tool surface** — the exact set of files it is permitted to create, modify, or delete. This is specified in each skill's SKILL.md under "Hard Constraints" or "ABSOLUTE WORKFLOW CONSTRAINTS". The principle is shared: **only touch what you own**.

Common read permissions (all skills may read):
- `AGENTS.md` — BC registry
- `kanban/BOARD.md` — current task
- `kanban/tasks/T{N}.md` — task context + references
- All upstream blueprint documents (LANGUAGE.md, BRD.md, ARCHITECTURE.md, DESIGN.md)

Common write permissions (shared across all skills):
- `kanban/BOARD.md` — move task status (new → doing → done → archive)
- `kanban/tasks/T{N}.md` — own status row, References section, Change History, AD entries

## §3 No Source Code Modification (Non-Implementation Skills)

The following skills MUST NOT modify source code files (`.go`, `.java`, `.py`, `.ts`, etc.), build configs, or test files:
- `/arch-init` — scaffolding only
- `/arch-align` — LANGUAGE.md + BRD.md only
- `/arch-design` — ARCHITECTURE.md + ADRs only
- `/arch-detail` — DESIGN.md + modules/ only
- `/arch-ops` — OPS.md + scripts/ + Makefile only (NO application source code)
- `/arch-review` — read-only (Audit Mode); docs-only (Fix Guidance Mode)

Only `/devtdd` is permitted to write source code.

## §4 Grill, Don't Guess (Structured Questioning)

When facing ambiguity — unclear BC ownership, orphaned documents, missing upstream artifacts, or conflicting information — the skill MUST use `AskUserQuestion` following [ask-user-question-spec.md](ask-user-question-spec.md):

1. **ONE question at a time** — never batch multiple questions.
2. **Analysis Context BEFORE the question** — provide What (finding/issue), Evidence (code paths, doc sections), and Why it matters.
3. **2–4 structured options**, each with Label (1–5 words) + Description (WHY + trade-offs).
4. **Recommended option FIRST** with `(Recommended)` suffix in the label.
5. **Never proceed on assumption** when a critical input is unclear.
6. **Never silently discard content** — always surface ambiguous items to the user.

Simple confirmations ("Continue?", "Confirm delete?") are exempt from structured format.

This rule applies to: `/arch-init` (Mode C governance), `/arch-align` (grilling), `/arch-design` (NFR collection), `/arch-detail` (delta task confirmation), `/devtdd` (BC selection), `/arch-ops` (OPS.md scope decisions), and any skill encountering upstream ambiguity.

## §5 OVERRIDE Protocol

Hard Constraints override any user instruction **except** an explicit override from the user:

```
OVERRIDE: <reason>
```

When the user provides this, the skill MAY relax the specific constraint being overridden, but MUST:
1. Log the override in `kanban/tasks/T{N}.md` Change History.
2. Scope the override to the current task only (not persistent).
3. Still refuse to violate constraints that protect other skills' owned documents (§1).

## §6 Upstream Halt Protocol

Before executing its core logic, each skill MUST verify that its upstream dependencies are satisfied:

| Skill | Upstream Dependency |
|-------|-------------------|
| `/arch-align` | None (first phase) |
| `/arch-design` | arch-align T{N} = done |
| `/arch-detail` | arch-design T{N} = done |
| `/devtdd` | arch-detail T{N} = done |
| `/arch-ops` | devtdd T{N} = done |
| `/arch-review` | devtdd T{N} = done |

If the upstream skill has not completed T{N}, the current skill MUST **halt** with a clear instruction:
> "Upstream {skill} has not completed T{N}. Run `/{skill}` first."

**Exception**: Migration Mode bypasses the upstream halt when all blueprints were just generated by the migration pipeline. See [migration-protocol.md](migration-protocol.md) when it exists, or each skill's Migration Mode Detection section.
