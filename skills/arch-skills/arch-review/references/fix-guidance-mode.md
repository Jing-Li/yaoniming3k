# AD Fix Guidance Mode (v4.1.0+)

arch-review is a **pure coordinator** — it NEVER directly modifies any file (code or document). Fix Guidance Mode orchestrates the AD lifecycle: present each AD to user for confirmation via AskUserQuestion, then **invoke the owning skill** (via Skill tool) to execute the fix, verify the result, mark resolved, and archive when all ADs close.

**Core principle: arch-review never touches files. It coordinates, dispatches, and verifies. One AD at a time.**

---

## Trigger

User says: "fix ADs", "guide fixes", "执行修复", "引导修复", "一个一个修", or after audit completion when user says "let's fix them".

---

## Workflow

**Step 1 — Load AD Inventory:**
1. Read `kanban/tasks/T{N}.md` → scan all `Architecture Discrepancies` sections
2. Collect all unresolved ADs (items with `[ ]`)
3. Group by target skill (arch-align / arch-design / arch-detail / arch-ops / devtdd / arch-review-self / other skills)
4. Order by Batch dependency (upstream first: align → design → detail → ops → devtdd → review-self)
5. Report: "Found N unresolved ADs across M skills. Starting fix guidance."

**Step 2 — Per-AD Fix Cycle (Progressive Disclosure, ONE at a time):**

For EACH unresolved AD, in dependency order:

```
┌─────────────────────────────────────────────────────┐
│  AD {ID} / {Total}  │  Route: /{target-skill}       │
├─────────────────────────────────────────────────────┤
│  Description: {AD description from T{N}.md}        │
│  User decision: {confirmed decision from audit}      │
├─────────────────────────────────────────────────────┤
│  Analysis: What needs to change, which files,       │
│            what the target state should look like    │
├─────────────────────────────────────────────────────┤
│  AskUserQuestion:                                   │
│    Question: "How to proceed with AD-{ID}?"         │
│    Header: "{target-skill}" (≤12 chars)             │
│    Options:                                         │
│      1. "Invoke /{skill} (Recommended)"             │
│         — describe fix scope and expected outcome   │
│      2. "Preview fix plan" — show diff before exec  │
│      3. "Defer" — skip, record in deferred          │
└─────────────────────────────────────────────────────┘
```

**Step 3 — Dispatch to Owning Skill:**

Based on user's choice:
- **"Invoke /{skill}"**: arch-review invokes the Skill tool with the target skill name, passing the AD context (AD ID, description, location, confirmed approach) as the skill argument. The **owning skill executes the fix** — arch-review does NOT touch any file.
- **"Preview fix plan"**: arch-review renders a before/after analysis (read-only), then asks again via AskUserQuestion: "Confirm execution?" with options "Execute" / "Defer"
- **"Defer"**: Mark as deferred in Change History, move to next AD

**Dispatch mapping (Skill invocation):**

| AD Route | Skill invoked | Skill modifies |
|----------|--------------|----------------|
| `/arch-align` | `/arch-align` | LANGUAGE.md, BRD.md |
| `/arch-design` | `/arch-design` | ARCHITECTURE.md, ADR files |
| `/arch-detail` | `/arch-detail` | DESIGN.md, module.md, interfaces/ |
| `/arch-ops` | `/arch-ops` | OPS.md, scripts/*.sh, Makefile |
| `/devtdd` | `/devtdd` | Source code (.go, tests, etc.) |
| `/arch-review-self` | `/arch-review` (self-fix) | arch-review skill files only |
| `/{any-skill}` (Skill Evolution) | `/{any-skill}` | That skill's own SKILL.md / reference files |

> **`/arch-review-self` exception**: Only for self-referential skill improvements, arch-review MAY modify its own skill files. This is the ONLY case where arch-review writes files directly.

**Step 4 — Post-Fix Verification:**

After the invoked skill completes its fix:
1. Re-grep the target file(s) to confirm the problematic pattern is gone
2. If verification passes:
   - Mark the AD as `[x]` with `(Resolved by /{skill}, {date})` in T{N}.md
   - Append to T{N}.md Change History: `{date} | {skill} | Resolved {AD-ID}: {what changed}`
   - Report: "✅ {AD-ID} resolved. {Remaining} ADs remaining."
3. If verification FAILS:
   - Report: "⚠️ {AD-ID} fix incomplete — pattern still present at {location}"
   - AskUserQuestion: "Fix failed verification. How to proceed?"
     - "Retry /{skill} (Recommended)" — retry with more context
     - "Manual handling" — user takes over
     - "Defer" — skip

**Step 5 — Skill Evolution Assessment (MANDATORY):**

After ALL fix ADs are resolved (or deferred), arch-review MUST perform a **Skill Evolution Assessment** before archiving:

1. **Per-skill SE trigger**: For each skill that received **1+ AD** in this audit cycle, analyze whether the ADs point to a skill deficiency (missing validation step, incomplete checklist, absent constraint, or protocol gap).
2. **Process failure detection**: Regardless of AD count, check for protocol violations during this audit cycle:
   - Did any skill skip AskUserQuestion confirmation?
   - Did any skill bypass kanban task creation?
   - Did any skill violate document ownership boundaries?
   - Did arch-review itself have process failures (skipped SE, violated single-position, etc.)?
3. **Cross-skill pattern detection**: If multiple skills share a common failure pattern (e.g., multiple skills lacking user confirmation steps), create a single SE AD targeting the shared protocol (e.g., kanban-spec) or each affected skill individually.
4. **Skill Evolution AD creation**: If any deficiency is identified, create a Skill Evolution AD:
   - Format: `- [ ] SE-{N} (Skill Evolution): {skill} lacks {capability}. Evidence: {AD-IDs or process failures}. Recommended improvement: {specific change to skill file}.`
   - Route: `/{skill}-self` (e.g., `/arch-design-self`, `/devtdd-self`)
   - These SE ADs are presented to user via AskUserQuestion (same protocol as regular ADs)
   - Upon confirmation, arch-review invokes the target skill to apply the improvement to its own SKILL.md / reference files
5. **arch-review-self SE**: If arch-review itself had process failures during this cycle (e.g., skipped AskUserQuestion, violated single-position, missed SE assessment), create SE ADs routed to `/arch-review-self`
6. **No SE needed**: If all ADs were one-off mistakes with no systemic pattern and no process failures detected, report: "No Skill Evolution items this cycle."

> **Why?** Fixing individual ADs without improving the originating skill leads to recurring debt. Skill Evolution closes the loop: audit → fix → improve the skill → prevent recurrence.

**Step 6 — Completion & Mandatory Archive:**

When all ADs (including SE ADs) are processed:

1. **Output summary**: Resolved N / Deferred M / Skipped K / Skill Evolution SE count
2. **If any deferred**: list them for user review, skip archive (no archive with open items)
3. **Update T{N}.md Status table**: For every skill that had at least one AD resolved → set Status = `done`, Started/Completed = today's date.
4. **Update BOARD.md**: For every skill updated in step 3 → add T{N} to that skill's `done` column.
5. **Archive check** (MANDATORY — subject to Hard Gate #10):
   - Condition: ALL skills `done` AND zero unresolved `[ ]` entries (including SE items)
   - If met: remove T{N} from Board, add to Archive table
   - If NOT met: leave in Board, note reason
6. **Append Change History**: `{date} | arch-review | All ADs resolved. T{N} archived.` (or reason)
7. Suggest re-running `/arch-review` for verification

> **Why mandatory?** Tasks left in Board table after all ADs resolved create visual noise and confuse future skill runs. Archive is the terminal state.

---

## Key Rules

- **arch-review NEVER modifies files** — all fixes executed by the owning skill via Skill tool invocation; arch-review only coordinates order, confirms approach, and verifies results
- **ONE AD at a time** — never batch multiple fixes into one question
- **Show analysis BEFORE asking** — user must understand what changes before confirming
- **Skill invocation, not manual edit** — use Skill tool to invoke `/arch-align`, `/arch-design`, `/arch-detail`, `/arch-ops`, `/devtdd`, or any skill for SE fixes
- **Verify AFTER each fix** — re-grep to confirm the fix worked before marking resolved
- **Skill Evolution is MANDATORY** — every audit cycle MUST assess whether originating skills need systemic improvement, not just one-off fixes
- **Idempotent** — if an AD is already resolved (e.g., from a previous session), skip it and report
- **User always decides** — even if the fix seems obvious, ask first via AskUserQuestion
- **End-to-end coordination** — arch-review stays engaged from first AD to archive. Never leave unresolved ADs orphaned.
- **Ordering is arch-review's job** — upstream ADs (align) before downstream (design → detail → ops → devtdd). arch-review determines and communicates the sequence.

---

## Example Session

```
arch-review: "Found 3 unresolved ADs. Dependency order: AD-5(align) → AD-3(design) → AD-1(detail)."

── AD-5 / 3 ── Route: /arch-align ──
Analysis: LANGUAGE.md §MVP-auth defines creator='local' but code sets creator='ayuan'.
Evidence: lifecycle_handler.go:45 sets Creator: "ayuan"

AskUserQuestion:
  Q: "How to proceed with AD-5?"
  Header: "arch-align"
  Options:
    1. "Invoke /arch-align (Recommended)" — update LANGUAGE.md to define creator as event-source identifier
    2. "Preview fix plan"
    3. "Defer"

User: → "Invoke /arch-align"

arch-review: [invokes Skill tool: /arch-align with AD-5 context]
  → /arch-align updates LANGUAGE.md §MVP-auth

arch-review: [verifies] grep "creator" LANGUAGE.md → ✅ updated
  → marks [x] AD-5, reports "✅ AD-5 resolved. 2 remaining."

── AD-3 / 3 ── Route: /arch-design ──
...

── Skill Evolution Assessment ──
arch-review: "arch-align received 2 ADs this cycle (AD-5, AD-9) both caused by
  ambiguous semantic definitions in LANGUAGE.md. Root cause: arch-align grilling
  does not validate field-level semantics against actual code usage.
  → SE-1: /arch-align-self — add 'field semantic validation' step to grilling checklist."

AskUserQuestion:
  Q: "How to proceed with SE-1 (arch-align skill improvement)?"
  Header: "align-self"
  Options:
    1. "Invoke /arch-align (Recommended)" — add validation step to grilling protocol
    2. "Defer to next cycle"
```
