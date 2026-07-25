# Expert Skill Patterns — Extracted from Industry Frameworks

> This file extracts actionable structural patterns from the top-performing skill frameworks
> and grading systems. Each pattern is cited to its source and mapped to our 7-dimension model.

---

## 1. SkillzWave Grading Model (100-point scale)

**Source**: SkillzWave marketplace grading system, used to score all Superpowers skills (github.com/obra/superpowers/issues/202, Dec 2025). Grading model: Claude via SkillzWave.

### 5 Pillars + Modifiers

| Pillar | Max | Sub-criteria | Maps to Our Dim |
|--------|:---:|-------------|:---:|
| **Progressive Disclosure Architecture** | 30 | Token Economy (10), Layered Structure (10), Reference Depth (5), Navigation Signals (5) | D2 |
| **Ease of Use** | 25 | Metadata Quality (10), Discoverability (6), Terminology Consistency (4), Workflow Clarity (5) | D3 + D4 |
| **Spec Compliance** | 15 | Frontmatter Validity (5), Name Conventions (4), Description Quality (4), Optional Fields (2) | D1 |
| **Writing Style** | 10 | Voice & Tense (4), Objectivity (3), Conciseness (3) | D5 |
| **Utility** | 20 | Problem Solving Power (8), Degrees of Freedom (5), Feedback Loops (4), Examples & Templates (3) | D6 |
| **Modifiers** | ±15 | Penalties: xml_tags_in_metadata (-5), first_second_person_description (-2). Bonuses: grep_friendly_structure (+1), gerund_style_name (+1) | D7 |

### Grade Scale

| Grade | Score | Meaning |
|:---:|:---:|---------|
| A | 90-100 | Production-ready |
| B | 80-89 | Good, minor work |
| C | 70-79 | Adequate, gaps |
| D | 60-69 | Needs work |
| F | <60 | Major revision |

### Key Findings from Grading Superpowers (68/100 = D)

Even the most popular skill framework (89K stars) scored D on its meta-skill. Issues found:
1. **Emotional/marketing language** in headers ("EXTREMELY-IMPORTANT", "not negotiable") → -2 Writing Style
2. **Second-person voice** ("you") instead of imperative/infinitive → -1 Writing Style
3. **Redundant content** (11 Red Flags repeating same message) → -2 PDA
4. **Missing concrete examples** (no before/after invocation examples) → -1 Utility
5. **Overly broad trigger** ("any conversation") → -1 Ease of Use

**Lesson for our audit**: Even expert skills have measurable deficiencies. Objective scoring catches what popularity hides.

---

## 2. Superpowers Enforcement Patterns

**Source**: Jesse Vincent, obra/superpowers (89K GitHub stars, MIT, Anthropic marketplace Jan 2026). Analysis from Termdock deep-dive (Mar 2026).

### The Iron Law Pattern

The single most effective enforcement structure observed across all skill frameworks:

```
> NO [ACTION] WITHOUT [PREREQUISITE] FIRST.
> [Violation consequence]. Start over. No exceptions.
```

**Real examples from Superpowers**:
- TDD: "NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST. Write code before the test? Delete it. Start over."
- Debugging: "NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST."
- Brainstorming: "Do NOT invoke any implementation skill, write any code, scaffold any project, or take any implementation action until you have presented a design and the user has approved it."

### Rigid vs Flexible Classification

Superpowers explicitly classifies each skill's enforcement level:

| Type | Characteristics | When to use |
|------|----------------|-------------|
| **Rigid** | Iron laws, explicit prohibitions, delete-and-restart consequences | Domains where cutting corners causes compounding damage (TDD, debugging) |
| **Structured-Adaptive** | Checklist + hard gate, but approach varies by context | Creative/exploratory work (brainstorming, planning) |
| **Advisory** | Reports findings + severity, human decides | Review/audit skills |

**Audit implication (D6)**: A skill should declare its enforcement level. If it claims to be rigid but uses "should/consider" language, that's a D6 deficiency.

### Process Chain Pattern

Superpowers' compounding effect comes from skill output → next skill input:

```
Brainstorming → spec document
  → Writing Plans → task list (2-5 min each, exact file paths, zero-context assumption)
    → Subagent Development → implementation (fresh context per task)
      → Code Review → severity report (separate agent, no implementer history)
```

**Audit implication (D4)**: Each skill's output format must match downstream's expected input. Hand-off triggers are not optional — they are interface contracts.

### Anti-Pattern Catalogue Pattern

Superpowers TDD skill includes a reference file cataloguing common mistakes:
- "Testing implementation details instead of behavior"
- "Writing tests after code (test-after development)"
- "Mocking everything (mockitis)"

**Audit implication (D2)**: Anti-pattern references are high-value progressive disclosure content — too verbose for SKILL.md body, perfect for references/.

---

## 3. Anthropic Official Guide Patterns

**Source**: "The Complete Guide to Building Skills for Claude", Anthropic, January 2026 (33 pages). Summary via Sola Fide (Mar 2026) + Anthropic Engineering Blog (Dec 2025).

### Three-Level Progressive Disclosure (Canonical)

| Level | What | When loaded | Token cost |
|:---:|------|------------|:---:|
| 1 | YAML frontmatter (name + description) | Always (system prompt) | ~50 tokens |
| 2 | SKILL.md body | When description matches task | ~500-2000 tokens |
| 3 | references/ files | On-demand, when skill body references them | Variable |

**Design principle**: "Like a well-organized manual that starts with a table of contents, then specific chapters, and finally a detailed appendix."

### Three Skill Categories

| Category | Pattern | Key technique |
|----------|---------|---------------|
| **Content Generation** | Produce consistent outputs (docs, code, designs) | Embedded style guides + template structures + quality checklists |
| **Multi-Step Workflows** | Consistent methodology with gates | Explicit steps + validation gates + dependencies + iterative refinement |
| **MCP Enhancement** | Reliable workflows on top of tool access | Coordinate multiple tool calls + embed domain expertise |

### Description Field Best Practices

```yaml
# GOOD — specific, actionable, includes triggers
description: >
  Analyzes Figma design files and generates developer handoff documentation.
  Use when user uploads .fig files, asks for "design specs",
  "component documentation", or "design-to-code handoff".

# BAD — too vague
description: Helps with projects.

# BAD — missing triggers
description: Creates sophisticated multi-page documentation systems.
```

### Body Writing Principles

1. **Specific > Abstract**: Not "validate the data" but "Run `python scripts/validate.py --input {filename}`"
2. **Error handling mandatory**: "When MCP connections fail, what should Claude check?"
3. **Conditional routing**: Different approaches based on context, with clear decision criteria
4. **Iterative refinement**: Generate → validate → fix → regenerate → repeat until threshold

### Testing Methodology (3 Areas)

| Area | Tests |
|------|-------|
| **Trigger** | Does it load when it should? Does it NOT load when it shouldn't? Test: obvious, paraphrased, unrelated |
| **Functional** | Do workflows produce correct outputs? Do error paths work? |
| **Comparative** | Does skill improve results vs no-skill? Measure: token usage, error rates, back-and-forth count |

---

## 4. Cross-Agent Portability Patterns

**Source**: Agensi.io, "SKILL.md Cross-Agent Compatibility: Tested Across 6 Agents", May 2026. 10 skills × 6 agents (Claude Code, Codex CLI, Gemini CLI, Cursor, Copilot, OpenClaw).

### Universal Compatibility Rules

| Rule | Evidence |
|------|---------|
| Use only `name` + `description` in frontmatter | 8/10 skills worked on all 6 agents with these fields only |
| Write instructions in plain markdown | Numbered steps, headers, code examples, tables — parsed by all |
| Don't assume subagent support | Design for linear execution; parallelism is bonus |
| Don't rely on tool permissions | `allowed-tools` only enforced by Claude Code + OpenClaw |
| Description is #1 trigger factor | Vague descriptions caused missed triggers on Gemini CLI and Copilot |
| Include concrete examples | Reduces cross-agent interpretation variance |

### Agent-Specific Quirks

| Agent | Quirk |
|-------|-------|
| Claude Code | Most reliable trigger; supports `when_to_use` for additional matching |
| Codex CLI | Occasionally needs more explicit prompts for trigger |
| Gemini CLI | Vague descriptions → more missed triggers than Claude Code |
| Cursor | Requires window reload after install; project-scoped only |
| Copilot | Most conservative triggering; needs close description match |
| OpenClaw | Follows SKILL.md spec closely; matches Claude Code behavior |

### Frontmatter Field Support

| Field | Support level |
|-------|:---:|
| `name`, `description` | Universal (6/6) |
| `when_to_use`, `argument-hint` | Wide (4+/6) |
| `allowed-tools`, `context`, `agent`, `hooks` | Agent-specific (1-2/6) |

---

## 5. Termdock Architecture Guidelines

**Source**: Termdock.com, "Agent Skills Guide 2026: Build, Share & Secure", March 2026.

### Structural Rules

| Rule | Rationale | Data |
|------|-----------|------|
| SKILL.md < 500 lines | Context window cost per load | ETH Zurich: overly detailed context degrades performance |
| One skill, one verb | Split when two trigger patterns exist | "Review code" ≠ "Write PR description" |
| Scripts for deterministic tasks | Linting, formatting, deploying have exact commands | Agent improvisation is expensive and unreliable |
| Progressive disclosure | Move large reference to separate files | 10,000 lines of knowledge → efficient context via 3-level loading |
| Description optimization | Highest-leverage single improvement | Skill Creator eval loop: 60% train / 40% test, 5 iterations |

### Context Hierarchy

| Mechanism | Scope | Loaded when | Best for |
|-----------|-------|------------|---------|
| CLAUDE.md / AGENTS.md | Project | Always | Architecture, conventions, hard constraints (200-500 words) |
| SKILL.md | Task | On demand | Specific procedures, templates, checklists |
| MCP Servers | External | On tool call | Live data access |

**Anti-pattern**: Stuffing everything into CLAUDE.md. If > 500 words, extract task-specific sections into skills.

---

## 6. Pattern Integration Matrix

How each expert pattern maps to our 7-dimension audit:

| Our Dim | SkillzWave Pillar | Superpowers Pattern | Anthropic Principle | Agensi Rule | Termdock Guideline |
|---------|-------------------|--------------------|--------------------|-------------|-------------------|
| D1 Structure | Spec Compliance (15pts) | — | Frontmatter spec | Universal fields | One skill one verb |
| D2 Disclosure | PDA (30pts) | Anti-pattern catalogue | 3-level loading | — | <500 lines |
| D3 Trigger | Ease of Use: Discoverability (6pts) | — | Description best practices | Description = #1 factor | Description optimization |
| D4 Coherence | Ease of Use: Workflow Clarity (5pts) | Process chain | Sequential workflows + gates | — | — |
| D5 Language | Writing Style (10pts) | — | Specific > Abstract | Plain markdown | — |
| D6 Enforcement | Utility: Problem Solving (8pts) | Iron Law + Rigid/Flexible | Validation gates | — | Scripts for deterministic |
| D7 Safety | Modifiers (±15pts) | — | Security considerations | Tool permission limits | — |

---

## 7. "What Good Looks Like" — Composite Exemplar

Synthesized from all sources, the ideal SKILL.md structure:

```markdown
---
name: <kebab-case, matches directory>
description: "<Verb> <artifact>. Use when/after <trigger context>. Trigger: /<command>, <phrase1>, <phrase2>."
version: <semver>
---

# <Title> (<Phase/Role>)

> | | |
> |---|---|
> | **Upstream** | <skill that produces this skill's input> |
> | **Downstream** | <skill that consumes this skill's output> |
> | **Owns** | <files this skill exclusively writes> |
> | **Does** | <3-5 core behaviors> |
> | **Does NOT** | <3-5 explicit exclusions> |

You are a [Specific Role Title]. <One-sentence mission with enforcement tone>.

## Hard Constraints

1. **<CONSTRAINT NAME>**: <Imperative statement>. <Violation consequence>.
   [Iron Law pattern for rigid constraints]

## Steps to Execute

1. **<Step Name>**: <Specific action with exact file paths and commands>
   - Validation: <how to verify this step succeeded>
   - On failure: <explicit recovery path>

## Output Format

<Exact structure of what this skill produces — template with placeholders>

## Hand-off Trigger

> <Exact message output when skill completes, directing to next skill>

## Manifest Protocol

This skill reads: <explicit file list>
This skill writes: <explicit file list>

## Additional Resources

- [references/<file>.md](references/<file>.md) — <when to read this>
```

### Why this structure (citation per element)

| Element | Source | Evidence |
|---------|--------|---------|
| Pipeline Context Table | Superpowers process chain | Skill output = next skill input; interface contract |
| "You are a [Role]" | Anthropic guide + PEEM Clarity | Persona anchoring improves Agent consistency |
| Iron Law constraints | Superpowers TDD/Debugging | "Speed bump vs speed limit sign" — enforcement > suggestion |
| Numbered steps with validation | Anthropic "Multi-Step Workflows" | Validation gates + dependencies + rollback |
| Output Format section | PEEM Response Clarity axis | 3-4 point Clarity improvement in zero-shot rewriting |
| Hand-off Trigger | Superpowers process chain | Explicit interface contract between skills |
| Manifest Protocol | Snyk ToxicSkills mitigation | Explicit file ownership prevents overreach |
| "read X when Y" references | Anthropic 3-level disclosure | Progressive disclosure = core design principle |
