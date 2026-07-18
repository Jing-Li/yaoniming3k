# AskUserQuestion Spec (结构化提问协议)

> Version: 1.0.0
> Scope: Cross-skill, referenced by all arch-skills that use AskUserQuestion
> This document defines the structured questioning protocol for all user-facing decision points.

---

## 1. Core Principle: Progressive Disclosure (渐进式披露)

Ask **ONE question at a time**. Wait for the user's response before asking the next. Never batch multiple questions into a single AskUserQuestion call.

### Why

- Reduces cognitive load — user focuses on one decision at a time
- Each answer may change the context for subsequent questions
- Mirrors expert consultation: one topic at a time, building on answers

---

## 2. Question Structure (问题结构)

Every AskUserQuestion call MUST follow this exact structure:

### 2.1 Analysis Context (分析先行 — BEFORE the question)

Before presenting options, provide:
- **What**: Brief summary of the finding/issue/decision point
- **Evidence**: Cite specific code paths, doc sections, line numbers
- **Why it matters**: Impact of this decision on the project

Format: Plain text paragraph(s) before the AskUserQuestion tool call.

### 2.2 Question (问题)

A clear, specific question ending with `?`. Example:
- "How should AD-D1 (SYSTEM.md Status column) be handled?"
- "Which approach for DESIGN.md §7 implementation tracking?"

### 2.3 Header (标题)

- **Max 12 characters**
- Use the relevant context: route name, skill name, or topic
- Examples: `"arch-design"`, `"arch-align"`, `"REVIEW.md"`, `"ops 目录"`

### 2.4 Options (选项)

**2-4 options**, each containing:

| Field | Requirement | Example |
|-------|------------|---------|
| **Label** | 1-5 words, concrete action name | "Remove Status column" |
| **Description** | 1-2 sentences: WHY this approach + evidence + trade-offs | "SYSTEM.md should only describe cross-BC topology. Status is already tracked in kanban. Eliminates duplication." |

**Option ordering rules:**
- **Recommended option FIRST**, with `"(Recommended)"` suffix in the label
- Remaining options in decreasing preference order
- Users always see "Other" for custom input (never include in options)

### 2.5 Example

```
Analysis: SYSTEM.md §4 tracks implementation status ("待实现"/"已实现") but this
duplicates DESIGN.md §5 + kanban. The Status column is not a system topology concern.
Evidence: SYSTEM.md L42-58 Status column vs DESIGN.md §5 Task Summary.

Question: "How should AD-D1 (SYSTEM.md Status column) be handled?"
Header: "arch-design"
Options:
  1. "Remove Status column (Recommended)" — SYSTEM.md should only describe
     cross-BC topology, not track implementation. Status is already in kanban.
  2. "Keep but simplify to existing/planned" — Retains a planning signal
     without implementation tracking, but still duplicates AGENTS.md.
  3. "Delete entire SYSTEM.md" — Each BC's ARCHITECTURE.md §6 already
     covers cross-BC contracts independently. Removes duplication entirely.
```

---

## 3. When to Apply (适用场景)

### 3.1 Mandatory (必须使用)

- **AD Confirmation** (arch-review §8.5): Each AD presented to user for decision
- **Architecture decisions** (arch-design): Boundary choices, technology selection
- **BRD grilling** (arch-align): Business requirement clarification
- **Scope decisions**: When multiple valid approaches exist with significant trade-offs

### 3.2 Optional (可以使用)

- **Fix execution** (arch-review Fix Guidance Mode): "Execute now / Show diff / Defer"
- **Simple confirmations**: When the recommended path is clear and alternatives are weak

### 3.3 Do NOT Use (不适用)

- **Trivial edits**: Spelling, formatting — just do it
- **Single obvious path**: No real choice to make
- **Batch operations**: When all items follow the same pattern

---

## 4. Quality Checklist (质量检查)

Before calling AskUserQuestion, verify:

- [ ] Analysis context written BEFORE the question (not inside options)
- [ ] Evidence cited (code paths, doc sections, line numbers)
- [ ] Question is specific and ends with `?`
- [ ] Header ≤ 12 characters
- [ ] 2-4 options (not 1, not 5+)
- [ ] Each option has Label (1-5 words) + Description (WHY + evidence)
- [ ] Recommended option is FIRST with "(Recommended)" label
- [ ] Only ONE question (not batched)

---

## 5. Anti-Patterns (反面模式)

| Anti-Pattern | Problem | Fix |
|-------------|---------|-----|
| "Which do you prefer? A or B?" | No analysis, no evidence | Add context + WHY for each option |
| 5+ options | Cognitive overload | Group related options, max 4 |
| Options without evidence | User can't evaluate trade-offs | Add "WHY" to each description |
| Recommended not marked | User doesn't know expert opinion | Mark first option "(Recommended)" |
| Batched questions | Overwhelming, breaks progressive disclosure | One question per AskUserQuestion call |
| Analysis inside options | User reads options before understanding context | Write analysis as separate paragraph before question |

---

## 6. Integration with arch-review AD Confirmation (与 arch-review 的集成)

arch-review §8.5 AD Confirmation Protocol uses this spec as its questioning standard. The AD-specific additions:

- **Route as Header**: Use the AD's Route tag as the header (e.g., `"arch-design"`)
- **AD ID in Question**: Include the AD identifier (e.g., "AD-D1")
- **Post-confirmation**: Record decision in AD description, write to T{N}.md
- **Skip condition**: Only if user says "skip confirmation" or "batch approve all"

---

## 7. Version History

| Version | Date | Change |
|---------|------|--------|
| 1.0.0 | 2026-07-18 | Extracted from arch-review §8.5, generalized for cross-skill use |
