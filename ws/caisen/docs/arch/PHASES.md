# Architecture Pipeline Status

> Last updated: 2026-07-11
> Current Cycle: C1

---

## Bounded Contexts

| BC | Slug | Phase 1 (Align) | Phase 2 (Design) | Phase 3 (Detail) | Phase 4 (Implement + Audit) |
|----|------|---------|---------|---------|---------|

### Phase Status Vocabulary

| Status | Meaning | When |
|--------|---------|------|
| (empty) | Not started | New BC registration |
| ✅ complete | Current Cycle done | Skill completes its work |
| 🔄 redoing | Needs rework in current Cycle | arch-review found ADs routed to this Phase |
| ⏭ invalidated | Cascaded invalidation from upstream | Upstream Phase marked 🔄, downstream auto-marked |

### Cycle Tracking

- **C1** = initial design cycle (arch-align through devtdd all complete)
- **C2+** = each time arch-review discovers ADs requiring upstream Phase rework, increment Cycle number
- Cycle number is tracked in the `> Current Cycle: C<N>` header

### Phase State Transitions

```
(empty) → ✅ complete          (normal completion)
✅ complete → 🔄 redoing    (arch-review found ADs for this Phase)
✅ complete → ⏭ invalidated (upstream Phase became 🔄, cascade downstream)
🔄 redoing → ✅ complete    (skill completed rework)
⏭ invalidated → 🔄 redoing (upstream Phase completed, downstream becomes ready)
⏭ invalidated → ✅ complete (if rework doesn't affect this Phase, upstream skill restores)
```

### Cascade Rules

When arch-review produces ADs routed to a skill, that skill's Phase and all downstream Phases are affected:

| AD Route | Directly mark 🔄 | Cascade mark ⏭ |
|----------|-----------------|----------------|
| `/arch-align` | Phase 1 | Phase 2, 3, 4 |
| `/arch-design` | Phase 2 | Phase 3, 4 |
| `/arch-detail` | Phase 3 | Phase 4 |
| `/devtdd` | Phase 4 | (none) |

If a review has ADs routed to multiple Phases, the highest-level Phase becomes 🔄 and all downstream become ⏭.

---

## File Locations

Each BC's outputs live in `docs/bc/<slug>/`:

| Phase | Skill | Output Files |
|-------|-------|-------------|
| 1 — Concept Alignment | `/arch-align` | `LANGUAGE.md`, `CONTEXT.md` |
| 2 — Boundary Design | `/arch-design` | `ARCHITECTURE.md` + `docs/arch/SYSTEM.md` (when 2+ BCs) |
| 3 — Detailed Design | `/arch-detail` | `DESIGN.md`, `design/modules/` |
| 4a — Implementation | `/devtdd` | source code + test files; updates `DESIGN.md` task status |
| 4b — Architecture Audit | `/arch-review` | `REVIEW.md` (current) + `reviews/` (active archives) + `reviews/done/` (closed archives) |

---

## Reading Protocol

All file paths are relative to the target BC directory `docs/bc/<slug>/`.

- `/arch-align` reads nothing (creates Phase 1 from scratch)
- `/arch-design` requires Phase 1 ✅ or 🔄 → reads `LANGUAGE.md` + `CONTEXT.md`
- `/arch-detail` requires Phase 2 ✅ or 🔄 → reads `ARCHITECTURE.md` + `LANGUAGE.md` + `CONTEXT.md`
- `/devtdd` requires Phase 3 ✅ or 🔄 → reads `DESIGN.md` + `design/modules/` + `ARCHITECTURE.md`
- `/arch-review` reads available outputs based on completed phases
- **⏭ HALT rule**: If a skill finds its own Phase is ⏭ invalidated, it MUST halt and instruct the user to complete the upstream Phase first.

## Writing Protocol

Each skill **must** update this file upon completion:

| Skill | On Startup | On Completion |
|-------|-----------|---------------|
| `/arch-align` | Read PHASES.md; check own Phase status (🔄=normal, ⏭=HALT) | Write Phase 1 files; mark Phase 1 ✅; if downstream Phases are ⏭, mark Phase 2 as 🔄 |
| `/arch-design` | Read PHASES.md; check Phase 2 status (🔄=normal, ⏭=HALT); scan REVIEW.md for ADs routed to `/arch-design` | Write `ARCHITECTURE.md`; mark Phase 2 ✅; if Phase 3/4 are ⏭, mark Phase 3 as 🔄 |
| `/arch-detail` | Read PHASES.md; check Phase 3 status (🔄=normal, ⏭=HALT) | Write `DESIGN.md` + `design/modules/`; mark Phase 3 ✅; if Phase 4 is ⏭, mark Phase 4 as 🔄 |
| `/devtdd` | Read PHASES.md; check Phase 4 status (🔄=normal, ⏭=HALT); scan REVIEW.md for ADs routed to `/devtdd` | Update `DESIGN.md` task status; write source code + tests; update PHASES.md |
| `/arch-review` | Read PHASES.md; determine completed phases; load previous REVIEW.md | Write REVIEW.md; generate AD Execution Plan; update PHASES.md Cycle number + Phase 🔄/⏭ marks |

## BC Selection Protocol

When a skill is invoked without specifying a BC:

1. Read `docs/arch/PHASES.md` and list all registered BCs
2. If only one BC exists, use it automatically
3. If multiple BCs exist, ask the user which BC to target
4. For `/arch-align` (new BC): prompt for a slug name and create `docs/bc/<slug>/`
