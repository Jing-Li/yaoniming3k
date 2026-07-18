# AD Fix Guidance Mode (v3.2.0+)

After audit produces ADs, this mode **guides the user through executing each AD fix one by one**, ensuring all are completed before re-running review.

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
- **"Execute fix now"**: Apply the change directly to the target document(s). Permitted modifications: `LANGUAGE.md`, `BRD.md`, `ARCHITECTURE.md`, `DESIGN.md`, `AGENTS.md`, `BOARD.md`, `T{N}.md`. Source code (`.go`, `.java`, `.py`, etc.) is **NEVER** modified by arch-review — for `/devtdd` ADs, instruct user to run `/devtdd` instead.
- **"Show me the diff first"**: Render a before/after diff block, then ask again: "Apply this change?"
- **"Defer to later"**: Mark as deferred in Change History, move to next AD

**Step 4 — Post-Fix Verification:**

After applying each fix:
1. Re-grep the modified file(s) to confirm the problematic pattern is gone
2. Mark the AD as `[x]` with `(Resolved by arch-review-fix, {date})` in T{N}.md
3. Append to T{N}.md Change History: `{date} | arch-review-fix | Resolved {AD-ID}: {what changed}`
4. Report: "✅ {AD-ID} resolved. {Remaining} ADs remaining."

**Step 5 — Completion:**

When all ADs are processed:
1. Output summary: Resolved N / Deferred M / Skipped K
2. If any deferred: list them for user review
3. If all resolved: suggest re-running `/arch-review` for verification
4. Update BOARD.md if needed (e.g., move task status)

## Fix Scope Matrix

| AD Route | arch-review can fix? | Action |
|----------|---------------------|--------|
| `/arch-init` | ✅ Yes | Modify AGENTS.md template, BOARD.md structure |
| `/arch-align` | ✅ Yes | Modify LANGUAGE.md, BRD.md |
| `/arch-design` | ✅ Yes | Modify ARCHITECTURE.md, ADR files, delete SYSTEM.md |
| `/arch-detail` | ✅ Yes | Modify DESIGN.md, module.md files |
| `/devtdd` | ❌ No | Instruct user to run `/devtdd` — source code out of scope |
| `/arch-review-self` | ✅ Yes | Modify skill configuration, reference files |

## Key Rules

- **ONE AD at a time** — never batch multiple fixes into one question
- **Show analysis BEFORE asking** — user must understand what changes
- **Verify AFTER fixing** — re-grep to confirm the fix worked
- **No source code** — arch-review NEVER touches `.go`/`.java`/`.py` files
- **Idempotent** — if an AD is already resolved (e.g., from a previous session), skip it and report
- **User always decides** — even if the fix seems obvious, ask first
