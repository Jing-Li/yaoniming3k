# Changelog

All notable changes to the arch-skills pipeline are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased] — 2026-07-12

### System-wide Audit Improvements

This release addresses a comprehensive 9-dimension audit (scored 75.5/100) of the arch-skills pipeline. All improvements are internal refactors and additive reference content — no breaking changes to skill interfaces or routing.

#### Changed
- **arch-review** (3.2.0 → 3.2.1): SKILL.md slimmed from 506→300 lines. Moved Standard Review Report template, Fix Guidance Mode, and Core Theoretical Foundations to reference files (progressive disclosure).
- **arch-design** (1.18.0 → 1.18.1): SKILL.md slimmed from 257→207 lines. Moved Architecture Specification Blueprint and Core Theoretical Foundations to reference files.
- **arch-detail** (3.3.0 → 3.3.1): SKILL.md slimmed from 217→204 lines. Moved Core Theoretical Foundations to reference file.
- **devtdd** (1.9.0 → 1.9.1): Reference file split from 767→549 lines (Code Craftsmanship Iron Rules extracted to standalone file).
- **arch-conventions** (1.1.0 → 1.1.1): Added `shared-constraints.md` — cross-skill hard constraints extracted from duplicated definitions across 5 skills.

#### Added
- `arch-conventions/references/shared-constraints.md` — Document Ownership, Restricted Tool Surface, No Source Code Modification, Migration Mode Detection, OVERRIDE Protocol, Upstream Halt.
- `arch-review/references/review-report-template.md` — Standard Review Report §1–§9 full templates.
- `arch-review/references/fix-guidance-mode.md` — AD Fix Guidance Mode workflow and scope matrix.
- `arch-review/references/examples.md` — Golden examples: AD entry, route decision, health score, severity table.
- `devtdd/references/code-craftsmanship-rules.md` — §9.1–§9.7 constant extraction, DRY, dead code, stdlib preference, test craftsmanship.
- `devtdd/references/examples.md` — Golden examples: micro-cycle plan, Red→Green→Refactor, craftsmanship check, state sync.
- `arch-detail/references/per-language-rules.md` — Go/Java/Python golden rules, skeleton code, diagnosis checklists.
- `arch-detail/references/examples.md` — Golden examples: DESIGN.md index, module.md, port interface.
- `arch-design/references/examples.md` — Golden examples: Architecture Overview, Mermaid diagram, ADR, cross-cutting strategies.

#### Internal
- All SKILL.md body content unified to English (Chinese body text removed; only user-facing trigger words retain Chinese).
- Reference files split for progressive disclosure — agent loads on demand instead of full context.
