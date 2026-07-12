# Arch-Kanban — Reference

Quick-access reference for the kanban protocol. For the full specification, read [kanban-spec.md](references/kanban-spec.md).

---

## 1. BOARD.md Template

Write this to `docs/bc/<slug>/kanban/BOARD.md`:

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

## Archive
```

---

## 2. T{N}.md Template

Write this to `docs/bc/<slug>/kanban/tasks/T{N}.md`:

```markdown
# T{N} — <Task Name>

## Description

One-line description of what this task delivers.

**Created by**: arch-align
**Created at**: YYYY-MM-DD

## References

### arch-align
- [BRD.md](../align/BRD.md) — <relevant sections>
- [LANGUAGE.md](../align/LANGUAGE.md) — <relevant terms>
- [brd-t{N}](../align/brds/brd-t{N}.md) — This task's BRD snapshot

### arch-design
- (not started)

### arch-detail
- (not started)

### devtdd
- (not started)

### arch-review
- (not started)

## Status

| Skill | Status | Started | Completed |
|-------|--------|---------|----------|
| arch-align | new | — | — |
| arch-design | new | — | — |
| arch-detail | new | — | — |
| devtdd | new | — | — |
| arch-review | new | — | — |

## Architecture Discrepancies

### arch-align
(empty)

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
| YYYY-MM-DD | arch-align | Initial creation |
```

---

## 3. Core Rules Quick Reference

### Board Invariants

| Rule | Description |
|------|-------------|
| **Single-position (ABSOLUTE)** | Each T appears in exactly ONE cell. No exceptions. |
| **Handover removal (MANDATORY)** | Downstream deletes T from upstream `done` + adds to own cell atomically. |
| **Archive trigger** | ALL skills done → remove from Board → append `- T{N} — YYYY-MM-DD` to Archive |
| **AD isolation** | ADs live in T{N}.md only. Never affect BOARD.md positions. |

### Pipeline Order

```
arch-align → arch-design → arch-detail → devtdd → arch-review
```

### Startup Sequence (every skill)

```
1. Read BOARD.md → find own row
2. Pick task: doing > new (leftmost)
3. Read T{N}.md → AD Check → upstream check
4. Handover removal: delete from upstream done → add to own cell
5. Idempotent check: read existing outputs, do only delta
6. Move to doing → set Started date
```

### Completion Sequence (every skill)

```
1. Write output files
2. Update T{N}.md: References + Status + Change History
3. Move to done in BOARD.md
4. Archive check: if ALL done → remove from Board + append to Archive
5. Hand-off message
```

---

## 4. Validation Checks

| Check | Rule | Severity |
|-------|------|----------|
| Single-position | T in exactly ONE cell | Error |
| Archive integrity | Archived T not on Board | Error |
| Phantom detection | T on Board but T{N}.md missing | Error |
| Orphan detection | T{N}.md exists but not on Board/Archive | Warning |
| Counter consistency | next_task_id > max T number | Warning |
| Status coherence | Board position matches T{N}.md Status | Warning |

---

## 5. File Paths

```
docs/bc/<slug>/
  kanban/
    BOARD.md          ← Per-BC board (counter + status + archive)
    tasks/
      T0.md           ← Task index files
      T1.md
```

---

## 6. AD (Architecture Discrepancy) Format

```markdown
## Architecture Discrepancies

### <target-skill>
- [ ] AD-{TargetInitial}{N}: <description> (by <discoverer>, <date>)
- [x] AD-{TargetInitial}{M}: <description> (by <discoverer>, <date>) (Resolved by <resolver>, <date>)
```

**Rules:**
- AD goes under **target skill's** section (the one who fixes it)
- ID format: `AD-A1` (arch-align), `AD-D1` (arch-design), `AD-Dt1` (arch-detail), `AD-T1` (devtdd), `AD-R1` (arch-review)
- Resolution: mark `[x]` + append `(Resolved by <resolver>, <date>)`
- ADs do NOT affect BOARD.md

---

## 7. Migration Mode

A task with `(migration)` tag in References triggers special behavior:

```markdown
## References
- Source: `(migration)` — reverse-engineering from existing code
```

**Task chaining**: each skill MUST add T{N} to next skill's `new` column upon completion.

| Completing Skill | Chain to |
|-----------------|----------|
| arch-align | arch-design/new |
| arch-design | arch-detail/new |
| arch-detail | devtdd/new |
| devtdd | arch-review/new |
| arch-review | (no chain — archive) |

---

## Full Specification

For complete protocol definition, read [kanban-spec.md](references/kanban-spec.md).
