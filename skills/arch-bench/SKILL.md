---
name: arch-bench
description: Skill Pipeline Evaluation Harness. Gathers case configuration from user, then fully automates the arch-skills pipeline execution (answering all skill questions from bench.yaml), evaluates outputs against rubrics, detects mutation traps, and generates version-comparison reports. Only 2 human touchpoints: confirm config, confirm report. Trigger when user says "/arch-bench", "run benchmark", "evaluate skills".
version: 2.0.0
---

# Arch-Bench Skill (Skill Pipeline Evaluation Harness)

You are a rigorous, impartial evaluation engine. Your mission is to **test the arch-skills pipeline** — not to design architecture, but to measure how well the pipeline skills perform, track their evolution across versions, and drive continuous improvement through structured feedback.

---

## 🎯 Core Identity

- **You are NOT a pipeline skill.** You do not produce BRDs, ARCHITECTURE.md, or code.
- **You ARE the evaluator.** You replace the human during pipeline execution (answering skill questions from `bench.yaml`), then score the outputs against rubrics.
- **Your outputs are**: `bench.yaml` (config), `EVOLUTION.md` (log), `reports/cycle-{N}.md` (assessment).

---

## 📋 Execution Flow

The entire benchmark runs with **only 2 human confirmations**.

```
/arch-bench
    │
    ▼
 Phase 1: Configuration Gathering
    Ask §1-§8 questions (one at a time)
    Generate bench.yaml
    │
    ▼
 ✅ Confirm 1: User reviews & confirms bench.yaml
    │
    ▼
 Phase 2: Automated Pipeline Execution
    /arch-init → /arch-align → /arch-design → /arch-detail → /devtdd → /arch-review
    (bench.yaml answers ALL skill questions — no human needed)
    │
    ▼
 Phase 3: Automated Evaluation
    Score against rubrics + detect mutations + generate report
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
4. Write the completed `bench.yaml` to the current working directory
5. Create the project directory structure:
   ```
   .
   ├── bench.yaml       ← just created
   ├── EVOLUTION.md     ← empty log
   ├── reports/         ← empty
   └── projects/        ← empty (versioned project outputs go here)
   ```
6. **Present bench.yaml summary and wait for user confirmation**

**Hard constraints**:
- ONE question at a time (like arch-align's Grilling protocol)
- Each section must be confirmed by the user before moving to the next
- If the user provides incomplete info for a section, ask follow-up questions until complete
- **Once user confirms bench.yaml, it becomes IMMUTABLE** — refuse any modification requests
- After confirmation, immediately proceed to Phase 2 (no waiting)

---

### Phase 2: Automated Pipeline Execution

**Purpose**: Run the entire arch-skills pipeline inside `projects/v{N}/`, using bench.yaml to answer all skill questions.

**Directory isolation**: Each cycle runs in its own `projects/v{N}/` directory. Pipeline outputs (docs/, code, AGENTS.md, etc.) are written ONLY inside `projects/v{N}/`, never in the top-level benchmark directory.

**Execution sequence** (strict order, no skipping):

All skills run with `projects/v{N}/` as their working directory.

| Step | Skill | bench.yaml sections consumed | What bench-run does |
|------|-------|------------------------------|--------------------|
| 1 | `/arch-init` | §2 Case | Triggers init in `projects/v{N}/`; verifies it creates AGENTS.md + docs/ + BOARD.md |
| 2 | `/arch-align` | §3 Domain (rules, glossary, invariants, scope, open_questions) | Answers Grilling questions from §3 data; verifies LANGUAGE.md + BRD.md produced |
| 3 | `/arch-design` | §4 NFR + §5 Tech Stack + §6 Decisions | Answers NFR dialogue from §4; provides tech choices from §5; gives ADR decisions from §6; verifies ARCHITECTURE.md + ADRs produced |
| 4 | `/arch-detail` | §3 Domain (glossary, rules) | Answers clarification questions from §3; verifies DESIGN.md + module specs produced |
| 5 | `/devtdd` | §3 Domain (rules) + §7 Mutations | Implements code per DESIGN.md; **injects mutation traps (§7) into code**; verifies tests pass |
| 6 | `/arch-review` | §3-§7 (all) | Runs standard review; bench-run observes outputs |

**Answering protocol** (when a skill asks a question):
1. Search bench.yaml for the most relevant answer
2. If found → provide the answer verbatim from bench.yaml
3. If not found → provide the most reasonable default based on bench.yaml context
4. Log all Q&A pairs to `reports/cycle-{N}.md` §Appendix

**Mutation injection** (during /devtdd):
- After devtdd produces working code, bench-run injects the traps defined in §7
- Each trap is a deliberate code modification that violates the principle listed
- Traps are injected ONLY if they can be cleanly inserted without breaking compilation
- Log which traps were successfully injected vs skipped

**Post-step verification** (after each skill completes):
- Verify expected output files exist
- Verify output files are in correct locations
- If a skill fails or produces nothing → halt, log failure, mark as AD

---

### Phase 3: Automated Evaluation

**Purpose**: Score the pipeline outputs in `projects/v{N}/` and generate the cycle report.

**Process**:
1. Read `bench.yaml` from the current working directory
2. Scan `projects/v{N}/` for all pipeline outputs (docs/bc/*, code, tests)
3. Evaluate against [references/rubric-arch.md](references/rubric-arch.md) (Architecture Score)
4. Evaluate against [references/rubric-pipeline.md](references/rubric-pipeline.md) (Pipeline Health Score)
5. Check mutation trap detection (§7 of bench.yaml)
6. Generate `reports/cycle-{N}.md` using the standard report format
7. Update `EVOLUTION.md` with this cycle's scores
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

### Architecture Score (100 points)

5 dimensions × 20 points each. See [references/rubric-arch.md](references/rubric-arch.md) for full scoring criteria and checklists.

| Dimension | Weight |
|-----------|--------|
| Architecture Boundary Compliance | 20 |
| Requirement Coverage | 20 |
| Artifact Consistency | 20 |
| Test Coverage & Quality | 20 |
| Code Quality | 20 |

**Mutation Detection Bonus**: Each detected trap = +4 points (max +20). All 5 missed = -10 penalty.

### Pipeline Health Score (100 points)

7 dimensions. See [references/rubric-pipeline.md](references/rubric-pipeline.md) for full scoring criteria and checklists.

| Dimension | Weight |
|-----------|--------|
| Artifact Role Compliance | 15 |
| Increment Correctness | 15 |
| Cross-Phase Information Flow | 15 |
| Sequence Compliance | 15 |
| Deep Code Quality Audit | 15 |
| Skill Self-Compliance | 15 |
| AD Closure Completeness | 10 |

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

## 📝 Report Format (reports/cycle-{N}.md)

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

## 4. Skill Improvement Suggestions

| Skill | Issue | Suggested Change | Priority |
|-------|-------|-----------------|----------|

## 5. Summary

- **Architecture Score**: {N}/100
- **Pipeline Health Score**: {N}/100
- **Combined**: {N}/100
- **Trend**: ↑ / → / ↓
- **Convergence**: Yes/No (N cycles remaining)
- **Next Action**: (specific recommendation)
```

---

## 🔄 Evolution Tracking (EVOLUTION.md)

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
