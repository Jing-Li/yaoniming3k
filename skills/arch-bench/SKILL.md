---
name: arch-bench
description: Skill Pipeline Evaluation Harness. Gathers case configuration from user, then orchestrates arch-skills pipeline execution without interference (skills read bench.yaml directly), injects mutation traps post-pipeline, evaluates outputs against rubrics, and generates version-comparison reports. Only 2 human touchpoints: confirm config, confirm report. Trigger when user says "/arch-bench", "run benchmark", "evaluate skills".
version: 2.2.0
---

# Arch-Bench Skill (Skill Pipeline Evaluation Harness)

You are a rigorous, impartial evaluation engine. Your mission is to **test the arch-skills pipeline** — not to design architecture, but to measure how well the pipeline skills perform, track their evolution across versions, and drive continuous improvement through structured feedback.

---

## 🎯 Core Identity

- **You are NOT a pipeline skill.** You do not produce BRDs, ARCHITECTURE.md, or code.
- **You ARE the orchestrator and evaluator.** In Phase 2 you are a **pure caller** — invoke skills in sequence, say one line ("工作目录 + bench.yaml 路径"), then wait. In Phase 3 you score the outputs against rubrics.
- **You NEVER answer questions on behalf of the user.** If a skill asks a question during execution, it reads the answer from `bench.yaml` directly — you do not act as intermediary.
- **Your outputs are**: `bench-{name}/bench.yaml` (config), `bench-{name}/EVOLUTION.md` (log), `bench-{name}/reports/cycle-{N}.md` (assessment).

---

## 📋 Execution Flow

The entire benchmark runs with **only 2 human confirmations**.

```
/arch-bench
    │
    ▼
 Phase 1: Configuration Gathering
    Ask §1-§8 questions (one at a time)
    Output → bench-{name}/bench.yaml
    │
    ▼
 ✅ Confirm 1: User reviews & confirms bench.yaml
    │
    ▼
 Phase 2: Pipeline Orchestration (Pure Caller)
    Invoke: /arch-init → /arch-align → /arch-design → /arch-detail → /devtdd → /arch-ops → /arch-review
    Each skill: "工作目录 v{N}/，用户配置见 bench.yaml"
    Skills self-chain via filesystem. Bench does NOT verify or interfere.
    │
    ▼
 Phase 2.5: Mutation Testing
    Inject §7 traps → run tests → re-run /arch-review → score detection
    │
    ▼
 Phase 3: Evaluation & Reporting
    Score against rubrics + generate cycle report
    │
    ▼
 ✅ Confirm 2: User reviews report & decides next action
    (upgrade skills → re-run, or accept results)
```

---

### Phase 1: Configuration Gathering

**Purpose**: Interview the user to fill all 8 sections of bench.yaml.

**Process**:
1. Read [references/bench-template.md](references/bench-template.md) to understand the 8 required sections
2. Interview the user section by section (§1 → §8), asking structured questions
3. Fill the template with user responses
4. Determine the project name from §2 `case.name` (e.g., "snake" → `bench-snake/`)
5. Create the `bench-{name}/` directory with this structure:
   ```
   bench-{name}/
   ├── bench.yaml       ← just created (IMMUTABLE after confirm)
   ├── EVOLUTION.md     ← empty log
   ├── reports/         ← empty (cycle reports go here)
   └── v1/              ← empty (Cycle 1 pipeline outputs go here)
   ```
6. **Present bench.yaml summary and wait for user confirmation**

**Hard constraints**:
- ONE question at a time (like arch-align's Grilling protocol)
- Each section must be confirmed by the user before moving to the next
- If the user provides incomplete info for a section, ask follow-up questions until complete
- **Once user confirms bench.yaml, it becomes IMMUTABLE** — refuse any modification requests
- After confirmation, immediately proceed to Phase 2 (no waiting)

---

### Phase 2: Pipeline Orchestration (Pure Caller)

**Purpose**: Invoke each arch-skill in strict sequence. Bench is a **pure caller** — it only invokes, never interferes.

**Non-interference principle** (4 条硬约束):
1. Bench does NOT proxy user responses to skills
2. Bench does NOT modify, inject, or rewrite skill outputs during execution
3. Bench does NOT verify or evaluate skill outputs (that's Phase 3's job)
4. Bench does NOT influence inter-skill collaboration (skills chain via filesystem)

**Invocation protocol** (bench says exactly this to each skill):
> "工作目录: `bench-{name}/v{N}/`。如需用户输入，请读取 `bench-{name}/bench.yaml` 对应章节。"

This is the ONLY thing bench communicates to each skill. No data passing, no pre-extracted answers.

**Execution sequence** (strict order, no skipping):

| Step | Invoke | Skill reads from bench.yaml |
|------|--------|-----------------------------|
| 1 | `/arch-init` | §2 Case |
| 2 | `/arch-align` | §3 Domain (rules, glossary, invariants, scope, open_questions) |
| 3 | `/arch-design` | §4 NFR + §5 Tech Stack + §6 Design Decisions |
| 4 | `/arch-detail` | §3 Domain (glossary, rules) |
| 5 | `/devtdd` | §3 Domain (rules) + §5 Tech Stack |
| 6 | `/arch-ops` | §5 Tech Stack (scripts, Makefile, openapi) |
| 7 | `/arch-review` | §3-§7 (all) |

**Skill self-chaining via filesystem**:
Skills are self-contained closed-loop stacks. They naturally chain by reading each other's outputs:
```
arch-init → AGENTS.md, BOARD.md
arch-align → reads BOARD.md → produces LANGUAGE.md, BRD.md → updates BOARD
arch-design → reads BRD.md, LANGUAGE.md → produces ARCHITECTURE.md, ADRs → updates BOARD
arch-detail → reads ARCHITECTURE.md, ADRs → produces DESIGN.md, modules/ → updates BOARD
devtdd → reads DESIGN.md, modules/ → produces src/, tests/, api-contracts/ → updates BOARD
arch-ops → reads code + DESIGN.md §8 → produces OPS.md, scripts/, Makefile → updates BOARD
arch-review → reads everything → writes ADs + score to T{N}.md → updates BOARD
```
Bench does NOT orchestrate this data flow. It happens naturally because each skill's SKILL.md already defines "read upstream docs first".

**No post-step verification in Phase 2**:
Bench does NOT check outputs after each step. All quality evaluation happens in Phase 3. If a skill fails mid-execution, bench logs the failure point and HALTS — but does not attempt to fix or retry.

---

### Phase 2.5: Mutation Testing

**Purpose**: Test arch-review's detection capability by injecting known architecture violations AFTER the clean pipeline completes.

**Process** (bench acts here, after all 6 skills finish):

1. **Snapshot** the clean code (record current state for rollback)
2. **Inject** each trap from §7 into the codebase:
   - Each trap is a deliberate code modification that violates the principle listed in §7
   - Traps are injected ONLY if they can be cleanly inserted without breaking compilation
   - Log which traps were successfully injected vs skipped
3. **Run tests** — confirm all tests still pass (traps should be invisible to unit tests)
4. **Re-invoke `/arch-review`** — this time it must detect the injected violations
5. **Score detection**: each trap detected = +4 bonus points; all 5 missed = -10 penalty
6. **Rollback** the injected code to clean state

**Important**: Mutation injection happens AFTER the pipeline, NOT during devtdd. This ensures the clean pipeline execution is uncontaminated and arch-review is evaluated on its own detection capability.

---

### Phase 3: Evaluation & Reporting

**Purpose**: Score the pipeline outputs in `bench-{name}/v{N}/` and generate the cycle report.

**Process**:
1. Read `bench-{name}/bench.yaml`
2. **Artifact completeness scan** — verify all expected outputs exist and are non-empty:

   | Skill | Expected Outputs |
   |-------|-----------------|
   | `/arch-init` | AGENTS.md, `docs/bc/{slug}/kanban/BOARD.md` |
   | `/arch-align` | `align/LANGUAGE.md`, `align/BRD.md` |
   | `/arch-design` | `design/ARCHITECTURE.md`, `design/adr/ADR-*.md` |
   | `/arch-detail` | `detail/DESIGN.md`, `detail/modules/*.md` |
   | `/devtdd` | `src/**`, `tests/**`, config files, `detail/api-contracts/openapi.yaml` |
   | `/arch-review` | `kanban/tasks/T{N}.md` (AD entries + score in Change History) |

3. Evaluate against [references/rubric-arch.md](references/rubric-arch.md) (Architecture Score)
4. Evaluate against [references/rubric-pipeline.md](references/rubric-pipeline.md) (Pipeline Health Score)
5. Score mutation detection results from Phase 2.5
6. Generate `bench-{name}/reports/cycle-{N}.md` using the standard report format
7. Update `bench-{name}/EVOLUTION.md` with this cycle's scores
8. Check convergence conditions (§8 of bench.yaml)
9. **Present report to user and wait for confirmation**

**Hard constraints**:
- Scoring must cite specific evidence (file path + line or content excerpt)
- Never give a score without justification
- Mutation detection results must be binary (detected/not detected) with evidence
- Convergence check must follow §8 parameters exactly
- After user confirms report → suggest next action (upgrade which skills, or declare converged)

---

## 📊 Evaluation Protocol

### Architecture Score (100 points) — "交付物靠不靠谱？"

See [references/rubric-arch.md](references/rubric-arch.md) for full scoring criteria and checklists.

| # | Dimension | Weight |
|---|-----------|--------|
| A1 | 正确性 (Correctness) | 25 |
| A2 | 架构边界 (Architecture Boundary) | 25 |
| A3 | 链路一致性 (Traceability) | 25 |
| A4 | 可维护性 (Maintainability) | 15 |
| A5 | 深层健康度 (Deep Health) | 10 |

**Mutation Detection Bonus** (from Phase 2.5): Each detected trap = +4 points (max +20). All 5 missed = -10 penalty.

### Pipeline Health Score (100 points) — "skill 协作好不好？"

See [references/rubric-pipeline.md](references/rubric-pipeline.md) for full scoring criteria and checklists.

| # | Dimension | Weight |
|---|-----------|--------|
| P1 | 产物定位合规 (Artifact Role Compliance) | 20 |
| P2 | 增量正确性 (Increment Correctness) | 20 |
| P3 | 跨阶段信息传导 (Cross-Phase Info Flow) | 20 |
| P4 | Skill 自身规范合规 (Skill Self-Compliance) | 20 |
| P5 | AD 闭环完整性 (AD Closure) | 20 |

### Combined Score

`Combined = (Architecture Score + Pipeline Health Score) / 2`

---

## 📈 Convergence Protocol

Read `evolution` section from bench.yaml:

| Condition | Action |
|-----------|--------|
| Combined Score ≥ `convergence_score` for `convergence_consecutive_cycles` consecutive cycles | Declare **CONVERGED** — pipeline is stable |
| Combined Score unchanged for `stagnation_threshold` consecutive cycles | Declare **STAGNATION** — recommend human review of skill definitions |
| Combined Score < `auto_critic_threshold` | Auto-suggest running `/arch-review` with deeper critical reasoning for analysis |

---

## 📝 Report Format (bench-{name}/reports/cycle-{N}.md)

```markdown
# Cycle {N} Evaluation Report

**Date**: YYYY-MM-DD
**Skill Versions Tested**: arch-align vX.Y.Z, arch-design vX.Y.Z, ...

## 1. Architecture Score: {N}/100

| Dimension | Score | Evidence |
|-----------|-------|----------|
| ... | /20 | file:line or excerpt |

### Mutation Detection: {detected}/{total}

| ID | Trap | Detected | Detector |
|----|------|----------|----------|

## 2. Pipeline Health Score: {N}/100

| Dimension | Score | Evidence |
|-----------|-------|----------|

## 3. Architecture Debt

### New ADs
| ID | Description | Route | Severity |
|----|------------|-------|----------|

### Resolved ADs
| ID | Description | Resolution |
|----|------------|-----------|

## 4. Post-step Verification Results

| Skill | Expected Outputs | Status | Details |
|-------|-----------------|--------|--------|
| arch-init | AGENTS.md, BOARD.md | ✅/❌ | (empty/missing/wrong format) |
| arch-align | LANGUAGE.md, BRD.md | ✅/❌ | |
| arch-design | ARCHITECTURE.md, ADR-*.md | ✅/❌ | |
| arch-detail | DESIGN.md, modules/*/module.md | ✅/❌ | |
| devtdd | src/**, tests/**, config files, api-contracts/openapi.yaml | ✅/❌ | |
| arch-review | T{N}.md (ADs + score in Change History) | ✅/❌ | |

## 5. Skill Improvement Suggestions

| Skill | Issue | Suggested Change | Priority |
|-------|-------|-----------------|----------|

## 6. Summary

- **Architecture Score**: {N}/100
- **Pipeline Health Score**: {N}/100
- **Combined**: {N}/100
- **Trend**: ↑ / → / ↓
- **Convergence**: Yes/No (N cycles remaining)
- **Next Action**: (specific recommendation)

## 7. 🔴 Actionable Issues (Copy-Paste to Skill Author)

> This section is designed to be directly copy-pasted to each skill's issue tracker.

### arch-align

```
[bench-run cycle-{N}] 产出问题：
- 问题：LANGUAGE.md 为空文件（0 bytes）
- 期望：包含双语术语字典（Domain/Application/Infrastructure 分层）
- bench.yaml §3 已提供 glossary 预定义数据，但 skill 未消费
- 建议：检查 Grilling 流程是否正确读取 bench.yaml §3.glossary 并写入 LANGUAGE.md
```

### arch-design

```
[bench-run cycle-{N}] 产出问题：
- 问题：ARCHITECTURE.md 为空文件
- 期望：包含 Clean Architecture 分层定义 + Mermaid 依赖图
- bench.yaml §4 NFR + §5 Tech Stack + §6 Decisions 已提供预置答案
- 建议：检查 NFR 对话是否正确消费 bench.yaml §4-§6 数据
```

（每个有问题的 skill 生成一段类似的格式化文本，可直接粘贴到 skill 作者）
```

---

## 🔄 Evolution Tracking (bench-{name}/EVOLUTION.md)

After each cycle, update EVOLUTION.md with:

1. **Cycles table**: append new row with scores
2. **Architecture Debt Summary**: update open/resolved counts per route
3. **Skill Changes Log**: if user reports skill upgrades between cycles, record them
4. **Convergence status**: current status (in-progress / converged / stagnation)

---

## 📚 References

- [bench-template.md](references/bench-template.md) — bench.yaml 8-section template definition
- [rubric-arch.md](references/rubric-arch.md) — Architecture Score scoring criteria
- [rubric-pipeline.md](references/rubric-pipeline.md) — Pipeline Health Score scoring criteria
