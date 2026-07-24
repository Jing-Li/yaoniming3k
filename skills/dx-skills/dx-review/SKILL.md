---
name: dx-review
description: "UX quality review skill with two modes. Pre-mode (optional): audit existing UI at dx pipeline entry to establish baseline issues for redesign. Post-mode (required, blocking gate): conformance check at dx pipeline exit — compares implementation against design spec/reference via screenshot diff, reports pass/fail with drift list. Failed items route as ADs to the responsible dx skill for fix. Trigger when user says '/dx-review', 'review this UI', 'audit the interface', 'check conformance', 'does it match the design', or asks about UX quality."
version: 1.0.0
---

# DX — Review

Two-mode UX quality review skill. The core question is always "how good is this UI?" — but the answer method differs by mode.

## Two Modes

| | Pre-Mode (Audit) | Post-Mode (Conformance) |
|---|---|---|
| **When** | dx pipeline entry | dx pipeline exit (blocking gate) |
| **Has reference?** | No — open-ended | Yes — design spec / reference image / url-dna.md |
| **Question** | "What's wrong with this UI?" | "Does this match the design?" |
| **Method** | Heuristic rules scan | Screenshot diff + fidelity comparison |
| **Output** | Ranked issue list → informs design direction | Pass/Fail + drift list → ADs to responsible skill |
| **Required?** | Optional (redesign scenarios) | Required (blocks sharing) |

## Pipeline Position

> **dx pipeline** · Quality Gate (dual position)
>
> | | |
> |---|---|
> | **Pre-Mode Upstream** | `arch-align` (BRD.md §5 UX Context) — redesign scenario |
> | **Pre-Mode Downstream** | `dx-image-to-code` / `dx-url-to-code` (informed by audit findings) |
> | **Post-Mode Upstream** | `dx-prototype` (working prototype) |
> | **Post-Mode Downstream** | PASS → `arch-ops` (deploy/share). FAIL → ADs to `dx-image-to-code` / `dx-prototype` |
> | **Owns** | `dx/review/` (review reports) |
> | **Does** | Heuristic audit OR conformance check, produce ranked issues or pass/fail verdict |
> | **Does NOT** | Fix issues (routes to responsible skill via AD), modify source code |

## HARD CONSTRAINTS

1. **No fixing.** You find issues and route them. You do not modify source code.
2. **Restricted tool surface.** Only create `dx/review/` reports and write ADs to `kanban/tasks/T{N}.md`.
3. **Post-mode is a blocking gate.** Nothing leaves the dx pipeline without passing post-mode review.
4. **Measure, don't eyeball.** Post-mode always uses screenshot diff. "Looks close" is not a verdict.
5. **Follow AskUserQuestion spec.** All user interactions use structured questions per `ask-user-question-spec.md`.
6. **Follow kanban-spec for AD routing.** Failed items go through the standard AD protocol.

---

## Pre-Mode: Audit (Optional)

### When to use
- Redesigning an existing product — audit the current UI before creating new designs.
- Understanding what's wrong with a competitor's interface.
- Establishing a baseline before the dx pipeline begins.

### Workflow
1. **Capture** the existing UI via browser-automation screenshots (or user-provided screenshots).
2. **Scan** against heuristic rules (see checklist below).
3. **Rank** issues by severity (P0–P3) and impact.
4. **Write** the audit report to `dx/review/audit-{date}.md`.

### Heuristic Checklist
- **Visual Hierarchy** — is the most important content most prominent?
- **Clarity** — can a user understand what to do within 5 seconds?
- **Consistency** — are patterns used consistently across screens?
- **Accessibility** — contrast ratios, focus states, screen reader support, keyboard navigation.
- **Feedback** — do interactive elements give clear feedback (hover, active, loading, success, error)?
- **Error Prevention** — are destructive actions guarded? Are errors recoverable?
- **Mobile Readiness** — does the layout work on smaller viewports?
- **Performance Perception** — are loading states handled? Is skeleton/shimmer used?

### Output: `dx/review/audit-{date}.md`

```markdown
# UX Audit: {subject}

## Summary
- Total issues: {N}
- P0 (blocking): {N}
- P1 (high): {N}
- P2 (medium): {N}
- P3 (low): {N}

## Issues (ranked by severity)

### P0 — {title}
- **Where**: {screen/element}
- **Problem**: {description}
- **Impact**: {who is affected and how}
- **Recommendation**: {fix suggestion}

### P1 — {title}
...

## Recommendations
- {top 3 actionable improvements}
```

---

## Post-Mode: Conformance (Required, Blocking)

### When to use
- After `dx-prototype` produces a working prototype, before sharing with stakeholders.
- After any fix cycle (AD resolution) to re-verify.

### Workflow (3-Pass Audit, v1.1.0+)

Post-mode runs THREE passes in sequence. All three are mandatory. Results are combined into a single report sorted by priority.

#### Pass 1: Visual Conformance

1. **Capture** the implementation via browser-automation screenshots at the same viewport as the reference.
2. **Compare** against the design spec (reference image, mockup, or url-dna.md).
3. **Check** five fidelity surfaces:
   - Layout — grid, spacing, alignment, component positioning
   - Typography — font family, size, weight, line-height, letter-spacing
   - Color — backgrounds, text colors, borders, semantic colors
   - Components — button styles, input states, card structures, nav patterns
   - Behavior — hover states, transitions, loading states, error states
4. **Anti-slop detection** (v1.1.0+): Read `dx-conventions/references/anti-slop-rules.md`. Check output against the 3 Default Looks and Generic Anti-Patterns. Hit with brief not requesting it → P0/P1 DRIFT.
5. **Design token consistency** (v1.1.0+): Compare code color values, font families, and spacing against `dx/design-system.md`. Undeclared values → P1 DRIFT. Anti-pattern violation → P0 DRIFT.

#### Pass 2: Performance Audit (v1.1.0+)

1. Read `dx-conventions/references/performance-rules.md`.
2. Scan all `.tsx` / `.jsx` / `.ts` / `.js` files in the generated frontend.
3. Check rules in priority order (P1 first):
   - P1 hit → BLOCKING (must fix)
   - P2 hit → WARNING (should fix)
   - P3/P4 hit → INFO (record)
4. Verdict: FAIL if ≥1 BLOCKING or ≥3 WARNINGs. Otherwise PASS.

#### Pass 3: Interaction Verification (v1.1.0+)

1. Read `dx-conventions/references/playwright-patterns.md`.
2. Based on page characteristics, select test patterns:
   - All pages: Pattern 1 (Load) + Pattern 4 (Responsive)
   - Has navigation: + Pattern 2 (Navigation)
   - Has forms: + Pattern 3 (Form)
   - Has data fetching: + Pattern 5 (States)
3. Generate and execute Playwright tests.
4. Each failed test = one DRIFT item:
   - Pattern 1/2/3 failure → P0 (broken = not deliverable)
   - Pattern 4/5 failure → P1
5. Verdict: FAIL if any P0. Otherwise PASS.

### Overall Verdict

- **PASS**: All 3 passes pass (no P0/P1 blocking items).
- **FAIL**: Any pass fails. Write ADs for each blocking item.

### Severity Scale
- **P0 (Blocking)** — visually broken, wrong layout, missing critical element, anti-slop default, page doesn't load, interaction broken
- **P1 (High)** — noticeable drift in type/color/spacing, performance critical hit, missing state
- **P2 (Medium)** — minor inconsistency, performance warning, only visible on close inspection
- **P3 (Low)** — cosmetic polish, performance info, acceptable to ship

### AD Routing on FAIL
Each issue becomes an Architecture Discrepancy in `kanban/tasks/T{N}.md`:
- Visual drift (layout/type/color/components/anti-slop) → AD routed to `dx-image-to-code` or `dx-url-to-code`
- Interaction/behavior drift → AD routed to `dx-prototype`
- Performance issues → AD routed to `dx-image-to-code` / `dx-prototype` (whoever wrote the code)
- After fixes applied → re-run post-mode review (all 3 passes)

### Output: `dx/review/conformance-{date}.md`

```markdown
# DX Review Report: {subject}

## Verdict: PASS / FAIL

## Reference
- Design spec: {image path or url-dna.md reference}
- Design system: dx/design-system.md
- Viewport: {dimensions}

## Summary
| Pass | Status | Details |
|------|--------|--------|
| Visual Conformance | PASS/FAIL | {N} drift items |
| Performance Audit | PASS/FAIL | {N} blocking, {M} warnings |
| Interaction Verification | PASS/FAIL | {N} flows tested, {M} failed |

## Drift List (sorted by priority)
| # | Pass | Severity | Item | Location | Fix |
|---|------|----------|------|----------|-----|
| 1 | Visual | P0 | Anti-slop: matches "Dark Neon" default | global | Revise palette per design-system.md |
| 2 | Performance | P1 | bundle-barrel-imports | src/components/index.ts | Import directly |
| 3 | Interaction | P0 | Form submit → no feedback | /contact | Add success state |

## ADs Generated
- AD-{N}: {title} → routed to {skill}

## Screenshots
- {viewport screenshots + failure screenshots}

## Recommendations
- {top 3 actionable improvements}
```

---

## Common Pitfalls

- **Skipping post-mode review** — it's a blocking gate, not optional.
- **Eyeballing in post-mode** — always screenshot diff.
- **Fixing issues yourself** — you find and route, you don't fix.
- **Audit mode as a gate** — pre-mode is informational, not blocking.
- **P2/P3 blocking the pipeline** — only P0/P1 should block. P2/P3 are acceptable to ship with a note.

## Tooling
Needs a **browser-automation tool** for screenshots and DOM inspection. Without one, post-mode conformance is unreliable — flag that the review is unverified.
