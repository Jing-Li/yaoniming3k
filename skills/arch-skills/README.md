# Arch Skills — Clean Architecture Pipeline

一套完整的 AI Agent 架构设计技能体系，驱动从需求对齐到代码实现的端到端流水线。

基于 **Clean Architecture**、**DDD (Domain-Driven Design)**、**PoEAA** 等经典方法论，将架构设计分解为可执行的阶段性技能。

## 流水线概览

```
        ┌───────────────────────────────────────────────────────────┐
        │  /arch-conventions (共享协议: kanban-spec + question-spec) │
        │  /arch-kanban      (看板执行者, 引用 conventions)          │
        └──────────────────────────┬────────────────────────────────┘
                                   │ 引用
        ┌───────────────────────────────────────────────────────────┐
Phase 0 │   Phase 1        Phase 2          Phase 3          Phase 4a         Phase 4b │
/arch-init → /arch-align → /arch-design → /arch-detail → /devtdd      → /arch-ops
 (脚手架)    (术语对齐)    (边界设计)      (详细设计)    (TDD实现)      (运维文档)
                                                              ↓
                                                         /arch-review
                                                        (架构审计)
```

## Skills 清单

| Skill | Phase | 描述 |
|-------|-------|------|
| **arch-init** | Phase 0 | 项目脚手架与文档治理。初始化 arch pipeline 文档结构，注册 Bounded Context，或审计/修复混乱的文档回归规范形式。幂等安全可重跑。 |
| **arch-conventions** | 基础设施 | 共享协议总持有者。统一管理 `kanban-spec.md`（任务生命周期协议）和 `ask-user-question-spec.md`（结构化提问协议），所有 arch-skills 从此处引用协议。 |
| **arch-kanban** | 基础设施 | 看板协议执行者与生命周期管理。引用 conventions 中的 kanban-spec，初始化 BOARD.md，校验看板一致性（单位置、归档、孤儿检测）。 |
| **arch-align** | Phase 1 | 概念与术语对齐。在任何设计工作之前，通过质询式对话对齐业务概念、统一语言 (DDD Ubiquitous Language) 和企业架构模式。产出 `LANGUAGE.md` + `BRD.md`。 |
| **arch-design** | Phase 2 | 边界设计与可视化。基于 Phase 1 产出，定义 Clean Architecture 分层、绘制 Mermaid 依赖图、产出 `ARCHITECTURE.md`，并管理 Architecture Decision Records (ADR)。 |
| **arch-detail** | Phase 3 | 详细设计与多语言实现映射。将 `ARCHITECTURE.md` 的边界翻译为模块化 `DESIGN.md` 索引 + 每模块设计文件 + 每方法接口契约，支撑垂直切片 TDD。 |
| **devtdd** | Phase 4a | 垂直切片 TDD 实现引擎。消费 Phase 3 产出（任务列表、模块设计、接口契约验收场景），驱动逐任务 red-green-refactor，同时强制架构边界。 |
| **arch-ops** | Phase 4b | 运维文档与工具。基于 DESIGN.md §8 和实现代码，生成 OPS.md runbook（前置依赖、构建、配置、启停、排障）、shell 脚本和 Makefile。 |
| **arch-review** | Phase 4c | 架构审计与代码守卫。审查代码是否符合架构蓝图，产出 `T{N}.md` 包含架构债务追踪、跨阶段路由和根因内省。检测架构漂移、抽象泄漏、框架污染等。内置 5 种批判推理模式（原 arch-critic）。 |

## 使用方式

### 快速开始

```bash
# 安装（以 skills CLI 为例）
npx skills@latest add <your-repo>/skills/arch-skills
```

### 典型工作流

1. **`/arch-init`** — 初始化项目文档结构
2. **`/arch-align`** — 与 AI 对齐业务领域术语和架构模式
3. **`/arch-design`** — 产出分层架构和依赖图
4. **`/arch-detail`** — 产出可执行的模块设计和任务分解
5. **`/devtdd`** — 按垂直切片逐任务 TDD 实现
6. **`/arch-review`** — 定期审计代码架构合规性

### 触发词

每个 skill 可通过斜杠命令或自然语言触发：

- `/arch-init` | "init arch" | "scaffold docs" | "set up architecture pipeline"
- `/arch-conventions` | "show kanban spec" | "show question spec" | "shared conventions"
- `/arch-kanban` | "check board" | "validate kanban" | "show board status"
- `/arch-align` | "align terms" | "grill the requirements" | "build the dictionary"
- `/arch-design` | "design architecture" | "draw the boundaries" | "visualize dependencies"
- `/arch-detail` | "detail design" | "vertical slice tasks" | "translate to code"
- `/devtdd` | "implement task" | "tdd this task" | "implement next task"
- `/arch-ops` | "write ops doc" | "generate runbook" | "create scripts" | "write Makefile"
- `/arch-review` | "audit this code" | "check architecture compliance" | "is this leaky" | "challenge this design" | "pre-mortem" | "red team"

## 理论基础

- **Clean Architecture** (Robert C. Martin) — 洋葱圈分层、依赖反转
- **Domain-Driven Design** (Eric Evans) — 统一语言、限界上下文、聚合
- **Patterns of Enterprise Application Architecture** (Martin Fowler) — 企业模式分类
- **Design Patterns** (GoF) — 可复用设计模式
- **A Philosophy of Software Design** (John Ousterhout) — 深模块、复杂性管理
- **Critical Reasoning & Pre-Mortem Analysis** (Gary Klein) — 批判推理、前瞻性失败分析

## 文件结构

```
arch-skills/
├── README.md              ← 本文件
├── CHANGELOG.md           ← 版本变更日志
├── arch-conventions/      ← 共享协议总持有者
│   ├── SKILL.md
│   └── references/
│       ├── kanban-spec.md ← 看板协议规范 (source of truth)
│       ├── ask-user-question-spec.md ← 结构化提问协议
│       └── shared-constraints.md ← 跨 skill 硬约束
├── arch-init/
│   ├── SKILL.md
│   └── reference.md
├── arch-kanban/
│   ├── SKILL.md
│   └── reference.md
├── arch-align/
│   ├── SKILL.md
│   ├── reference.md
│   └── references/        ← EARS 格式、Spec Mining 技术
├── arch-design/
│   ├── SKILL.md
│   ├── reference.md
│   └── references/        ← ADR 指南、PoEAA、NFR、架构模式、数据库选型、examples
├── arch-detail/
│   ├── SKILL.md
│   ├── reference.md
│   └── references/        ← 语言规则、API 契约标准、安全检查点、examples
├── devtdd/
│   ├── SKILL.md
│   ├── reference.md
│   └── references/        ← 代码工艺铁律、测试反模式、examples
├── arch-ops/
│   ├── SKILL.md
│   ├── reference.md
│   └── references/        ← OPS.md 模板、脚本模板
└── arch-review/
    ├── SKILL.md
    ├── reference.md
    └── references/        ← 报告模板、修复引导、OWASP、批判推理、examples
```

## 兼容性

这些 skills 遵循通用的 Agent Skill 格式（SKILL.md frontmatter + markdown body），兼容：

- Qoder
- Claude Code
- Cursor
- Amp
- Codex
- 以及其他支持 skills 协议的 AI coding agent

## License

MIT
