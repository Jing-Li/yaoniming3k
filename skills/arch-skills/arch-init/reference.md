# Arch-Init — Reference

Templates and verification checklist for the `arch-init` skill. Loaded only when needed (progressive disclosure from [SKILL.md](SKILL.md)).

---

## 1. BOARD.md Template

Write this to `docs/bc/<slug>/kanban/BOARD.md`. Replace `<bc-slug>` with the actual slug.

```markdown
# <bc-slug> — Kanban

## Counter
next_task_id: 0

## Board

| Skill | new | doing | done |
|-------|-----|-------|------|
| arch-align | | | |
| arch-design | | | |
| arch-detail | | | |
| devtdd | | | |
| arch-review | | | |
```

### Board Rules

- **Three states**: `new` → `doing` → `done` (left to right)
- **Each cell** contains comma-separated task IDs (e.g., `T1, T2`)
- **Empty cell** = no tasks in that state for that skill
- **Counter** starts at `0`; incremented each time a new task is created by arch-align
- **See [kanban-spec.md](../arch-conventions/references/kanban-spec.md)** for the full interaction protocol

---

## File Locations

Each BC's outputs live in skill-based subdirectories under `docs/bc/<slug>/`:

| Phase | Skill | Skill Directory | Output Files |
|-------|-------|-----------------|-------------|
| 1 — Concept Alignment | `/arch-align` | `align/` | `LANGUAGE.md`, `BRD.md` |
| 2 — Boundary Design | `/arch-design` | `design/` | `ARCHITECTURE.md` + `adr/*.md` + `docs/arch/SYSTEM.md` (when 2+ BCs) |
| 3 — Detailed Design | `/arch-detail` | `detail/` | `DESIGN.md`, `modules/` |
| 4a — Implementation | `/devtdd` | (source code) | source code + test files; updates `detail/DESIGN.md` task status |
| 4b — Architecture Audit | `/arch-review` | `review/` | `REVIEW.md` (current) + `reviews/` (active archives) + `reviews/done/` (closed archives) |

---

## Reading Protocol

All file paths are relative to the target BC directory `docs/bc/<slug>/`.

- `/arch-align` reads nothing (creates tasks from scratch)
- `/arch-design` reads `kanban/BOARD.md` → finds own task → reads `kanban/tasks/T{N}.md` → follows References to `align/LANGUAGE.md` + `align/BRD.md`
- `/arch-detail` reads `kanban/BOARD.md` → reads `kanban/tasks/T{N}.md` → follows References to upstream files
- `/devtdd` reads `kanban/BOARD.md` → reads `kanban/tasks/T{N}.md` → follows References to upstream files
- `/arch-review` reads `kanban/BOARD.md` → reads `kanban/tasks/T{N}.md` → follows References to all completed outputs
- **Upstream HALT rule**: If a skill finds its upstream is NOT `done` for T{N}, it MUST halt and instruct the user to complete the upstream skill first.

## Writing Protocol

Each skill **must** update `kanban/BOARD.md` and `kanban/tasks/T{N}.md` per the [kanban-spec.md](../arch-conventions/references/kanban-spec.md) protocol:

| Skill | On Completion |
|-------|---------------|
| `/arch-align` | Write `align/LANGUAGE.md` + `align/BRD.md`; update `kanban/tasks/T{N}.md` References; move T{N} to `done` in BOARD.md |
| `/arch-design` | Write `design/ARCHITECTURE.md` + `design/adr/*.md`; update `kanban/tasks/T{N}.md`; move T{N} to `done` |
| `/arch-detail` | Write `detail/DESIGN.md` + `detail/modules/`; update `kanban/tasks/T{N}.md`; move T{N} to `done` |
| `/devtdd` | Write source code + tests; update `kanban/tasks/T{N}.md`; move T{N} to `done` |
| `/arch-review` | Write `review/REVIEW.md`; update `kanban/tasks/T{N}.md`; move T{N} to `done` |

## BC Selection Protocol

When a skill is invoked without specifying a BC:

1. Read `AGENTS.md` BC registry and list all registered BCs
2. If only one BC exists, use it automatically
3. If multiple BCs exist, ask the user which BC to target
4. For `/arch-align` (new BC): prompt for a slug name and create `docs/bc/<slug>/` with skill subdirectories

---

## 2. AGENTS.md Template

Write this to `AGENTS.md` at the project root. If the file already exists, **preserve** existing project-specific content (description, build commands, etc.) and **append** the BC Registry section below.

Replace `<project-description>` with the user's one-line project description.

```markdown
# AGENTS.md

<project-description>

## BC Registry

| BC | Slug | Docs Directory |
|----|------|---------------|

_(Populated by `/arch-init` Mode B and `/arch-align`)_
```

---

## 3. Verification Checklist

After scaffolding, silently verify:

### Mode A (New Project)

- [ ] `docs/bc/` directory exists
- [ ] `AGENTS.md` exists at project root with BC Registry (empty)
- [ ] No per-BC `kanban/BOARD.md` files exist yet (BCs are created by `/arch-align` or Mode B)

### Mode B (New BC)

- [ ] `docs/bc/<slug>/` directory exists with all directories from the canonical structure (see SKILL.md Mode A tree)
- [ ] `docs/bc/<slug>/kanban/BOARD.md` exists with counter=0 and all skill rows empty
- [ ] `AGENTS.md` BC Registry has a new row for the slug
- [ ] No task files (T{N}.md) or Phase 1-4 content files were created inside the new BC

If any check fails, report the missing item and halt. Do not create files outside the scaffolding scope.

---

## 4. Edge Cases

### `docs/` exists but `docs/bc/` does not

Some projects have a pre-existing `docs/` directory. Create `docs/arch/` and `docs/bc/` as subdirectories without disturbing existing content in `docs/`.

### `AGENTS.md` exists with unrelated content

Read existing content, identify the project description line, and append the BC Registry section below any existing content. Do not delete or restructure existing sections.

### User provides BC name but not slug

Derive the slug from the name: lowercase, spaces → hyphens, remove special characters. Confirm with the user before creating.

Example: "Order Management" → `order-management`

### User wants to init without any BC

Mode A creates the scaffolding with an empty BC Registry. The user can run `/arch-align` later to create the first BC. This is the default behavior.

---

## 5. Multi-BC Code Scaffolding (Independent Module Split)

When `AGENTS.md` BC Registry lists 2+ BCs with **independent processes**, each BC MUST be a completely independent module. Zero shared code.

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
| `LANGUAGE.md` | `docs/bc/<slug>/align/LANGUAGE.md` | `LANGUAGE.md` at project root or `docs/bc/<slug>/LANGUAGE.md` (missing skill dir) |
| `BRD.md` | `docs/bc/<slug>/align/BRD.md` | `BRD.md` in `docs/` |
| `ARCHITECTURE.md` | `docs/bc/<slug>/design/ARCHITECTURE.md` | `ARCHITECTURE.md` at project root |
| `DESIGN.md` | `docs/bc/<slug>/detail/DESIGN.md` | `DESIGN.md` in `docs/arch/` |
| `BOARD.md` | `docs/bc/<slug>/kanban/BOARD.md` | `BOARD.md` at project root, `docs/bc/<slug>/BOARD.md` (missing kanban/ dir), or `docs/arch/PHASES.md` (legacy) |
| `REVIEW.md` | `docs/bc/<slug>/review/REVIEW.md` | `REVIEW.md` at BC root |
| Any ADR file | `docs/bc/<slug>/design/adr/` | ADRs in flat `docs/adr/` or `docs/bc/<slug>/adr/` (missing design/ parent) |

### 6.2 Orphaned Files

A file is **orphaned** if it's in `docs/` or the project root and has no role in the current pipeline structure. Common examples:

- Old PRDs (`PRD.md`, `prd/*.md`) not tied to any BC
- Stale audit reports (`arch-review-*.md`) outside any BC directory
- Working notes (`.scratch/` contents) after the issue tracker was removed
- Legacy context files (`context-legacy-*.md`) superseded by `align/LANGUAGE.md` + `align/BRD.md`
- Old `docs/agents/domain.md` (content merged into AGENTS.md)
- Empty directories with no pipeline role

**Exception**: Files explicitly kept by user decision (recorded as "保留例外" in the governance report) are not orphaned.

### 6.3 Unregistered BC

A directory `docs/bc/<slug>/` exists but has no corresponding row in `AGENTS.md` BC Registry. **Resolution**: Ask user whether to register or delete.

### 6.4 Phantom BC

A row in `AGENTS.md` BC Registry references a slug whose `docs/bc/<slug>/` directory does not exist. **Resolution**: Ask user whether to create the empty directory or remove the row.

### 6.5 Broken References

Cross-references (`[text](path)`) in any `.md` file under `docs/` that point to non-existent files. **Resolution**: Auto-fix if the target was moved (update to new path). Ask user if the target was deleted (remove the reference or replace with inline text).

### 6.6 Stale AGENTS.md

- BC Registry rows don't match actual `docs/bc/` directories

### 6.7 Stale BOARD.md (per-BC)

- Board claims T{N} is `done` at a skill but the corresponding output file doesn't exist
- Board has no entry for a skill that clearly has output files
- `kanban/tasks/` directory is missing or has orphaned T{N}.md files not reflected in the board

---

## 7. Mode C — Verification Checklist

After Phase C4 (Execute), silently verify:

- [ ] Every `docs/bc/<slug>/` directory has a row in `AGENTS.md` BC Registry
- [ ] Every row in `AGENTS.md` BC Registry has a corresponding `docs/bc/<slug>/` directory
- [ ] Each per-BC `kanban/BOARD.md` state is consistent with actual skill output files and `kanban/tasks/T{N}.md` files
- [ ] Every BC has correctly named skill subdirectories: `align/`, `design/`, `detail/`, `review/`
- [ ] No `.md` files exist at the project root except `AGENTS.md` and `README.md`
- [ ] No `docs/agents/` directory exists (removed in v1.5.0)
- [ ] No legacy `docs/arch/PHASES.md` exists (replaced by per-BC kanban in v1.6.0)
- [ ] No broken cross-references in any file under `docs/`
- [ ] No orphaned files remain (except recorded "保留例外" items)

If any check fails, report it in the governance report as an unresolved item.

---

## 8. Mode C — Grill Question Patterns

Use these templates when asking the user during Phase C3. One question per response.

### Misplaced file

> Found `<filename>` at `<current-path>`. The canonical location is `docs/bc/<slug>/<skill-dir>/<filename>`. Move it there? (If the BC is ambiguous, ask: "Which BC does this belong to?")

### Orphaned file

> `<filepath>` has no role in the current pipeline structure. It appears to be <brief description>. Delete it, or move it somewhere specific?

### Unregistered BC

> `docs/bc/<slug>/` exists but is not registered in AGENTS.md. Register it as a new BC named "<suggested-name>", or should this directory be removed?

### Phantom BC

> AGENTS.md lists BC "<name>" (`<slug>`) but `docs/bc/<slug>/` doesn't exist. Create the empty directory, or remove this row from AGENTS.md?

### Broken reference

> `<source-file>` references `<broken-path>` which doesn't exist. The target appears to have been <moved to X / deleted>. Update the link / remove the reference?

### Stale phase status

> BOARD.md claims T{N} is `done` at `<skill>` but `<filename>` doesn't exist in `docs/bc/<slug>/<skill-dir>/`. Reset to `new`, or is the file missing and needs to be recreated?

### Keep-as-is confirmation

> You chose to keep `<filepath>` outside the standard structure. This will be recorded as a "保留例外" in the governance report. Confirm?

### Delete confirmation

> Confirm delete `<filepath>`? This cannot be undone. (Y/N)

---

## 9. Mode C — Scan Patterns

During Phase C1 (Scan & Inventory), execute these targeted scans instead of open-ended tree walking:

### Scan 1: Full .md file inventory

```
Glob('**/*.md', exclude=[
  'node_modules/**', '.git/**', 'vendor/**',
  'dist/**', 'build/**', '.next/**', '.qoder/**'
])
```

→ Produces: complete path list of all `.md` files. Count this total for Checkpoint C1→C2.

### Scan 2: Cross-reference extraction

```
Grep('\[.*?\]\(.*?\.md\)', path='docs/', include='*.md')
```

→ Produces: all inter-file links as source→target pairs. Used by C2 to detect broken references (§6.5).

### Scan 3: Root anomaly detection

```
Glob('*.md')   # project root only
```

→ Expected results: `AGENTS.md`, `README.md` only. Any other `.md` at root is a drift candidate.

### Scan 4: Per-BC file matrix

For each `docs/bc/<slug>/` directory, check existence of:

| Expected Path | Phase |
|---------------|-------|
| `kanban/BOARD.md` | metadata |
| `align/LANGUAGE.md` | 1 |
| `align/BRD.md` | 1 |
| `align/brds/` | 1 |
| `design/ARCHITECTURE.md` | 2 |
| `design/adr/` | 2 |
| `detail/DESIGN.md` | 3 |
| `detail/modules/` | 3 |
| `review/REVIEW.md` | 4b |
| `review/reviews/` | 4b |

→ Produces: per-BC existence matrix. Used by C2 to detect stale BOARD.md (§6.7) and missing skill directories.

### Scan 5: Orphan directory detection

```
Glob('docs/bc/*/')   # list all BC directories
```

Compare against AGENTS.md BC Registry rows. Any directory without a registry row = Unregistered BC (§6.3). Any registry row without a directory = Phantom BC (§6.4).

### Scan 6: Legacy artifact detection (v1.5.0 migration)

```
Grep('docs/arch/PHASES\.md', include='*.md')   # legacy global PHASES.md references
Grep('PHASES\.md', include='*.md')              # legacy PHASES.md references (replaced by kanban/BOARD.md in v1.6.0)
Glob('docs/agents/**')                          # old domain.md and agents directory
```

→ Detects remnants of pre-v1.5.0 structure that need migration or removal.

---

## 10. Migration Mode (v1.7.0+)

When a legacy project has existing source code but empty or partial skill documentation directories, the downstream skills (arch-align through arch-review) must support **Migration Mode** — reverse-engineering documentation from the existing codebase.

### 10.1 Migration Detection (per skill)

Each downstream skill detects migration mode at startup:

```
IF own output directory is empty (no content files)
AND source code directories exist (internal/, domain/, cmd/, etc.)
AND T{N}.md has `(migration)` tag in References
THEN → enter Migration Mode
```

### 10.2 Migration Mode Behavior (per skill)

| Skill | Normal Mode | Migration Mode |
|-------|------------|----------------|
| **arch-align** | Interactive grilling with user | Read source code → extract terminology, domain concepts, business rules → generate LANGUAGE.md + BRD.md. Ask user to confirm accuracy. |
| **arch-design** | Design from BRD | Read source code + align docs → reverse-engineer architecture (layers, ports, adapters, dependencies) → generate ARCHITECTURE.md |
| **arch-detail** | Design from ARCHITECTURE | Read source code + ARCHITECTURE.md → reverse-engineer modules, interfaces, contracts → generate DESIGN.md + modules/ + interfaces/ |
| **devtdd** | TDD implement tasks | Read source code + DESIGN.md → mark implemented sub-tasks as ✅, write missing tests only → update DoD |
| **arch-review** | Audit against blueprints | Normal audit — all blueprints now exist. No special behavior needed. |

### 10.3 Migration Task Flow

The migration task T{N} flows through the pipeline like any normal task:

```
init creates T1 → align/new
align runs → generates LANGUAGE.md + BRD.md → T1 to align/done, add to design/new
design runs → generates ARCHITECTURE.md → T1 to design/done, add to detail/new
detail runs → generates DESIGN.md + modules/ → T1 to detail/done, add to devtdd/new
devtdd runs → writes missing tests → T1 to devtdd/done, add to review/new
review runs → audits code vs docs → T1 to review/done → archive check
```

### 10.4 Key Differences from Normal Flow

1. **No halt on empty upstream docs**: In migration mode, skills don't halt when their own output is empty — they generate it from code.
2. **User confirmation at each stage**: Each skill presents its generated docs to the user for verification before marking done.
3. **Partial gaps**: If some docs exist (e.g., LANGUAGE.md exists but BRD.md doesn't), the skill only generates the missing ones.
4. **Task chaining**: When a skill completes T{N} in migration mode, it MUST also add T{N} to the next skill's `new` column on BOARD.md (not just mark itself done).

### 10.5 Migration T{N}.md Template

```markdown
# T{N} — Migration: Reverse-engineer documentation from existing codebase

## References
- Source: `(migration)` — reverse-engineering from existing code
- align: (to be generated)
- design: (to be generated)
- detail: (to be generated)

## Status
pending

## Change History
- T{N} created by /arch-init Mode C Phase C6 (migration)
```
