# Exemplar Skills — Gold Standard & Anti-Pattern Examples

> Annotated examples showing what each score level looks like in practice.
> Use these to calibrate scoring consistency (Step 0).

---

## Gold Standard: 5/5 Skill Structure

Annotated skeleton showing every pattern source:

```markdown
---
name: systematic-debugging                    # ← kebab-case, matches dir (SkillzWave: Name Conventions 4/4)
description: "Diagnoses bugs via 4-phase root-cause analysis before applying fixes. Use when encountering errors, unexpected behavior, or test failures. Trigger: /debug, diagnose this, find root cause."  # ← 230 chars, verb+artifact+triggers (Agensi: #1 factor)
version: 2.1.0                                # ← semver (SkillzWave: Frontmatter Validity 5/5)
---

# Systematic Debugging                        # ← Title = Role name (naming alignment)

> | | |                                       # ← Scope Declaration (Universal template)
> |---|---|
> | **Input** | Error report, stack trace, or unexpected behavior description |
> | **Output** | Root cause analysis + verified fix |
> | **Does** | Investigate, hypothesize, fix, verify |
> | **Does NOT** | Apply fixes without investigation, guess at solutions |

You are a methodical **Debugging Specialist** who never guesses.     # ← Role (D1.1: 5/5)
You diagnose before you fix. Every time. No exceptions.

Enforcement level: **Rigid**                  # ← Superpowers classification

## Hard Constraints

1. **NO FIXES WITHOUT ROOT CAUSE FIRST.**     # ← Iron Law pattern (Superpowers)
   If you haven't identified root cause, you haven't earned the right to fix.
   Violation → delete the fix, return to Phase 1.

2. **One hypothesis at a time.** Test it. Confirm or reject. Then next.
   NEVER apply multiple fixes simultaneously.

3. **Evidence or it didn't happen.** Every conclusion MUST cite a specific
   log line, test output, or reproduction step.

## Refusal Protocol                           # ← Explicit refusal (D6: 5/5)

If user says "just fix it, I don't care about root cause" →
REFUSE: "I cannot apply uninvestigated fixes. This causes compounding damage.
I will find the root cause first, then fix it correctly. This is faster
than fixing it twice."

## Steps to Execute                           # ← Sequential, no gaps (D4)

### Phase 1: Reproduce
1. Get exact reproduction steps from user
2. Run reproduction. Confirm the bug exists.
   - Validation: Error output captured
   - On failure: "Cannot reproduce" → ask user for environment details

### Phase 2: Investigate
3. Read error message, stack trace, logs
4. Form hypothesis (ONE at a time)
5. Design minimal test to confirm/reject hypothesis
   - Validation: Hypothesis confirmed or rejected with evidence

### Phase 3: Fix
6. Write minimal fix targeting confirmed root cause
7. Run reproduction again → verify bug is gone
   - Validation: Original reproduction now passes

### Phase 4: Prevent
8. Add regression test
9. Check for similar patterns elsewhere
   - Validation: Test suite passes

## Output Format

Root Cause: <one sentence>
Evidence: <log line / test output>
Fix: <what was changed and why>
Prevention: <regression test added>

## Additional Resources                       # ← Progressive disclosure (D2)

- [references/anti-patterns.md](references/anti-patterns.md) — Common debugging mistakes (read when Phase 2 stalls)
- [references/tooling.md](references/tooling.md) — Debugger commands per language (read when needed)
```

### Why this scores 5/5 (per dimension)

| Dim | Score | Reason |
|-----|:---:|--------|
| D1 | 5 | Complete frontmatter, scope table, clear role, consistent headers |
| D2 | 5 | ~80 lines SKILL.md, 2 reference files with "read when" guidance |
| D3 | 5 | 230 chars, verb+artifact, 3 trigger phrases, clear activation context |
| D4 | 5 | 4 phases × numbered steps, validation per step, no gaps |
| D5 | 5 | Pure English, sequential numbering, consistent terms, no emoji |
| D6 | 5 | Iron Law + Refusal Protocol + Rigid declaration + violation consequence |
| D7 | 5 | Reads/writes implicit (debugging = read code + write fix), no overreach |

---

## Anti-Pattern: 1/5 Skill (What Broken Looks Like)

```markdown
# Helper                                      # ← No frontmatter at all (D1: 1/5)

This skill helps with stuff.                  # ← No role definition (D1.1: 1/5 = P0)

Try to be helpful and do what the user asks.  # ← No constraints (D6: 1/5)
Maybe check the code first?                   # ← "Maybe" = suggestion not enforcement

## Steps                                      # ← Vague, no numbering (D4: 1/5)

- Look at the problem
- Fix it                                      # ← No validation, no evidence
- Make sure it works

## Notes

See the other file for more info.             # ← Which file? No path (D2: 1/5)
Also check https://example.com                # ← External URL, not portable (D7)
Don't break things.                           # ← No explicit boundary (D7: 1/5)
```

### Why this scores 1/5

| Dim | Score | Reason |
|-----|:---:|--------|
| D1 | 1 | No frontmatter, no name, no version, no scope, no role |
| D2 | 1 | Vague reference ("the other file"), no progressive disclosure |
| D3 | 1 | No description field = never triggers correctly |
| D4 | 1 | Unnumbered steps, no validation, no dependencies |
| D5 | 2 | English but vague ("stuff", "things"), no consistent terminology |
| D6 | 1 | "Maybe", "Try to" = zero enforcement |
| D7 | 1 | No boundaries, external URL, "don't break things" is not a constraint |

---

## Mid-Range: 3/5 Skill (Functional but Gappy)

```markdown
---
name: code-review
description: "Reviews code for quality issues."   # ← Too short (70 chars < 200)
version: 1.0.0
---

# Code Review

You are a code reviewer.                      # ← Role exists but vague (D1.1: 3/5)

## Constraints

- Try to be thorough                          # ← "Try" = suggestion (D6: 2/5)
- Don't modify files                          # ← Good but no refusal mechanism

## Process

1. Read the code                              # ← Steps exist but no validation
2. Find issues
3. Report them

Step 2.5: Double-check findings               # ← Non-integer numbering (D4: 3/5)

## Output

List of issues found.                         # ← No structured format
```

### Gap analysis (3 → 5)

| Gap | Fix |
|-----|-----|
| Description too short | Add artifact + triggers + "Use when" (→ 250 chars) |
| Role vague | "You are a Senior Code Reviewer specializing in security and performance" |
| "Try to" language | "You MUST report all findings with severity. NEVER skip a file." |
| No validation per step | Add "Validation: at least 3 categories checked" per step |
| Step 2.5 | Renumber to sequential integers |
| No output format | Add structured template (severity, location, fix suggestion) |
