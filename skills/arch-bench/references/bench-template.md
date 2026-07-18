# bench.yaml Template Definition

`/arch-bench init` 按此模板逐节追问用户，生成完整 bench.yaml。

---

## 输出目录结构

bench.yaml 生成后，所有产物位于 `bench-{name}/` 目录（`{name}` 取自 §2 `case.name`）：

```
bench-{name}/
├── bench.yaml                    ← 本文件（IMMUTABLE after confirm）
├── EVOLUTION.md                  ← 跨轮次进化日志
├── reports/
│   └── cycle-{N}.md              ← 每轮评估报告
└── v{N}/                         ← Cycle N 管线产出（隔离目录）
    ├── AGENTS.md
    ├── docs/bc/{slug}/
    │   ├── kanban/
    │   ├── align/
    │   ├── design/
    │   ├── detail/
    │   └── review/
    ├── src/
    ├── tests/
    └── (config files)
```

---

## §1 Benchmark Meta

harness 元信息，自动填充，无需追问。

```yaml
benchmark:
  name: "arch-skills evaluation harness"
  version: "1.0.0"
  purpose: "skill pipeline version comparison through controlled case execution"
```

**追问**：无。直接填充。

---

## §2 Case Definition

靶场基本信息，所有 skill 的入口认知。

```yaml
case:
  name: ""            # 靶场名称（唯一标识，如 snake/chess/tetris）
  description: ""     # 一句话描述
  domain: ""          # 领域（如 game/ecommerce/healthcare）
  bc_slug: ""         # 生成的 BC slug（通常为 domain 值）
```

**追问**：
1. 这个 benchmark 的主题是什么？（一句话描述你要构建的东西）
2. 它属于什么领域？

---

## §3 Domain Requirements

领域需求，供 arch-align Grilling 阶段消费。

```yaml
domain:
  rules: {}           # 结构化业务规则（因 case 而异）
  glossary:           # 业务术语预定义
    - term: ""
      definition: ""
  invariants:         # 业务不变量
    - ""
  scope:
    in: []            # 明确做什么
    out: []           # 明确不做什么
  open_questions:     # 预置答案
    - question: ""
      answer: ""
```

**追问流程**（分 4 轮）：

**轮 1 — 规则**：描述这个系统的核心业务规则。（追问直到规则完整）

**轮 2 — 术语**：列出关键业务术语及其精确定义。

**轮 3 — 不变量 + 范围**：
- 有哪些绝对不能违反的业务规则？（不变量）
- 明确哪些在范围内、哪些不在？

**轮 4 — 预置答案**：如果 align 问以下类型的问题，你希望怎么回答？
- 模糊需求的澄清
- 边界 case 的处理方式
- 优先级冲突的取舍

---

## §4 Non-Functional Requirements

非功能需求，供 arch-design NFR 对话消费。

```yaml
nfr:
  performance: []     # 性能要求
  scalability: []     # 扩展性
  security: []        # 安全要求
  testability: []     # 可测试性
  maintainability: [] # 可维护性
```

**追问**：
1. 对性能有什么要求？（响应时间、吞吐量等）
2. 需要考虑扩展性吗？（并发、分布式等）
3. 有安全要求吗？
4. 对代码可测试性有什么期望？（如"domain 层必须 100% 可单测"）
5. 对可维护性有什么偏好？（如"严格分层"、"小函数优先"）

---

## §5 Technology Preferences

技术选型偏好，供 arch-design 技术决策消费。

```yaml
tech_stack:
  language: ""
  database: ""
  ui: ""
  test_framework: ""
  constraints: []     # 技术约束（如"不用 ORM"、"不用第三方引擎"）
```

**追问**：
1. 用什么编程语言？
2. 数据库选型？
3. UI 形态？（终端/Web/API/移动端）
4. 测试框架偏好？
5. 有什么技术约束或禁忌？（如"不用 ORM"、"不用 CGO"）

---

## §6 Design Decisions

预置架构决策，供 arch-design ADR 拍板时消费。

```yaml
design_decisions:
  - question: ""      # 决策问题
    answer: ""        # 预置答案
    reason: ""        # 理由
```

**追问**：列出你期望的关键架构决策。（格式：问题 + 你希望的答案 + 理由）

例如：
- "状态管理用 FSM 还是行为树？" → "FSM，因为简单可测试"
- "渲染和逻辑分离还是耦合？" → "分离，便于独立测试"

---

## §7 Mutation Tests

变异测试陷阱，验证 arch-review 的检测能力（含内置批判推理模式）。

```yaml
mutation_tests:
  - id: ""            # M1, M2, ...
    trap: ""          # 陷阱描述（自然语言）
    violates: ""      # 违反了什么原则
    expected_detector: ""  # 期望被谁检测出
```

**追问**：你希望故意埋哪些架构陷阱来测试检测能力？（每个陷阱需要：描述 + 违反的原则 + 期望被谁检测）

**提示**：好的变异陷阱应该：
- 看起来"合理"但其实违反架构原则
- 分别针对不同的 skill 检测能力（review 的检测 vs critic 的检测 vs devtdd 的检测）
- 覆盖不同的违规类型（依赖方向、关注点分离、确定性、可测试性）

---

## §8 Evolution Parameters

进化参数，供 bench-run 判定收敛和停滞。

```yaml
evolution:
  max_cycles: 10                         # 最大轮次
  convergence_score: 90                   # Combined Score 目标
  convergence_consecutive_cycles: 2       # 连续 N 轮达标才算收敛
  stagnation_threshold: 3                 # 连续 N 轮无提升判定停滞
  auto_critic_threshold: 60               # 低于此分自动触发 /arch-review 深度批判模式
```

**追问**：
1. 最多跑多少轮？（默认 10）
2. 目标分数多少？（默认 90）
3. 连续几轮达标算收敛？（默认 2）
4. 连续几轮无提升算停滞？（默认 3）

如用户不回答，使用默认值。
