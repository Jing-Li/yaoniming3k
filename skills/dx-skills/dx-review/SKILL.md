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

### Workflow
1. **Capture** the implementation via browser-automation screenshots at the same viewport as the reference.
2. **Compare** against the design spec (reference image, mockup, or url-dna.md).
3. **Check** five fidelity surfaces (see below).
4. **Verdict**: PASS or FAIL.
5. **If FAIL**: write ADs to `kanban/tasks/T{N}.md`, route each issue to the responsible skill.
6. **If PASS**: mark review complete, downstream can proceed to `arch-ops`.

### Five Fidelity Surfaces
1. **Layout** — grid, spacing, alignment, component positioning
2. **Typography** — font family, size, weight, line-height, letter-spacing
3. **Color** — backgrounds, text colors, borders, semantic colors
4. **Components** — button styles, input states, card structures, nav patterns
5. **Behavior** — hover states, transitions, loading states, error states

### Severity Scale
- **P0 (Blocking)** — visually broken, wrong layout, missing critical element
- **P1 (High)** — noticeable drift in type/color/spacing that undermines the design
- **P2 (Medium)** — minor inconsistency, only visible on close inspection
- **P3 (Low)** — cosmetic polish, acceptable to ship

### AD Routing on FAIL
Each issue becomes an Architecture Discrepancy in `kanban/tasks/T{N}.md`:
- Visual drift (layout/type/color/components) → AD routed to `dx-image-to-code` or `dx-url-to-code`
- Interaction/behavior drift → AD routed to `dx-prototype`
- After fixes applied → re-run post-mode review

### Output: `dx/review/conformance-{date}.md`

```markdown
# Conformance Review: {subject}

## Verdict: PASS / FAIL

## Reference
- Design spec: {image path or url-dna.md reference}
- Viewport: {dimensions}

## Surface-by-Surface Results

| Surface | Status | Drift Details | Severity |
|---------|--------|---------------|----------|
| Layout  | PASS/FAIL | {details} | P{N} |
| Typography | PASS/FAIL | {details} | P{N} |
| Color | PASS/FAIL | {details} | P{N} |
| Components | PASS/FAIL | {details} | P{N} |
| Behavior | PASS/FAIL | {details} | P{N} |

## ADs Generated
- AD-{N}: {title} → routed to {skill}
- AD-{N}: {title} → routed to {skill}

## Notes
- {any context about acceptable deviations}
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
