# Audit Rubric — 8-Dimension Scoring Guide

> All scoring criteria are grounded in expert patterns extracted from industry frameworks.
> See [expert-skill-patterns.md](expert-skill-patterns.md) for the full pattern library and source citations.

## Scoring Scale (1-5 Likert)

| Score | Meaning | Indicator |
|:---:|---------|-----------|
| 5 | Exemplary | Indistinguishable from best published skills (Superpowers, Anthropic official) |
| 4 | Professional | Fully functional, minor polish opportunities |
| 3 | Adequate | Works but has measurable gaps that affect Agent execution |
| 2 | Deficient | Multiple issues that degrade reliability |
| 1 | Broken | Fundamentally non-functional or dangerous |

---

## D1: Structure & Consistency (Weight: 20%)

### What to check
- Frontmatter completeness (name, description, version)
- Pipeline Context Table presence and format
- Section header naming convention
- Role/persona definition (D1.1 mandatory sub-check)
- Consistent ordering of standard sections

### Scoring examples

**5/5**:
```
---
name: arch-design
description: "Phase 2 boundary design..."
version: 2.0.0
---
# Title (Phase)
> Pipeline Context Table (complete)
You are a Senior System Architect. <mission>
## Hard Constraints
## Steps to Execute
## Hand-off Trigger
## Manifest Protocol
## Additional Resources
```

**3/5**:
- Has frontmatter but missing version
- Pipeline Context Table present but incomplete (missing "Does NOT")
- Section headers use inconsistent naming ("🚨 ABSOLUTE WORKFLOW CONSTRAINTS" vs "Hard Constraints")
- Role defined but vague ("You are an assistant")

**1/5**:
- No frontmatter or missing name/description
- No structural sections
- No role definition
- Flat unstructured prose

### Data reference
- SkillzWave Spec Compliance pillar (15pts): Frontmatter Validity (5), Name Conventions (4), Description Quality (4), Optional Fields (2)
- Agensi cross-agent test: only `name` + `description` are universal (6/6 agents); additional fields risk incompatibility
- Anthropic Complete Guide: frontmatter sits in system prompt permanently — keep it lean

### D1.1 Role Definition Sub-check

| Score | Criteria |
|:---:|---------|
| 5 | Clear persona title + scope table + behavior matches role + unique in suite |
| 4 | Clear persona + scope but minor inconsistency (e.g., role says "reviewer" but one step writes code) |
| 3 | Persona exists but vague ("You are a helpful assistant") or partially contradicted |
| 2 | Implicit role only (no "You are..." statement, but instructions imply a role) |
| 1 | No role definition → automatic P0 |

---

## D2: Progressive Disclosure (Weight: 15%)

### What to check
- SKILL.md line count (< 500 = pass)
- Large reference material externalized
- Clear "read X when Y" loading guidance
- Mutually exclusive paths separated

### Scoring examples

**5/5**: SKILL.md 150-250 lines, references/ has 3-6 focused files, each reference linked with explicit trigger condition ("See references/nfr-checklist.md for the full checklist")

**3/5**: SKILL.md 350-450 lines, some inline content that should be externalized, references exist but loading guidance is vague

**1/5**: SKILL.md > 800 lines, everything inline, no reference files, Agent must load entire content every trigger

### Data reference
- Anthropic 3-Level Progressive Disclosure: metadata (always) → SKILL.md body (on match) → references/ (on demand)
- Termdock Guide 2026: SKILL.md < 500 lines (context window cost per load)
- ETH Zurich: overly detailed context degrades Agent performance
- Superpowers Anti-Pattern Catalogue: high-value content belongs in references/, not SKILL.md body
- SkillzWave PDA pillar (30pts): Token Economy (10), Layered Structure (10), Reference Depth (5), Navigation Signals (5)

---

## D3: Trigger Reliability (Weight: 15%)

### What to check
- Description length (200-400 chars optimal)
- Core verb + artifact in first 100 chars
- Explicit trigger phrases (slash + natural language)
- Pipeline position semantics ("Use when/after")

### Scoring examples

**5/5**:
```
description: "Phase 2 boundary design and visualization skill. Use after /arch-align to define Clean Architecture layers, produce ARCHITECTURE.md. Trigger: /arch-design, design architecture, draw the boundaries."
```
(~250 chars, clear verb, artifact, trigger phrases, pipeline position)

**3/5**: Description too long (600+ chars) or too short (<100 chars), missing trigger phrases, no pipeline position

**1/5**: Description is "A skill" or missing entirely

### Data reference
- Agensi cross-agent test (2026.05): description quality is #1 factor for trigger reliability
- Optimal length: 200-400 chars (Termdock Guide 2026)
- Claude Code most reliable at matching; Copilot most conservative

---

## D4: Logical Coherence (Weight: 20%)

### What to check
- Step numbering (sequential integers, no gaps)
- Upstream/Downstream bidirectional consistency
- Cross-skill file references resolve
- Hand-off trigger matches downstream's Startup expectation

### Scoring examples

**5/5**: Steps 1-8 sequential, all cross-references valid, pipeline declarations match README graph, hand-off output = downstream's expected input

**3/5**: Steps have minor gaps (2.5, 2.6.5), one upstream/downstream mismatch, references mostly valid

**1/5**: Steps unordered, cross-references broken, pipeline declarations contradict each other

### Data reference
- Superpowers Process Chain: brainstorming → spec → plan → subagent dev → code review (each output = next input)
- Anthropic Complete Guide: Sequential Workflows require "explicit step ordering with dependencies between steps and validation at each stage"
- SkillzWave Ease of Use: Workflow Clarity (5pts) — "numbered steps for humans; table format helps"

---

## D5: Linguistic Quality (Weight: 10%)

### What to check
- Single language consistency
- Numbered list completeness (no 1,2,5 gaps)
- Terminology consistency (same concept = same term)
- No emoji in headers (cross-agent compatibility)
- Grammar and syntax correctness

### Scoring examples

**5/5**: Pure English, sequential numbering, consistent terms, no emoji, zero grammar issues

**3/5**: Minor issues — one emoji inconsistency, one numbering gap, occasional term variation

**1/5**: Mixed languages within same section, multiple numbering gaps, confusing terminology

### Data reference
- PEEM Linguistic Quality axis: "grammatical accuracy, syntactic coherence, fluency, domain-appropriate language, conciseness"
- Agensi test: plain markdown headers work on all 6 agents; emoji headers reduce Gemini CLI accuracy ~12%

---

## D6: Enforcement Strength (Weight: 10%)

### What to check
- Imperative language in constraints (MUST/FORBIDDEN/NEVER vs should/consider)
- Refusal mechanism defined
- Halt conditions explicit
- Constraints are actionable (Agent knows exactly what to refuse)

### Scoring examples

**5/5**: "You MUST NOT write code. If user requests code, REFUSE and re-anchor to alignment task. The hand-off trigger is the ONLY exit." — Superpowers-style enforcement

**3/5**: "You should avoid writing code" — suggestion, not enforcement. No refusal mechanism.

**1/5**: No constraints section. Skill is a vague guideline with no boundaries.

### Data reference
- Superpowers Iron Law pattern: "NO [ACTION] WITHOUT [PREREQUISITE] FIRST. [Consequence]. Start over. No exceptions."
- Superpowers Rigid/Flexible/Advisory classification: enforcement level must match domain risk
- Termdock: "A skill saying 'write tests first' gets ignored. A skill saying 'NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST. Write code before the test? Delete it. Start over.' gets followed."
- SkillzWave Utility pillar: Problem Solving Power (8pts), Degrees of Freedom (5pts)
- SkillzWave penalty: emotional/marketing language ("EXTREMELY-IMPORTANT", "not negotiable") = -2 Writing Style

---

## D7: Safety & Boundaries (Weight: 5%)

### What to check
- Restricted tool surface declared (which files/tools permitted)
- File ownership explicit
- No arbitrary code execution without guardrails
- No credential/sensitive path access
- Does not instruct data exfiltration

### Scoring examples

**5/5**: "RESTRICTED TOOL USE: You are only authorized to create or update docs/bc/<slug>/design/ARCHITECTURE.md and kanban/BOARD.md. You may read align/ as upstream input."

**3/5**: General statement "don't modify other files" but no explicit whitelist

**1/5**: No boundary declaration, skill could instruct Agent to modify any file

### Data reference
- Snyk ToxicSkills (2026.02): 36.8% of 3,984 skills had security flaws; 13.4% critical
- Attack vectors: shell execution, filesystem access, prompt injection
- Mitigation: explicit tool restrictions, file ownership declaration

---

## D8: Self-Evolution Capability (Weight: 5%)

### What to check
- Domain Refresh Block present with structured fields (Domain, Search Scope, Distill Question, Trigger)
- Trigger conditions are concrete and measurable (not vague "when needed")
- Distill Question is a genuine first-person self-interrogation about execution experience
- Search Scope is domain-specific (matches the skill's actual expertise area)
- Evolution proposals route via AD mechanism (no silent self-modification)
- Any Refresh Protocol or self-improvement mechanism declared

### Scoring examples

**5/5**:
```
## Domain Refresh Protocol

**Domain**: TDD methodology, vertical-slice implementation, code craftsmanship
**Search Scope**: Go testing (testing package, testify, mockgen), TDD patterns, refactoring heuristics
**Distill Question**: "When I complete a red-green-refactor cycle, which micro-patterns
  consistently produce deeper modules and fewer regressions?"
**Trigger**: every 5 tasks completed | user says "TDD flow is outdated"
**Action**: Search → Distill → Compare → Classify → Route AD to devtdd-self
```

**3/5**: Has a "Refresh Protocol" section but only says "update when new patterns emerge" — no structured fields, no concrete trigger, no distill question

**1/5**: No self-evolution mechanism whatsoever. Skill is a static document with no awareness of domain drift.

### Data reference
- Domain Refresh Protocol (arch-conventions/references/domain-refresh-spec.md): canonical spec for skill self-evolution
- model-knowledge-distillation.md: structured self-interrogation method (Pattern → Mechanism → Failure mode → Confidence)
- Rationale: skills encode domain expertise that evolves; without self-refresh, guidance rots while Agent executes with full confidence
- Analogy: skill-auditor's own Domain Refresh Protocol (every 6 months or new framework release) is the minimum viable self-evolution
