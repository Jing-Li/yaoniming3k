# Kanban Protocol v2.0.0 — Migration Changelog

> Date: 2025-07-12
> Scope: All arch-skills (arch-align, arch-design, arch-detail, devtdd, arch-review, arch-critic)
> Spec: [kanban-spec.md](kanban-spec.md)

---

## Overview

Kanban v2.0.0 replaces the old round-based iteration model with a task-based pipeline. Each task (T{N}) flows through 5 skills in a strict single-position board, with handover removal, automatic archival, and Architecture Discrepancy (AD) tracking for cross-skill feedback.

---

## Breaking Changes (from old model)

| Old Mechanism | New Mechanism (v2.0.0) |
|---|---|
| BOARD.md per-phase rows (Phase/Status/Date) | Kanban board: Skill × (new / doing / done) matrix |
| Round-based iteration (Round 1, Round 2...) | Task-based (T0, T1, T2...) — each T is an independent unit of work |
| Version History in BRD.md §5 | Change History in T{N}.md (append-only, reverse chronological) |
| Version History in ARCHITECTURE.md §7 | Change History in T{N}.md |
| Impact Assessment per round | Change History in T{N}.md (⚠️ Breaking / ➕ Additive classification) |
| Cycle-Aware Startup Guard (🔄/⏭) | Upstream done check at startup (explicit halt if upstream incomplete) |
| Cascade Rule (Phase 3 ⏭ → 🔄) | Runtime upstream check — no cascade, just halt with clear message |
| Prior Design Review (redo) | T{N}.md Change History + user confirmation before re-execution |
| Task counter in AGENTS.md only | AGENTS.md (global) + BOARD.md `next_task_id` (local mirror per BC) |

---

## New Mechanisms

### 1. Single-Position Rule

Each T number appears in **exactly ONE cell** across the entire Board table. No duplicates, no ghost entries.

### 2. Handover Removal

When a downstream skill picks up T, it **removes T from the upstream skill's `done` column**. T moves directly to the downstream skill's `doing` column. This ensures the single-position rule is maintained during handover.

**Pipeline order**: `arch-align → arch-design → arch-detail → devtdd → arch-review`

### 3. Archive Mechanism

When ALL skills in T{N}.md Status are `done` **AND** no unresolved Architecture Discrepancy entries exist in T{N}.md:
- T{N} is added to the Archive table with completion date
- T{N} is removed from all Board rows entirely
- Archived tasks never reappear on the Board (unless AD fix is needed — see Startup Fallback below)

### 4. Architecture Discrepancy (AD) Mechanism

ADs replace the old "round redo" model. When a downstream skill discovers upstream issues:
- It writes AD entries in `T{N}.md → Architecture Discrepancies → <target skill> section`
- AD entries are tracked in T{N}.md only — they do NOT change BOARD.md positions
- The targeted skill fixes ADs on its next startup (detected in step 4 of Startup)
- AD fix is **incremental** and **idempotent** — only what the AD requires is modified
- Format: `- [ ] AD-{ID}: <description> (by <discoverer>, <date>)` → `- [x] ... (Resolved by <resolver>, <date>)`

### 5. Idempotent Execution

Every skill's startup includes an idempotent check:
- Read own existing output files
- Read AD entries targeting this skill
- Identify delta: what's new vs what's already done
- Skip completed work; only execute what's missing or needs fixing

This means re-running a skill is safe — it will only do what hasn't been done yet.

### 6. Startup Fallback for Archived ADs (v2.0.0 Audit Fix)

When a skill's Board row has no tasks (both `doing` and `new` are empty), it checks archived T{N}.md files for unresolved ADs targeting this skill. If found, the task is temporarily restored to the Board for AD fix, then re-archived after completion.

---

## Files Changed

### kanban-spec.md (Source of Truth)

| Change | Section | Description |
|---|---|---|
| Handover clarification | §2 Board Rules | "T moves directly to downstream's `doing` column" (was: "`new` or `doing`") |
| Archive + AD condition | §2 Board Rules + §2 Archive Rules | Archive requires ALL done AND no unresolved ADs |
| Startup archive fallback | §4.1 Step 5 | Check archived T{N}.md for unresolved ADs when Board has no tasks |
| Completion archive condition | §4.2 Step 4 | "ALL done AND no unresolved ADs" |

### arch-align/SKILL.md

| Change | Section | Description |
|---|---|---|
| AD fix idempotent context | On Startup §4 | "read own existing output (LANGUAGE.md, BRD.md)" added to AD fix mode |
| Archive condition | On Completion §5 | Added "AND no unresolved Architecture Discrepancy entries exist in T{N}.md" |

### arch-design/SKILL.md

| Change | Section | Description |
|---|---|---|
| Archive condition | On Completion §3 | Added "AND no unresolved Architecture Discrepancy entries exist in T{N}.md" |

### arch-detail/SKILL.md

| Change | Section | Description |
|---|---|---|
| Archive condition | On Completion §5 | Added "AND no unresolved Architecture Discrepancy entries exist in T{N}.md" |

### devtdd/SKILL.md

| Change | Section | Description |
|---|---|---|
| AD terminology fix | Hard Constraint #7, Step 1.7, Step 6.5, L234-236 | "Architecture Debt" → "Architecture Discrepancy" (6 instances) |
| Startup halt message | On Startup §2 | "Run upstream skills first" → "Run `/arch-detail` first" |
| Idempotent check added | On Startup §5 | New explicit step: read existing output + AD entries → delta |
| Archive condition | On Completion §7 | Added "AND no unresolved Architecture Discrepancy entries exist in T{N}.md" |

### arch-review/SKILL.md

| Change | Section | Description |
|---|---|---|
| Archive condition | On Completion §3 | Added "AND no unresolved Architecture Discrepancy entries exist in T{N}.md" |

### arch-critic/SKILL.md

No changes required. arch-critic is a read-only skill outside the kanban pipeline.

---

## Migration Checklist

For each existing BC using the old round-based model:

- [ ] **BOARD.md**: Replace old phase-row format with Skill × (new/doing/done) matrix
- [ ] **T{N}.md files**: Create task index files for each existing round (T0, T1, ...)
- [ ] **Version History**: Extract from BRD.md §5 and ARCHITECTURE.md §7 → move to T{N}.md Change History
- [ ] **Impact Assessments**: Convert to ⚠️ Breaking / ➕ Additive format in Change History
- [ ] **Counters**: Set `next_task_id` in BOARD.md to match the next available task number
- [ ] **AD entries**: Convert any open "redo items" to AD format in T{N}.md Architecture Discrepancies sections
- [ ] **Archive**: Move fully-completed rounds (all 5 skills done, no open ADs) to Archive table
- [ ] **Skill startup**: Verify each skill's On Startup follows the v2.0.0 sequence (AD Check → Upstream → Handover → Idempotent → Move to doing)
