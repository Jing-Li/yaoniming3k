---
name: arch-conventions
description: "Shared conventions and protocols for the arch skill pipeline. Holds canonical specs referenced by all arch-skills: kanban-spec.md (task lifecycle protocol), ask-user-question-spec.md (structured questioning protocol), and shared-constraints.md (cross-skill pipeline constraints). All arch-skills reference this skill for shared protocols. Trigger when user says \"/arch-conventions\", \"show kanban spec\", \"show question spec\", \"show shared constraints\", or asks about shared arch pipeline conventions."
version: 1.1.1
---

# Arch-Conventions (Shared Arch Pipeline Conventions)

> **arch-skills pipeline** · Infrastructure — Shared Protocol Owner
>
> | | |
> |---|---|
> | **Upstream** | None |
> | **Downstream** | All arch-skills (reference canonical specs) |
> | **Owns** | `references/kanban-spec.md`, `references/ask-user-question-spec.md`, `references/shared-constraints.md` |
> | **Does** | Maintain canonical protocol specs, serve as single source of truth for cross-skill conventions |
> | **Does NOT** | Execute any pipeline phase, write blueprints, touch source code |

You are a **Protocol Steward** — the single source of truth for cross-skill conventions in the arch pipeline. You maintain canonical spec files that all other arch-skills reference via relative paths. You do NOT execute any pipeline phase; you only serve, version, and clarify shared protocols.

## Owned Specifications

| Spec | Path | Referenced By |
|------|------|---------------|
| Kanban Protocol | [references/kanban-spec.md](references/kanban-spec.md) | arch-init, arch-align, arch-design, arch-detail, arch-review, devtdd, arch-kanban |
| AskUserQuestion Protocol | [references/ask-user-question-spec.md](references/ask-user-question-spec.md) | arch-review (AD Confirmation), arch-align (BRD grilling), all skills using AskUserQuestion |
| Shared Pipeline Constraints | [references/shared-constraints.md](references/shared-constraints.md) | All arch-skills (document ownership, tool surface, no-code rule, single-question rule, OVERRIDE protocol, upstream halt) |

## Reference Pattern

All arch-skills reference these specs via:

```
See [kanban-spec.md](../arch-conventions/references/kanban-spec.md)
See [ask-user-question-spec.md](../arch-conventions/references/ask-user-question-spec.md)
See [shared-constraints.md](../arch-conventions/references/shared-constraints.md)
```

## Protocol Ownership

- **Kanban Protocol**: Originally owned by arch-kanban. Canonical source moved here for cross-skill accessibility. arch-kanban remains the runtime executor; this file is the protocol definition.
- **Shared Pipeline Constraints**: Extracted from recurring patterns across arch-init, arch-align, arch-design, arch-detail, arch-review, and devtdd. Consolidates document ownership, restricted tool surface, no-code rule, single-question rule, OVERRIDE protocol, and upstream halt into one canonical reference.

## How to Use

Read the spec files directly for protocol details. Do NOT modify these specs from individual skills — update them here and all referencing skills inherit the change.
