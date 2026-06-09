# Arch Skills — Clean Architecture Pipeline

一套完整的 AI Agent 架构设计技能体系，驱动从需求对齐到代码实现的端到端流水线。

基于 **Clean Architecture**、**DDD (Domain-Driven Design)**、**PoEAA** 等经典方法论，将架构设计分解为可执行的阶段性技能。

## 流水线概览

```
Phase 0        Phase 1        Phase 2          Phase 3          Phase 4
/arch-init  →  /arch-align  →  /arch-design  →  /arch-detail  →  /arch-review
  (脚手架)       (术语对齐)       (边界设计)        (详细设计)        (架构审计)
                                                      ↓
                                                  /devtdd
                                               (垂直切片TDD实现)
```

## Skills 清单

| Skill | Phase | 描述 |
|-------|-------|------|
| **arch-init** | Phase 0 | 项目脚手架与文档治理。初始化 arch pipeline 文档结构，注册 Bounded Context，或审计/修复混乱的文档回归规范形式。幂等安全可重跑。 |
| **arch-align** | Phase 1 | 概念与术语对齐。在任何设计工作之前，通过质询式对话对齐业务概念、统一语言 (DDD Ubiquitous Language) 和企业架构模式。产出 `LANGUAGE.md` + `CONTEXT.md`。 |
| **arch-design** | Phase 2 | 边界设计与可视化。基于 Phase 1 产出，定义 Clean Architecture 分层、绘制 Mermaid 依赖图、产出 `ARCHITECTURE.md`。 |
| **arch-detail** | Phase 3 | 详细设计与多语言实现映射。将 `ARCHITECTURE.md` 的边界翻译为模块化 `DESIGN.md` 索引 + 每模块设计文件 + 每方法接口契约，支撑垂直切片 TDD。 |
| **arch-review** | Phase 4 | 架构审计与代码守卫。审查代码是否符合架构蓝图，产出 `REVIEW.md` 包含架构债务追踪、跨阶段路由和根因内省。检测架构漂移、抽象泄漏、框架污染等。 |
| **devtdd** | 实现 | 垂直切片 TDD 实现引擎。消费 Phase 3 产出（任务列表、模块设计、接口契约验收场景），驱动逐任务 red-green-refactor，同时强制架构边界。 |

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
- `/arch-align` | "align terms" | "grill the requirements" | "build the dictionary"
- `/arch-design` | "design architecture" | "draw the boundaries" | "visualize dependencies"
- `/arch-detail` | "detail design" | "vertical slice tasks" | "translate to code"
- `/arch-review` | "audit this code" | "check architecture compliance" | "is this leaky"
- `/devtdd` | "implement task" | "tdd this task" | "implement next task"

## 理论基础

- **Clean Architecture** (Robert C. Martin) — 洋葱圈分层、依赖反转
- **Domain-Driven Design** (Eric Evans) — 统一语言、限界上下文、聚合
- **Patterns of Enterprise Application Architecture** (Martin Fowler) — 企业模式分类
- **Design Patterns** (GoF) — 可复用设计模式
- **A Philosophy of Software Design** (John Ousterhout) — 深模块、复杂性管理

## 文件结构

```
arch-skills/
├── README.md              ← 本文件
├── arch-init/
│   ├── SKILL.md           ← 主技能定义
│   └── reference.md       ← 补充参考
├── arch-align/
│   ├── SKILL.md
│   └── reference.md
├── arch-design/
│   ├── SKILL.md
│   └── reference.md
├── arch-detail/
│   ├── SKILL.md
│   └── reference.md
├── arch-review/
│   ├── SKILL.md
│   └── reference.md
└── devtdd/
    ├── SKILL.md
    └── reference.md
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
