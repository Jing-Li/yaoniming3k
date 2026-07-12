# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- **`docs/bc/<slug>/CONTEXT.md`** — per-BC bounded context & glossary
- **`docs/arch/PHASES.md`** — pipeline status across all BCs
- **`docs/adr/`** — read ADRs that touch the area you're about to work in. Current ADRs: 0001–0020 (see AGENTS.md for status index).

If any of these files don't exist, **proceed silently**. Don't flag their absence.

## File structure

Multi-BC repo:

```
/
├── AGENTS.md                 # Agent config entry
├── docs/
│   ├── arch/
│   │   └── PHASES.md         # Pipeline status (all BCs)
│   ├── bc/                   # One directory per BC
│   ├── adr/                  # System-wide architecture decision records
│   │   ├── 0001-datasource-independent-project.md
│   │   ├── ...
│   │   └── 0020-llm-param-optimizer.md
│   └── agents/               # Agent tool config
│       └── domain.md         # This file
└── src/
```

## Use the glossary's vocabulary

When your output names a domain concept, use the term as defined in the target BC's `LANGUAGE.md`. Don't drift to synonyms the glossary explicitly avoids.

_(Populated by `/arch-align` as terms are aligned.)_

## Architecture invariants

_(Populated by `/arch-align` as constraints are locked.)_

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR-0007 (event-sourced orders) — but worth reopening because…_
