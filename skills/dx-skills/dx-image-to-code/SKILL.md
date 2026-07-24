---
name: dx-image-to-code
description: "Turn a reference image or mockup into a working local frontend that matches it closely. Inspects the image, extracts the design system (layout, type, spacing, color, components), implements it, then screenshot-compares and iterates to close the gap. Part of the dx pipeline. Uses a browser tool for screenshot verification."
version: 1.0.0
---

# DX — Image To Code

Reproduce a reference image as a real, runnable frontend — verified by screenshot diff, not "looks roughly like it". The discipline that separates this from generic codegen: you *measure* the result against the reference and iterate until the gap is minor and explainable.

## Pipeline Position

> **dx pipeline** · Frontend Implementation (from image)
>
> | | |
> |---|---|
> | **Upstream** | `arch-align` (BRD.md §5 UX Context) + `arch-detail` (OpenAPI contracts) + reference image/mockup |
> | **Downstream** | `dx-prototype` (wire interactivity) |
> | **Owns** | Frontend source code, `dx/screens/`, `dx/design-system.md` |
> | **Does** | Extract design system from image, implement frontend, screenshot-compare, iterate to close gaps |
> | **Does NOT** | Wire interactions/flow (that's dx-prototype), write backend code, deploy |

## HARD CONSTRAINTS

1. **Restricted tool surface.** Only modify frontend source code and `dx/screens/`. Do not touch `detail/api-contracts/`, backend source, or arch pipeline artifacts.
2. **Match, don't improve.** Reproduce the reference unless explicitly asked to deviate. Note any forced deviations (e.g. for a11y).
3. **Measure, don't eyeball.** Always capture + screenshot diff. "Looks close" isn't verification.
4. **Reuse before inventing.** If the project has existing components/tokens/fonts, use them. Don't create duplicates.
5. **Follow AskUserQuestion spec.** All user interactions use structured questions per `ask-user-question-spec.md`.

## When to use
- You have a mockup/screenshot (from a designer, arch-design ideate output, or generated) to implement.
- "Build this design", "code this screenshot", "make this real".
- Recreating a UI you can see but don't have code for.

## When NOT to use
- The source is a *live site* (you can hit its URL/HTML) → `dx-url-to-code` (it can extract real CSS).
- No image yet, just an idea → need design direction first.
- You need interactivity/flow wiring, not a static match → `dx-prototype` (run this first to build screens).

## Inputs
- The **reference image(s)** (path).
- **Target stack**: confirm via AskUserQuestion; default to matching the repo, else React + Vite + Tailwind + TS.
- `arch-align` BRD.md §5 UX Context (visual constraints, design system).
- `detail/api-contracts/openapi.yaml` — Code-first OpenAPI 3.x spec (generated from real code by devtdd, see `make openapi`).

## Workflow

0. **Generate design system** (v1.1.0+):
   a. Read `dx-conventions/references/design-tokens-spec.md` for the canonical structure.
   b. If `dx/design-system.md` already exists → read it, skip to Step 1.
   c. From the reference image, extract: palette, typography, spacing, layout, components.
   d. Read `dx-conventions/references/anti-slop-rules.md` → generate the Anti-Patterns section.
   e. Determine Signature Element (the one memorable thing) + Motion Tier.
   f. Write `dx/design-system.md` following the design-tokens-spec.md format.
1. **Inspect** the image with a vision/read tool. Inventory every meaningful element. Extract the design system: layout grid, type scale, spacing rhythm, palette, components, radii, shadows.
2. **Initialize project**: Read `dx-conventions/references/component-stack.md`. If no existing project → scaffold per the recommended stack (React+TS+Vite+Tailwind+shadcn/ui). If project exists → reuse. Translate `dx/design-system.md` tokens into CSS variables + Tailwind config.
3. **Reuse before inventing**: if adapting an existing project, read its components/tokens/fonts first and use them.
4. **First pass**: build to match the **primary viewport** as closely as possible. Don't chase responsive yet.
5. **Capture**: run the app, screenshot at the reference's exact dimensions via a browser-automation tool.
6. **Compare & list mismatches** in priority order: layout → type → spacing → color → icons.
7. **Iterate** until differences are minor and explainable. *Then* handle responsive (tablet/mobile).
8. **Missing assets**: use supplied files; generate raster assets with an image tool; or use clearly-marked placeholders + a note.

## Quality bar / Definition of done
- Implementation screenshot ≈ reference at the target viewport; remaining diffs are minor and *explained*.
- Existing design-system components/tokens reused, not duplicated.
- Build + typecheck clean; runs locally with one command.
- Responsive handled after the reference-size match is solid.

## Common pitfalls
- **Claiming parity without comparing** — always capture + diff.
- **"Improving" the design** — match the reference unless explicitly asked to deviate.
- **Inventing new tokens** when the project already has a scale — creates drift.
- **Chasing responsive too early** — nail the reference viewport first.
- **Eyeballing spacing/type** — measure against the reference; "looks like 16" is often 24.

## Handoff
Static screens done → `dx-prototype` (wire interactivity/flow) → `dx-review` (conformance).

## Tooling
Needs a **vision/read tool** (inspect the image) and a **browser-automation tool** (screenshot the build for comparison). Optional image tool for missing assets. Without a browser tool you can still build, but flag that visual parity is unverified.
