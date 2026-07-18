# AD Fix Guidance Mode (v3.4.0+)

After audit produces ADs, this mode **takes end-to-end coordination of the AD lifecycle**: it guides the user through executing each AD fix one by one, dispatches fixes to the owning skill, verifies each fix, marks resolved, and archives the task when all ADs are closed.

arch-review is the **coordinator** — it does not dump ADs and walk away. It stays engaged until every AD is resolved and the task is archived. However, it does NOT directly modify source code — source code ADs are dispatched to `/devtdd`.

---

## Trigger

User says: "fix ADs", "guide fixes", "执行修复", "引导修复", "一个一个修", or after audit completion when user says "let's fix them".

## Workflow

**Step 1 — Load AD Inventory:**
1. Read `kanban/tasks/T{N}.md` → scan all `Architecture Discrepancies` sections
2. Collect all unresolved ADs (items with `[ ]`)
3. Group by target skill (arch-init / arch-align / arch-design / arch-detail / devtdd / arch-review)
4. Order by Batch dependency (upstream first: init → align → design → detail → devtdd → review)
5. Report: "Found N unresolved ADs across M skills. Starting fix guidance."

**Step 2 — Per-AD Fix Cycle (Progressive Disclosure):**

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
│  Question: "How to proceed with {AD-ID}?"           │
│  Options:                                           │
│    1. "Execute fix now (Recommended)" — description │
│    2. "Show me the diff first" — preview changes    │
│    3. "Defer to later" — skip, come back            │
└─────────────────────────────────────────────────────┘
```

**Step 3 — Execute Fix:**

Based on user's choice:
- **"Execute fix now"**: Apply the change directly to the target document(s). Permitted modifications: `LANGUAGE.md`, `BRD.md`, `ARCHITECTURE.md`, `DESIGN.md`, `AGENTS.md`, `BOARD.md`, `T{N}.md`, `OPS.md`, `scripts/*.sh`, `Makefile`. Source code (`.go`, `.java`, `.py`, etc.) is **dispatched to the owning skill** — for `/devtdd` ADs, instruct user to run `/devtdd`, then arch-review verifies the fix.
- **"Show me the diff first"**: Render a before/after diff block, then ask again: "Apply this change?"
- **"Defer to later"**: Mark as deferred in Change History, move to next AD

**Step 4 — Post-Fix Verification:**

After applying each fix:
1. Re-grep the modified file(s) to confirm the problematic pattern is gone
2. Mark the AD as `[x]` with `(Resolved by arch-review-fix, {date})` in T{N}.md
3. Append to T{N}.md Change History: `{date} | arch-review-fix | Resolved {AD-ID}: {what changed}`
4. Report: "✅ {AD-ID} resolved. {Remaining} ADs remaining."

**Step 5 — Completion & Mandatory Archive:**

When all ADs are processed, execute the following steps **in order** — none are optional:

1. **Output summary**: Resolved N / Deferred M / Skipped K
2. **If any deferred**: list them for user review, skip to step 6 (no archive)
3. **Update T{N}.md Status table**: For every skill that had at least one AD resolved in this session → set Status = `done`, Started/Completed = today's date. This reflects that the skill's redo obligation is fulfilled.
4. **Update BOARD.md**: For every skill updated in step 3 → add T{N} to that skill's `done` column in BOARD.md Board table.
5. **Archive check** (MANDATORY when all ADs resolved):
   - Condition: ALL skills in T{N}.md Status table are `done` AND no unresolved `[ ]` Architecture Discrepancy entries exist in T{N}.md
   - If condition met:
     a. Remove T{N} from ALL skill rows in BOARD.md Board table
     b. Add T{N} row to BOARD.md Archive table: `| T{N} | {comma-separated skill list} | {date} |`
   - If condition NOT met (e.g., some skills still `new` with no ADs targeting them): leave T{N} in Board table, note reason in summary
6. **Append to T{N}.md Change History**: `{date} | arch-review-fix | All ADs resolved. T{N} archived.` (or: `... T{N} not archived: {reason}.`)
7. Suggest re-running `/arch-review` for verification

> **Why mandatory?** Tasks left in Board table after all ADs resolved create visual noise and confuse future skill runs. Archive is the terminal state — every resolved task MUST reach it.

## Fix Scope Matrix (v3.4.0+)

| AD Route | arch-review can fix? | Action |
|----------|---------------------|--------|
| `/arch-init` | ✅ Yes | Modify AGENTS.md template, BOARD.md structure |
| `/arch-align` | ✅ Yes | Modify LANGUAGE.md, BRD.md |
| `/arch-design` | ✅ Yes | Modify ARCHITECTURE.md, ADR files |
| `/arch-detail` | ✅ Yes | Modify DESIGN.md, module.md files |
| `/arch-ops` | ✅ Yes | Modify OPS.md, scripts, Makefile |
| `/devtdd` | ❌ No | Dispatch to `/devtdd` — instruct user to run the skill, then verify fix |
| `/arch-review-self` | ✅ Yes | Modify skill configuration, reference files |

> **v3.4.0 change**: `/devtdd` ADs are dispatched, not executed directly. arch-review coordinates the full lifecycle but respects skill ownership boundaries — source code changes belong to `/devtdd`.

## Key Rules

- **ONE AD at a time** — never batch multiple fixes into one question
- **Show analysis BEFORE asking** — user must understand what changes
- **Verify AFTER fixing** — re-grep to confirm the fix worked
- **Document-only fixes** — arch-review in Fix Guidance Mode directly modifies blueprint docs + ops artifacts only; source code ADs are dispatched to `/devtdd`
- **Idempotent** — if an AD is already resolved (e.g., from a previous session), skip it and report
- **User always decides** — even if the fix seems obvious, ask first
- **End-to-end coordination** — arch-review stays engaged from audit through dispatch, verify, and archive. Never leave unresolved ADs orphaned.
