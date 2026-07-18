# AD Fix Guidance Mode (v3.3.0+)

After audit produces ADs, this mode **takes end-to-end ownership of the AD lifecycle**: it guides the user through executing each AD fix one by one (including source code changes), verifies each fix, marks resolved, and archives the task when all ADs are closed.

arch-review is the **coordinator** — it does not dump ADs and walk away. It stays engaged until every AD is resolved and the task is archived.

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
- **"Execute fix now"**: Apply the change directly to the target file(s). **All file types are in scope** — documents, source code, tests, build configs. Permitted modifications depend on the AD route (see Fix Scope Matrix above).
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

## Fix Scope Matrix (v3.3.0+)

| AD Route | arch-review can fix? | Action |
|----------|---------------------|--------|
| `/arch-init` | ✅ Yes | Modify AGENTS.md template, BOARD.md structure |
| `/arch-align` | ✅ Yes | Modify LANGUAGE.md, BRD.md |
| `/arch-design` | ✅ Yes | Modify ARCHITECTURE.md, ADR files |
| `/arch-detail` | ✅ Yes | Modify DESIGN.md, module.md files |
| `/devtdd` | ✅ Yes | Modify source code (`.go`, `.java`, `.py`, etc.), tests, build configs |
| `/arch-review-self` | ✅ Yes | Modify skill configuration, reference files |

> **v3.3.0 change**: `/devtdd` ADs are no longer out of scope. arch-review owns the full fix lifecycle — if an AD requires source code changes, arch-review makes those changes directly after user confirmation.

## Key Rules

- **ONE AD at a time** — never batch multiple fixes into one question
- **Show analysis BEFORE asking** — user must understand what changes
- **Verify AFTER fixing** — re-grep to confirm the fix worked
- **No file type restriction** — arch-review in Fix Guidance Mode can modify any file needed to resolve ADs (source code included)
- **Idempotent** — if an AD is already resolved (e.g., from a previous session), skip it and report
- **User always decides** — even if the fix seems obvious, ask first
- **End-to-end ownership** — arch-review stays engaged from audit through fix, verify, and archive. Never leave unresolved ADs orphaned.
