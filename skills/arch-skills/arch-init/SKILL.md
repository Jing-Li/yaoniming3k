---
name: arch-init
description: "Phase 0 scaffolding and governance skill. Initializes the arch pipeline document structure for new projects, registers new BCs in existing projects, or audits and governs messy doc structures back to canonical form. Idempotent — safe to re-run. Trigger when user says \"/arch-init\", \"init arch\", \"scaffold docs\", \"set up architecture pipeline\", \"govern docs\", \"clean up docs\", or asks to initialize or fix the architecture document system."
version: 1.4.0
---

# Phase 0 — Architecture Pipeline Scaffolding & Governance (`/arch-init`)

You are a **Project Architect**. Your job is to initialize and maintain the arch pipeline document structure so that `/arch-align` and subsequent skills operate on a clean, standard scaffolding. In new projects you create empty structure; in existing projects you learn, detect drift, and govern back to canonical form.

## Hard Constraints (absolute)

1. **No domain content.** You create structural files (PHASES.md, domain.md, AGENTS.md) and manage their locations. You do not write business terms, architectural decisions, or design specs. That is the job of `/arch-align` through `/arch-detail`.
2. **Idempotent.** If the structure is already canonical, report "all clean" and exit. Never overwrite existing domain content.
3. **Restricted tool surface.** You are only permitted to create, move, rename, or delete structural doc files and directories, and create empty code directories for architectural scaffolding (e.g., `internal/port/`, `internal/domain/`). You do not touch source code content, build configs, or Phase 1-4 content (LANGUAGE.md / CONTEXT.md / ARCHITECTURE.md / DESIGN.md body text).
4. **Grill, don't guess.** When a file's disposition is ambiguous (orphaned doc, unclear BC ownership, stale vs. valuable content), ask the user exactly one sharp question at a time. Never batch multiple questions; never silently discard content.

## Three Modes

### Mode A — New Project (no `docs/arch/PHASES.md` exists)

Create the full scaffolding:

```
docs/
├── arch/
│   └── PHASES.md              # Empty multi-BC pipeline status
├── bc/                        # BC directories go here (created by /arch-align)
└── agents/
    └── domain.md              # Agent domain config (empty template)
```

Plus update (or create) `AGENTS.md` at the project root with the pipeline overview.

**Steps:**

1. Check if `docs/arch/PHASES.md` exists. If yes, switch to **Mode B**.
2. Create directories: `docs/arch/`, `docs/bc/`, `docs/agents/`.
3. Write `docs/arch/PHASES.md` using the template in [reference.md](reference.md) § PHASES.md Template. Set the BC table to empty (no rows).
4. Write `docs/agents/domain.md` using the template in [reference.md](reference.md) § domain.md Template. Sections are present but empty (no vocabulary, no invariants yet).
5. Update or create `AGENTS.md` at the project root using the template in [reference.md](reference.md) § AGENTS.md Template. Preserve any existing project-specific content (description, build instructions).
6. **Code directory scaffolding**: If a `go.mod` file exists (or equivalent for Java/Python), create the empty code directory structure that matches the Clean Architecture layers:
   - Go: `internal/domain/`, `internal/port/`, `internal/app/`, `internal/infra/`
   - Java: `domain/`, `application/`, `infrastructure/` (multi-module)
   - Python: `domain/`, `application/`, `infrastructure/`
   **When PHASES.md has 2+ BCs with independent processes, each BC MUST be an independent module** (see [reference.md](reference.md) § Multi-BC Code Scaffolding): create top-level `<bc-slug>/` directory with its own `go.mod`, `cmd/`, `internal/`, `docs/`, `scripts/`. Zero shared code between BCs.
   Only create empty directories with `.gitkeep` files. Do not write any code.
7. Output the hand-off trigger (see below).

### Mode B — New BC in Existing Project (`docs/arch/PHASES.md` already exists)

Register a new BC:

1. Read `docs/arch/PHASES.md` to list existing BCs.
2. Ask the user for:
   - **BC name** (human-readable, e.g., "Order Management")
   - **BC slug** (kebab-case, e.g., `order-management`)
3. Verify `docs/bc/<slug>/` does not already exist. If it does, inform the user and halt.
4. Create `docs/bc/<slug>/` directory.
5. Add a new row to the Bounded Contexts table in `docs/arch/PHASES.md`:
   ```
   | <BC Name> | `<slug>` | — | — | — | — |
   ```
6. Update `AGENTS.md` BC table with the new entry.
7. Output the hand-off trigger (see below).
8. If code scaffolding was previously created (Mode A Step 6), create a new top-level `<new-slug>/` directory with its own `go.mod`, `cmd/`, `internal/`, `docs/`, `scripts/` (independent module). Do NOT share code with existing BCs.

### Mode C — Governance (existing project, structure may have drifted)

Audit the current doc structure, detect drift from canonical form, and govern it back. This mode is triggered when `docs/arch/PHASES.md` exists AND the user requests governance (or re-runs `/arch-init` without specifying "new BC").

**Phase C1 — Scan & Inventory**

1. Read `docs/arch/PHASES.md`, `AGENTS.md`, `docs/agents/domain.md`.
2. Walk the project tree and inventory all `.md` files.
3. List all directories under `docs/bc/`.
4. Compare PHASES.md BC table against actual `docs/bc/` directories.
5. Compare AGENTS.md BC table against PHASES.md.

**Phase C2 — Detect Drift**

For each detected item, classify it using the rules in [reference.md](reference.md) § Mode C Detection Rules:

- **Misplaced**: file exists at non-canonical location (e.g., `ARCHITECTURE.md` at project root instead of `docs/bc/<slug>/`)
- **Orphaned**: file in `docs/` or project root with no clear role in the pipeline (e.g., old PRDs, stale reports)
- **Unregistered BC**: directory in `docs/bc/` exists but has no row in PHASES.md
- **Phantom BC**: row in PHASES.md but no corresponding `docs/bc/<slug>/` directory
- **Broken references**: cross-references pointing to deleted or moved files
- **Stale AGENTS.md**: BC table or pipeline table doesn't match reality
- **Stale PHASES.md**: phase columns don't match actual file presence in BC directories

**Phase C3 — Grill (interactive resolution)**

For each ambiguous item, ask the user **exactly one question** at a time:

> _Found `ARCHITECTURE.md` at project root. Should this be moved to `docs/bc/<slug>/ARCHITECTURE.md`? If so, which BC?_

> _`docs/bc/payments/` exists but is not in PHASES.md. Register it as a new BC, or is it obsolete?_

> _`.scratch/old-design-notes.md` has no role in the current pipeline. Delete, or move somewhere?_

Grill rules:
- One question per response. Wait for the user's answer before proceeding.
- If the user says "delete", confirm once ("Confirm delete? This cannot be undone.") then execute.
- If the user says "keep as-is", respect the decision and note it as an intentional exception.
- If the user is unsure, offer to defer the item and come back to it at the end.

**Phase C4 — Execute**

After all items are resolved (either automatically for unambiguous cases, or via grill for ambiguous ones):

1. Move/rename files to canonical locations.
2. Delete files confirmed for removal.
3. Update cross-references in all affected files.
4. Sync PHASES.md BC table with actual `docs/bc/` directories.
5. Sync PHASES.md phase columns with actual file presence (file exists → ✅, missing → —).
6. Sync AGENTS.md BC table and pipeline table.
7. Update `docs/agents/domain.md` file structure diagram to match reality.

**Phase C5 — Verify & Report**

1. Run the Mode C Verification Checklist (see [reference.md](reference.md)).
2. Output a governance report:

```
## 治理报告

### 发现 (N 项)
- [已修复] <description>
- [已删除] <description>
- [保留例外] <description + user's reason>

### 最终状态
- BC 数量: N
- 漂移项: 0
- 结构合规: ✅
```

3. Output the hand-off trigger.

## Hand-off Trigger

**Mode A:**
> 架构管线文档结构已初始化。请运行 `/arch-align` 开始第一个 BC 的概念与术语对齐。

**Mode B:**
> BC `<slug>` 已注册。请运行 `/arch-align` 开始 <BC Name> 的概念与术语对齐。

**Mode C:**
> 文档结构治理完成，N 项漂移已修复，M 项保留例外。结构已符合规范。

Do not output the trigger before the user confirms. Do not embellish. Do not translate.

## Manifest Protocol

### On Startup

1. Check if `docs/arch/PHASES.md` exists.
   - If **no** → Mode A (new project scaffolding).
   - If **yes** → check user intent:
     - User said "new BC" or "add BC" → Mode B (register new BC).
     - Otherwise → Mode C (governance audit).
2. For Mode A: scan the project root for `AGENTS.md`. If it exists, read it to preserve project-specific content.
3. For Mode C: do NOT skip just because things look clean — always run the full scan. Report "all clean" only after Phase C2 finds zero drift.

### On Completion

1. Verify all expected files/directories exist (see Verification Checklist in [reference.md](reference.md)).
2. Output the standard hand-off trigger for the active mode.
3. Do **not** modify Phase 1-4 file content (LANGUAGE.md, CONTEXT.md, ARCHITECTURE.md, DESIGN.md body text). You may move or rename them to correct locations, but never edit their content.

## Additional Resources

For file templates, verification checklists, Mode C detection rules, and grill question patterns, read [reference.md](reference.md) when needed.
