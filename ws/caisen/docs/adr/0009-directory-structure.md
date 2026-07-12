# ADR-0009: 目录结构标准

## Status
Accepted

## Context

项目目录结构不统一，导致：
- 新模块放置位置混乱（有时放顶层，有时放子目录）
- 缺少明确的命名规范
- 开发时没有检查机制，随意创建

例如：
- `strategy/patterns/` 目录描述清晰
- `server/` 被删除后重建为 `web/`，未遵循原结构
- `frontend/` 结构完整，但 `web/` 只有一个 `main.py`

## Decision

### 1. 顶层目录结构

```
src/caisen/
├── core/              # 回测引擎核心
│   ├── engine.py      # BacktestEngine
│   ├── config.py      # BacktestConfig
│   ├── bar.py         # Bar 数据类型
│   ├── bar_result.py  # BarResult（策略输出）
│   ├── order.py       # Order 数据类型
│   ├── position.py    # Position 持仓
│   ├── portfolio.py   # Portfolio 组合
│   ├── trade.py       # Trade 成交
│   └── annotation.py  # Annotation + AnnotationType（14 种）
├── strategy/          # 策略实现
│   ├── base.py        # Strategy 基类
│   ├── registry.py    # StrategyRegistry 策略注册表
│   ├── algorithm/     # 蔡森策略（Code Strategy）
│   │   ├── cai_sen.py             # CaiSenStrategy 主策略
│   │   ├── detector.py            # PatternDetector + ConfidenceFactors
│   │   ├── caisen_config.py       # 策略配置加载
│   │   ├── caisen_optimizer.py    # 网格暴力参数法（Grid Search）
│   │   ├── patterns/              # 形态检测器（12 种）
│   │   └── caisen_components/     # 组件（Factory/Aggregator/PositionMgr/VolumeAnalyzer）
│   └── llm/           # LLM 策略（智能蔡森策略）
│       ├── strategy.py    # LLMStrategy 主策略（离线预计算+回放）
│       ├── prompt.py      # PromptBuilder
│       ├── provider.py    # OpenAIProvider
│       ├── client.py      # LLMClient 接口
│       ├── evolver.py     # PromptEvolver 进化器
│       ├── cache.py       # 信号缓存
│       ├── response.py    # ResponseParser
│       └── prompts/       # Prompt 模板
├── data/              # 数据加载模块
│   ├── source.py      # DataSource 接口
│   ├── local_source.py # LocalDataSource 实现
│   ├── scanner.py     # DataSourceScanner
│   ├── config.py      # DataConfig
│   ├── registry.py    # 数据源注册表
│   └── exceptions.py  # 数据异常
├── result/            # 回测结果处理
│   ├── types.py       # BacktestResult 数据类型
│   ├── metrics.py     # 绩效指标定义
│   ├── calculator.py  # MetricsCalculator
│   └── persistence.py # ResultPersister（Parquet + JSON）
├── backtest/          # 回测运行器
│   └── runner.py      # BacktestRunner（CLI 统一入口）
├── config/            # 项目配置
│   └── project_config.py  # ProjectConfig（加载 project.yaml）
├── frontend/          # 前端可视化（Vite 项目）
│   ├── index.html     # 入口
│   ├── report.html    # K线图详情页
│   ├── strategy.html  # 策略中心页
│   ├── src/js/        # 26 个 JS 模块
│   ├── src/css/       # CSS 样式
│   ├── tests/         # Vitest 单元测试
│   └── e2e/           # Playwright E2E 测试
├── web/               # Web API 服务
│   ├── main.py        # FastAPI 应用
│   └── optimizer.py   # 异步优化任务管理器
└── cli/               # 命令行工具
    └── main.py        # CLI 入口
```

### 2. 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 目录名 | `snake_case` | `strategy`, `data_source` |
| 文件名 | `snake_case.py` | `local_source.py` |
| 类名 | `PascalCase` | `LocalDataSource` |
| 函数/变量 | `snake_case` | `load_bars` |
| 常量 | `UPPER_SNAKE_CASE` | `MAX_DRAWDOWN` |
| 私有成员 | `_leading_underscore` | `_cache` |

### 3. 子模块结构规范

**Frontend Bundle（前端子目录）**：
```
frontend/
├── index.html         # 主页（runs 列表）
├── report.html        # 详情页（K线图）
├── package.json      # npm 依赖
├── vite.config.js    # Vite 配置
├── src/
│   ├── js/           # JS 模块
│   └── css/          # CSS 文件
├── tests/            # 单元测试
└── e2e/              # E2E 测试
```

**Pattern Detectors（形态检测器子目录）**：
```
patterns/
├── __init__.py       # 导出所有检测器
├── base.py           # 可选：检测器基类（如有公共逻辑）
├── w_bottom.py       # W底检测器
├── m_top.py          # M头检测器
├── head_shoulders.py # 头肩顶/底检测器
├── triangle.py       # 三角形态检测器
└── other.py          # 其他形态（旗形、矩形等）
```

### 4. 新模块创建检查清单

创建新模块时需确认：

1. **归属判断**：新模块属于哪个顶层目录？
   - 有 `on_bar` 方法 → `strategy/`
   - 处理回测结果 → `result/`
   - 加载行情数据 → `data/`
   - Web 服务 → `web/`
   - 前端代码 → `frontend/`
   - 回测运行/编排 → `backtest/`

2. **命名检查**：是否符合命名规范？

3. **初始化**：
   - Python 模块需 `__init__.py`
   - 需导出主要类型到 `__all__`

4. **测试**：
   - 是否有对应的测试文件？
   - 测试文件名：`test_{module_name}.py`

5. **文档**：
   - 是否需要更新 CONTEXT.md？
   - 是否需要创建 ADR？

### 5. 禁止的模式

- 禁止在 `src/caisen/` 根目录直接放置业务代码
- 禁止使用 `server/` 等非标准目录名
- 禁止单个文件模块（除非是顶层入口如 `__init__.py`）

### 6. CI 检查（TODO）

后续应添加：
- 目录结构 linting（检查顶层目录是否存在）
- 命名检查（正则匹配）
- 禁止模式检测

## Consequences

### Positive
- 目录结构可预期，新开发者可快速定位代码
- 命名统一，减少认知负担
- 检查清单降低犯错概率

### Negative
- 需要迁移现有代码到标准位置
- 需要持续维护检查清单

## References
- CONTEXT.md: 目录结构规范
- ADR-0007: 可视化报告架构
- ADR-0008: LLM 策略架构