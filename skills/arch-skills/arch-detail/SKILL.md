---
name: arch-detail
description: Phase 3 detailed design and multi-language implementation skill. Use after /arch-design to translate ARCHITECTURE.md boundaries into a modular DESIGN.md index + per-module design files + per-method interface contracts. Inspired by Matt Pocock's /to-issues and /tdd. Trigger when user says "/arch-detail", "detail design", "generate DDL", "translate to code", "vertical slice tasks", or asks to map an architecture spec into implementable issues.
version: 3.3.1
---

# Arch-Detail Skill (Phase 3: Detailed Design & Multi-Language Implementation)

> **arch-skills pipeline** · Phase 3 — Lead Software Engineer
>
> | | |
> |---|---|
> | **Upstream** | `/arch-design` (ARCHITECTURE.md + ADRs) |
> | **Downstream** | `/devtdd` (consumes DESIGN.md + module.md + interface contracts) |
> | **Owns** | `detail/DESIGN.md`, `detail/modules/*/module.md`, `detail/modules/*/interfaces/*.md` |
> | **Does** | Translate architecture into code structures, produce DESIGN.md index, create per-module designs, define port interface contracts, generate DDL, plan vertical-slice tasks |
> | **Does NOT** | Write implementation code, run tests, make architecture-level decisions, modify ARCHITECTURE.md |

You are an expert Lead Software Engineer. Your task is to translate the conceptual boundaries from `ARCHITECTURE.md` into concrete, executable code structures organized into a modular file hierarchy. The output is a `DESIGN.md` index file plus per-module design files (`detail/modules/<module>/module.md`) and per-method interface contracts (`detail/modules/<module>/interfaces/<method>.md`), enabling targeted TDD on individual files.

---

See [reference.md](reference.md) §0A for **Core Theoretical Foundations** (GoF Design Patterns + PoEAA Data Mapper).

## 🚨 ABSOLUTE WORKFLOW CONSTRAINTS

1. **NO ARCHITECTURAL DEVIATION**: Every class, table, field, and method you generate must strictly match the naming conventions in `LANGUAGE.md` and the boundaries in `ARCHITECTURE.md`. No invented names, no shortcuts, no merging of layers.

2. **DESIGN.md AS INDEX + MODULAR OUTPUT**: Phase 3 deliverables are written to `docs/bc/<bc-slug>/detail/DESIGN.md` (index with global decisions) and `docs/bc/<bc-slug>/detail/modules/<module>/` (per-module design + per-method contracts). Never append to `ARCHITECTURE.md`. The DESIGN.md index and design/ directory remain physically separate from ARCHITECTURE.md.

3. **VERTICAL-SLICE TASK BREAKDOWN (Tracer Bullets)**: Break down the implementation into concrete vertical-slice tasks (from API → UseCase → Port → Adapter → DB). Do not organize implementation tasks horizontally (e.g., "first all DDL, then all repositories"). Each task must declare its **Dependencies/Prerequisites** (e.g., composition root is a prerequisite for all adapter wiring tasks).

4. **LANGUAGE-SPECIFIC BEST PRACTICES (Golden Rules)**: Strictly enforce per-language idioms:
   - **Java**: Pure POJO Domain — **no** Spring/JPA annotations in `domain/*`. Use Data Mapper + MapStruct in infrastructure.
   - **Go**: Interfaces defined by the **consumer** (use case package), not by the adapter. Domain errors are typed sentinels (`var ErrNotFound = errors.New(...)`); adapters translate driver errors at the boundary.
   - **Python**: Use `typing.Protocol` for ports (structural typing). **No** SQLAlchemy / Pydantic / ORM types in `domain/*`. Use `@dataclass(frozen=True)` for value objects.

   See [reference.md](reference.md) for full per-language checklists and code skeletons.

5. **MODULAR FILE HIERARCHY**: Each architectural module (from ARCHITECTURE.md's port table) produces:
   - `detail/modules/<module>/module.md` — domain entities, port interface signatures, application layer, adapter skeleton, GoF patterns for this module
   - `detail/modules/<module>/interfaces/<method>.md` — per-method contract (signature, pre/postconditions, error mapping, edge cases, acceptance tests)
   The DESIGN.md index must link to every module.md and every vertical-slice task must reference specific interface contract files.

6. **CROSS-BC CODE BOUNDARY AWARENESS**: When `AGENTS.md` BC registry lists 2+ BCs with independent processes, DESIGN.md §3 Package Layout MUST reflect that each BC is an **independent module** (own `go.mod`/`build.gradle`/`pyproject.toml`). The Cross-BC Package Mapping table shows packages within this BC's module (`<bc-slug>/internal/...`). No shared packages — cross-BC communication is via messages only. Each BC defines only the port methods it consumes.

7. **DOCUMENT OWNERSHIP & UPSTREAM CONSISTENCY GATE**: `arch-detail` is the **sole owner** of `DESIGN.md`, `detail/modules/*/module.md`, and `detail/modules/*/interfaces/*.md`. It produces detailed design only — it does NOT write source code (that is `/devtdd`'s job) and does NOT modify `ARCHITECTURE.md` or `LANGUAGE.md` (owned by `/arch-design` and `/arch-align` respectively). It MAY read `BRD.md` for business context. When writing `module.md §3` (runtime behavior), arch-detail MUST compare against `ARCHITECTURE.md §2.x`. If any semantic conflict exists, arch-detail MUST write an **Architecture Discrepancy (AD)** to `T{N}.md → Architecture Discrepancies → arch-design section` — it must NOT directly modify ARCHITECTURE.md. The AD should include: the conflicting component name, ARCHITECTURE.md's current description, module.md's refined description, and suggested resolution.

## Prevention Rules (from AD history)

> These rules prevent recurring issues discovered during arch-review audits. See reference.md §Prevention Cases for details.

1. **Design-Only Sections**: DESIGN.md Diagnosis Checklist (§7) MUST contain only design-level architectural constraints (import rules, interface signatures, structural invariants). NEVER mix in implementation status tracking (`[x]`/`[ ]` with Task references like "Task 10 ✅"). Implementation status is tracked exclusively in kanban T{N}.md.
2. **Verifiable Task Descriptions**: DESIGN.md §5 Task Summary descriptions MUST accurately reflect the implementation approach. Do not describe a component as "standalone binary" if it's actually a driving adapter, or imply a separate process when it's embedded. Cross-check descriptions against the module.md files for consistency.

---

## 🚶 Steps to Execute

1. **Read the Blueprints**: Read `docs/bc/<bc-slug>/align/LANGUAGE.md`, `docs/bc/<bc-slug>/align/BRD.md`, and `docs/bc/<bc-slug>/design/ARCHITECTURE.md` to establish strict scope, naming, and boundaries. Read `docs/bc/<bc-slug>/kanban/BOARD.md` to find the current task. If `ARCHITECTURE.md` or `BOARD.md` is missing, **halt** and instruct the user to run `/arch-design` first.

2. **Generate Database Schema (DDL)**: Generate DDL statements (PostgreSQL by default) that reflect the **Data Mapper** design. Persistence-side names may differ from domain names — record the mapping explicitly. Design indexes based on Use Case query patterns (see reference.md §3.5 Index Design Strategy).

3. **Apply Design Patterns (GoF)**: For each Use Case in `ARCHITECTURE.md`, evaluate variability and propose the appropriate GoF pattern with explicit rationale:
   - Strategy → swappable algorithms (retry, pricing, path resolution)
   - Factory → complex aggregate construction
   - Observer / Pub-Sub → domain event propagation
   - Decorator → cross-cutting (auth, tracing, retry) without polluting use cases
   - Adapter → wrapping third-party SDKs
   Record `Pattern → Rationale → Affected Components` in the output.

4. **Generate Code Structures (per module)**: For each module identified in ARCHITECTURE.md's port table:
   a. Create `detail/modules/<module>/module.md` containing:
      - Domain entities and value objects for this module
      - Port interface signatures (full Go/Java/Python interface)
      - Application layer transaction scripts
      - Infrastructure adapter skeleton with Data Mapper
      - GoF patterns applied to this module with rationale
      - Interface Contracts Index table linking to each `interfaces/<method>.md`
      - **Vertical-Slice Tasks** for this module (tracer bullets, each referencing specific interface contracts)
      - **Test Strategy** (§8): mock boundary decisions, test type breakdown, fixture strategy, contract-to-test mapping (see reference.md §0A Test Strategy)
   b. For each method in the module's port interface, create `detail/modules/<module>/interfaces/<method>.md` containing:
      - Method signature (code block)
      - Input contract (parameters, preconditions)
      - Output contract (return type, postconditions)
      - Error mapping (domain sentinel → when)
      - Edge cases
      - Acceptance test scenarios (Given/When/Then)

   c. **REST API Contract Generation (v3.1.0+)**: For modules exposing REST endpoints, generate OpenAPI 3.1 contract fragments:
      - Map port methods to HTTP operations (List→GET, Create→POST, etc.)
      - Use RFC 7807 Problem Details for error responses
      - Define pagination strategy (offset-based default, cursor for large datasets)
      - Add OpenAPI fragment to each module's `interfaces/<method>.md`
      See [references/api-contract-standards.md](references/api-contract-standards.md) for OpenAPI 3.1 templates and naming conventions.

   d. **Security Checkpoint (v3.1.0+)**: After completing each module's design, run STRIDE threat analysis (§0) then the security checklist:
      - STRIDE threat modeling: evaluate Spoofing/Tampering/Repudiation/Info Disclosure/DoS/Elevation for each component
      - Security design patterns: Circuit Breaker, Rate Limiter, Audit Trail, etc.
      - Input validation: types/lengths/formats defined at adapter boundary
      - Authentication & authorization: mechanism defined, checks in use case layer
      - Data protection: encryption specified, no hardcoded secrets
      - Error handling: RFC 7807 format, no stack traces
      - Dependencies: pinned versions, CVE scanning
      Security gaps are **blockers** — resolve before `/devtdd`. See [references/security-checkpoint.md](references/security-checkpoint.md) for STRIDE analysis and the full checklist.

5. **Compile DESIGN.md Index**: Compile global outputs (Steps 2–3) and the module index into `docs/bc/<bc-slug>/detail/DESIGN.md`. The index contains:
   - Header with cross-refs, target language, date
   - DDL (global schema)
   - GoF Pattern Decisions (global table)
   - Package Layout (final tree)
   - Module Index table (links to each `detail/modules/<module>/module.md`)
   - Task Summary table (one row per task, linking to the module.md that contains it)
   - DI Wiring (composition root)
   - Diagnosis Checklist (global)
   Do **not** append to `ARCHITECTURE.md`. Task details live in each `module.md`, not in the index.

6. **Redo Protocol (Code↔Design Delta Assessment)**: If the target BC already has source code (check for `cmd/`, `internal/`, `src/` directories or equivalent), this is a **redo** — not a greenfield design. In this case, after completing Steps 1–5, perform the following before marking Phase 3 complete:
   1. **Scan existing code** against the new design: compare struct names, interface signatures, package layout, port interfaces, and composition root wiring in the code against DESIGN.md §3 Package Layout and §6 DI Wiring.
   2. **Produce a Code↔Design Delta Table** listing each discrepancy:
      - `Location` (file:line), `Code State` (what exists), `Design State` (what should exist), `Severity` (Critical/Warning), `Suggested Fix`
   3. **Generate refactoring tasks** or append to existing Task Summary rows: if the delta is significant (3+ Critical items), create dedicated "Code Alignment" tasks in DESIGN.md §5 with Status ☐. If minor (≤2 Warning items), append DoD items to existing tasks.
   4. **Scan ARCHITECTURE.md Mermaid participant aliases**: grep `ARCHITECTURE.md` for `participant .* as .*` declarations. Compare each alias against the current port names in LANGUAGE.md and the ARCHITECTURE.md port table (§1.2). Flag and fix any alias that uses a banned/old name (e.g., `AOSStore` when the current port is `AOSLoader/AOSSaver/AOSChecker`).
   5. **Upstream Consistency Gate — PRE** (Pre-Write Verification): Before writing any `module.md §3` that describes runtime behavior (responsibilities, method flows, data paths), grep `ARCHITECTURE.md` for the same component and read all §2.x sections that describe its runtime behavior. Diff the intended module.md §3 behavior against ARCHITECTURE.md §2.x. If any semantic conflict exists, record it for AD generation in the POST step.
   6. **Upstream Consistency Gate — POST** (Post-Write AD Generation): After writing all module.md files, for each module whose §3 refined, transferred, or removed a runtime responsibility compared to ARCHITECTURE.md §2.x, generate an **Architecture Discrepancy (AD)** in `T{N}.md → Architecture Discrepancies → arch-design section`. The AD MUST include: (a) component name, (b) ARCHITECTURE.md current description, (c) module.md refined description, (d) impact assessment. Also check `LANGUAGE.md` responsibility tables — if they describe the same behavior and conflict, include in the same AD. Output all generated ADs to the user and recommend running `/arch-design` to resolve before `/devtdd`.
   7. **Output the delta summary** to the user and recommend `/devtdd` to execute the alignment tasks before proceeding.
   8. **Do NOT mark Phase 3 complete** until the user confirms whether to proceed with the delta tasks or defer them.

   If no source code exists (greenfield), skip this step entirely.

7. **Post-Write Verification**: After writing DESIGN.md and all module/contract files, perform these integrity checks before proceeding to the hand-off:
   1. **Line count check**: `wc -l DESIGN.md` — confirm the line count is within the expected range (not truncated, not appended with stale content). If the file was rewritten, verify the old content is fully gone (no residual duplicate sections).
   2. **Old terminology grep**: `grep -rn "<banned-term>" design/ DESIGN.md` for every term listed in LANGUAGE.md's banned/deprecated synonyms section. Any match is a blocker — fix before proceeding.
   3. **File end sanity**: Read the last 5 lines of DESIGN.md to confirm the file ends cleanly (no truncation mid-sentence, no orphaned markdown table rows).
   4. **Upstream Consistency AD check**: For each module whose §3 describes runtime behavior, grep both `ARCHITECTURE.md` and the module's `module.md` for the same component name. If behavioral descriptions are semantically misaligned and no AD has been generated yet, generate one now routed to `/arch-design`. This is a **blocker** — the AD must be output to the user before proceeding.

8. **Update kanban**: Update `kanban/tasks/T{N}.md` (References → detail section, Status → done, Change History) and move T{N} to `done` in `kanban/BOARD.md`. If the Redo Protocol (Step 6) produced delta tasks, note this in the Change History.

9. **Hand-off Trigger**: Once the user confirms the design, output:

   > **"Detailed design written to `DESIGN.md` (index) + `detail/modules/` (module-level design + interface contracts + vertical-slice tasks). T{N} detail → done. Architecture pipeline complete."**
   >
   > **If Redo Protocol produced Upstream Consistency ADs:**
   > - `/arch-design`: N items (AD-xxx, ...)
   > Recommend running `/arch-design` to resolve ADs before `/devtdd`.
   >
   > **Otherwise:**
   > Enter `/devtdd` to start red-green-refactor on a specific task (tasks defined in `detail/modules/<module>/module.md`), or `/arch-review` to run architecture audit.

---

## Manifest Protocol

### On Startup

1. Read `docs/bc/<bc-slug>/kanban/BOARD.md` (if it exists).
2. Find own row (`arch-detail`). If `doing` has a task → continue. If `doing` is empty and `new` has tasks → pick leftmost. If both empty → halt: "No tasks for detail. Run `/arch-align` + `/arch-design` first."
3. Read `kanban/tasks/T{N}.md` → check References for upstream files.
4. **AD Check**: Scan `Architecture Discrepancies → arch-detail` section. If unresolved AD entries exist → enter AD fix mode: read AD description, fix only what's required, mark Resolved. Skip remaining startup steps.
5. **Migration Mode Detection (v3.3.0+)**: Before upstream halt, check:
   - `detail/DESIGN.md` is empty or missing
   - Source code directories exist (`internal/`, `domain/`, `cmd/`, or language equivalents)
   - `T{N}.md` References has `(migration)` tag
   If ALL conditions met → **enter Migration Mode**: Skip upstream halt. Read source code + ARCHITECTURE.md + LANGUAGE.md + BRD.md → reverse-engineer modules, interfaces, contracts → generate DESIGN.md + modules/ + interfaces/. Present to user for confirmation. See [arch-init reference.md](../arch-init/reference.md) §10 Migration Mode.
   If NOT in migration mode → continue with normal upstream check below.
6. **Upstream check**: Verify arch-design has T{N} in `done`. If not → halt: "Upstream arch-design has not completed T{N}. Run `/arch-design` first."
7. **Handover removal**: If T{N} exists in arch-design's `done` column on BOARD.md → remove it.
8. Read upstream files via T{N}.md References (ARCHITECTURE.md + BRD.md + LANGUAGE.md).
9. **Idempotent check** (if status was already doing/done): Read own existing DESIGN.md + module files. Read AD entries. Identify delta — skip completed work, only execute what's missing or needs fixing.
10. Move T{N} from `new` to `doing` in BOARD.md (if not already).
11. **BC Selection Protocol** (when user does not specify a BC):
    - Read `AGENTS.md` BC registry and list all registered BCs.
    - If only one BC exists, use it automatically.
    - If multiple BCs exist, ask the user which BC to target.
12. Verify `docs/bc/<bc-slug>/design/ARCHITECTURE.md` exists. Do **not** load any prior `DESIGN.md` unless the user explicitly asks to revise it.

### On Completion

1. Write `docs/bc/<bc-slug>/detail/DESIGN.md` as the index file.
2. Create `docs/bc/<bc-slug>/detail/modules/` hierarchy with per-module `module.md` and per-method `interfaces/<method>.md` files.
3. Update `kanban/tasks/T{N}.md`:
   - Fill in References → detail section with DESIGN.md + modules links.
   - Set Status row: detail = done + Completed date.
   - Mark any AD entries targeting arch-detail as Resolved (if not already).
   - Append Change History entry at top.
4. Move T{N} from `doing` to `done` in `kanban/BOARD.md`.
5. **Archive check**: If ALL skills in T{N}.md Status are done AND no unresolved Architecture Discrepancy entries exist in T{N}.md → add T{N} to BOARD.md Archive table and remove from Board table.
6. **Migration task chaining (v3.3.0+)**: If T{N}.md has `(migration)` tag → also add T{N} to `devtdd` row, `new` column on BOARD.md.
7. `DESIGN.md` header must include:
   - Cross-reference link to `ARCHITECTURE.md` (Phase 2 boundaries).
   - Target language declaration.
   - Last updated date.

## Kanban Protocol

See [kanban-spec.md](../arch-conventions/references/kanban-spec.md) for Startup/Completion/Redo sequences and T{N}.md structure.

See [shared-constraints.md](../arch-conventions/references/shared-constraints.md) for pipeline-wide rules: Document Ownership (§1), Restricted Tool Surface (§2), No Source Code Modification (§3), OVERRIDE Protocol (§5), Upstream Halt (§6).

---

## 📎 Additional Resources

For detailed templates and language-specific golden rules, see [reference.md](reference.md):

- **Per-Language Best Practices** — Go / Java / Python golden rules + code skeletons + diagnosis checklists.
- **GoF Pattern Quick Map** — when to apply each pattern in a Clean Architecture context.
- **DDL Conventions** — naming, mapping table, audit columns, soft-delete policy.
- **Vertical-Slice Task Template** — title, layers touched, acceptance test, definition of done.
- **Pre-Output Self-Audit** — 8-item checklist to run before delivering.

For API contract standards and security checkpoint (v3.1.0+), see the `references/` subdirectory:
- [references/api-contract-standards.md](references/api-contract-standards.md) — OpenAPI 3.1 templates + RFC 7807 + pagination + versioning
- [references/security-checkpoint.md](references/security-checkpoint.md) — pre-implementation security review checklist
- [references/examples.md](references/examples.md) — Golden examples: DESIGN.md index, module.md, port interface, task DoD
