# Domain Refresh Protocol — Skill Self-Evolution Spec

> Canonical spec owned by arch-conventions. All arch-skills reference this for
> domain self-reflection and autonomous evolution capability.

---

## §1 Purpose

A skill is NOT a static document. It encodes domain expertise that evolves over time
(new language features, new patterns, new anti-patterns discovered). Without a
self-evolution mechanism, skills rot — their guidance becomes stale while the Agent
executes them with full confidence.

This protocol gives each skill the ability to:
1. **Detect** when its domain knowledge may be stale
2. **Search** for current best practices in its specific domain
3. **Distill** patterns from the model's own execution experience
4. **Validate** new knowledge against existing constraints
5. **Propose** updates via AD routing (never self-modify silently)

---

## §2 Protocol Structure

Each skill declares a **Domain Refresh Block** with these fields:

```markdown
## Domain Refresh Protocol

**Domain**: <the skill's expertise area, e.g., "TDD methodology + Go testing ecosystem">
**Search Scope**: <what to search for, e.g., "Go testing patterns, table-driven tests, fuzzing, benchmark practices">
**Distill Question**: <first-person self-interrogation, e.g., "When I execute red-green-refactor, which patterns produce the most maintainable code?">
**Trigger**:
  - Periodic: every <N> task completions (or every 6 months)
  - Event: user reports "this guidance is outdated" or "there's a better way"
  - Detection: skill encounters a pattern it cannot classify with existing rules

**Action** (on trigger):
1. Search: query current best practices within Search Scope
2. Distill: answer the Distill Question from execution experience
3. Compare: new findings vs existing Hard Constraints and Steps
4. Classify:
   - ADDITIVE (new pattern, no conflict) → propose as reference addition
   - CONFLICTING (contradicts existing constraint) → propose as AD to self
   - OBSOLETE (existing rule no longer applies) → propose as AD to self with deprecation
5. Route: write AD targeting `<skill-name>-self` with proposal. NEVER auto-modify.
```

---

## §3 Per-Skill Declaration Examples

### devtdd

```
Domain: TDD methodology, vertical-slice implementation, code craftsmanship
Search Scope: Go testing (testing package, testify, mockgen), TDD patterns,
  refactoring heuristics, test architecture, coverage strategies
Distill Question: "When I complete a red-green-refactor cycle, which micro-patterns
  consistently produce deeper modules and fewer regressions?"
Trigger: every 5 tasks completed | user says "TDD flow is outdated"
```

### arch-design

```
Domain: Clean Architecture, DDD tactical patterns, dependency management
Search Scope: Clean Architecture evolution, new ADR practices, module boundary
  patterns, polyglot architecture, event-driven patterns
Distill Question: "When I define layer boundaries, which decisions lead to
  the least dependency violations in downstream devtdd?"
Trigger: every 3 BC designs completed | user says "architecture patterns outdated"
```

### arch-align

```
Domain: Domain-Driven Design strategic patterns, ubiquitous language, UX clarification
Search Scope: DDD community updates, bounded context heuristics, event storming
  evolution, UX writing patterns
Distill Question: "When I grill terminology, which question patterns converge
  fastest to a stable dictionary with fewest revisions?"
Trigger: every 4 BCs aligned | user says "alignment process outdated"
```

### arch-review

```
Domain: Architecture compliance auditing, code review methodology, critical reasoning
Search Scope: Static analysis evolution, architecture fitness functions,
  review automation, OWASP updates, technical debt measurement
Distill Question: "When I audit code against blueprints, which detection heuristics
  find the most impactful violations with fewest false positives?"
Trigger: every 5 audits completed | user says "audit criteria outdated"
```

---

## §4 Distillation Method

The Distill step uses **structured self-interrogation** (same method as
skill-auditor's model-knowledge-distillation.md):

1. **Recall**: Think of the last N executions of this skill's core workflow
2. **Pattern extraction**: "What did I do that worked unexpectedly well/poorly?"
3. **Mechanism**: "WHY did it work/fail from the executor's perspective?"
4. **Generalization**: Strip project-specific details → produce a reusable pattern
5. **Confidence**: Rate High/Medium/Low based on how many executions support it

Output format per distilled pattern:

```
Pattern: <what the instruction looks like>
Mechanism: <why it works from executor's cognitive architecture>
Evidence: <N executions observed, success rate>
Confidence: High/Medium/Low
Recommendation: ADD to references / MODIFY existing step / DEPRECATE old rule
```

---

## §5 Search Protocol

When the Trigger fires, the skill SHOULD:

1. **Scope the query** to its declared Search Scope (not generic "best practices")
2. **Prefer primary sources**: official docs, RFCs, conference talks > blog posts
3. **Cross-validate**: a pattern from 1 source is a hypothesis; from 3+ sources is a candidate
4. **Date-filter**: prefer sources from the last 12 months for fast-moving domains;
   last 3 years for stable domains (DDD, Clean Architecture)
5. **Record provenance**: every new pattern cites its source (author, date, URL/title)

---

## §6 Integration with AD Protocol

Domain Refresh findings route through the standard AD mechanism:

```
AD-{ID}: Domain Refresh — <pattern title>
  Location: <which section/step of the skill>
  Type: ADDITIVE | CONFLICTING | OBSOLETE
  Evidence: <source citation + distillation confidence>
  Proposal: <concrete change description>
  (by <skill-name> Domain Refresh, <date>)
```

**Hard rules**:
- Domain Refresh NEVER auto-modifies the skill. It proposes via AD only.
- User confirms before any change is applied (AskUserQuestion per AD).
- ADDITIVE changes to references/ may be batch-approved.
- CONFLICTING/OBSOLETE changes to Hard Constraints require individual confirmation.

---

## §7 Compliance Levels

| Level | Meaning | Audit Score (D8) |
|:---:|---------|:---:|
| Full | Domain Refresh Block present + all fields filled + trigger conditions defined | 5/5 |
| Partial | Block present but missing Search Scope or Distill Question | 3-4/5 |
| Minimal | Only a "Refresh Protocol" mention without structured fields | 2/5 |
| None | No self-evolution mechanism declared | 1/5 |

---

## §8 Relationship to skill-auditor

skill-auditor checks D8 (Self-Evolution Capability) against this spec:
- Does the skill declare a Domain Refresh Block?
- Are Trigger conditions concrete (not just "when needed")?
- Is the Distill Question a genuine first-person interrogation?
- Does the Search Scope match the skill's actual domain?
- Is the AD routing mechanism present (no silent self-modification)?

See skill-auditor `references/audit-rubric.md` §D8 for scoring criteria.
