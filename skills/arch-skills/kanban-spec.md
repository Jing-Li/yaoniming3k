# Kanban Spec (看板协议)

> Version: 2.0.0
> Scope: Per-BC, referenced by all arch-skills
> This document defines the protocol. Each BC has a `BOARD.md` as its runtime instance.

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│              docs/bc/<slug>/kanban/BOARD.md              │
│           next_task_id: N  (Counter owner)               │
│                                                         │
│  ┌──────────┬──────────┬──────────┬──────────┐         │
│  │ Skill    │ new      │ doing    │ done     │         │
│  ├──────────┼──────────┼──────────┼──────────┤         │
│  │ align    │ T3       │          │          │         │
│  │ design   │          │ T2       │          │         │
│  │ detail   │ T1       │          │          │         │
│  │ devtdd   │          │          │          │         │
│  │ review   │          │          │          │         │
│  └──────────┴──────────┴──────────┴──────────┘         │
│                                                         │
│  (Each T appears in exactly ONE cell on the board)       │
│                                                         │
│  ┌─────────────────────────────────────────────┐       │
│  │ Archive                                      │       │
│  │ T0 — completed 2025-01-10                    │       │
│  └─────────────────────────────────────────────┘       │
└───────────────────────────┬─────────────────────────────┘
                            │ references
                            ▼
┌─────────────────────────────────────────────────────────┐
│              docs/bc/<slug>/kanban/tasks/                │
│                                                         │
│  T1.md ──→ References: align/BRD.md,                │
│                        design/ARCHITECTURE.md,           │
│                        detail/modules/order/             │
│                                                         │
│  T2.md ──→ References: ...                               │
│  T3.md ──→ References: (empty, not started)             │
└─────────────────────────────────────────────────────────┘
                            │ reads via References
                            ▼
┌─────────────────────────────────────────────────────────┐
│              BC-Level Documents (Aggregations)           │
│                                                         │
│  align/LANGUAGE.md    ← all tasks' terms                │
│  align/BRD.md     ← all tasks' business overview    │
│  design/ARCHITECTURE.md ← all tasks' architecture       │
│  detail/DESIGN.md     ← all tasks' detailed design      │
│  detail/modules/**    ← task-specific modules           │
└─────────────────────────────────────────────────────────┘
```

---

## 2. BOARD.md — Runtime Instance (运行时实例)

Each BC has exactly one BOARD.md at `docs/bc/<slug>/kanban/BOARD.md`.

### Structure

```markdown
# Kanban — <BC Name>

## Counter
next_task_id: 4

## Board

| Skill | new | doing | done |
|-------|-----|-------|------|
| arch-align | T3 | | |
| arch-design | | T2 | |
| arch-detail | T1 | | |
| devtdd | | | |
| arch-review | | | |

## Archive

| Task | Completed |
|------|----------|
| T0   | 2025-01-10 |
```

### Counter Rules

- `next_task_id` starts at `0` (set by arch-init)
- Incremented by 1 each time a new task is created
- Each BC's `BOARD.md` owns its own `next_task_id` counter (set to `0` by arch-init)
- Counter only goes up — never decremented or reused

### Board Rules

- **Single position**: each T number appears in exactly ONE cell across the entire Board table
- **Three states**: `new` → `doing` → `done`
- **Left-to-right flow**: tasks enter at `new`, move to `doing`, then `done`
- **Handover removal**: when a downstream skill picks up T, remove T from the upstream skill's `done` column. T moves directly to the downstream skill's `doing` column
- **Archive**: when ALL skills in T{N}.md Status are `done` AND no unresolved Architecture Discrepancy entries exist in T{N}.md → move T{N} to the Archive table and remove from the Board table entirely
- **AD does not affect Board**: Architecture Discrepancies are tracked in T{N}.md only; they do NOT change BOARD.md positions
- **Sequential processing**: each skill processes one task at a time in `doing`
- **Multiple tasks in same cell**: comma-separated (e.g., `T1, T2`)
- **Empty cell**: no tasks in that state for that skill

### Archive Rules

- Archive table has two columns: `Task` and `Completed`
- Tasks in Archive are implicitly all-done; no per-skill status needed
- `Completed` date = the date the last skill marked `done`
- Once archived, a task never reappears on the Board table
- **Archive with unresolved ADs**: a task is NOT archived if any unresolved Architecture Discrepancy entries exist in T{N}.md, even if all skills are `done`. Skills must fix their ADs first, then re-trigger archive

### Initialization (by arch-init)

```markdown
# Kanban — <BC Name>

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

## Archive

| Task | Completed |
|------|----------|
```

---

## 3. T{N}.md — Task Index File (任务索引)

### Location

`docs/bc/<slug>/kanban/tasks/T{N}.md`

### Structure

```markdown
# T{N} — <Task Name>

## Description

One-line description of what this task delivers.

**Created by**: arch-align
**Created at**: YYYY-MM-DD

## References

### arch-align
- [BRD.md](../align/BRD.md) — §2 Scope (Order)
- [LANGUAGE.md](../align/LANGUAGE.md) — Order, OrderItem, Money
- [brd-t0](../align/brds/brd-t0.md) — This task's BRD snapshot at creation

### arch-design
- [ARCHITECTURE.md](../design/ARCHITECTURE.md) — §0 Overview, §1.2 Ports
- [ADR-003](../design/adr/003-postgres-storage.md)

### arch-detail
- (not started)

### devtdd
- (not started)

### arch-review
- (not started)

## Status

| Skill | Status | Started | Completed |
|-------|--------|---------|----------|
| arch-align | done | 2025-01-15 | 2025-01-15 |
| arch-design | done | 2025-01-16 | 2025-01-16 |
| arch-detail | doing | 2025-02-01 | — |
| devtdd | new | — | — |
| arch-review | new | — | — |

## Architecture Discrepancies

### arch-align
- [x] AD-A1: BRD §2 missing cancel-order scope (by arch-detail, 2025-02-01) (Resolved by arch-align, 2025-02-02)

### arch-design
(empty)

### arch-detail
(empty)

### devtdd
(empty)

### arch-review
(empty)

## Change History

| Date | Skill | Change |
|------|-------|--------|
| 2025-02-01 | arch-detail | Started module design |
| 2025-01-16 | arch-design | Added 2 ports (OrderRepository, EventPublisher), PostgreSQL + RocketMQ |
| 2025-01-15 | arch-align | Initial — Order scope, 3 terms, 2 invariants |
```

### Architecture Discrepancies (AD) Rules

- **Placement**: AD entries go under the **target skill's** section (the skill responsible for fixing), NOT the discoverer's
- **Format**: `- [ ] AD-{ID}: <description> (by <discoverer>, <date>)`
- **Resolution**: when resolved, mark `[x]` and append `(Resolved by <resolver>, <date>)`
- **ID format**: `AD-{TargetInitial}{N}` (e.g., AD-A1 for arch-align, AD-D1 for arch-design)
- **Does not affect Board**: AD entries are tracked here only; BOARD.md positions remain unchanged

### Rules

- **Index only** — contains references, status, ADs, and metadata, not business content
- **Each skill updates**: its own References section, Status row, AD section, and appends to Change History
- **Change History is append-only** — new entries at the top (reverse chronological)

---

## 4. Skill Interaction Protocol (交互协议)

### 4.1 Common Startup Sequence

Every skill follows this exact sequence:

```
1. Read docs/bc/<slug>/kanban/BOARD.md
2. Find own row in Board
3. If doing column has a task → use it (continue current work or AD fix)
4. If doing is empty → pick leftmost from new column
5. If new is also empty → check archived T{N}.md files for unresolved ADs targeting this skill:
   - If found → add T{N} back to own `doing` column, enter AD fix mode (skip to step 9)
   - If not found → halt: "No tasks available. Ask upstream to create tasks."
6. Read kanban/tasks/T{N}.md
7. AD Check: scan Architecture Discrepancies → own section
   - If unresolved AD entries exist for this skill → enter AD fix mode (skip to step 9)
   - If no AD → continue normal startup
8. Check upstream: find the skill directly above in pipeline
   - If upstream's status for T{N} is NOT done → halt: "Upstream <skill> has not completed T{N}."
   - If upstream is done → proceed
9. Handover removal: if T{N} exists in upstream's `done` column on BOARD.md → remove it
10. Read upstream files via T{N}.md References
11. Idempotent check (if status was already doing/done):
    - Read own existing output files
    - Read AD entries for this skill
    - Identify delta: what's new vs what's already done
    - Skip completed work; only execute what's missing or needs fixing
12. Move T{N} from new to doing in BOARD.md (if not already doing)
13. Update T{N}.md Status: set Started date
```

### 4.2 Common Completion Sequence

```
1. Write own output files (per skill's responsibility)
2. Update kanban/tasks/T{N}.md:
   a. Fill in own References section with file links
   b. Set Status row: done + Completed date
   c. Mark any AD entries targeting this skill as Resolved (if not already)
   d. Append Change History entry at top
3. Move T{N} from doing to done in BOARD.md
4. Archive check: if ALL skills in T{N}.md Status are done AND no unresolved Architecture Discrepancy entries exist in T{N}.md →
   a. Add T{N} to BOARD.md Archive table with today's date
   b. Remove T{N} from all rows in BOARD.md Board table
5. If this skill can create tasks (e.g., arch-align):
   - Check if new tasks are needed → create T{N+1}
6. Output hand-off message:
   > "T{N} completed at <skill>.
   >  Change: <summary>
   >  Next: kanban/tasks/T{N}.md → <downstream skill> References"
   >  If AD entries exist: "Pending ADs: <list>"
```

### 4.3 Task Creation Protocol

Only specific skills can create new tasks (typically arch-align):

```
1. Read `kanban/BOARD.md` → get `next_task_id` (e.g., 3)
2. Increment `kanban/BOARD.md` `next_task_id` to 4
3. Create docs/bc/<slug>/kanban/tasks/T3.md with initial structure
4. Update BOARD.md: add T3 to own `new` column
5. Set T3.md Status: own row = new
```

### 4.4 AD-Driven Redo Protocol (AD 驱动的纠偏)

When a downstream skill discovers upstream issues, it writes AD entries in T{N}.md targeting the responsible skill. The targeted skill fixes them on its next run:

```
Discovery (by downstream skill, e.g., arch-detail):
1. Write AD entry in T{N}.md → Architecture Discrepancies → target skill's section
   Format: - [ ] AD-{ID}: <description> (by <discoverer>, <date>)
2. Include AD summary in hand-off message
   > "T{N} completed at <skill>.
   >  Pending ADs: AD-A1 (→ arch-align), AD-D1 (→ arch-design)"

Fix (by targeted skill, e.g., arch-align):
3. On next startup, detect unresolved AD in own section (Step 7 of Startup)
4. Read Change History → understand what was done before
5. Read own existing output files → understand current state
6. Read AD description → understand what needs fixing
7. Idempotent fix: only modify what the AD requires, skip unchanged parts
8. Update output files
9. Mark AD as [x] with (Resolved by <resolver>, <date>)
10. Append Change History: "AD fix — <what changed>"
11. Set Status: done + new Completed date
```

Key rules:
- AD fix is **incremental** — never re-execute work that's already correct
- AD fix is **idempotent** — running the same AD fix twice produces the same result
- Multiple ADs for the same skill are fixed in a single pass

---

## 5. Pipeline Order and Dependencies (管线顺序)

```
arch-align → arch-design → arch-detail → devtdd → arch-review
```

### Dependency Rules

- Each skill depends on the **directly upstream** skill being `done` for the same T{N}
- arch-align has no upstream dependency (it creates tasks)
- arch-design requires arch-align done for T{N}
- arch-detail requires arch-design done for T{N}
- devtdd requires arch-detail done for T{N}
- arch-review requires devtdd done for T{N}

### Parallel Work

Different skills can work on different tasks simultaneously:

```
| Skill | new | doing | done |
|-------|-----|-------|------|
| align | T3 | | |           ← align can start T3
| design | | T2 | |              ← design is working on T2
| detail | T1 | | |              ← detail can start T1
| devtdd | | | |
| arch-review | | | |
```

Each T appears in exactly one cell. When design picks up T1 next, it moves from detail's `new` to design's column (after detail's done is cleared by handover).

---

## 6. File Path Conventions (路径约定)

```
AGENTS.md                                  ← Global task counter
docs/
  bc/<slug>/
    kanban/
      BOARD.md                              ← Kanban board + local counter
      tasks/
        T1.md                                ← Task index file
        T2.md
    align/
      LANGUAGE.md                          ← BC-level aggregation
      BRD.md                           ← BC-level aggregation
    design/
      ARCHITECTURE.md                      ← BC-level aggregation
      adr/                                 ← Architecture decision records
    detail/
      DESIGN.md                            ← BC-level aggregation
      modules/                             ← Task-specific modules
    review/
      REVIEW.md                            ← Review reports
      reviews/                             ← Archived reviews
```

---

## 7. BC-Level Documents as Aggregations (聚合视图)

BC-level documents aggregate content from all tasks. They are updated when tasks complete:

| Document | Updated When | Aggregation Method |
|----------|-------------|-------------------|
| LANGUAGE.md | Task done at align | Merge terms from all completed align tasks |
| BRD.md | Task done at align | Merge business rules from all completed align tasks |
| ARCHITECTURE.md | Task done at design | Merge architecture decisions from all completed design tasks |
| DESIGN.md | Task done at detail | Merge module designs from all completed detail tasks |

### Version History

- **No separate Version History sections** in BC-level documents
- Change history is tracked per-task in `T{N}.md` Change History
- To understand "what changed and when", read across all task files

---

## 8. Edge Cases (边界情况)

### Task Cancellation

If a task is no longer needed:

1. Append to T{N}.md Change History: `Cancelled — <reason>`
2. Set all remaining `new`/`doing` statuses to `cancelled` in T{N}.md Status
3. Remove T{N} from BOARD.md Board table entirely (do NOT add to Archive)

### Task Blocked

If a task cannot proceed (missing input, ambiguous requirement):

1. Keep T{N} in current position on BOARD.md (do NOT move to another cell)
2. Append to T{N}.md Change History: `Blocked — <reason>`
3. Skill halts with clear error message to user

### AD with Multiple Upstream Issues

If a downstream skill discovers issues in multiple upstream skills:

1. Write AD entries in each target skill's section in T{N}.md
2. BOARD.md remains unchanged (AD does not affect positions)
3. User resolves in dependency order: align first → design → detail
4. Each skill's Startup detects its own ADs and fixes them incrementally

### Multiple BCs

Each BC has its own `kanban/` directory containing `BOARD.md` and `tasks/`. Task numbers are globally unique (via AGENTS.md counter) but tasks are scoped to their BC.

### Counter Overflow

`next_task_id` is an integer. No practical overflow risk for any project lifecycle.

---

## 9. Migration from Old Model (迁移对照)

| Old Mechanism | New Mechanism |
|---------------|--------------|
| BOARD.md per-phase rows (Phase/Status/Date) | Kanban board with T{N} numbers |
| Round-based iteration (Round 1, Round 2...) | Task-based (T1, T2, T3...) |
| Version History in BRD.md §5 | Change History in T{N}.md |
| Version History in ARCHITECTURE.md §7 | Change History in T{N}.md |
| Impact Assessment per round | Change History in T{N}.md |
| Cycle-Aware Startup Guard (🔄/⏭) | Upstream done check at startup |
| Cascade Rule (Phase 3 ⏭ → 🔄) | Runtime upstream check, no cascade |
| Prior Design Review (redo) | T{N}.md Change History + user confirmation |
| Task counter in AGENTS.md only | AGENTS.md (global) + BOARD.md (local mirror) |

---

## 10. Migration Mode Protocol (v2.1.0+)

When migrating a legacy project (existing code, no/empty documentation), the pipeline enters **Migration Mode** after `/arch-init` Mode C Phase C6 creates a migration task.

### 10.1 Migration Task Identification

A migration task is identified by the `(migration)` tag in `T{N}.md` References:

```markdown
## References
- Source: `(migration)` — reverse-engineering from existing code
```

### 10.2 Task Chaining Rule

In migration mode, each skill MUST add T{N} to the **next skill's `new` column** upon completion (not just mark itself done). This ensures the pipeline flows automatically without user intervention:

| Completing Skill | Chain to |
|-----------------|----------|
| arch-align | arch-design/new |
| arch-design | arch-detail/new |
| arch-detail | devtdd/new |
| devtdd | arch-review/new |
| arch-review | (no chain — last skill, normal archive) |

### 10.3 Upstream Halt Override

When T{N} has the `(migration)` tag, each skill checks for migration mode **before** the upstream halt check. If migration conditions are met (own output empty + code exists), the upstream halt is skipped.

### 10.4 User Confirmation at Each Stage

Each skill in migration mode MUST present its generated documentation to the user for verification before marking done. This ensures the reverse-engineered docs are accurate.

### 10.5 Partial Migration

If some documentation already exists (e.g., LANGUAGE.md present but BRD.md missing), the skill only generates the missing files. It does not overwrite existing content.
