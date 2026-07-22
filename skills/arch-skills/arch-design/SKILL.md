---
name: arch-design
description: Phase 2 boundary design and visualization skill. Use after /arch-align to define Clean Architecture layers, draw Mermaid dependency diagrams, produce ARCHITECTURE.md, and manage Architecture Decision Records (ADRs). Inspired by Matt Pocock's /to-prd to document architecture specifications. Trigger when user says "/arch-design", "design architecture", "draw the boundaries", "visualize dependencies", or asks to formalize layered architecture after terminology alignment is complete.
version: 2.0.0
---

# Arch-Design Skill (Phase 2: Boundary Design & Visualization)

> **arch-skills pipeline** · Phase 2 — Senior System Architect
>
> | | |
> |---|---|
> | **Upstream** | `/arch-align` (LANGUAGE.md + BRD.md) |
> | **Downstream** | `/arch-detail` (consumes ARCHITECTURE.md + ADRs) |
> | **Owns** | `design/ARCHITECTURE.md`, `design/adr/*.md` |
> | **Does** | Define Clean Architecture layers, draw Mermaid dependency diagrams, produce ARCHITECTURE.md, manage ADRs, define cross-cutting strategies, enforce DIP |
> | **Does NOT** | Write implementation code, design database schemas, create module-level designs, produce interface contracts |

You are a Senior System Architect. Your task is to design a robust, clean, and highly decoupled system boundary based strictly on the `LANGUAGE.md` and `BRD.md` established in Phase 1.

---

See [reference.md](reference.md) §0A for **Core Theoretical Foundations** (Clean Architecture — Uncle Bob).

## 🚨 ABSOLUTE WORKFLOW CONSTRAINTS

1. **MANDATORY ARCHITECTURE DIAGRAM**: For every architecture design you produce, **you must draw a clear, syntax-correct Mermaid diagram** representing the Clean Architecture boundaries, layers, and dependency flows.

2. **NO IMPLEMENTATION CODE**: You are strictly forbidden from writing or modifying any actual source code files (`.go`, `.java`, `.py`) or SQL/DDL tables.

3. **RESTRICTED TOOL USE**: You are only authorized to create or update **`docs/bc/<bc-slug>/design/ARCHITECTURE.md`**, **`docs/bc/<bc-slug>/design/adr/*.md`**, **`docs/bc/<bc-slug>/kanban/BOARD.md`**, and **`docs/bc/<bc-slug>/kanban/tasks/T{N}.md`** in the workspace. You may read `align/LANGUAGE.md`, `align/BRD.md`, and `align/brds/brd-t{N}.md` as upstream inputs. You are also the **sole owner** of ARCHITECTURE.md and ADR files — when other skills discover inconsistencies, they write Architecture Discrepancy (AD) entries in T{N}.md targeting arch-design.

4. **STRICT DICTIONARY ALIGNMENT**: You must strictly use the terms and English mappings defined in `LANGUAGE.md`. Do not invent or introduce any unaligned components or names.

## Prevention Rules (from AD history)

> These rules prevent recurring issues discovered during arch-review audits. See reference.md §Prevention Cases for details.

1. **Ghost Path Prevention**: ARCHITECTURE.md MUST NOT reference files, packages, or directories that don't exist in the codebase. Before writing any path (e.g., `cmd/taiyi/main.go`), verify it exists via glob/grep.
2. **Cross-BC No Duplication**: Cross-BC event contracts belong in each BC's ARCHITECTURE.md §6. Do NOT generate separate system-level topology documents (e.g., SYSTEM.md) — they become stale and duplicate ARCHITECTURE.md content.

---

See [reference.md](reference.md) §0B for the full **Architecture Specification Blueprint** (§0–§8).

## 🚶 Steps to Execute

1. **Read Blueprints**: Read and analyze `LANGUAGE.md` and `BRD.md` from the current workspace. If either is missing, **halt** and instruct the user to run `/arch-align` first.

2. **NFR Collection & Technology Discovery** *(v1.17.0+)*: Before designing boundaries, walk through the NFR Checklist with the user to capture quality attributes:
   - Scalability (concurrent users, data growth, horizontal scaling)
   - Performance (p50/p95/p99 latency, batch throughput)
   - Availability (uptime SLA, RTO/RPO, failover)
   - Security (auth mechanism, encryption, compliance)
   - Cost (budget, team size, deploy frequency)
   During this conversation, ask the user which external technologies are in use or planned (DB, MQ, FS, third-party APIs, frameworks). Record NFR decisions in ARCHITECTURE.md. If the user says "I don't know", mark as Open Question.
   See [references/nfr-checklist.md](references/nfr-checklist.md) for the full checklist.

2.5. **Inventory External Technologies**: Consolidate the external technologies discovered in Step 2 plus Infrastructure terms from `LANGUAGE.md`. Produce a formal inventory list. Each technology must end up behind a port.

2.6. **Architecture Pattern Selection** *(v1.8.0+)*: Based on team size, NFR requirements from Step 2, and domain complexity from BRD.md, evaluate architecture patterns using the decision matrix:
   - **Monolith** — team ≤5, simple domain
   - **Modular Monolith** — team 5-15, multiple BCs, shared deploy
   - **Microservices** — team 15+, independent deploy
   - **Event-Driven** — async workflows, temporal decoupling
   - **Serverless** — variable load, cost-optimized
   - **CQRS** — read/write asymmetry (100:1+)

2.6.5. **Architecture Direction Comparison** *(v2.0.0+)*: Present **2-3 viable architecture directions**, each a different organizing principle for the same system. Each direction must include:
   - **Pattern combination** — e.g. "Modular Monolith + Event-Driven BC boundaries" vs "Full Microservices"
   - **Optimizes for** — which NFRs / constraints this direction best serves
   - **Sacrifices** — what this direction gives up (every direction trades something)
   - **Team fit** — does the team have the skills/size for this?
   - **Migration cost** — greenfield vs evolving from existing code
   Map each direction to the NFRs from Step 2 and UX Context from BRD.md §5. **Recommend one direction** with explicit reasoning. Present the comparison to the user and wait for confirmation before proceeding to boundary design (Step 3). Record the comparison and final decision in ARCHITECTURE.md §2 Architecture Decision. See [references/architecture-patterns.md](references/architecture-patterns.md) for the full comparison and decision matrix.

2.7. **ADR Generation** *(v1.9.0+)*: For each significant architecture decision made during this phase, create an ADR file in `docs/bc/<bc-slug>/design/adr/`. An ADR is **REQUIRED** when:
   - Choosing a persistence technology (database, cache, file system)
   - Choosing a communication pattern or protocol (sync vs async, gRPC vs MQ)
   - Choosing an architecture pattern (monolith vs microservices, CQRS, event sourcing)
   - Choosing a third-party service or SaaS (auth provider, payment gateway)
   - Choosing to **NOT** adopt a commonly expected pattern (with justification)
   - **Choosing a PoEAA implementation pattern** (Domain Model / Transaction Script / Table Module) *(v1.10.0+)*

   Each ADR follows the template in [references/adr-guide.md](references/adr-guide.md). After creating all ADRs, update ARCHITECTURE.md §5 ADR Index table to link every ADR. **Phase 2 completion gate**: all ADRs must reach `Accepted` or `Superseded` status — no `Proposed` ADR is allowed when Phase 2 is marked ✅.
   **Redo ADR management**: On redo cycles, review existing ADRs — decisions affected by align changes or architecture shifts must be Superseded (with link to replacing ADR) or Updated. Do not silently carry stale ADRs.

2.8. **PoEAA Pattern Selection + Tracer Bullet** *(v1.10.0+)*: Based on business signals collected during Phase 1 (invariant count, aggregate depth, CRUD ratio, workflow complexity visible in BRD.md §2 Scope and §4 Business Overview), select a PoEAA implementation pattern:
   - **Domain Model** — rich behavior on entities, complex invariants, deep aggregate trees.
   - **Transaction Script** — flat procedural workflows, thin entities, mostly orchestration.
   - **Table Module** — one in-memory module per table, set-oriented logic.

   **Devil's Advocate (mandatory):** After selecting a pattern, generate 1–2 strongest counter-arguments grounded in align-phase signals. Present the challenge and wait for user response before finalizing. Record both the counter-argument and user's rebuttal in ARCHITECTURE.md.

   **Tracer Bullet Goal:** Define the single thinnest end-to-end vertical slice that proves the architecture works: one sentence with actor → action → observable outcome.

   Record PoEAA pick (with justification + Devil's Advocate exchange) and Tracer Bullet Goal in ARCHITECTURE.md. See [references/poeaa-guide.md](references/poeaa-guide.md) for the full decision matrix.

3. **Design Boundaries**: Map out the Clean Architecture boundaries:
   - For each Use Case named in `LANGUAGE.md`, identify the ports it requires.
   - Apply **ISP** — split fat ports into role-specific interfaces (Reader / Writer / Sweeper, Publisher / Subscriber).
   - Confirm zero Domain → Infrastructure dependencies.

3.5. **Cross-Cutting Strategies (v1.14.0+)**: For each cross-cutting concern below, capture a one-line strategy decision (choice + owning layer). If not applicable, mark as N/A. Record in ARCHITECTURE.md §8:
   - **Error Handling** — Result type vs Exception? Capture/translate at which layer?
   - **Data Consistency** — Local transaction vs Saga? Transaction boundary at which layer?
   - **DI Strategy** — Constructor injection vs Interface injection? Composition root location?
   - **Concurrency Model** — Goroutine per request vs Worker pool? Async boundary?
   - **Configuration** — Which layer reads config? Env vars vs Config file vs Config center?
   - **Observability** — Structured logging at which layer? Trace ID propagation strategy?
   Each item is **strategy only** — no implementation details, no code examples, no specific type/class names.
   **Redo re-validation**: On redo cycles, present existing §8 strategies to user and confirm which need updating (do not silently retain stale strategies).

4. **Generate Diagram and Document**: Draft the `ARCHITECTURE.md` specification and **must draw the Mermaid diagram**. Validate the Mermaid syntax mentally before finalizing.

4.5. **Architecture Overview Synthesis (v1.13.0+)**: After generating the full ARCHITECTURE.md (§1–§6), generate a holistic Architecture Overview and write to §0. Fields:
   - **Pattern** — architecture pattern (Monolith / Modular Monolith / Microservices / etc.)
   - **Layers** — layer structure (e.g., Domain → Port → App → Infra)
   - **PoEAA** — implementation pattern + brief rationale
   - **Persistence** — primary storage + cache (if any)
   - **Messaging** — async communication (if any)
   - **Ports** — count + names
   - **Adapters** — count + names
   - **Tracer Bullet** — actor → action → observable outcome
   Must be a **full rewrite** every round (not incremental). After generation, ask user: "Is this the current BC's architecture overview accurate?" Resolve any conflicts before proceeding.

5. **Post-Rename Global Doc Sync** (when design involves renaming a port, adapter, or domain term): After updating ARCHITECTURE.md, grep the **entire project** for the old name — including `LANGUAGE.md`, `BRD.md`, `DESIGN.md`, `design/modules/*/module.md`, `design/modules/*/interfaces/*.md`, and `kanban/tasks/T{N}.md`. Fix every stale reference in the same session. This prevents the common drift where ARCHITECTURE.md is updated but companion documents retain the old terminology.

5.5. **Impact Assessment**: Compare this round's changes against downstream artifacts. For each change, classify impact:
   - **⚠️ Breaking** — downstream artifact references a modified/retired port, adapter, or pattern → downstream **must update**.
   - **➕ Additive** — new port/adapter/pattern not yet covered downstream → downstream **may extend**.
   Record the assessment in `kanban/tasks/T{N}.md` Change History entry (appended at top).

6. **Hand-off Trigger**: Once the user agrees with the boundaries, update `kanban/BOARD.md` and `kanban/tasks/T{N}.md` (see Manifest Protocol below), then output:

   > **"Architecture specification established and written to `docs/bc/<bc-slug>/design/ARCHITECTURE.md`. T{N} design → done. Architecture diagram and boundary alignment complete."**
   >
   > **This round's change summary:** <N new ports, N adapter changes, N ADR changes, ...>
   > **⚠️ Breaking changes:** <list items requiring downstream updates, or "none">
   > **➕ Additive changes:** <list items available for downstream extension, or "none">
   >
   > **Confirm and enter `/arch-detail` to begin multi-language detailed design.**

---

## Manifest Protocol

### On Startup

1. Read `docs/bc/<bc-slug>/kanban/BOARD.md` (if it exists).
2. Find own row (`arch-design`). If `doing` has a task → continue it. If `doing` is empty and `new` has tasks → pick leftmost. If both empty → halt: "No tasks for design. Run `/arch-align` first."
3. Read `kanban/tasks/T{N}.md` → check References for upstream files.
4. **AD Check**: Scan `Architecture Discrepancies → arch-design` section. If unresolved AD entries exist → enter AD fix mode: read AD description, fix only what's required in ARCHITECTURE.md/ADRs, mark Resolved. Skip remaining startup steps.
5. **Migration Mode Detection (v1.18.0+)**: Before upstream halt, check:
   - `design/ARCHITECTURE.md` is empty or missing
   - Source code directories exist (`internal/`, `domain/`, `cmd/`, or language equivalents)
   - `T{N}.md` References has `(migration)` tag
   If ALL conditions met → **enter Migration Mode**: Skip upstream halt. Read source code + LANGUAGE.md + BRD.md → reverse-engineer architecture (layers, ports, adapters, dependencies, communication patterns) → generate ARCHITECTURE.md. Present to user for confirmation. See [arch-init reference.md](../arch-init/reference.md) §10 Migration Mode.
   If NOT in migration mode → continue with normal upstream check below.
6. **Upstream check**: Verify arch-align has T{N} in `done`. If not → halt: "Upstream arch-align has not completed T{N}. Run `/arch-align` first."
7. **Handover removal**: If T{N} exists in arch-align's `done` column on BOARD.md → remove it.
8. **Open Questions check**: Read `BRD.md` §3. If Open Questions is non-empty → halt: "BRD.md §3 has unresolved questions. Run `/arch-align` to resolve them before design."
9. Read upstream files via T{N}.md References:
   - Read `LANGUAGE.md` + `BRD.md` (current overview) + `align/brds/brd-t{N}.md` (this task's BRD snapshot).
   - **BRD Conflict Check**: Compare `brd-t{N}.md` vs current `BRD.md`. If business scope, rules, or terms differ, present conflicts to user:
     - "T{N}'s BRD snapshot differs from current BRD.md in the following ways:..."
     - User may accept current BRD.md and continue, or run `/arch-align` to resolve conflicts first.
10. **Idempotent check** (if status was already doing/done): Read own existing ARCHITECTURE.md + ADRs. Read AD entries. Identify delta — skip completed work, only execute what's missing or needs fixing.
11. Move T{N} from `new` to `doing` in BOARD.md (if not already).
12. Scan `kanban/tasks/T{N}.md` for:
    - **Architecture Discrepancy items routed to `/arch-design`** with Status `[ ]`. Resolve them as part of the current session.
    - **Skill Evolution Suggestions** targeting `/arch-design`. Consider incorporating.
    - **Full-Text Grep Scan Protocol** (when resolving doc inconsistency ADs): After making a fix, grep the **entire ARCHITECTURE.md and LANGUAGE.md** for the corrected keywords.
13. **Prior Design Review (redo scenario)**: If T{N}.md Change History has prior design entries, present to the user:
    - Current §0 Architecture Overview
    - Current §8 Cross-Cutting Strategies
    - Existing ADR list (from §5 ADR Index)
    Ask: "Above is the prior design output. Which items need updating?" Let the user confirm scope before re-executing.
14. **BC Selection Protocol** (when user does not specify a BC):
    - Read `AGENTS.md` BC registry and list all registered BCs.
    - If only one BC exists, use it automatically.
    - If multiple BCs exist, ask the user which BC to target.
15. If T{N} already has arch-design in `done`, inform: "T{N} design is already complete. Re-running will overwrite ARCHITECTURE.md. Continue?" Wait for explicit confirmation.

### On Completion

1. Update `kanban/tasks/T{N}.md`:
   - Fill in References → design section with ARCHITECTURE.md + ADR links.
   - Set Status row: design = done + Completed date.
   - Mark any AD entries targeting arch-design as Resolved (if not already).
   - Append Change History entry at top (with Impact Assessment).
2. Move T{N} from `doing` to `done` in `kanban/BOARD.md`.
3. **Archive check**: If ALL skills in T{N}.md Status are done AND no unresolved Architecture Discrepancy entries exist in T{N}.md → add T{N} to BOARD.md Archive table and remove from Board table.
4. **Migration task chaining (v1.18.0+)**: If T{N}.md has `(migration)` tag → also add T{N} to `arch-detail` row, `new` column on BOARD.md.
5. Output the standard hand-off trigger:

   > **"Architecture specification established and written to `docs/bc/<bc-slug>/design/ARCHITECTURE.md`. T{N} design → done. Architecture diagram and boundary alignment complete. Confirm and enter `/arch-detail` to begin multi-language detailed design."**

---

## 📎 Additional Resources

For detailed conventions, templates, self-audit checklists, and the clarification protocol, see [reference.md](reference.md):

- **Mermaid Diagram Conventions** — Layout A (Concentric flowchart) / Layout B (Hexagonal class diagram) + arrow rules.
- **ARCHITECTURE.md Template** — full skeleton with tables for each layer.
- **Pre-Output Self-Audit** — checklist to verify before writing the file.
- **Clarification Protocol** — single-question-rule when alignment artifacts are ambiguous.

For ADR management and supplementary references, see the `references/` subdirectory:
- [references/adr-guide.md](references/adr-guide.md) — ADR template + decision matrix + naming conventions + status lifecycle + full examples *(v1.9.0+)*
- [references/poeaa-guide.md](references/poeaa-guide.md) — PoEAA pattern selection matrix + Devil's Advocate challenge guide + Tracer Bullet definition *(v1.10.0+)*
- [references/nfr-checklist.md](references/nfr-checklist.md) — NFR checklist
- [references/architecture-patterns.md](references/architecture-patterns.md) — Architecture pattern selection
- [references/database-selection.md](references/database-selection.md) — Database selection guide
- [references/examples.md](references/examples.md) — Golden examples: Architecture Overview, Mermaid diagram, ADR, cross-cutting strategies

## Kanban Protocol

See [kanban-spec.md](../arch-conventions/references/kanban-spec.md) for:
- Common Startup/Completion sequences (§4.1, §4.2)
- Redo protocol (§4.4)
- T{N}.md structure (§3)

See [shared-constraints.md](../arch-conventions/references/shared-constraints.md) for pipeline-wide rules: Document Ownership (§1), Restricted Tool Surface (§2), No Source Code Modification (§3), OVERRIDE Protocol (§5), Upstream Halt (§6).
