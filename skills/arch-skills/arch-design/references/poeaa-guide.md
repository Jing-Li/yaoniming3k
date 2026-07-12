# PoEAA Pattern Selection Guide

Reference for Step 2.8 of `/arch-design`. Load when selecting PoEAA implementation pattern.

---

## 1. PoEAA Pattern Decision Matrix

Use this matrix to select the implementation pattern. The pick is whichever row has the most "yes".

| Signal | Domain Model | Transaction Script | Table Module |
|--------|:------------:|:------------------:|:------------:|
| Many invariants attached to entity state | ✅ | ❌ | ⚠️ |
| Behavior naturally lives on the noun | ✅ | ❌ | ⚠️ |
| Aggregate depth ≥ 2 | ✅ | ❌ | ❌ |
| Mostly CRUD with occasional rules | ❌ | ✅ | ⚠️ |
| Set-oriented / report-heavy logic | ❌ | ⚠️ | ✅ |
| Team is small and domain is shallow | ❌ | ✅ | ⚠️ |
| Workflow orchestration dominates | ❌ | ✅ | ❌ |
| ORM-friendly but logic is per-table | ❌ | ❌ | ✅ |

**Rules of thumb:**
- If you cannot name three non-trivial invariants, **don't** pick Domain Model — you'll over-engineer.
- If most use cases are "load → mutate one field → save", pick Transaction Script.
- Table Module is rare outside legacy/reporting systems.

---

## 2. Devil's Advocate Challenge (mandatory)

After selecting a pattern, generate 1–2 strongest counter-arguments based on signals collected during Phase 1.

### When user selects Domain Model

Challenge if:
- Invariant count ≤ 3
- Aggregate depth ≤ 1
- Most operations are simple CRUD

Example:
> ⚠️ Devil's Advocate: Your invariants are only 3 and aggregate depth is ≤1. Transaction Script may be simpler — are you sure you need Domain Model's complexity? If the domain grows, you can always refactor later, but over-engineering now costs immediate productivity.

### When user selects Transaction Script

Challenge if:
- State machine has 5+ states
- Multiple conditional combinations on same entity
- Business rules span 3+ conditions

Example:
> ⚠️ Devil's Advocate: You mentioned order cancellation has 3 condition combinations and the state machine has 5 states. Transaction Script can handle it, but you'll regret it when conditions multiply — consider Domain Model?

### When user selects Table Module

Challenge if:
- Business has any non-trivial invariants
- Domain has meaningful relationships between entities

Example:
> ⚠️ Devil's Advocate: Table Module works for report-heavy systems, but your domain has entity relationships and invariants. Are you sure this isn't a legacy bias?

### Protocol

1. Present the challenge to the user
2. Wait for user response
3. Record both the counter-argument and user's rebuttal in ARCHITECTURE.md
4. If user cannot defend their choice, suggest reconsidering

---

## 3. Tracer Bullet Goal

The single thinnest end-to-end vertical slice that proves the architecture works.

**Format:** One sentence with three components:
- **Actor** — who initiates the action
- **Action** — what they do
- **Observable outcome** — what confirms success

**Examples:**
- "An operator registers a new agent via CLI and sees it appear in `census list`."
- "A customer places an order and receives an order confirmation with tracking number."
- "An admin imports a CSV of products and sees them appear in the search index within 5 seconds."

**Rules:**
- Must traverse ALL architecture layers (Domain → Application → Infrastructure → Delivery)
- Must be implementable as a single devtdd task or small cluster of tasks
- Must produce an externally observable result (CLI output, HTTP response, database row, log entry)

---

## 4. Recording in ARCHITECTURE.md

Add to ARCHITECTURE.md a new section:

```markdown
## PoEAA Pattern & Tracer Bullet

**PoEAA Pick:** `Domain Model | Transaction Script | Table Module`

**Justification:**
> <one paragraph grounded in business signals from BRD.md>

**Devil's Advocate:**
> Challenge: <counter-argument>
> Response: <user's rebuttal>

**Tracer Bullet Goal:**
> <actor → action → observable outcome>
```

This section should also be covered by an ADR (see Step 2.7 ADR Generation triggers).
