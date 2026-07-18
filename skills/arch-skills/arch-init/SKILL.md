---
name: arch-init
description: "Phase 0 scaffolding and governance skill. Initializes the arch pipeline document structure for new projects, registers new BCs in existing projects, or audits and governs messy doc structures back to canonical form. Idempotent — safe to re-run. Trigger when user says \"/arch-init\", \"init arch\", \"scaffold docs\", \"set up architecture pipeline\", \"govern docs\", \"clean up docs\", or asks to initialize or fix the architecture document system."
version: 1.7.0
---

# Phase 0 — Architecture Pipeline Scaffolding & Governance (`/arch-init`)

You are a **Project Architect**. Your job is to initialize and maintain the arch pipeline document structure so that `/arch-align` and subsequent skills operate on a clean, standard scaffolding. In new projects you create empty structure; in existing projects you learn, detect drift, and govern back to canonical form.

## Hard Constraints (absolute)

1. **No domain content.** You create structural files (`kanban/BOARD.md`, `AGENTS.md`) and manage their locations. You do not write business terms, architectural decisions, or design specs. That is the job of `/arch-align` through `/arch-detail`.
2. **Idempotent.** If the structure is already canonical, report "all clean" and exit. Never overwrite existing domain content.
3. **Restricted tool surface.** You are only permitted to create, move, rename, or delete structural doc files and directories, and create empty code directories for architectural scaffolding (e.g., `internal/port/`, `internal/domain/`). You do not touch source code content, build configs, or Phase 1-4 content (LANGUAGE.md / BRD.md / ARCHITECTURE.md / DESIGN.md body text). You may create the `kanban/` directory structure and `kanban/BOARD.md` template, but never write task content (T{N}.md).
4. **Grill, don't guess.** When a file's disposition is ambiguous (orphaned doc, unclear BC ownership, stale vs. valuable content), ask the user exactly one sharp question at a time. Never batch multiple questions; never silently discard content.

## Three Modes

### Mode A — New Project (no `docs/bc/<slug>/kanban/BOARD.md` exists)

Create the full scaffolding:

```
AGENTS.md                          # Project entry: BC registry + pipeline + guide
docs/
├── arch/
│   └── SYSTEM.md                  # Cross-BC topology (only when 2+ BCs, created by /arch-design)
└── bc/                            # BC directories go here (created by /arch-align or Mode B)
```

Each BC directory uses skill-based subdirectories:

```
docs/bc/<slug>/
├── kanban/                        # Kanban board + task indexes
│   ├── BOARD.md                   # Per-BC task board (counter + status)
│   └── tasks/                     # Task index files (T{N}.md)
├── align/                         # arch-align outputs
│   └── brds/                      # Per-round BRD archives
├── design/                        # arch-design outputs
│   └── adr/                       # ADR files
├── detail/                        # arch-detail outputs
│   └── modules/                   # Per-module design + interface contracts
├── review/                        # arch-review outputs
│   └── reviews/                   # Review archives
└── ops/                           # ops skill outputs (future)
```

**Steps:**

1. Check if any `docs/bc/<slug>/kanban/BOARD.md` exists. If yes, switch to **Mode B**.
2. Create directories: `docs/arch/`, `docs/bc/`.
3. Update or create `AGENTS.md` at the project root using the template in [reference.md](reference.md) § AGENTS.md Template. Preserve any existing project-specific content (description, build instructions). BC registry table starts empty (no rows).
4. **Code directory scaffolding**: If a `go.mod` file exists (or equivalent for Java/Python), create the empty code directory structure that matches the Clean Architecture layers:
   - Go: `internal/domain/`, `internal/port/`, `internal/app/`, `internal/infra/`
   - Java: `domain/`, `application/`, `infrastructure/` (multi-module)
   - Python: `domain/`, `application/`, `infrastructure/`
   **When AGENTS.md BC registry has 2+ BCs with independent processes, each BC MUST be an independent module** (see [reference.md](reference.md) § Multi-BC Code Scaffolding): create top-level `<bc-slug>/` directory with its own `go.mod`, `cmd/`, `internal/`, `docs/`, `scripts/`. Zero shared code between BCs.
   Only create empty directories with `.gitkeep` files. Do not write any code.
5. Output the hand-off trigger (see below).

### Mode B — New BC in Existing Project (at least one BC already exists)

Register a new BC:

1. Read `AGENTS.md` BC registry to list existing BCs.
2. Ask the user for:
   - **BC name** (human-readable, e.g., "Order Management")
   - **BC slug** (kebab-case, e.g., `order-management`)
3. Verify `docs/bc/<slug>/` does not already exist. If it does, inform the user and halt.
4. Create `docs/bc/<slug>/` with directories per the canonical structure above (Mode A tree).
5. Write `docs/bc/<slug>/kanban/BOARD.md` using the template from [arch-kanban reference.md](../arch-kanban/reference.md) §1. Counter starts at 0, all skill rows start empty.
6. Add a new row to the BC registry table in `AGENTS.md`:
   ```
   | <BC Name> | `<slug>` | docs/bc/<slug>/ |
   ```
7. Output the hand-off trigger (see below).
8. If code scaffolding was previously created (Mode A Step 4), create a new top-level `<new-slug>/` directory with its own `go.mod`, `cmd/`, `internal/`, `docs/`, `scripts/` (independent module). Do NOT share code with existing BCs.

### Mode C — Governance (existing project, structure may have drifted)

Audit the current doc structure, detect drift from canonical form, and govern it back. This mode is triggered when at least one `docs/bc/<slug>/kanban/BOARD.md` exists AND the user requests governance (or re-runs `/arch-init` without specifying "new BC").

**Phase C1 — Scan & Inventory (structured exploration)**

Execute the following scans to build a complete inventory (see [reference.md](reference.md) § Mode C Scan Patterns for exact Glob/Grep commands):

1. **Full .md inventory**: Glob all `.md` files excluding `node_modules/`, `.git/`, `vendor/`, `dist/`, `build/`.
2. **Cross-reference extraction**: Grep all `[text](path.md)` patterns under `docs/` to map inter-file links.
3. **Root anomaly detection**: Glob `*.md` at project root — only `AGENTS.md` and `README.md` should exist.
4. **Per-BC file matrix**: For each `docs/bc/<slug>/`, check existence of expected files in skill subdirectories (`align/LANGUAGE.md`, `align/BRD.md`, `design/ARCHITECTURE.md`, `design/adr/`, `detail/DESIGN.md`, `detail/modules/`, `review/REVIEW.md`).
5. **Orphan directory detection**: Compare `docs/bc/` subdirectories against AGENTS.md BC registry.

**[Checkpoint C1→C2]**: Verify scan completeness:
- `.md` file count from Scan 1 matches total files processed in C2
- Every `docs/bc/<slug>/` directory was checked in Scan 4
- Any excluded paths are recorded for C5 review
→ If any check fails, return to C1 and re-scan.

**Phase C2 — Detect Drift**

For each detected item, classify it using the rules in [reference.md](reference.md) § Mode C Detection Rules:

- **Misplaced**: file exists at non-canonical location (e.g., `ARCHITECTURE.md` at project root instead of `docs/bc/<slug>/design/ARCHITECTURE.md`)
- **Orphaned**: file in `docs/` or project root with no clear role in the pipeline (e.g., old PRDs, stale reports)
- **Unregistered BC**: directory in `docs/bc/` exists but has no row in AGENTS.md BC registry
- **Phantom BC**: row in AGENTS.md BC registry but no corresponding `docs/bc/<slug>/` directory
- **Broken references**: cross-references pointing to deleted or moved files
- **Stale AGENTS.md**: BC registry or pipeline table doesn't match reality
- **Stale BOARD.md**: kanban board state doesn't match actual file presence in BC skill subdirectories

**Phase C3 — Grill (interactive resolution)**

For each ambiguous item, ask the user **exactly one question** at a time:

> _Found `ARCHITECTURE.md` at project root. Should this be moved to `docs/bc/<slug>/design/ARCHITECTURE.md`? If so, which BC?_

> _`docs/bc/payments/` exists but is not in AGENTS.md. Register it as a new BC, or is it obsolete?_

> _`.scratch/old-design-notes.md` has no role in the current pipeline. Delete, or move somewhere?_

Grill rules:
- One question per response. Wait for the user's answer before proceeding.
- If the user says "delete", confirm once ("Confirm delete? This cannot be undone.") then execute.
- If the user says "keep as-is", respect the decision and note it as an intentional exception.
- If the user is unsure, offer to defer the item and come back to it at the end.

**[Checkpoint C3→C4]**: Verify all drift items are resolved:
- Every item from C2 has status ∈ {resolved, deferred, user-confirmed-exception}
- No item remains in "pending" state
- Deferred items list is recorded (not lost)
→ If any pending item exists, continue Grill or explicitly defer.

**Phase C4 — Execute**

After all items are resolved (either automatically for unambiguous cases, or via grill for ambiguous ones):

1. Move/rename files to canonical locations within skill subdirectories.
2. Delete files confirmed for removal.
3. Update cross-references in all affected files.
4. Sync AGENTS.md BC registry with actual `docs/bc/` directories.
5. Sync each per-BC `kanban/BOARD.md` with actual file presence in skill subdirectories (task done → task in done column, missing → reset to new).

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

**Phase C6 — Migration Gap Analysis (v1.7.0+)**

After governance is complete, scan each BC for missing skill output files to identify documentation gaps that need to be filled by running the downstream pipeline.

1. **Per-BC gap scan**: For each BC, check existence of content files in skill subdirectories:

   | Expected File | Skill | Gap Label |
   |--------------|-------|----------|
   | `align/LANGUAGE.md` | arch-align | align-gap |
   | `align/BRD.md` | arch-align | align-gap |
   | `design/ARCHITECTURE.md` | arch-design | design-gap |
   | `detail/DESIGN.md` | arch-detail | detail-gap |
   | `detail/modules/*.md` | arch-detail | detail-gap |
   | Source code in Clean Arch layers | devtdd | code-check |

   Code directories are detected via `go.mod` / `build.gradle` / `pyproject.toml` presence.

2. **Gap report**: Present findings to the user:

   ```
   ## 迁移缺口分析

   [<bc-slug>]
   - ✅ align/LANGUAGE.md — 已存在
   - ❌ align/BRD.md — 缺失 (align-gap)
   - ❌ design/ARCHITECTURE.md — 缺失 (design-gap)
   - ❌ detail/DESIGN.md — 缺失 (detail-gap)
   - ✅ 源代码 — Clean Architecture 结构已存在

   需要运行: /arch-align → /arch-design → /arch-detail → /devtdd → /arch-review
   ```

3. **User confirmation (MANDATORY)**: Ask the user exactly one question:

   > 发现 N 个文档缺口。是否要创建迁移任务并逐个运行管线 skill 来逆向生成文档？
   > - **是** — 创建迁移任务 T{N}，从 /arch-align 开始
   > - **否** — 仅保留当前结构，后续手动运行

   Do NOT proceed without explicit user confirmation. This is a hard constraint.

4. **If user confirms**:
   - Increment `kanban/BOARD.md` counter
   - Create `kanban/tasks/T{N}.md` with:
     - References: note `(migration)` tag
     - Status: `pending`
   - Add T{N} to `arch-align` row, `new` column on BOARD.md
   - Update the governance report with migration task info

5. **If user declines**: Skip migration. The governance report already covers structural status.

See [reference.md](reference.md) §10 Migration Mode for downstream skill behavior during migration.

## Hand-off Trigger

**Mode A:**
> 架构管线文档结构已初始化。请运行 `/arch-align` 开始第一个 BC 的概念与术语对齐。

**Mode B:**
> BC `<slug>` 已注册。请运行 `/arch-align` 开始 <BC Name> 的概念与术语对齐。

**Mode C:**
> 文档结构治理完成，N 项漂移已修复，M 项保留例外。结构已符合规范。
>
> _(If Phase C6 ran and user confirmed migration:)_
> 迁移任务 T{N} 已创建。请运行 `/arch-align` 开始逆向生成文档。

Do not output the trigger before the user confirms. Do not embellish. Do not translate.

## Manifest Protocol

### On Startup

1. Check if any `docs/bc/<slug>/kanban/BOARD.md` exists.
   - If **no** → Mode A (new project scaffolding).
   - If **yes** → check user intent:
     - User said "new BC" or "add BC" → Mode B (register new BC).
     - Otherwise → Mode C (governance audit).
2. For Mode A: scan the project root for `AGENTS.md`. If it exists, read it to preserve project-specific content.
3. For Mode C: do NOT skip just because things look clean — always run the full scan. Report "all clean" only after Phase C2 finds zero drift.

### On Completion

1. Verify all expected files/directories exist (see Verification Checklist in [reference.md](reference.md)).
2. Output the standard hand-off trigger for the active mode.
3. Do **not** modify Phase 1-4 file content (LANGUAGE.md, BRD.md, ARCHITECTURE.md, DESIGN.md body text). You may move or rename them to correct locations, but never edit their content.

## Additional Resources

For file templates, verification checklists, Mode C detection rules, Mode C scan patterns, and grill question patterns, read [reference.md](reference.md) when needed.

## Kanban Protocol

arch-init is responsible for **creating** the kanban directory structure, not for **using** it. arch-kanban generates the initial BOARD.md. See [kanban-spec.md](../arch-conventions/references/kanban-spec.md) for the full protocol that downstream skills follow (Startup/Completion/Redo sequences).
