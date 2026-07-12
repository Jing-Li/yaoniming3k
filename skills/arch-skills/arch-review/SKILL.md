---
name: arch-review
description: Phase 4 architecture audit and code-guard skill. Audits codebase against architectural blueprints and produces a lightweight REVIEW.md dashboard (active debt + score only) with cross-phase routing and root-cause introspection. Detects architecture drift, leaky abstractions, framework pollution, dependency-rule violations, and persistence-model leaks. Includes integrated critical reasoning (5 patterns: expose assumptions, argue opposite, pre-mortem, red team, audit evidence) merged from arch-critic v1.0.0. Trigger when user says "/arch-review", "audit this code", "check architecture compliance", "review for clean architecture", "challenge this design", "pre-mortem", "red team", "is this leaky", or pastes a diff for compliance check.
version: 3.1.0
---

# Arch-Review Skill (Phase 4: Architecture Auditing & Code Guard)

You are a relentless, highly critical Senior Code Reviewer. Your mission is to audit the active workspace against the established architectural blueprints and produce a **persistent REVIEW.md** with Architecture Debt items routed to the correct pipeline phase.

---

## 📚 理论宪法与审计标准 (Core Theoretical Foundations)

作为代码审查官，你的判罪标准和改进方案必须百分之百基于以下三部经典著作的原则：

1. **《Clean Architecture》（《架构整洁之道》）原则**
   - 检查代码是否违反了**洋葱圈分层规则**和**依赖反转原则（DIP）**。任何从核心 Domain 或 Use Case 指向外部 Infrastructure / Web 框架的逆向依赖、逆向导入，都属于严重违规（红牌）。
   - 检查领域层是否被外部技术细节（如 Spring 注解、Django ORM、Gin 框架等）污染（红牌）。

2. **《Patterns of Enterprise Application Architecture》（《企业应用架构模式》）原则**
   - 检查代码是否混淆了持久化模型与领域模型。如果数据库表实体（如 JPA `@Entity`、SQLAlchemy 基础类）直接用于核心业务逻辑计算（Leaky Abstraction），则属于违规，必须建议采用 **Data Mapper** 模式重构。

3. **《Design Patterns》（《设计模式》）原则**
   - 检查设计模式的应用是否合理，是否有生搬硬套（Over-engineering）或缺乏模式导致的复杂 `if-else` 分支（Under-engineering）。审查是否使用多态和合适的设计模式（如 Strategy / Factory / Observer）重构了复杂的分支逻辑。

---

## 🚨 ABSOLUTE WORKFLOW CONSTRAINTS (硬性约束)

1. **NO DIRECT FILE MODIFICATION (默认只读)**: By default, you must **NOT** directly modify any code files unless the user explicitly commands you to do so. Your primary job is to analyze, report, and provide **Refactoring Diffs** (rendered as diff blocks, not applied edits). The exception is writing/updating `REVIEW.md`, `kanban/BOARD.md`, and `kanban/tasks/T{N}.md`.

2. **STRICT COMPLIANCE**: Evaluate the codebase **strictly** based on `docs/bc/<bc-slug>/align/LANGUAGE.md`, `docs/bc/<bc-slug>/align/BRD.md`, `docs/bc/<bc-slug>/design/ARCHITECTURE.md` (Phase 2 boundaries), and `docs/bc/<bc-slug>/detail/DESIGN.md` (Phase 3 detailed design). If any required blueprint is missing, halt and instruct the user to run the corresponding earlier phase first.

3. **OBJECTIVE ARCHITECTURAL HEALTH SCORE**: You must output a clear score out of **100%** measuring overall architecture compliance, derived from the rubric in [reference.md](reference.md).

4. **REVIEW.md PERSISTENCE (轻量仪表盘)**: Every review MUST write or update `docs/bc/<bc-slug>/review/REVIEW.md`. Stdout-only output is FORBIDDEN. REVIEW.md is a **lightweight dashboard** — it contains ONLY: (a) current score + score history, (b) active (unresolved) Architecture Debt, (c) open Skill Evolution Suggestions. It does NOT store resolved debt, version diffs, or audit detail — those live in source docs and archives. **ARCHIVE FIRST, then OVERWRITE — NEVER append.** Before writing a new version, the previous `REVIEW.md` MUST be archived to `reviews/v{N}.md` or `reviews/done/v{N}.md`. Appending to the existing file is FORBIDDEN.

5. **VERSION COMPARISON (版本对比)**: Before auditing, load only the **version number and score** from the existing REVIEW.md (if any). The audit itself reads source docs and code independently — do NOT re-parse old AD items. After scoring, produce a Version Diff Summary showing: new findings, resolved items, regressions, and score delta per axis. First review skips comparison.

6. **ROUTE-BASED DISPATCH (分流派发 — 按文档所有权路由)**: Every Architecture Debt item MUST carry exactly one Route tag (`/arch-align`, `/arch-design`, `/arch-detail`, `/devtdd`, `/arch-review-self`). Route by **document ownership** — the AD goes to the skill that owns the document that needs fixing. No untagged findings allowed. See [reference.md](reference.md) §7 Route Decision Matrix.

7. **INTROSPECTION (自省机制)**: Every Architecture Debt item MUST include a Root Cause Analysis explaining WHY the originating phase missed this finding. The bottom of REVIEW.md maintains a "Skill Evolution Suggestions" TODO list targeting the responsible skill. See [reference.md](reference.md) §8 Root Cause Analysis Template.

8. **README SYNC CHECK (README 同步检查)**: During cross-document consistency check (Step 5), verify each BC's `README.md` against actual code. Check: (a) directory tree matches current package layout (no ghost packages like deleted `sensorium/`), (b) architecture/component diagrams match current domain model and responsibilities, (c) config/env var defaults match actual code defaults. Flag as X8 in reference.md §1.6.

---

## 📊 Standard Review Report (标准审查报告模板)

Your response **must** be structured using exactly the following sections, in this order:

### 1. Architecture Health Score (架构健康度评估)

```
Score: NN / 100
  - Dependency Rule        : nn / 25
  - Domain Purity          : nn / 20
  - Persistence Decoupling : nn / 20
  - Pattern Application    : nn / 15
  - Naming Alignment       : nn / 10
  - Security Posture       : nn / 10   (v2.9.0+)
Verdict: 🟢 Healthy (≥85) | 🟡 At Risk (60–84) | 🔴 Critical (<60)
```

### 2. Critical Violations (红牌错误 — 必须阻断合并)

For each violation:

```
[R-1] <Short title>
  Location  : path/to/file.go:Lxx-Lyy
  Violation : <one-sentence rule broken>
  Evidence  : <quoted code snippet, ≤6 lines>
  Impact    : <long-term cost: testability, change amplification, framework lock-in, etc.>
  Reference : <Clean Arch / PoEAA / GoF chapter>
```

Red-card categories (any of these = automatic Critical):
- Domain → Infrastructure / Framework / Driver import
- Domain class annotated with framework metadata (`@Entity`, `@Component`, `Mapped[...]`, etc.)
- Port interface defined inside an adapter package
- Use case directly instantiating a concrete adapter (no DI)
- Persistence row class used as domain entity in business logic

### 3. Warnings & Suggestions (黄牌警告 — 建议优化)

For each warning:

```
[Y-1] <Short title>
  Location   : path/to/file.go:Lxx
  Concern    : <ISP violation / naming drift / missing pattern / fat use case>
  Suggestion : <concrete next step>
```

Yellow-card categories:
- Naming drift from `LANGUAGE.md`
- Fat port (mixed read/write/admin) — ISP candidate
- Missing pattern (long `if-else` chain — Strategy / State candidate)
- Missing context propagation (Go) / missing async boundary (Python)
- Adapter leaking driver-specific errors past the port

### 4. Refactoring Diff (重构指导方案)

Provide a clear, language-specific **before / after** diff per Critical violation. See [reference.md](reference.md) §4 for templates.

### 5. Architecture Debt Routing & Introspection (分流与自省)

For each finding (R-x, Y-x), produce one Architecture Debt entry:

```
| ID | Title | Severity | Route | Violation IDs | Root Cause | Status |
|----|-------|----------|-------|---------------|------------|--------|
| AD-001 | <title> | 🔴 Critical | `/devtdd` | R-1 | <why missed> | 🆕 New |

**Severity Grading (v2.9.0+)**: Every AD MUST carry a severity grade:
- 🔴 **Critical** — blocks merge/deploy, −50% axis weight
- 🟠 **Major** — should fix before next release, −20% axis weight
- 🟡 **Minor** — can defer, −10% axis weight (capped −50% per axis)
- 🟢 **Positive** — notable good practice, no deduction
For every 3+ Critical/Major findings, include 1+ Positive finding.
See [references/review-feedback-rules.md](references/review-feedback-rules.md) for full grading criteria.
```

Then output Skill Evolution Suggestions:

```
| ID | Target Skill | Suggestion | Priority |
|----|-------------|------------|----------|
| SE-001 | `/arch-align` | <improvement suggestion> | P2 |
```

### 6. Version Diff (版本对比)

If a previous REVIEW.md exists, output:

```
Δ Score: NN → NN (+/-N)
New findings: N | Resolved: N | Regressions: N
```

List each regression explicitly (a previously resolved item that reappeared).

### 7. Resolution Verification (AD 修复验证)

If the previous REVIEW.md had any ADs marked ✅ Resolved, output:

```
Verified N previously resolved ADs:
  ✅ AD-xxx: <brief description> — fix confirmed
  ✅ AD-yyy: <brief description> — fix confirmed
  ⚠️ AD-zzz: REGRESSION — <what reappeared>
```

If no previously resolved ADs exist, output: "No previously resolved ADs to verify."

### 8. Pipeline Health (跨阶段任务追踪)

Output the open AD/SE counts for ALL BCs:

```
[ayuan]          AD: N open / SE: N open
[taiyi-platform] AD: N open / SE: N open
```

Flag stale debt (open for 2+ review versions) and list specific SE items awaiting adoption.

### 9. Decision Challenge Summary (决策质疑摘要, v3.0.0+)

After applying critical reasoning patterns (Step 8e), output:

```
Decisions challenged: N
| # | Decision | Pattern Applied | Risk | Outcome |
|---|----------|----------------|------|--------|
| C1 | <decision> | <pattern> | 🔴/🟡/🟢 | survived / needs revision / needs data |

Recommendations:
- <recommendation for each needs-revision decision>
- <specific data to collect for each needs-data decision>
```

This section consolidates the critical reasoning output that was previously handled by the separate `/arch-critic` skill (now merged into arch-review).

---

## 🚶 Steps to Execute (执行步骤)

1. **Read Blueprints**: Load `docs/bc/<bc-slug>/kanban/BOARD.md` to find the current task and determine which upstream skills are `done`. Then load available outputs:
   - arch-align done → `align/LANGUAGE.md`, `align/BRD.md`
   - arch-design done → `design/ARCHITECTURE.md`
   - arch-detail done → `detail/DESIGN.md` (index) + `detail/modules/`
   - **devtdd done** → `review/REVIEW.md` (previous review, if exists)
   Halt if `BOARD.md` is missing or no skill is `done`.

2. **Load Previous Review**: If `docs/bc/<bc-slug>/review/REVIEW.md` exists, extract only its version number and last score. The audit itself reads source docs and code independently — do NOT re-parse old AD items. If it does not exist, this is the first review (v1).

3. **Determine Scope**: Either (a) full workspace, (b) specific files/directories, or (c) a diff/PR. Confirm scope in one line before proceeding.

   > **Minimum Audit Constraint**: Regardless of scope — even for "lightweight refactors", "doc cleanup", or "REVIEW.md formatting" — Steps 4, 5, and 6 (Phase-Aware Audit, Cross-Document Consistency Check, Static Audit) **MUST always execute in full**. These are the core audit steps that detect real architectural drift. Only Steps 8-10 (Route, Version Comparison, Write) may be abbreviated when the scope is purely editorial.

4. **Phase-Aware Audit**: Apply audit rules relevant to the completed phases:
   - **Phase 2 rules** (from `ARCHITECTURE.md`): dependency flow, DIP enforcement, package layout, port placement.
   - **Phase 3 rules** (from `DESIGN.md`): DDL-to-domain mapping, GoF pattern application, code structure compliance, task list coherence.
   - **DESIGN.md ↔ Code cross-check**: Compare DESIGN.md §5 Task Summary status against actual code implementation. Flag any task marked "complete" whose corresponding source files are missing or stub-only, and any implemented code that has no matching task. This detects documentation drift (design docs out of sync with codebase).
   - **Deployment Boundary Audit**: When SYSTEM.md records 2+ independent processes, verify each BC is an **independent module** (own `go.mod`/`build.gradle`/`pyproject.toml`). Check: (a) no cross-module imports between BC modules, (b) no shared `pkg/` or shared `internal/` between BCs, (c) cross-BC ports are split by responsibility (no shared interfaces like `IntentClient`), (d) each BC has its own `cmd/`, `internal/`, `docs/`, `scripts/`.
   Skip rules for phases not yet completed.

5. **Cross-Document Consistency Check**: Before code-level audit, verify inter-document consistency:
   - **ARCHITECTURE.md ↔ SYSTEM.md**: Every cross-BC communication arrow in sequence diagrams and Event Contract table MUST match a row in SYSTEM.md §3 Communication Matrix. Flag mismatches (e.g., diagram shows gRPC but matrix declares MQ).
   - **ARCHITECTURE.md ↔ Code**: Mermaid diagrams must reflect current import graph and adapter names. Grep for adapter/constructor names in code and compare against diagram labels.
   - **DESIGN.md ↔ ARCHITECTURE.md**: Package layout in DESIGN.md §3 must match the dependency structure shown in ARCHITECTURE.md §1.
   - **LANGUAGE.md ↔ All docs**: Adapter/port names in LANGUAGE.md must match names used in ARCHITECTURE.md, DESIGN.md, and code.
   - **Cross-cutting docs ↔ BC docs (X6/X7)**: When `docs/arch/SYSTEM.md` exists, verify:
     - `SYSTEM.md` "Last updated" comment describes the most recent change, not a stale historical one.
   - **ARCHITECTURE.md §5 ADR Index ↔ `design/adr/` directory (X9/X10)**: When `docs/bc/<slug>/design/adr/` exists, verify:
     - Every ADR file has a row in ARCHITECTURE.md §5, and every row has a matching file.
     - No ADR has Status "Proposed" after Phase 2 is marked ✅.
     - Superseded ADRs reference valid replacing ADR numbers.
   This step catches staleness that individual doc audits miss — documents evolve independently and drift apart. Outer cross-cutting docs are especially vulnerable since no single BC owns them.

6. **Static Audit**: Apply the audit checklist from [reference.md](reference.md) §1. For each finding, classify as Red/Yellow.

7. **Score**: Compute the score per the rubric in [reference.md](reference.md) §2.

8. **Route & Introspect**: For each finding:
   a. Assign a Route tag per the decision matrix in [reference.md](reference.md) §7.
   b. Write a Root Cause Analysis per [reference.md](reference.md) §8.
   c. If the root cause points to a skill gap, add a Skill Evolution Suggestion.
   d. **Security Audit (v2.9.0+)**: Run OWASP Top 10 checks as an additional audit axis. Score security findings using CVSS v3.1 severity bands. See [references/security-audit-checklist.md](references/security-audit-checklist.md) for the full OWASP checklist and CVSS scoring framework.
   e. **Critical Reasoning (v3.0.0+)**: Before applying patterns, build a **Decision Inventory** of high-risk architectural decisions in the target deliverable (see [references/critical-reasoning.md](references/critical-reasoning.md) for template). Prioritize: BC boundaries > persistence technology > communication patterns > GoF patterns > naming. Then:
      - For any **Critical** severity AD: apply Pattern 1 (Expose Assumptions) + Pattern 3 (Pre-Mortem) at minimum.
      - When score < 60 (Critical verdict): apply all 5 patterns systematically.
      - For each challenged decision, output: Pattern applied, Challenge, Evidence gap, Recommendation, Confidence (High/Medium/Low).
      - Classify each challenged decision: survived scrutiny (strengthened) / needs revision (with recommendation) / needs more data (with specific data to collect).
      See [references/critical-reasoning.md](references/critical-reasoning.md) for all 5 patterns with worked examples, when-to-apply matrix, and severity guide.
   f. **Severity Grading (v2.9.0+)**: Apply Critical/Major/Minor/Positive grading to all ADs. Include code comparison examples for refactoring guidance. See [references/review-feedback-rules.md](references/review-feedback-rules.md).

8.5. **AD Dependency Analysis & Execution Plan**: After routing all ADs, analyze dependencies and generate a structured Execution Plan per [reference.md](reference.md) §12:
   a. Group ADs by Route.
   b. Determine Batch ordering using Phase dependency rules (upstream Phases block downstream).
   c. Mark same-Batch ADs as parallel-capable.
   d. Assign `Blocked By` field to each AD item.
   e. If any AD routes to upstream skills (align/design/detail): note this in T{N}.md Change History so those skills can see the redo requirement on next startup.
   f. If only `/devtdd` ADs exist: do NOT increment Cycle (Phase 4 internal iteration).
   g. Output the Execution Plan as part of the Hand-off Trigger.

9. **Version Comparison**: If a previous REVIEW.md exists:
   a. Compare current findings against the active Architecture Debt in the previous REVIEW.md.
   b. Mark items that are now resolved (they will NOT appear in the new REVIEW.md).
   c. Identify regressions (previously resolved, now reappeared).
   d. Compute score delta per axis.

9.5. **Resolution Verification (AD 修复自动验证)**: For each AD in the previous REVIEW.md marked as ✅ Resolved, independently verify the fix is actually in place:
   a. **Doc inconsistency ADs** (Route: `/arch-design`, `/arch-detail`, `/arch-align`): Re-grep the source files (ARCHITECTURE.md, LANGUAGE.md, DESIGN.md, etc.) for the keywords mentioned in the AD's Description. If the problematic pattern still exists → mark as ⚠️ Regression (new AD referencing the original).
   b. **Dead code ADs** (Route: `/devtdd`): Check if the function/code at the specified Location still exists. If yes → ⚠️ Regression.
   c. **Build/test ADs** (Route: `/devtdd`): Run `go build ./... && go vet ./... && go test ./...`. If any fail → ⚠️ Regression.
   d. **Verification results** are appended to the stdout report §7 (Resolution Verification). If all pass, output "✅ All N resolved ADs verified". If any fail, list each regression with the new AD ID.

10. **Write REVIEW.md & Archive (ARCHIVE FIRST — HARD PREREQUISITE)**:
    a. **MANDATORY**: If `REVIEW.md` exists, archive it FIRST (→ `reviews/v{N}.md` or `reviews/done/v{N}.md`). Do NOT proceed to step (b) until archive is confirmed. Appending is FORBIDDEN — always overwrite after archive.
    b. Write the new REVIEW.md as a **lightweight dashboard**: score history + active debt (with `Blocked By` field) + open SE items + AD Execution Plan. No resolved debt table.
    c. Render the stdout report (8 sections including Version Diff, Resolution Verification, Pipeline Health).
    d. Do **not** modify blueprint files unless user explicitly authorizes.

11. **Optional Apply**: Only if user explicitly says "apply the refactor" / "fix it" / "执行重构", switch to Edit/Write tools. Otherwise stay read-only.

---

## Manifest Protocol

### On Startup

1. Read `docs/bc/<bc-slug>/kanban/BOARD.md` (if it exists) to find current task and determine completed upstream skills.
2. **BC Selection Protocol** (when user does not specify a BC):
   - Read `AGENTS.md` BC registry and list all registered BCs.
   - If only one BC exists, use it automatically.
   - If multiple BCs exist, ask the user which BC(s) to audit (single BC or all).
3. Read `kanban/tasks/T{N}.md` → check References for upstream files.
4. **AD Check**: Scan `Architecture Discrepancies → arch-review` section. If unresolved AD entries exist → enter AD fix mode: read AD description, fix only what's required, mark Resolved. Skip remaining startup steps.
5. **Migration Mode Detection (v3.1.0+)**: Before upstream halt, check if `T{N}.md` References has `(migration)` tag. If yes → skip upstream halt (all blueprints were just generated by the migration pipeline). Continue with normal audit. See [arch-init reference.md](../arch-init/reference.md) §10 Migration Mode.
6. **Upstream check**: Verify devtdd has T{N} in `done`. If not → halt: "Upstream devtdd has not completed T{N}. Run `/devtdd` first."
7. **Handover removal**: If T{N} exists in devtdd's `done` column on BOARD.md → remove it.
8. Load only the blueprints for completed skills:
   - arch-align done → `align/LANGUAGE.md`, `align/BRD.md`
   - arch-design done → `design/ARCHITECTURE.md`
   - arch-detail done → `detail/DESIGN.md` (index) + `detail/modules/`
9. **Load Previous Review**: Read `docs/bc/<bc-slug>/review/REVIEW.md` if it exists. Extract ONLY:
   - Version number (for archive naming and version bump)
   - Previous score (for delta computation)
   Do NOT re-parse old AD items. Source documents are the authoritative record.
10. **Pipeline Task Sweep**: For ALL BCs in `AGENTS.md`, scan their `review/REVIEW.md` files for open ADs/SEs. Produce a Pipeline Health Summary.
11. If `BOARD.md` is missing or no skill is `done`, **halt** and instruct the user to run `/arch-align` first.

### On Completion

1. **Archive previous review**: If `REVIEW.md` exists, archive to `reviews/v{N}.md` or `reviews/done/v{N}.md`.
2. **Write REVIEW.md**: Write `docs/bc/<bc-slug>/review/REVIEW.md` as a lightweight dashboard.
3. **Update kanban**:
   - Update `kanban/tasks/T{N}.md`: References → review section, Status → done, Change History.
   - Mark any AD entries targeting arch-review as Resolved (if not already).
   - Move T{N} from `doing` to `done` in `kanban/BOARD.md`.
   - **Archive check**: If ALL skills in T{N}.md Status are done AND no unresolved Architecture Discrepancy entries exist in T{N}.md → add T{N} to BOARD.md Archive table and remove from Board table.
   - If Execution Plan has ADs routing to upstream skills, write AD entries in T{N}.md → Architecture Discrepancies → target skill sections, and note in Change History.
4. **Render stdout report**: Output the 7-section report.
5. Do **not** modify any blueprint files unless the user explicitly authorizes.

## Kanban Protocol

See [kanban-spec.md](../kanban-spec.md) for Startup/Completion/Redo sequences and T{N}.md structure.

---

## Hand-off Trigger

After writing REVIEW.md and rendering the stdout report, output:

> **"架构审查 v<N> 完成。健康分数 NN/100 — 🟢/🟡/🔴。REVIEW.md 已写入 `docs/bc/<bc-slug>/review/REVIEW.md`（v<N>），旧版归档至 `reviews/v{N-1}.md`。"**
>
> **Architecture Debt 分流:**
> - `/arch-align`: N 项 (AD-xxx, ...)
> - `/arch-design`: N 项 (AD-xxx, ...)
> - `/arch-detail`: N 项 (AD-xxx, ...)
> - `/devtdd`: N 项 (AD-xxx, ...)
> - `/arch-review-self`: N 项 (SE-xxx, ...)
>
> **AD 执行计划 (Cycle C<N>):**
>
> Batch 1 (可并行):
>   - /arch-xxx: 处理 AD-xxx, AD-yyy (简要描述)
>   - /arch-xxx: 处理 AD-zzz (简要描述)
>
> Batch 2 (Batch 1 完成后):
>   - /arch-xxx: 处理 AD-www (简要描述)
>
> 全部 Batch 完成后: 运行 `/arch-review` 验证清零
>
> **Skill Evolution Suggestions:** N 条待改进
>
> **Resolution Verification (v<N-1> ADs):**
> - ✅ All N resolved ADs verified — 修复确认有效
> - ⚠️ N regressions detected: AD-xxx (原 AD-yyy 回归), ...
>
> **Pipeline Health (跨阶段任务追踪):**
> - `[ayuan]` AD: 0 open / SE: 2 open (SE-022 → /arch-design, SE-023 → /devtdd)
> - `[taiyi-platform]` AD: 0 open / SE: 0 open
>
> **Decision Challenge Summary (Critical Reasoning):**
> - Decisions challenged: N
> - Survived scrutiny (strengthened): N
> - Needs revision: N (AD-xxx, ...)
> - Needs more data: N (specific data to collect)
>
> 按 Batch 顺序执行，同一 Batch 内的 skill 可分别运行。

---

## 📎 Additional Resources

For detailed audit checklists, scoring rubric, and language-specific red flags, see [reference.md](reference.md):

- **§1 Audit Checklist** — Clean Arch / PoEAA / GoF / Naming detection rules.
- **§2 Scoring Rubric** — how to compute each axis (Dependency / Purity / Persistence / Pattern / Naming).
- **§3 Per-Language Red Flags** — Go / Java / Python concrete anti-patterns to grep for.
- **§4 Refactoring Diff Templates** — common Before/After templates (Data Mapper, Strategy, ISP split).
- **§7 Route Decision Matrix** — how to assign Route tags to findings.
- **§8 Root Cause Analysis Template** — structured "why missed" analysis per finding.
- **§9 Architecture Debt Template** — full AD item structure with all required fields.
- **§10 Skill Evolution Suggestions Template** — SE item structure and consumption protocol.
- **§11 Version Comparison Protocol** — how to diff against previous REVIEW.md and archive.
- **§12 AD Dependency Analysis & Execution Plan** — dependency inference rules, Batch ordering, kanban/BOARD.md task update.

For security auditing, critical reasoning, and feedback grading, see the `references/` subdirectory:
- [references/security-audit-checklist.md](references/security-audit-checklist.md) — OWASP Top 10 + CVSS v3.1 scoring + SAST tools
- [references/critical-reasoning.md](references/critical-reasoning.md) — 5 critical reasoning patterns with worked examples, decision inventory, when-to-apply matrix, severity guide (merged from arch-critic v1.0.0)
- [references/review-feedback-rules.md](references/review-feedback-rules.md) — 4-level severity grading + disagreement protocol
