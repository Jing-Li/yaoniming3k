# `arch-align` — Reference

Progressive-disclosure companion to `SKILL.md`. Load only when actively running `/arch-align`.

---

## 1. `LANGUAGE.md` Template Skeleton

```markdown
# LANGUAGE.md — Ubiquitous Language Dictionary

> Bounded Context: `<context-name>`
> Last updated: `<YYYY-MM-DD>`

## Domain (technology-free)

| 中文术语 | English term | 定义（一句话） | 同义词 / 禁用词 |
|---------|--------------|---------------|-----------------|
| 智能体 | Agent | 系统中可独立思考与行动的最小单元 | 同义：worker、bot；禁用：service |
| 印记 | Imprint | 智能体留下的不可变记忆痕迹 | 禁用：log、record |
| ... | ... | ... | ... |

## Application (use cases, orchestration verbs)

| 中文术语 | English term | 定义 | 触发者 |
|---------|--------------|------|--------|
| 注册智能体 | RegisterAgent | 将一个新智能体登记进总册 | CLI / API |
| ... | ... | ... | ... |

## Infrastructure (adapters / external systems — kept separate)

| 中文术语 | English term | 定义 | 所属适配器 |
|---------|--------------|------|-----------|
| Postgres 总册 | Postgres Census | 智能体登记的关系型存储实现 | PostgresCensusAdapter |
| ... | ... | ... | ... |

## Banned / Retired Terms

| 弃用词 | 原因 | 替代词 |
|-------|------|--------|
| service | 与 DDD 应用服务混淆 | use case 或具体动词 |
| ... | ... | ... |
```

**Rules:**
- Every Domain term MUST be technology-neutral (no `JSON`, `HTTP`, `class`, `table`, `JSON-RPC`).
- Synonyms collapse into one canonical term; the rest go to "Banned / Retired".
- Application verbs must be active imperative form (`RegisterAgent`, not `AgentRegistration`).
- Infrastructure terms always carry a suffix that signals adapter status (`Adapter`, `Producer`, `Census`, `Store`).

---

## 2. `BRD.md` Template Skeleton

```markdown
# BRD.md — Business Requirements Document (BRD)

## 1. Bounded Context

**Name:** `<short-noun-phrase>`

**One-line description:** `<what this context is responsible for>`

## 2. Scope

**In scope:**
- ...
- ...

**Out of scope (explicitly excluded):**
- ...
- ...

## 3. Open Questions (must be empty before /arch-design)

- [ ] ...
- [ ] ...

## 4. Business Overview

> Overwritten every round — always reflects the latest complete picture.

### Core Business Flow
<End-to-end narrative: starting event → key actions → terminal state>

### Key Participants
| Role | Type | Responsibility |
|------|------|---------------|
| ... | Human / System / External | ... |

### State Machine
| Entity | State A → State B | Trigger |
|--------|-------------------|--------|
| ... | ... | User action / System event / Timer |

### Key Business Rules
1. <rule> (applies to: <context>)
2. <rule> (applies to: <context>)

## 5. Change History (in T{N}.md)

> No longer in BRD.md. Change history is tracked per-task in `kanban/tasks/T{N}.md`.
> See [kanban-spec.md](../kanban-spec.md) §3 for T{N}.md format.
```

---

## 3. Grilling Question Library (3-Phase)

Structured by Grilling phase. Pick one question per turn. Never batch.

### Phase A — Discovery (open-ended)

Focus: BC scope + candidate term extraction.

- "描述一下这个系统的核心业务流程，从头到尾走一遍。"
- "哪些操作是这个 BC 管的，哪些不是？给我一个明确的边界。"
- "你提到了 X，但我看不算实现——那它进 Out of Scope 还是进 Open Questions？"

### Phase B — Terminology (structured options preferred)

Focus: synonym resolution, layer assignment, banned words.

- [结构化选项] "`record` vs `imprint` —— 这是同一个东西吗？保留哪一个？" → 单选：`[record]` `[imprint]` `[都不同，各保留]` `[都不是]`
- [结构化选项] "`agent` 和 `worker` 在你的语境里有区别吗？" → 单选：`[同一个概念]` `[有区别，我来说]`
- [结构化选项] "`PostgresCensus` 归入 Infrastructure 层，确认？" → 单选：`[确认]` `[不，它是业务概念]`

### Phase C — Invariants (open-ended)

Focus: hidden business rules, edge cases, boundary conditions.

- "一个 agent 在什么情况下不能被注册？列出所有失败原因。"
- "如果两个 agent 同时尝试 X，预期行为是什么？谁赢、谁输、还是都失败？"
- "状态从 A 到 B 之外，还有哪些合法转移？哪些是非法的？"

---

## 5. Ambiguity Detection Patterns

Trigger a grilling question whenever the user input contains any of:

| Pattern | Why it's ambiguous | Example response |
|---------|--------------------|------------------|
| Two words for one concept | Synonym drift | "`record` vs `imprint` —— 同义吗？" |
| Tech term inside business sentence | Layer pollution | "`JSON` 是业务的还是协议的？" |
| "等" / "之类" / "etc." | Hidden requirements | "请把'等'里剩下的两个补全。" |
| Adjectives without measurement | Vague invariant | "'快速' 是 < 100ms 还是 < 1s？" |
| Passive voice, no actor | Missing trigger | "这个动作是谁触发的？" |
| "可能 / 也许 / 大概" | Soft commitment | "确定还是不确定？不确定就进 Open Questions。" |
| Plural without cardinality | Missing constraint | "多个是 2 个还是 N 个？上限多少？" |

---

## 6. Pre-Output Self-Audit (run before each `LANGUAGE.md` / `BRD.md` save)

Mentally run through these checks. If any fails, do not save — ask another grilling question.

1. **Domain section is technology-neutral.** No `JSON`, `HTTP`, `Postgres`, `class`, `table`, `gRPC`, `Kafka`, `Redis`, `repository_impl`.
2. **No synonyms inside Domain.** Each concept has exactly one canonical term.
3. **All Application verbs are imperative active.** `RegisterAgent`, not `AgentRegistration` or `register_agent_handler`.
4. **Infrastructure suffix is consistent.** Every Infrastructure term ends in `Adapter | Producer | Consumer | Census | Store | Gateway`.
5. **Open Questions section is honestly populated.** Empty only when truly empty; never empty as a shortcut.
6. **Banned Terms list is not empty** (if any synonym was discussed). Drift candidates must be recorded.
7. **Business Overview (§4) is current.** If any term, rule, or scope changed this round, §4 must be rewritten before hand-off.
8. **T{N}.md Change History has this round's entry.** All changes from this round are recorded with impact classification.
9. **Impact Assessment is complete.** Every Change History entry has a corresponding impact classification (⚠️ Breaking or ➕ Additive).

---

## 8. Impact Assessment Guide

When comparing this round's changes against downstream artifacts, use this decision matrix:

| Change Type | Downstream Artifact | Classification | Action Required |
|------------|-------------------|---------------|----------------|
| Term renamed/retired | ARCHITECTURE.md, DESIGN.md, module docs | ⚠️ Breaking | Downstream must update all references |
| Invariant modified/removed | DESIGN.md § business rules | ⚠️ Breaking | Downstream must re-validate design |
| Scope item removed | All downstream artifacts | ⚠️ Breaking | Downstream must remove related content |
| New term added | DESIGN.md, modules | ➕ Additive | Downstream may add related modules |
| New invariant added | DESIGN.md, modules | ➕ Additive | Downstream may add validation logic |
| Scope item added | ARCHITECTURE.md | ➕ Additive | Downstream may extend boundary design |

**Scan targets for Impact Assessment:**
1. `docs/bc/<slug>/design/ARCHITECTURE.md` — check for references to modified/retired terms
2. `docs/bc/<slug>/detail/DESIGN.md` — check for references to modified terms or rules
3. `docs/bc/<slug>/detail/modules/*/module.md` — check for modules using modified terms
4. Source code (if Phase 4 exists) — check for code referencing retired terms

**First round:** No prior T{N}.md Change History exists → skip Impact Assessment, set Change History to "Initial alignment."

---

## 7. Clarification Protocol

When the user pushes back on a constraint, follow this exact sequence:

1. **Restate the constraint.** "Hard constraint #N says: ..."
2. **Restate their intent.** "I understand you want to ..."
3. **Show the conflict.** "These conflict because ..."
4. **Offer two paths:**
   - (a) revise their intent to fit the constraint, or
   - (b) explicit `OVERRIDE: <reason>` from them, which you record verbatim in `BRD.md` § Open Questions before proceeding.
5. **Wait.** Do not proceed until they pick (a) or (b).

Never silently bend a hard constraint. Never proceed on assumption.
