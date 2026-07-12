## Agent skills

### Issue tracker

Issues are tracked as local Markdown files in `docs/agents/issues/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Standard five-role vocabulary (needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout (CONTEXT.md + docs/adr/ at repo root). See `docs/agents/domain.md`.

### Arch Skills Pipeline

基于 Clean Architecture + DDD 的端到端架构设计技能管线，已安装至 `.qoder/skills/`。

```
Phase 0        Phase 1        Phase 2          Phase 3          Phase 4
/arch-init  →  /arch-align  →  /arch-design  →  /arch-detail  →  /arch-review
  (脚手架)       (术语对齐)       (边界设计)        (详细设计)        (架构审计)
                                                      ↓
                                                  /devtdd
                                               (垂直切片TDD实现)
```

| Skill | 触发 | 描述 |
|-------|------|------|
| arch-init | `/arch-init` | 项目脚手架与文档治理，幂等可重跑 |
| arch-align | `/arch-align` | 概念与术语对齐，产出 LANGUAGE.md + CONTEXT.md |
| arch-design | `/arch-design` | 边界设计与 Mermaid 依赖图，产出 ARCHITECTURE.md |
| arch-detail | `/arch-detail` | 详细设计 + 模块设计文件 + 接口契约 |
| arch-review | `/arch-review` | 架构审计与代码守卫，产出 REVIEW.md |
| devtdd | `/devtdd` | 垂直切片 TDD 实现引擎 |

### 运维 Skills

| Skill | 触发 | 描述 |
|-------|------|------|
| caisen-ops | `/caisen-ops` | 启动、诊断、监控 caisen 量化回测服务 |

## 策略体系

项目支持两大策略范式，三种优化路径：

| 方案 | 命名 | 策略 | CLI 命令 | 状态 |
|------|------|------|---------|------|
| A | 网格暴力参数法 | CaiSenStrategy | `caisen optimize` | 已实现 |
| B | 网格智能蔡森参数法 | CaiSenStrategy | `caisen llm-optimize` | 规划中（ADR-0020） |
| C | 智能蔡森策略 | LLMStrategy | `caisen evolve-prompt` | 已实现 |

- **CaiSenStrategy**（Code Strategy）：蔡森十二形态检测器 + 加权投票 + 分阶段仓位管理
- **LLMStrategy**（智能蔡森策略）：LLM 递增窗口预计算 + 信号回放，不依赖形态检测器

## ADR 决策索引

| ADR | 标题 | Status |
|-----|------|--------|
| 0001 | 数据源独立为 caisen-data | Superseded |
| 0002 | Parquet 数据存储 | Accepted |
| 0003 | Strategy ABC 接口 | Accepted |
| 0004 | LLM 策略架构（智能蔡森策略） | Accepted |
| 0005 | 可视化标注与报告 | Implemented |
| 0006 | 对比模式（代码/LLM 双实现） | Partially Implemented |
| 0007 | Data Module 实现 | Accepted |
| 0008 | 架构深化改进 | Implemented |
| 0009 | 目录结构标准 | Accepted |
| 0010 | 前端模块化重构 | Implemented |
| 0011 | CaiSenStrategy 组件拆分 | Implemented |
| 0012 | Metrics 计算统一 | Implemented |
| 0013 | Annotation 提升到 core | Implemented |
| 0014 | LLM Provider 简化 | Accepted |
| 0015 | LLMStrategy 依赖注入 | Accepted |
| 0016 | PlatformUtils 共享工具 | Implemented |
| 0017 | 四因子置信度模型 | Implemented |
| 0018 | 多周期共振框架 | Proposed（未实现） |
| 0019 | 自适应参数优化引擎 | Superseded by ADR-0020 |
| 0020 | 网格智能蔡森参数法 | Accepted（规划中） |

## 策略中心前端

策略中心（`strategy.html`）是策略浏览与优化的专用页面，三大区域：

| 区域 | JS 模块 | 职责 |
|------|---------|------|
| 左侧栏 — 策略浏览器 | `strategy-explorer.js` | 策略卡片列表、params_schema 展示（CaiSen 显示真实搜索范围，LLM 显示 prompt 模板） |
| 右侧上 — 网格搜索面板 | `optimize-panel.js` | CaiSen 专属：从 `optimize_config.params` 读取真实 GridSearchConfig 值，渲染参数 chips + 形态预设卡片 |
| 右侧下 — 进化面板 | `evolve-panel.js` | LLM 专属：Prompt 进化参数（max_generations、交易规则模板） |

**面板自动切换**：`strategy-page.js` 的 `switchPanel(strategyType)` 根据策略类型自动显示对应面板。侧栏点击、下拉框切换均走 `onStrategySelectChange()` 统一入口。

**params_schema 增强机制**：`registry.py` 中 `_enrich_schema_with_ranges()` 将 `optimize_config` 的真实搜索范围注入 CaiSen 的 `params_schema.options` 字段；LLM 策略由 `_build_llm_schema()` 生成含 prompt 模板（`type="text"`）的专用 schema。

**端口约定**：前端 Vite `:8000`，后端 FastAPI `:8001`，Vite 自动代理 `/api` 和 `/ws` 到 8001。项目使用 **uv**（非 pip）安装。

## 工作流程

架构设计工作流由 arch-skills 管线驱动（Phase 0→4 + devtdd）。日常编码后的架构合规性由 `/arch-review` 审计保障。

## 文档入口

| 文档 | 路径 | 用途 |
|------|------|------|
| BC 定义 | `docs/bc/<slug>/` | 每个 BC 的领域知识（LANGUAGE / CONTEXT / ARCHITECTURE / DESIGN） |
| 管线状态 | `docs/arch/PHASES.md` | 所有 BC 的架构管线进度与 BC Selection Protocol |
| Agent 领域配置 | `docs/agents/domain.md` | 文件结构图、术语规范、架构不变量 |

## Bounded Contexts

| BC | Slug | 阶段进度 |
|----|------|---------|

_(由 `/arch-align` 和 `/arch-init` Mode B 填充)_

## 架构管线 Skills

4 阶段管线，每阶段一个 skill：

| Phase | Skill | 产出 |
|-------|-------|------|
| 0 — 管线初始化 | `/arch-init` | `docs/` 目录结构 + `PHASES.md` + `domain.md` + `AGENTS.md` |
| 1 — 概念对齐 | `/arch-align` | `LANGUAGE.md` + `CONTEXT.md` |
| 2 — 边界设计 | `/arch-design` | `ARCHITECTURE.md` |
| 3 — 详细设计 | `/arch-detail` | `DESIGN.md` + `design/modules/` |
| 4 — 架构审计 | `/arch-review` | 审计报告 (stdout) |

新项目先跑 `/arch-init` 搭建骨架，再 `/arch-align` 创建第一个 BC。已有项目中 `/arch-init` 可注册新 BC 或治理文档漂移。

## 仓库结构

```
caisen/
├── AGENTS.md                 # 本文件
├── CONTEXT.md                # 领域术语表（待 /arch-align 迁移至 docs/bc/<slug>/）
├── docs/
│   ├── arch/
│   │   └── PHASES.md         # 管线状态
│   ├── bc/                   # BC 目录（由 /arch-align 创建）
│   ├── adr/                  # 架构决策记录（0001-0020）
│   ├── issues/               # 问题追踪
│   └── agents/
│       ├── domain.md         # Agent 领域配置
│       ├── issue-tracker.md
│       └── triage-labels.md
├── src/caisen/               # Python 源码
├── configs/                  # YAML 配置
├── tests/                    # 测试
├── scripts/                  # 脚本
├── examples/                 # 示例
└── runs/                     # 回测结果
```
