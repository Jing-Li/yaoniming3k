---
name: dx-prototype
description: "Assemble a clickable, runnable prototype from screens/components — wiring navigation, state, and interactions so a team can actually click through it. Use when the user says 'make it clickable', 'build a prototype', 'wire up the flow', 'interactive prototype', or has static screens that need to come alive. Part of the dx pipeline. Verifies interactions with a browser tool."
version: 1.0.0
---

# DX — Prototype

Turn static screens into a working clickable flow that demonstrates the experience end to end. A prototype's job is to let someone *experience the flow* and give feedback — not to be production-hardened. Stubs are fine and expected; broken navigation is not.

## Pipeline Position

> **dx pipeline** · Interaction Wiring
>
> | | |
> |---|---|
> | **Upstream** | `dx-image-to-code` or `dx-url-to-code` (static screens) + `arch-detail` (OpenAPI contracts in `detail/api-contracts/`) |
> | **Downstream** | `dx-review` (conformance check, blocking gate) |
> | **Owns** | Prototype source code (frontend app), `dx/prototype/` |
> | **Does** | Wire routing/navigation, add interaction states, stub data, verify happy path + error states |
> | **Does NOT** | Design visual layout, write backend code, implement real API calls, deploy |

## HARD CONSTRAINTS

1. **Restricted tool surface.** Only modify prototype source code and `dx/prototype/`. Do not touch `detail/api-contracts/`, backend source, or arch pipeline artifacts.
2. **Stub, don't implement.** Use in-memory stores, fixture data, and mock responses. Mark every stub with `TODO: real API`. Never wire a real backend.
3. **One command to run.** `npm install && npm run dev` (or project equivalent). Reviewers must be able to start it without thinking.
4. **Follow AskUserQuestion spec.** All user interactions use structured questions per `ask-user-question-spec.md`.

## When to use
- You have screens/components (from image-to-code, url-to-code, or ideate) and need them connected.
- "Make it clickable", "wire the flow", "let me click through it".
- Validating a UX flow with stakeholders before real backend work.

## When NOT to use
- No screens exist yet → build them first (`dx-image-to-code` / `dx-url-to-code`).
- You need production code with real data/auth — that's an engineering task (`devtdd`).
- Just checking a built prototype against the design → `dx-review`.

## Inputs
- The **screens/components** to connect (from upstream dx skill).
- The **flow to demonstrate**: happy path + key states (from BRD.md §5 UX Context).
- `detail/api-contracts/openapi.yaml` — Code-first OpenAPI 3.x spec for API stub shapes (generated from real code by devtdd).

## Workflow

1. **Map the flow graph**: screens are nodes, actions are edges (click → navigate, submit → state change). Write it down before wiring.
2. **Wire routing/navigation** between screens.
3. **Add interaction states**: hover, active, disabled, loading, empty, error, success. Cover at least the **happy path + one error state** (the most-skipped, most-important state).
4. **Stub data** so it's clickable without a backend; clearly mark where real data plugs in. Align stub shapes with `detail/api-contracts/` OpenAPI specs.
5. **Verify**: drive the whole happy path in a browser-automation tool — click every step, confirm nothing dead-ends. Fix what breaks.
6. Keep it **runnable with one command**.

## Quality bar / Definition of done
- Full happy path is clickable end to end.
- At least one error/empty state is present and reachable.
- No dead ends or broken links.
- Runs locally; build + typecheck clean.
- A browser walkthrough of the happy path passes.

## Common pitfalls
- **Happy-path only** — skipping error/empty/loading states; those are where real feedback comes from.
- **Dead ends** — a button that goes nowhere kills the demo. Walk every path.
- **Over-engineering** — wiring a real backend/auth for a prototype. Stub it, mark the TODO.
- **Style drift** — re-styling screens during wiring so they no longer match the locked direction.
- **No verification** — assuming it works without clicking through it.

## Handoff
Working prototype → `dx-review` (conformance check vs the design + requirements). Don't share before review on anything stakeholder-facing.

## Tooling
Needs a **browser-automation tool** to verify the flow by clicking through it. Without one, wire carefully and manually note that the walkthrough is unverified.
