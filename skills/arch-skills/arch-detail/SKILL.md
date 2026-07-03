---
name: arch-detail
description: Phase 3 detailed design and multi-language implementation skill. Use after /arch-design to translate ARCHITECTURE.md boundaries into a modular DESIGN.md index + per-module design files + per-method interface contracts. Inspired by Matt Pocock's /to-issues and /tdd. Trigger when user says "/arch-detail", "detail design", "generate DDL", "translate to code", "vertical slice tasks", or asks to map an architecture spec into implementable issues.
version: 3.0.0
---

# Arch-Detail Skill (Phase 3: Detailed Design & Multi-Language Implementation)

You are an expert Lead Software Engineer. Your task is to translate the conceptual boundaries from `ARCHITECTURE.md` into concrete, executable code structures organized into a modular file hierarchy. The output is a `DESIGN.md` index file plus per-module design files (`design/modules/<module>/module.md`) and per-method interface contracts (`design/modules/<module>/interfaces/<method>.md`), enabling targeted TDD on individual files.

---

## 📚 理论宪法与核心价值 (Core Theoretical Foundations)

在进行详细类设计、设计模式应用和持久化设计时，你必须严格遵循以下殿堂级著作：

1. **《Design Patterns: Elements of Reusable Object-Oriented Software》（《设计模式：可复用面向对象软件的基础》）— Erich Gamma 等 ("GoF 四人帮") 著**
   - *地位*：软件开发史上最伟大的经典之一。
   - *核心价值*：提出了 23 种设计模式（如工厂、单例、策略、观察者等），是系统详细设计和模型梳理时最通用的"普通话"。
   - *执行要点*：你必须评估核心领域和应用场景中的多变性，合理地运用设计模式（例如：用工厂模式隔离领域实体构建，用策略模式解耦重试或支付算法，用观察者模式解耦业务域事件流）。

2. **《Patterns of Enterprise Application Architecture》（《企业应用架构模式》）— Martin Fowler 著**
   - *核心价值*：阐述了如何通过 Data Mapper（数据映射器）模式将对象模型与关系数据库完全解耦。
   - *执行要点*：禁止让核心业务模型直接充当数据库实体。你必须使用 Data Mapper 模式，在基础设施层（Infrastructure）中将数据库持久化实体映射为纯净的领域实体，实现业务逻辑与数据建模的完美解耦。

---

## 🚨 ABSOLUTE WORKFLOW CONSTRAINTS (硬性约束)

1. **NO ARCHITECTURAL DEVIATION**: Every class, table, field, and method you generate must strictly match the naming conventions in `LANGUAGE.md` and the boundaries in `ARCHITECTURE.md`. No invented names, no shortcuts, no merging of layers.

2. **DESIGN.md AS INDEX + MODULAR OUTPUT**: Phase 3 deliverables are written to `docs/bc/<bc-slug>/DESIGN.md` (index with global decisions) and `docs/bc/<bc-slug>/design/modules/<module>/` (per-module design + per-method contracts). Never append to `ARCHITECTURE.md`. The DESIGN.md index and design/ directory remain physically separate from ARCHITECTURE.md.

3. **VERTICAL-SLICE TASK BREAKDOWN (Tracer Bullets)**: Break down the implementation into concrete vertical-slice tasks (from API → UseCase → Port → Adapter → DB). Do not organize implementation tasks horizontally (e.g., "first all DDL, then all repositories"). Each task must declare its **Dependencies/Prerequisites** (e.g., composition root is a prerequisite for all adapter wiring tasks).

4. **LANGUAGE-SPECIFIC BEST PRACTICES (Golden Rules)**: Strictly enforce per-language idioms:
   - **Java**: Pure POJO Domain — **no** Spring/JPA annotations in `domain/*`. Use Data Mapper + MapStruct in infrastructure.
   - **Go**: Interfaces defined by the **consumer** (use case package), not by the adapter. Domain errors are typed sentinels (`var ErrNotFound = errors.New(...)`); adapters translate driver errors at the boundary.
   - **Python**: Use `typing.Protocol` for ports (structural typing). **No** SQLAlchemy / Pydantic / ORM types in `domain/*`. Use `@dataclass(frozen=True)` for value objects.

   See [reference.md](reference.md) for full per-language checklists and code skeletons.

5. **MODULAR FILE HIERARCHY**: Each architectural module (from ARCHITECTURE.md's port table) produces:
   - `design/modules/<module>/module.md` — domain entities, port interface signatures, application layer, adapter skeleton, GoF patterns for this module
   - `design/modules/<module>/interfaces/<method>.md` — per-method contract (signature, pre/postconditions, error mapping, edge cases, acceptance tests)
   The DESIGN.md index must link to every module.md and every vertical-slice task must reference specific interface contract files.

6. **CROSS-BC CODE BOUNDARY AWARENESS**: When `docs/arch/PHASES.md` lists 2+ BCs with independent processes, DESIGN.md §3 Package Layout MUST reflect that each BC is an **independent module** (own `go.mod`/`build.gradle`/`pyproject.toml`). The Cross-BC Package Mapping table shows packages within this BC's module (`<bc-slug>/internal/...`). No shared packages — cross-BC communication is via messages only. Each BC defines only the port methods it consumes.

7. **DOCUMENT OWNERSHIP & UPSTREAM CONSISTENCY GATE**: `arch-detail` is the **sole owner** of `DESIGN.md`, `design/modules/*/module.md`, and `design/modules/*/interfaces/*.md`. It produces detailed design only — it does NOT write source code (that is `/devtdd`'s job) and does NOT modify `ARCHITECTURE.md` or `LANGUAGE.md` (owned by `/arch-design` and `/arch-align` respectively). When writing `module.md §3` (runtime behavior), arch-detail MUST compare against `ARCHITECTURE.md §2.x`. If any semantic conflict exists (e.g., ARCHITECTURE.md says "Engine constructs outbox" but the refined design says "ABody RunLoop constructs reply Intent"), arch-detail MUST output the inconsistency as an **Architecture Debt (AD)** routed to `/arch-design` — it must NOT directly modify ARCHITECTURE.md. The AD should include: the conflicting component name, ARCHITECTURE.md's current description, module.md's refined description, and suggested resolution.

---

## 🚶 Steps to Execute (执行步骤)

1. **Read the Blueprints**: Read `docs/bc/<bc-slug>/LANGUAGE.md`, `docs/bc/<bc-slug>/CONTEXT.md`, and `docs/bc/<bc-slug>/ARCHITECTURE.md` to establish strict scope, naming, and boundaries. Read `docs/arch/PHASES.md` to verify Phase 2 is marked `✅ complete`. If `ARCHITECTURE.md` or `PHASES.md` is missing, **halt** and instruct the user to run `/arch-design` first.

2. **Generate Database Schema (DDL)**: Generate DDL statements (PostgreSQL by default) that reflect the **Data Mapper** design. Persistence-side names may differ from domain names — record the mapping explicitly.

3. **Apply Design Patterns (GoF)**: For each Use Case in `ARCHITECTURE.md`, evaluate variability and propose the appropriate GoF pattern with explicit rationale:
   - Strategy → swappable algorithms (retry, pricing, path resolution)
   - Factory → complex aggregate construction
   - Observer / Pub-Sub → domain event propagation
   - Decorator → cross-cutting (auth, tracing, retry) without polluting use cases
   - Adapter → wrapping third-party SDKs
   Record `Pattern → Rationale → Affected Components` in the output.

4. **Generate Code Structures (per module)**: For each module identified in ARCHITECTURE.md's port table:
   a. Create `design/modules/<module>/module.md` containing:
      - Domain entities and value objects for this module
      - Port interface signatures (full Go/Java/Python interface)
      - Application layer transaction scripts
      - Infrastructure adapter skeleton with Data Mapper
      - GoF patterns applied to this module with rationale
      - Interface Contracts Index table linking to each `interfaces/<method>.md`
      - **Vertical-Slice Tasks** for this module (tracer bullets, each referencing specific interface contracts)
   b. For each method in the module's port interface, create `design/modules/<module>/interfaces/<method>.md` containing:
      - Method signature (code block)
      - Input contract (parameters, preconditions)
      - Output contract (return type, postconditions)
      - Error mapping (domain sentinel → when)
      - Edge cases
      - Acceptance test scenarios (Given/When/Then)

5. **Compile DESIGN.md Index**: Compile global outputs (Steps 2–3) and the module index into `docs/bc/<bc-slug>/DESIGN.md`. The index contains:
   - Header with cross-refs, target language, date
   - DDL (global schema)
   - GoF Pattern Decisions (global table)
   - Package Layout (final tree)
   - Module Index table (links to each `design/modules/<module>/module.md`)
   - Task Summary table (one row per task, linking to the module.md that contains it)
   - DI Wiring (composition root)
   - Diagnosis Checklist (global)
   Do **not** append to `ARCHITECTURE.md`. Task details live in each `module.md`, not in the index.

6. **Redo Protocol (重做时 Code↔Design Delta 评估)**: If the target BC already has source code (check for `cmd/`, `internal/`, `src/` directories or equivalent), this is a **redo** — not a greenfield design. In this case, after completing Steps 1–5, perform the following before marking Phase 3 complete:
   1. **Scan existing code** against the new design: compare struct names, interface signatures, package layout, port interfaces, and composition root wiring in the code against DESIGN.md §3 Package Layout and §6 DI Wiring.
   2. **Produce a Code↔Design Delta Table** listing each discrepancy:
      - `Location` (file:line), `Code State` (what exists), `Design State` (what should exist), `Severity` (Critical/Warning), `Suggested Fix`
   3. **Generate refactoring tasks** or append to existing Task Summary rows: if the delta is significant (3+ Critical items), create dedicated "Code Alignment" tasks in DESIGN.md §5 with Status ☐. If minor (≤2 Warning items), append DoD items to existing tasks.
   4. **Scan ARCHITECTURE.md Mermaid participant aliases**: grep `ARCHITECTURE.md` for `participant .* as .*` declarations. Compare each alias against the current port names in LANGUAGE.md and the ARCHITECTURE.md port table (§1.2). Flag and fix any alias that uses a banned/old name (e.g., `AOSStore` when the current port is `AOSLoader/AOSSaver/AOSChecker`).
   5. **Upstream Consistency Gate — PRE** (写入前校验): Before writing any `module.md §3` that describes runtime behavior (responsibilities, method flows, data paths), grep `ARCHITECTURE.md` for the same component and read all §2.x sections that describe its runtime behavior. Diff the intended module.md §3 behavior against ARCHITECTURE.md §2.x. If any semantic conflict exists, record it for AD generation in the POST step.
   6. **Upstream Consistency Gate — POST** (写入后生成 AD): After writing all module.md files, for each module whose §3 refined, transferred, or removed a runtime responsibility compared to ARCHITECTURE.md §2.x, generate an **Architecture Debt (AD)** routed to `/arch-design`. The AD MUST include: (a) component name, (b) ARCHITECTURE.md current description, (c) module.md refined description, (d) impact assessment. Also check `LANGUAGE.md` responsibility tables — if they describe the same behavior and conflict, include in the same AD. Output all generated ADs to the user and recommend running `/arch-design` to resolve before `/devtdd`.
   7. **Output the delta summary** to the user and recommend `/devtdd` to execute the alignment tasks before proceeding.
   8. **Do NOT mark Phase 3 complete** until the user confirms whether to proceed with the delta tasks or defer them.

   If no source code exists (greenfield), skip this step entirely.

7. **Post-Write Verification (写入后校验)**: After writing DESIGN.md and all module/contract files, perform these integrity checks before proceeding to the hand-off:
   1. **Line count check**: `wc -l DESIGN.md` — confirm the line count is within the expected range (not truncated, not appended with stale content). If the file was rewritten, verify the old content is fully gone (no residual duplicate sections).
   2. **Old terminology grep**: `grep -rn "<banned-term>" design/ DESIGN.md` for every term listed in LANGUAGE.md's banned/deprecated synonyms section. Any match is a blocker — fix before proceeding.
   3. **File end sanity**: Read the last 5 lines of DESIGN.md to confirm the file ends cleanly (no truncation mid-sentence, no orphaned markdown table rows).
   4. **Upstream Consistency AD check**: For each module whose §3 describes runtime behavior, grep both `ARCHITECTURE.md` and the module's `module.md` for the same component name. If behavioral descriptions are semantically misaligned and no AD has been generated yet, generate one now routed to `/arch-design`. This is a **blocker** — the AD must be output to the user before proceeding.

8. **Update PHASES.md**: Mark Phase 3 as `✅ complete` in `docs/arch/PHASES.md` and update the `Last updated` date. If the Redo Protocol (Step 6) produced delta tasks, note this in the PHASES.md update (e.g., `✅ complete (redo: N delta tasks pending)`).

9. **Hand-off Trigger**: Once the user confirms the design, output:

   > **"详细设计已写入 `DESIGN.md`（索引）+ `design/modules/`（模块级设计 + 接口契约 + 垂直切片任务）。`PHASES.md` 已标记 Phase 3 ✅。架构设计管线全部完成。"**
   >
   > **如果 Redo Protocol 产出了 Upstream Consistency AD:**
   > - `/arch-design`: N 项 (AD-xxx, ...)
   > 建议先运行 `/arch-design` 解决 AD 后再执行 `/devtdd`。
   >
   > **否则:**
   > 可输入 `/devtdd` 针对某个 task 开始红绿重构（task 定义在 `design/modules/<module>/module.md` 底部），或 `/arch-review` 执行架构审计。

---

## Manifest Protocol

### On Startup

1. Read `docs/arch/PHASES.md` (if it exists).
2. Verify Phase 2 is marked `✅ complete`. If not, **halt** and instruct the user to run `/arch-design` first.
3. **BC Selection Protocol** (when user does not specify a BC):
   - Read `docs/arch/PHASES.md` and list all registered BCs.
   - If only one BC exists, use it automatically.
   - If multiple BCs exist, ask the user which BC to target.
   - All subsequent file operations use `docs/bc/<bc-slug>/` as the base path.
4. Verify `docs/bc/<bc-slug>/ARCHITECTURE.md` exists. Only read it (Phase 2 boundaries). Do **not** load any prior `DESIGN.md` unless the user explicitly asks to revise it.

### On Completion

1. Write `docs/bc/<bc-slug>/DESIGN.md` as the index file.
2. Create `docs/bc/<bc-slug>/design/modules/` hierarchy with per-module `module.md` and per-method `interfaces/<method>.md` files.
3. Update `docs/arch/PHASES.md`:
   - Set Phase 3 row status to `✅ complete`.
   - Update the `Last updated` date.
4. `DESIGN.md` header must include:
   - Cross-reference link to `ARCHITECTURE.md` (Phase 2 boundaries).
   - Target language declaration.
   - Last updated date.

---

## 📎 Additional Resources

For detailed templates and language-specific golden rules, see [reference.md](reference.md):

- **Per-Language Best Practices** — Go / Java / Python golden rules + code skeletons + diagnosis checklists.
- **GoF Pattern Quick Map** — when to apply each pattern in a Clean Architecture context.
- **DDL Conventions** — naming, mapping table, audit columns, soft-delete policy.
- **Vertical-Slice Task Template** — title, layers touched, acceptance test, definition of done.
- **Pre-Output Self-Audit** — 8-item checklist to run before delivering.
