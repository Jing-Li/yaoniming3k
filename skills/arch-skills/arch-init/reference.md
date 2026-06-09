# Arch-Init — Reference

Templates and verification checklist for the `arch-init` skill. Loaded only when needed (progressive disclosure from [SKILL.md](SKILL.md)).

---

## 1. PHASES.md Template

Write this to `docs/arch/PHASES.md`. Replace `<YYYY-MM-DD>` with today's date. The BC table starts **empty** (no rows).

```markdown
# Architecture Pipeline Status

> Last updated: <YYYY-MM-DD>

---

## Bounded Contexts

| BC | Slug | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
|----|------|---------|---------|---------|---------|

---

## File Locations

Each BC's outputs live in `docs/bc/<slug>/`:

| Phase | Skill | Output Files |
|-------|-------|-------------|
| 1 — Concept Alignment | `/arch-align` | `LANGUAGE.md`, `CONTEXT.md` |
| 2 — Boundary Design | `/arch-design` | `ARCHITECTURE.md` |
| 3 — Detailed Design | `/arch-detail` | `DESIGN.md`, `design/modules/` |
| 4 — Architecture Audit | `/arch-review` | Report to stdout |

---

## Reading Protocol

All file paths are relative to the target BC directory `docs/bc/<slug>/`.

- `/arch-align` reads nothing (creates Phase 1 from scratch)
- `/arch-design` requires Phase 1 ✅ → reads `LANGUAGE.md` + `CONTEXT.md`
- `/arch-detail` requires Phase 2 ✅ → reads `ARCHITECTURE.md` + `LANGUAGE.md` + `CONTEXT.md`
- `/arch-review` reads available outputs based on completed phases

## Writing Protocol

Each skill **must** update this file upon completion:

| Skill | On Startup | On Completion |
|-------|-----------|---------------|
| `/arch-align` | Read PHASES.md; if Phase 2+ exists for target BC, warn | Create `docs/bc/<slug>/` dir; write Phase 1 files; update PHASES.md |
| `/arch-design` | Read PHASES.md; verify target BC Phase 1 ✅ | Write `ARCHITECTURE.md`; update PHASES.md |
| `/arch-detail` | Read PHASES.md; verify target BC Phase 2 ✅ | Write `DESIGN.md` + `design/modules/`; update PHASES.md |
| `/arch-review` | Read PHASES.md; determine completed phases | Update Phase 4 column |

## BC Selection Protocol

When a skill is invoked without specifying a BC:

1. Read `docs/arch/PHASES.md` and list all registered BCs
2. If only one BC exists, use it automatically
3. If multiple BCs exist, ask the user which BC to target
4. For `/arch-align` (new BC): prompt for a slug name and create `docs/bc/<slug>/`
```

---

## 2. domain.md Template

Write this to `docs/agents/domain.md`. All example sections are **empty** — they get populated by later skills.

```markdown
# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- **`docs/bc/<slug>/CONTEXT.md`** — per-BC bounded context & glossary
- **`docs/arch/PHASES.md`** — pipeline status across all BCs

If any of these files don't exist, **proceed silently**. Don't flag their absence.

## File structure

Multi-BC repo:

\```
/
├── AGENTS.md                 # Agent config entry
├── docs/
│   ├── arch/
│   │   └── PHASES.md         # Pipeline status (all BCs)
│   ├── bc/                   # One directory per BC
│   └── agents/               # Agent tool config
\```

## Use the glossary's vocabulary

When your output names a domain concept, use the term as defined in the target BC's `LANGUAGE.md`. Don't drift to synonyms the glossary explicitly avoids.

_(Populated by `/arch-align` as terms are aligned.)_

## Architecture invariants

_(Populated by `/arch-align` as constraints are locked.)_
```

---

## 3. AGENTS.md Template

Write this to `AGENTS.md` at the project root. If the file already exists, **preserve** existing project-specific content (description, build commands, etc.) and **append** the sections below.

Replace `<project-description>` with the user's one-line project description.

```markdown
# AGENTS.md

<project-description>

## 文档入口

| 文档 | 路径 | 用途 |
|------|------|------|
| BC 定义 | `docs/bc/<slug>/` | 每个 BC 的领域知识（LANGUAGE / CONTEXT / ARCHITECTURE / DESIGN） |
| 管线状态 | `docs/arch/PHASES.md` | 所有 BC 的架构管线进度与 BC Selection Protocol |
| Agent 领域配置 | `docs/agents/domain.md` | 文件结构图、术语规范、架构不变量 |

## Bounded Contexts

| BC | Slug | 阶段进度 |
|----|------|---------|

_(由 `/arch-align` 和 `/arch-init` Mode B 填充)_

## 架构管线 Skills

4 阶段管线，每阶段一个 skill：

| Phase | Skill | 产出 |
|-------|-------|------|
| 0 — 管线初始化 | `/arch-init` | `docs/` 目录结构 + `PHASES.md` + `domain.md` + `AGENTS.md` |
| 1 — 概念对齐 | `/arch-align` | `LANGUAGE.md` + `CONTEXT.md` |
| 2 — 边界设计 | `/arch-design` | `ARCHITECTURE.md` |
| 3 — 详细设计 | `/arch-detail` | `DESIGN.md` + `design/modules/` |
| 4 — 架构审计 | `/arch-review` | 审计报告 (stdout) |

新项目先跑 `/arch-init` 搭建骨架，再 `/arch-align` 创建第一个 BC。已有项目中 `/arch-init` 可注册新 BC 或治理文档漂移。

## 仓库结构

\```
<project>/
├── AGENTS.md                 # 本文件
├── docs/
│   ├── arch/
│   │   └── PHASES.md
│   ├── bc/                   # BC 目录（由 /arch-align 创建）
│   └── agents/
│       └── domain.md
\```
```

---

## 4. Verification Checklist

After scaffolding, silently verify:

### Mode A (New Project)

- [ ] `docs/arch/PHASES.md` exists and contains the multi-BC table (empty rows)
- [ ] `docs/bc/` directory exists
- [ ] `docs/agents/domain.md` exists and contains the empty template
- [ ] `AGENTS.md` exists at project root with the pipeline overview sections
- [ ] No Phase 1-4 files were created (LANGUAGE.md, CONTEXT.md, ARCHITECTURE.md, DESIGN.md)

### Mode B (New BC)

- [ ] `docs/bc/<slug>/` directory exists and is empty
- [ ] `docs/arch/PHASES.md` BC table has a new row for the slug
- [ ] `AGENTS.md` BC table has a new row for the slug
- [ ] No Phase 1-4 files were created inside the new BC directory

If any check fails, report the missing item and halt. Do not create files outside the scaffolding scope.

---

## 5. Edge Cases

### `docs/` exists but `docs/arch/` does not

Some projects have a pre-existing `docs/` directory. Create `docs/arch/`, `docs/bc/`, `docs/agents/` as subdirectories without disturbing existing content in `docs/`.

### `AGENTS.md` exists with unrelated content

Read existing content, identify the project description line, and append the pipeline sections below any existing content. Do not delete or restructure existing sections.

### User provides BC name but not slug

Derive the slug from the name: lowercase, spaces → hyphens, remove special characters. Confirm with the user before creating.

Example: "Order Management" → `order-management`

### User wants to init without any BC

Mode A creates the scaffolding with an empty BC table. The user can run `/arch-align` later to create the first BC. This is the default behavior.

---

## 9. Multi-BC Code Scaffolding (Independent Module Split)

When `docs/arch/PHASES.md` registers 2+ BCs with **independent processes**, each BC MUST be a completely independent module. Zero shared code.

### Go (Multi-BC — Independent Modules)

```
<project-root>/                  # Not a Go module (no go.mod at root)

<bc-slug-a>/                     # BC-A — independent Go module
  go.mod                         # module github.com/<org>/<project>/<bc-slug-a>
  go.sum
  cmd/<entry>/                   # Entry point (main.go)
  internal/
    domain/                      # BC-A domain types
    port/<module>/               # BC-A port interfaces
    app/                         # BC-A use cases
    config/                      # BC-A config loading
    infra/<tech>/                # BC-A adapters
  docs/                          # BC-A design docs
  scripts/                       # BC-A scripts

<bc-slug-b>/                     # BC-B — independent Go module
  go.mod                         # module github.com/<org>/<project>/<bc-slug-b>
  ...
```

### Java (Multi-BC — Independent Modules)

```
<bc-slug-a>/                     # BC-A — independent Gradle/Maven module
  build.gradle
  src/main/java/
    domain/
    application/
    infrastructure/

<bc-slug-b>/                     # BC-B — independent module
  build.gradle
  ...
```

### Python (Multi-BC — Independent Modules)

```
<bc_slug_a>/                     # BC-A — independent Python package
  pyproject.toml
  domain/
  application/
  infrastructure/

<bc_slug_b>/                     # BC-B — independent package
  pyproject.toml
  ...
```

### Single-BC projects

Use flat Clean Architecture layers within the project root (single `go.mod` / `build.gradle` / `pyproject.toml`). No top-level BC directory needed.

---

## 6. Mode C — Detection Rules

During Phase C2 (Detect Drift), classify each finding using these rules:

### 6.1 Misplaced Files

A file is **misplaced** if it exists at a non-canonical location:

| File | Canonical Location | Drift Example |
|------|-------------------|---------------|
| `LANGUAGE.md` | `docs/bc/<slug>/LANGUAGE.md` | `LANGUAGE.md` at project root |
| `CONTEXT.md` | `docs/bc/<slug>/CONTEXT.md` | `CONTEXT.md` in `docs/` |
| `ARCHITECTURE.md` | `docs/bc/<slug>/ARCHITECTURE.md` | `ARCHITECTURE.md` at project root |
| `DESIGN.md` | `docs/bc/<slug>/DESIGN.md` | `DESIGN.md` in `docs/arch/` |
| `PHASES.md` | `docs/arch/PHASES.md` | `PHASES.md` at project root |
| `domain.md` | `docs/agents/domain.md` | `domain.md` at project root |
| Any ADR file | `docs/bc/<slug>/adr/` (if kept) | ADRs in flat `docs/adr/` |

### 6.2 Orphaned Files

A file is **orphaned** if it's in `docs/` or the project root and has no role in the current pipeline structure. Common examples:

- Old PRDs (`PRD.md`, `prd/*.md`) not tied to any BC
- Stale audit reports (`arch-review-*.md`) outside any BC directory
- Working notes (`.scratch/` contents) after the issue tracker was removed
- Legacy context files (`context-legacy-*.md`) superseded by `LANGUAGE.md` + `CONTEXT.md`
- Empty directories with no pipeline role

**Exception**: Files explicitly kept by user decision (recorded as "保留例外" in the governance report) are not orphaned.

### 6.3 Unregistered BC

A directory `docs/bc/<slug>/` exists but has no corresponding row in `docs/arch/PHASES.md` Bounded Contexts table. **Resolution**: Ask user whether to register or delete.

### 6.4 Phantom BC

A row in `docs/arch/PHASES.md` references a slug whose `docs/bc/<slug>/` directory does not exist. **Resolution**: Ask user whether to create the empty directory or remove the row.

### 6.5 Broken References

Cross-references (`[text](path)`) in any `.md` file under `docs/` that point to non-existent files. **Resolution**: Auto-fix if the target was moved (update to new path). Ask user if the target was deleted (remove the reference or replace with inline text).

### 6.6 Stale AGENTS.md

- BC table rows don't match `docs/arch/PHASES.md` BC table
- Pipeline skills table is missing or lists wrong phases
- File structure diagram doesn't match actual `docs/` tree

### 6.7 Stale PHASES.md

- Phase columns claim ✅ but the file doesn't exist in the BC directory
- Phase columns claim — but the file exists
- BC table rows reference slugs that don't have directories

---

## 7. Mode C — Verification Checklist

After Phase C4 (Execute), silently verify:

- [ ] Every `docs/bc/<slug>/` directory has a row in `docs/arch/PHASES.md`
- [ ] Every row in `docs/arch/PHASES.md` has a corresponding `docs/bc/<slug>/` directory
- [ ] PHASES.md phase columns match actual file presence (✅ ↔ file exists, — ↔ file absent)
- [ ] `AGENTS.md` BC table matches `docs/arch/PHASES.md` BC table
- [ ] `AGENTS.md` pipeline table lists all 5 phases (0-4)
- [ ] `docs/agents/domain.md` file structure diagram matches actual `docs/` tree
- [ ] No `.md` files exist at the project root except `AGENTS.md` and `README.md`
- [ ] No broken cross-references in any file under `docs/`
- [ ] No orphaned files remain (except recorded "保留例外" items)

If any check fails, report it in the governance report as an unresolved item.

---

## 8. Mode C — Grill Question Patterns

Use these templates when asking the user during Phase C3. One question per response.

### Misplaced file

> Found `<filename>` at `<current-path>`. The canonical location is `docs/bc/<slug>/<filename>`. Move it there? (If the BC is ambiguous, ask: "Which BC does this belong to?")

### Orphaned file

> `<filepath>` has no role in the current pipeline structure. It appears to be <brief description>. Delete it, or move it somewhere specific?

### Unregistered BC

> `docs/bc/<slug>/` exists but is not registered in PHASES.md. Register it as a new BC named "<suggested-name>", or should this directory be removed?

### Phantom BC

> PHASES.md lists BC "<name>" (`<slug>`) but `docs/bc/<slug>/` doesn't exist. Create the empty directory, or remove this row from PHASES.md?

### Broken reference

> `<source-file>` references `<broken-path>` which doesn't exist. The target appears to have been <moved to X / deleted>. Update the link / remove the reference?

### Stale phase status

> PHASES.md claims `<slug>` has Phase N ✅ but `<filename>` doesn't exist in `docs/bc/<slug>/`. Reset to —, or is the file missing and needs to be recreated?

### Keep-as-is confirmation

> You chose to keep `<filepath>` outside the standard structure. This will be recorded as a "保留例外" in the governance report. Confirm?

### Delete confirmation

> Confirm delete `<filepath>`? This cannot be undone. (Y/N)
