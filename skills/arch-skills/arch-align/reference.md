# `arch-align` — Reference

Progressive-disclosure companion to `SKILL.md`. Load only when actively running `/arch-align`.

---

## 1. `LANGUAGE.md` Template Skeleton

```markdown
# LANGUAGE.md — Ubiquitous Language Dictionary

> Bounded Context: `<context-name>`
> Last updated: `<YYYY-MM-DD>`
> PoEAA Pattern: `<Domain Model | Transaction Script | Table Module>`

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

## 2. `CONTEXT.md` Template Skeleton

```markdown
# CONTEXT.md — Bounded Context & Pattern Decision

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

## 3. PoEAA Pattern Decision

**Pick:** `Domain Model | Transaction Script | Table Module`

**Justification (one paragraph):**
> Why this pick and not the others, grounded in observed business complexity.
> Mention: number of invariants, depth of aggregates, frequency of behavior on entities,
> presence of long-running workflows.

## 4. Tracer Bullet Goal

The thinnest end-to-end vertical slice that proves the architecture works:

> `<one sentence: actor → action → observable outcome>`

Example: "An operator registers a new agent via CLI and sees it appear in `census list`."

## 5. Open Questions (must be empty before /arch-design)

- [ ] ...
- [ ] ...
```

---

## 3. PoEAA Pattern Decision Matrix

Use this matrix to drive Step 2 ("PoEAA Pattern Probing"). The pick is whichever row has the most "yes".

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

## 4. Grilling Question Library

Pick one question per turn. Never batch.

### A. Synonym Resolution
- "你刚才用了 `record` 和 `imprint`，这是同一个东西吗？如果是，我们保留哪一个，废弃哪一个？"
- "`agent` 和 `worker` 在你的语境里有区别吗？给我一个能区分它们的具体例子。"

### B. Hidden Invariant Discovery
- "一个 agent 在什么情况下不能被注册？列出所有失败原因。"
- "如果两个 agent 同时尝试 X，预期行为是什么？谁赢、谁输、还是都失败？"
- "状态从 A 到 B 之外，还有哪些合法转移？哪些是非法的？"

### C. Domain vs Infrastructure Separation
- "`Postgres census` 是真的业务概念，还是只是当前实现选择？如果换成 SQLite，业务方还会这么叫它吗？"
- "JSON 这个词出现在你的描述里——是协议细节还是业务约束？"

### D. PoEAA Anchor
- "给我一条非平凡的、必须由 `Agent` 自己保证的不变量。如果给不出，我们就不该用 Domain Model。"
- "这个用例除了'读一行、改一个字段、写回去'，还有别的吗？"

### E. Tracer Bullet Sharpening
- "如果只能交付一条端到端的路径来证明架构成立，是哪一条？给我一句话：谁、做什么、看到什么。"
- "Tracer Bullet 完成后，可观察的输出是什么？CLI 输出？数据库行？日志？"

### F. Out-of-Scope Pinning
- "你提到了 X，但我看你说不打算实现——那它进 Out of Scope 还是进 Open Questions？"

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

## 6. Pre-Output Self-Audit (run before each `LANGUAGE.md` / `CONTEXT.md` save)

Mentally run through these checks. If any fails, do not save — ask another grilling question.

1. **Domain section is technology-neutral.** No `JSON`, `HTTP`, `Postgres`, `class`, `table`, `gRPC`, `Kafka`, `Redis`, `repository_impl`.
2. **No synonyms inside Domain.** Each concept has exactly one canonical term.
3. **All Application verbs are imperative active.** `RegisterAgent`, not `AgentRegistration` or `register_agent_handler`.
4. **Infrastructure suffix is consistent.** Every Infrastructure term ends in `Adapter | Producer | Consumer | Census | Store | Gateway`.
5. **PoEAA pick has a written justification.** Not just the name.
6. **Tracer Bullet has actor + action + observable outcome.** Three components, all present.
7. **Open Questions section is honestly populated.** Empty only when truly empty; never empty as a shortcut.
8. **Banned Terms list is not empty** (if any synonym was discussed). Drift candidates must be recorded.

---

## 7. Clarification Protocol

When the user pushes back on a constraint, follow this exact sequence:

1. **Restate the constraint.** "Hard constraint #N says: ..."
2. **Restate their intent.** "I understand you want to ..."
3. **Show the conflict.** "These conflict because ..."
4. **Offer two paths:**
   - (a) revise their intent to fit the constraint, or
   - (b) explicit `OVERRIDE: <reason>` from them, which you record verbatim in `CONTEXT.md` § Open Questions before proceeding.
5. **Wait.** Do not proceed until they pick (a) or (b).

Never silently bend a hard constraint. Never proceed on assumption.
