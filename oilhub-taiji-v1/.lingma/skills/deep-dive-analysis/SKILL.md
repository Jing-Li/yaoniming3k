---
name: deep-dive-analysis
description: Deep source code analysis with root-cause tracing, precise code location, call-chain mapping, and self-validating iteration. Use when user says "analyze this code", "why does this error occur", "debug this", requests code review, or needs to trace bugs/performance issues to their origin.
---

# Deep Dive Analysis

刨根问底式代码分析技能：精准定位问题根因，追溯调用链，提供有据可查的深度分析。

## Core Principles

1. **Evidence-based**: Every claim must cite specific file paths, line numbers, and code snippets
2. **Chain tracing**: Map the complete call chain from symptom to root cause
3. **Self-validating**: Each hypothesis is tested and verified before proceeding
4. **Iterative refinement**: Document assumption changes and corrections transparently

## Quick Start Workflow

When triggered, follow this loop:

```
Reproduce → Minimize → Hypothesize → Instrument → Verify → Iterate
```

### Step 1: Reproduce & Locate

- Identify the exact symptom (error message, unexpected behavior, performance metric)
- Locate the entry point in source code using `search_symbol` or `search_codebase`
- Read the relevant files to understand context

### Step 2: Trace Call Chain

- Use `search_symbol` with `relation` fields to map callers/callees
- Build a dependency graph: who calls whom, what data flows where
- Identify boundary crossings (module → module, service → service)

### Step 3: Form Hypotheses

List possible root causes ranked by likelihood:
1. Most likely based on evidence so far
2. Alternative explanations
3. Edge cases to rule out

### Step 4: Validate Each Hypothesis

For each hypothesis:
- **Instrument**: Add logs, breakpoints, or test cases
- **Execute**: Run the code or test to confirm/deny
- **Record**: Document pass/fail outcome with evidence

### Step 5: Iterate Until Root Cause Found

If hypothesis fails:
- Update understanding based on new evidence
- Refine or replace hypothesis
- Repeat validation

## Output Format

Every analysis must include:

### 1. Problem Statement
Clear description of the observed issue.

### 2. Evidence Trail
| Claim | Source | Line(s) |
|-------|--------|---------|
| e.g., "Function X returns null" | `src/module.ts` | 42-45 |

### 3. Call Chain Diagram
```
entry_point()
  → middleware_a()
    → service_b.query()
      → database_driver.execute()  ← ROOT CAUSE HERE
```

### 4. Root Cause Analysis
- **What**: Precise description of the bug
- **Why**: Why it occurs (code logic flaw, data issue, config error)
- **Impact**: What symptoms this causes

### 5. Validation Results
```
Hypothesis 1: [PASS/FAIL] - Evidence: ...
Hypothesis 2: [PASS/FAIL] - Evidence: ...
Final conclusion: [Confirmed root cause]
```

### 6. Fix Recommendation (if applicable)
Specific, minimal change to resolve the issue.

## Iteration Log Template

Track your analysis progress:

```markdown
## Analysis Iteration Log

**Iteration 1:**
- Hypothesis: [Description]
- Test: [What you ran/checked]
- Result: [PASS/FAIL + evidence]
- Next: [Refinement or new hypothesis]

**Iteration 2:**
...
```

## Tool Usage Guide

| Task | Tool | How |
|------|------|-----|
| Find symbol definitions | `search_symbol` | Use `symbol` + `relation` (calls, called_by, references) |
| Semantic search | `search_codebase` | Use keywords + query for concept-based search |
| Read file content | `Read` | Always read before editing or citing |
| Run tests/commands | `Bash` | Execute validation steps |
| Check errors | `get_problems` | See compile/lint errors in files |

## Additional Resources

- For detailed methodology, see [reference.md](reference.md)
- For worked examples, see [examples.md](examples.md)
