---
name: dx-url-to-code
description: "Clone a live website as a runnable local frontend. Fetches the page, extracts its design system and structure, and rebuilds it locally in your stack, then screenshot-compares to the original. Part of the dx pipeline. Produces url-dna.md for reuse. Uses browser tools for screenshot verification."
version: 1.0.0
---

# DX — URL To Code

Reproduce a live website as a local, runnable frontend that looks and behaves like the source. The key difference from `dx-image-to-code`: you have access to the real DOM, CSS, and assets — extract them, don't guess.

## Pipeline Position

> **dx pipeline** · Frontend Implementation (from URL)
>
> | | |
> |---|---|
> | **Upstream** | `arch-align` (BRD.md §5 UX Context) + `arch-detail` (OpenAPI contracts) + live URL |
> | **Downstream** | `dx-prototype` (wire interactivity) |
> | **Owns** | Frontend source code, `dx/screens/`, `dx/url-dna.md` |
> | **Does** | Fetch page, extract design DNA, rebuild components, screenshot-compare, iterate |
> | **Does NOT** | Copy backend logic, clone auth/API behavior, wire interactivity (that's dx-prototype) |

## HARD CONSTRAINTS

1. **Restricted tool surface.** Only modify frontend source code, `dx/screens/`, and `dx/url-dna.md`. Do not touch `detail/api-contracts/`, backend source, or arch pipeline artifacts.
2. **Extract, don't guess.** Use browser automation to read real CSS, measure real spacing, download real assets. Don't eyeball from screenshots.
3. **Rebuild, don't copy-paste.** Translate the design into clean, idiomatic components in the target stack. Don't dump raw HTML/CSS.
4. **Reuse before inventing.** If the project has existing components/tokens, use them. Don't create duplicates.
5. **Measure, don't eyeball.** Always capture + screenshot diff. "Looks close" isn't verification.
6. **Follow AskUserQuestion spec.** All user interactions use structured questions per `ask-user-question-spec.md`.

## When to use
- You have a **live URL** to reproduce locally.
- "Clone this page", "rebuild this site", "make it look like linear.app".
- Capturing design language from a reference site for reuse.

## When NOT to use
- The source is a **static image/mockup** (no live URL) → `dx-image-to-code`.
- You need interactivity/flow wiring → `dx-prototype`.
- The source is a complex web app with backend logic → you can clone the *look*, not the *behavior*.

## Inputs
- The **live URL** to reproduce.
- **Target stack**: confirm via AskUserQuestion; default to matching the repo, else React + Vite + Tailwind + TS.
- `arch-align` BRD.md §5 UX Context (visual constraints).
- `detail/api-contracts/openapi.yaml` — Code-first OpenAPI 3.x spec (generated from real code by devtdd, see `make openapi`).

## Workflow

1. **Fetch & inspect** the page via a browser-automation tool. Scroll to capture the full page (multiple screenshots if needed). Read the DOM to extract structure.
2. **Extract the Design DNA** — read real CSS, measure real spacing, identify the design system:
   - Typography: fonts, sizes, weights, line-heights
   - Colors: palette (primary, secondary, neutral, accent, semantic)
   - Spacing: scale (4px? 8px? 16px rhythm?)
   - Components: buttons, inputs, cards, nav patterns
   - Layout: grid system, breakpoints, container widths
   - Assets: icons, images, logos
3. **Write `url-dna.md`** — the extracted design system, reusable for future reference.
4. **Download assets** — fonts, icons, images. Save to `dx/assets/`.
5. **Build components** — translate the extracted design into clean components in the target stack. Match the structure, not the raw HTML.
6. **Screenshot compare** — capture your build at the same viewport as the source. Diff and iterate until gaps are minor and explained.
7. **Handle responsive** — after the primary viewport matches, adapt for other breakpoints.

## Standard Output: `dx/url-dna.md`

```markdown
# URL DNA: {url}

## Typography
- Headings: {font} — {sizes/weights}
- Body: {font} — {sizes/weights}
- Scale: {ratio or pattern}

## Colors
- Primary: {hex}
- Secondary: {hex}
- Neutral: {scale}
- Accent: {hex}
- Semantic: success/warn/error

## Spacing
- Base unit: {px}
- Scale: {pattern}
- Container max-width: {px}

## Components
- Button: {variants, sizes, states}
- Input: {variants, states}
- Card: {structure, padding, shadow}
- Nav: {pattern, behavior}

## Layout
- Grid: {columns, gap}
- Breakpoints: {list}
- Page structure: {header/sidebar/main/footer}

## Assets
- Fonts: {list + paths}
- Icons: {system used}
- Images: {paths}
```

## Quality bar / Definition of done
- Local build screenshot ≈ source at the target viewport; remaining diffs are minor and *explained*.
- `url-dna.md` accurately reflects the extracted design system.
- Assets downloaded and referenced correctly.
- Build + typecheck clean; runs locally with one command.
- Responsive handled after the reference-size match is solid.

## Common pitfalls
- **Eyeballing from screenshots** — you have the DOM, read it.
- **Copy-pasting raw HTML** — translate to clean components.
- **Missing scroll content** — scroll the full page before extracting.
- **Ignoring url-dna.md** — it's a reusable artifact, not throwaway.
- **Claiming parity without comparing** — always capture + diff.

## Handoff
Static screens + `url-dna.md` done → `dx-prototype` (wire interactivity/flow) → `dx-review` (conformance).

## Tooling
Needs a **browser-automation tool** (fetch page, read DOM, screenshot comparison). Optional image tool for missing assets. Without a browser tool you can still build from screenshots, but flag that extraction is limited.
