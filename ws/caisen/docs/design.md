# 系统设计文档

本文档描述 caisen 量化回测系统的类图设计和各模块职责。

## 1. UML 类图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                Core 模块                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐      │
│  │     Config      │     │      Bar        │     │     Order       │      │
│  ├─────────────────┤     ├─────────────────┤     ├─────────────────┤      │
│  │ initial_capital │     │ timestamp       │     │ symbol          │      │
│  │ commission_rate │     │ symbol          │     │ side: Side      │      │
│  │ slippage        │     │ freq            │     │ quantity        │      │
│  │ strategy        │     │ open/high/low   │     │ stop_loss       │      │
│  │ data            │     │ close/volume    │     │ target          │      │
│  ├─────────────────┤     └────────┬────────┘     └────────┬────────┘      │
│  │ +from_yaml()    │              │                      │               │
│  └─────────────────┘              │                      │               │
│                                    │                      │               │
│  ┌─────────────────┐     ┌────────┴────────┐     ┌────────┴────────┐      │
│  │   Portfolio     │     │     Trade       │     │   Position     │      │
│  ├─────────────────┤     ├─────────────────┤     ├─────────────────┤      │
│  │ initial_capital │     │ timestamp       │     │ symbol          │      │
│  │ cash            │     │ symbol          │     │ quantity        │      │
│  │ positions       │     │ side            │     │ avg_cost        │      │
│  ├─────────────────┤     │ quantity/price  │     ├─────────────────┤      │
│  │ +cost_value()   │     │ commission      │     │ +is_long()      │      │
│  │ +get_equity()   │     │ slippage       │     │ +is_short()     │      │
│  └────────┬────────┘     └─────────────────┘     └─────────────────┘      │
│           │                                                             │
│           │ 1..*                                                       │
│           ▼                                                             │
│  ┌─────────────────┐                                                   │
│  │  BacktestEngine │                                                   │
│  ├─────────────────┤                                                   │
│  │ portfolio       │◄─────────┐                                         │
│  │ config          │          │                                         │
│  ├─────────────────┤          │                                         │
│  │ +run()          │          │                                         │
│  │ +_execute_order()          │                                         │
│  │ +_update_position()        │                                         │
│  └────────┬────────┘          │                                         │
└───────────┼───────────────────┼─────────────────────────────────────────┘
            │                   │
            │ 使用               │ 返回
            ▼                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             Strategy 模块                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                    <<abstract>> Strategy                               ││
│  ├─────────────────────────────────────────────────────────────────────────┤│
│  │ +bars, position, entry_price, current_stop_loss                       ││
│  ├─────────────────────────────────────────────────────────────────────────┤│
│  │ +on_init(config)                                                       ││
│  │ +on_bar(bar) -> Optional[Order]                                       ││
│  │ +on_session_end()                                                     ││
│  │ +get_annotations() -> List[Annotation]                                ││
│  │ +reset()                                                               ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                    ▲                                        ▲               │
│                    │                                        │               │
│  ┌─────────────────┴────────┐          ┌────────────────┴───────────┐   │
│  │     CaiSenStrategy       │          │        LLMStrategy          │   │
│  ├──────────────────────────┤          ├────────────────────────────┤   │
│  │ detectors: List[Pattern] │          │ llm_client, cache           │   │
│  │ weights, threshold       │          │ _bars, position              │   │
│  ├──────────────────────────┤          ├────────────────────────────┤   │
│  │ +from_config()           │          │ +on_init() 预计算模式       │   │
│  │ +on_bar() 入场/止损/止盈  │          │ +on_bar() 查缓存返回        │   │
│  └──────────────────────────┘          └────────────────────────────┘   │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐   │
│  │               <<abstract>> PatternDetector                        │   │
│  ├───────────────────────────────────────────────────────────────────┤   │
│  │ name, tolerance, stop_loss_factor, min_profit_pct                 │   │
│  │ _bars, _first_xxx_bar, _second_xxx_bar, _neckline                  │   │
│  ├───────────────────────────────────────────────────────────────────┤   │
│  │ +update(bar)                                                      │   │
│  │ +detect() -> Optional[PatternSignal]                              │   │
│  │ +reset()                                                           │   │
│  │ #_find_xxx()                                                      │   │
│  │ #_create_signal()                                                 │   │
│  │ #_calculate_confidence()                                          │   │
│  └───────────────────────────────────────────────────────────────────┘   │
│                    ▲                                                      │
│     ┌──────────────┼──────────────┬──────────────┬──────────────┐        │
│     │              │              │              │              │        │
│  ┌──┴───┐      ┌──┴───┐     ┌───┴────┐     ┌───┴───┐     ┌───┴───┐  │
│  │W底   │      │M头   │     │头肩形  │     │三角   │     │其他   │  │
│  │Detec│      │Detec │     │Detec  │     │Detec  │     │Detec  │  │
│  └──┬───┘      └──┬───┘     └───┬────┘     └───┬───┘     └───┬───┘  │
│     │             │            │              │              │        │
│     └─────────────┴────────────┴──────────────┴──────────────┘        │
│                           implements                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                               Data 模块                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌────────────────────┐                                                  │
│  │  <<protocol>>      │           ┌─────────────────────┐                │
│  │     DataSource     │           │   LocalDataSource   │                │
│  ├────────────────────┤           ├─────────────────────┤                │
│  │ +load(config)      │           │ data_dir            │                │
│  │ +name              │           ├─────────────────────┤                │
│  └────────┬───────────┘           │ +load(config)       │                │
│           │                       │ +_get_files()       │                │
│           │ implements            │ +_df_to_bars()      │                │
│           ▼                       └─────────────────────┘                │
│  ┌────────────────────┐                                                  │
│  │      Registry      │                                                  │
│  ├────────────────────┤                                                  │
│  │ +register()        │                                                  │
│  │ +set_active()      │                                                  │
│  │ +load_datasource() │                                                  │
│  └────────────────────┘                                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                              Result 模块                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐      │
│  │ BacktestResult  │     │ PerformanceMetrics│    │  ResultPersister │      │
│  ├─────────────────┤     ├─────────────────┤     ├─────────────────┤      │
│  │ strategy_name   │     │ annual_return   │     │ +save()         │      │
│  │ bars            │     │ max_drawdown    │     │ +load()         │      │
│  │ trades          │     │ sharpe_ratio    │     │ +list_runs()    │      │
│  │ equity_curve    │     │ win_rate        │     │ +load_viz()     │      │
│  │ annotations     │     │ total_trades    │     └─────────────────┘      │
│  │ initial_capital │     │ profit_factor   │                              │
│  │ final_equity    │     └────────┬────────┘                              │
│  └─────────────────┘              │                                       │
│                                   │ 计算                                   │
│  ┌─────────────────┐     ┌────────┴────────┐                              │
│  │   Annotations    │     │ MetricsCalculator│                              │
│  ├─────────────────┤     ├─────────────────┤                              │
│  │ type: Annotation│     │ +calculate()    │                              │
│  │ timestamp        │     └─────────────────┘                              │
│  │ data             │                                                    │
│  ├─────────────────┤                                                      │
│  │ +buy_signal()   │                                                     │
│  │ +sell_signal()  │                                                     │
│  │ +horizontal_line│                                                     │
│  └─────────────────┘                                                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 2. 核心类职责声明

### 2.1 Core 模块

| 类名 | 文件 | 职责 |
|------|------|------|
| **BacktestEngine** | `core/engine.py` | 回测执行引擎。加载数据，逐根K线遍历，调用策略，处理订单，更新持仓，计算净值。 |
| **Config** | `core/config.py` | 回测配置容器。管理 initial_capital, commission_rate, slippage, strategy, data 等配置。从 YAML 加载。 |
| **Portfolio** | `core/portfolio.py` | 账户资金和持仓状态。管理现金、持仓、净值计算。提供 cost_value 和 get_equity_with_prices 方法。 |
| **Position** | `core/position.py` | 单标的持仓。记录数量和均价。提供 is_long, is_short 判断。 |
| **Order** | `core/order.py` | 交易指令。包含标的、方向、数量、止损价、目标价。由策略生成，引擎执行。 |
| **Trade** | `core/trade.py` | 成交记录。记录实际成交的时间、价格、手续费、滑点。 |
| **Bar** | `core/bar.py` | K线数据。包含时间戳、OHLCV。 |
| **Annotation** | `core/annotation.py` | 可视化标注。策略在K线图上绘制的辅助信息（买卖点、趋势线、形态标记）。 |

### 2.2 Strategy 模块

| 类名 | 文件 | 职责 |
|------|------|------|
| **Strategy** | `strategy/base.py` | 策略基类（抽象）。定义 on_init, on_bar, on_session_end, get_annotations, reset 接口。 |
| **CaiSenStrategy** | `strategy/algorithm/cai_sen.py` | 蔡森策略实现。基于 PatternDetector 架构，多检测器加权投票产生信号。负责入场/止损/止盈决策。 |
| **PatternDetector** | `strategy/algorithm/detector.py` | 形态检测器基类（抽象）。提供 update, detect, reset 接口。各形态继承实现具体检测逻辑。 |
| **PatternSignal** | `strategy/algorithm/detector.py` | 形态信号。包含 pattern, confidence, stop_loss, target, points。由检测器返回，策略使用。 |
| **WBottomDetector** | `algorithm/patterns/w_bottom.py` | W底检测器。检测双底形态，颈线突破时返回信号。 |
| **MTopDetector** | `algorithm/patterns/m_top.py` | M头检测器。检测双顶形态，颈线跌破时返回信号。 |
| **HeadAndShouldersBottomDetector** | `algorithm/patterns/head_shoulders.py` | 头肩底检测器。 |
| **HeadAndShouldersTopDetector** | `algorithm/patterns/head_shoulders.py` | 头肩顶检测器。 |
| **TriangleDetector** | `algorithm/patterns/triangle.py` | 三角形态检测器。检测收敛三角形突破。 |
| **FlagDetector** | `algorithm/patterns/other.py` | 旗形检测器。 |
| **RectangleDetector** | `algorithm/patterns/other.py` | 矩形检测器。 |
| **RoundingBottomDetector** | `algorithm/patterns/other.py` | 圆弧底检测器。 |
| **CupHandleDetector** | `algorithm/patterns/other.py` | 杯柄形态检测器。 |
| **BreakoutPullbackDetector** | `algorithm/patterns/other.py` | 破底翻检测器。 |
| **LLMStrategy** | `strategy/llm/strategy.py` | LLM策略实现。离线预计算模式，一次性分析历史数据，缓存后逐帧回放。 |
| **LLMClient** | `strategy/llm/client.py` | LLM客户端基类。定义 call_llm 接口。 |
| **OpenAIProvider** | `strategy/llm/provider.py` | OpenAI API 实现。 |
| **SignalCache** | `strategy/llm/cache.py` | LLM响应缓存。按策略名+版本+timestamp 标识。 |
| **PromptEvolver** | `strategy/llm/evolver.py` | Prompt 优化器。演化改进 Prompt。 |

### 2.3 Data 模块

| 类名 | 文件 | 职责 |
|------|------|------|
| **DataSource** | `data/source.py` | 数据源接口协议。定义 load(config) 方法。 |
| **LocalDataSource** | `data/local_source.py` | 本地数据源实现。从 Parquet 文件加载K线数据。 |
| **DataConfig** | `data/config.py` | 数据配置。包含 symbol, freq, start, end, data_dir。 |
| **Registry** | `data/registry.py` | 数据源注册表。管理已注册的数据源，支持动态发现。 |

### 2.4 Result 模块

| 类名 | 文件 | 职责 |
|------|------|------|
| **BacktestResult** | `result/types.py` | 回测结果。包含 bars, trades, equity_curve, annotations 等。 |
| **PerformanceMetrics** | `result/calculator.py` | 绩效指标。包含 annual_return, max_drawdown, sharpe_ratio, win_rate 等。 |
| **MetricsCalculator** | `result/calculator.py` | 指标计算器。从 BacktestResult 计算绩效指标。 |
| **ResultPersister** | `result/persistence.py` | 结果持久化。保存/加载回测结果到本地目录。 |

## 3. 模块依赖关系

```
                    ┌─────────────┐
                    │   Config    │
                    └──────┬──────┘
                           │ 配置
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │DataSource   │ │  Strategy   │ │BacktestEngine│
    └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
           │               │               │
           │ 加载数据       │ 决策          │ 执行
           ▼               ▼               ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │    Bar      │ │   Order     │ │  Portfolio  │
    └─────────────┘ └──────┬──────┘ │   Position │
                          │         │   Trade    │
                          │         └──────┬──────┘
                          │                │
                          ▼                ▼
                   ┌────────────────────────┐
                   │    BacktestResult     │
                   │  (bars, trades, equity │
                   │   annotations)        │
                   └────────────┬───────────┘
                                │
                                ▼
                   ┌────────────────────────┐
                   │  PerformanceMetrics   │
                   └────────────────────────┘
```

## 4. 关键设计决策

### 4.1 策略与检测器分离

CaiSenStrategy 采用策略-检测器分离架构：
- **策略**：只做决策。根据检测器信号判断入场/止损/止盈
- **检测器**：只做检测。识别形态，返回 PatternSignal
- **加权投票**：多检测器信号通过权重加权，达到阈值触发交易

### 4.2 LLM 离线预计算

LLMStrategy 采用离线预计算模式：
1. 回测开始时一次性加载所有历史数据
2. 调用 LLM 分析，生成所有时间点的信号和标注
3. 缓存结果到本地
4. 逐帧回放时查缓存返回 Order

优点：不改变回测引擎逻辑，支持任意 LLM

### 4.3 数据源注册机制

通过 Python entry points 注册数据源：
- 允许插件式添加新数据源
- 回测时动态发现可用的数据源
- LocalDataSource 是默认实现

### 4.4 结果持久化

ResultPersister 管理回测结果：
- 保存到 `./runs/{run_id}/` 目录
- 使用 Parquet 存储结构化数据
- 前端通过 data.json 渲染可视化

## 5. 文件清单

```
src/caisen/
├── core/
│   ├── __init__.py
│   ├── engine.py        # BacktestEngine
│   ├── config.py        # Config, BacktestConfig
│   ├── portfolio.py     # Portfolio
│   ├── position.py      # Position
│   ├── order.py         # Order, Side
│   ├── trade.py         # Trade
│   ├── bar.py           # Bar
│   └── annotation.py     # Annotation, AnnotationType
│
├── strategy/
│   ├── __init__.py
│   ├── base.py          # Strategy (abstract)
│   ├── algorithm/
│   │   ├── __init__.py
│   │   ├── cai_sen.py   # CaiSenStrategy
│   │   ├── detector.py  # PatternDetector, PatternSignal
│   │   ├── patterns/
│   │   │   ├── __init__.py
│   │   │   ├── w_bottom.py
│   │   │   ├── m_top.py
│   │   │   ├── head_shoulders.py
│   │   │   ├── triangle.py
│   │   │   └── other.py
│   │   └── caisen_components/
│   │       ├── __init__.py
│   │       ├── factory.py
│   │       ├── aggregator.py
│   │       └── position_manager.py
│   └── llm/
│       ├── __init__.py
│       ├── strategy.py   # LLMStrategy
│       ├── client.py     # LLMClient
│       ├── provider.py   # OpenAIProvider
│       ├── cache.py      # SignalCache
│       ├── evolver.py    # PromptEvolver
│       └── prompts/
│           ├── __init__.py
│           ├── default.py
│           └── caisen_pattern.py
│
├── data/
│   ├── __init__.py
│   ├── source.py        # DataSource (protocol)
│   ├── local_source.py  # LocalDataSource
│   ├── config.py        # DataConfig
│   ├── registry.py      # Registry
│   └── exceptions.py
│
├── result/
│   ├── __init__.py
│   ├── types.py         # BacktestResult
│   ├── calculator.py    # PerformanceMetrics, MetricsCalculator
│   └── persistence.py   # ResultPersister
│
├── web/
│   ├── __init__.py
│   └── main.py          # Web server
│
├── frontend/
│   └── (Vite 项目)
│
├── cli/
│   ├── __init__.py
│   └── main.py          # CLI commands
│
└── lint_structure.py    # Structure linting
```

## 6. 文档同步检查清单

代码变更后，检查以下文档是否同步更新：

| 代码变更 | 需检查文档 |
|----------|-----------|
| 新增/删除类 | `docs/design.md` 类图和类职责声明 |
| 新增/删除模块 | `CONTEXT.md` 目录结构规范 |
| 新增术语/概念 | `CONTEXT.md` Language 章节 |
| 架构决策变更 | `docs/adr/` 相关 ADR |
| 接口变更 | `CONTEXT.md` Relationships |

---

_最后更新: 2026-05-22_