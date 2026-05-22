# Context

量化回测系统。为交易策略提供历史数据回测能力，通过模拟交易生成绩效指标，辅助策略评估与优化。支持代码策略和大语言模型（LLM）策略两种实现方式。

## Language

**Backtest（回测）**:
在给定的历史数据上运行交易策略，模拟交易并生成绩效指标的过程。
_Avoid_: 模拟交易、策略测试

**Strategy（策略）**:
由用户实现的、遵循约定接口的交易逻辑。回测系统负责加载并执行策略。一个策略定义了何时买入、何时卖出、仓位管理等规则。

**Code Strategy（代码策略）**:
以 Python 代码形式实现的策略。继承 `Strategy` 基类，硬编码交易逻辑（如 MA 金叉死叉）。

**LLM Strategy（LLM 策略）**:
以大语言模型驱动的策略。通过 Prompt 描述交易逻辑，LLM 根据历史数据自主决策。策略提供数据，LLM 提供决策。采用离线预计算模式：历史数据一次性喂给 LLM，决策结果缓存后逐帧回放给回测引擎。

**离线预计算（Offline Pre-computation）**:
LLM 策略的架构模式。将完整历史数据一次性发送给 LLM 分析，LLM 返回所有时间点的信号和标注，策略缓存后逐帧回放。不改变回测引擎逻辑。

**Strategy Plugin（策略插件）**:
一种具体的 Strategy 实现，以独立的 Python 文件形式存放在约定目录中。回测系统通过配置文件指定路径加载。
_Avoid_: 策略文件

**Strategy Discovery（策略发现）**:
回测系统扫描策略目录，自动识别符合接口约定的策略类的过程。
_Avoid_: 策略插件发现

**Backtest Run / Run（回测运行）**:
一次具体的回测执行，包含：一个策略、一段回测周期、一组参数、一组结果数据。

**Result（回测结果）**:
一次 Run 的输出，包含交易记录、净值曲线、绩效指标、可视化标注等结构化数据。持久化到本地存储。

**Performance Metrics（绩效指标）**:
用于评估策略表现的量化指标，如年化收益率、最大回撤、夏普比率、胜率等。

**Data Fetcher（数据抓取模块）**:
负责从外部数据源获取行情数据并保存为文件的独立工具（caisen-data 项目）。独立于回测系统运行。
_Avoid_: 数据下载器

**DataSource（数据源）**:
行情数据的来源接口。回测系统通过 DataSource 从本地存储加载 K 线数据。
_Avoid_: 数据提供者

**Bar（K线）**:
一根 K 线数据，包含时间戳、开盘价、收盘价、最高价、最低价、成交量等字段。
_Avoid_: K线数据、K棒

**Order（订单）**:
策略发出的交易指令，包含标的、方向（买入/卖出）、数量等信息。回测引擎负责撮合成交。

**Position（持仓）**:
当前账户持有的某标的仓位，包含数量和平均成本。正数为多头，负数为空头。

**Portfolio（组合/账户）**:
回测账户的资金和持仓状态。管理初始资金、当前现金、持仓、净值计算等。
_Avoid_: 账户、资金账户

**成本价值（Cost Value）**:
持仓的成本估算价值。计算方式：`cash + sum(quantity * avg_cost)`。反映买入时的成本，不反映当前盈亏。
_参见_: `Portfolio.cost_value`（属性），原 `equity` 属性已改为别名

**市值价值（Market Value）**:
持仓的当前市场价值。计算方式：`cash + sum(quantity * current_price)`。反映真实的市场价值。
_参见_: `Portfolio.get_equity_with_prices(prices)`（方法）

**BacktestEngine（回测引擎）**:
核心执行单元。加载数据、逐根 K 线遍历、调用策略、处理订单、更新持仓、计算净值。

**Session（会话）**:
一次回测的生命周期。从 `on_init` 开始，逐根 K 线执行，到 `on_session_end` 结束。

**LLM Provider（LLM 提供者）**:
LLM API 的封装接口。支持多种 LLM（OpenAI、Claude、本地模型等），通过统一接口切换。

**Annotation（可视化标注）**:
策略在 K 线图上绘制的辅助信息，包含支撑线、阻力线、趋势线、买卖点标记等。用于回测报告可视化。

**Checkpoint（检查点）**:
回测中断时保存的运行状态。包含已处理的 K 线索引、Portfolio 状态、交易记录等，支持断点续传。

**LLM Cache（LLM 缓存）**:
LLM 响应的本地缓存。按策略名+版本+bar timestamp 标识，避免重复调用相同数据。

**Report（回测报告）**:
回测结果的可视化输出，包含摘要、净值曲线、交易记录、可视化标注等。格式为 HTML。

**Compare Mode（对比模式）**:
同时运行代码策略和 LLM 策略，对比两者的交易决策和绩效指标。

**Entry Points（入口点）**:
Python 插件机制。caisen 定义 `caisen.datasources` 入口点，数据源实现通过入口点注册，使回测引擎可以动态发现可用的数据源。

**Config（配置）**:
YAML 格式的回测参数文件。包含初始资金、手续费率、策略参数、数据范围、LLM 配置、Checkpoint 配置等。

**Run ID（运行ID）**:
一次 Run 的唯一标识符，格式为 `{策略名}_{YYYYMMDD}_{序号}`，如 `MACrossStrategy_20260518_1`。序号从 1 开始，同一策略同日多次运行自动递增。用于关联结果文件和后续查询。

**Trade（交易记录）**:
一次成交的记录，包含成交时间、标的、方向、数量、成交价、手续费、滑点成本等。

**Pattern（形态）**:
价格与支撑/阻力位的结构性互动关系，如整理平台、破底翻、假突破等。蔡森十二形态描述的是主力在关键位置的操盘意图，而非单根K线的形状。

**Platform（整理平台）**:
价格在一段时间内在某个区间内来回波动，既不创新高也不创新低。是多空力量暂时均衡的区域，也是所有大行情启动前的必经阶段。
_Avoid_: 盘整区间、横盘

**Breakdown Pullback（破底翻）**:
价格跌破整理平台下沿（破底）后迅速拉回并站回平台内部（翻），形成强烈底部反转信号。第一买点在站回颈线时，第二买点在突破平台上沿时。

**Fake Breakout（假突破）**:
价格突破整理平台上沿后迅速跌回平台内部，是破底翻的反向关系，代表顶部或中继陷阱。本质是主力诱多出货。

**Neckline（颈线）**:
整理平台的上沿（阻力位）和下沿（支撑位）。价格突破或跌破颈线意味着整理结束，趋势启动。

**Equity Curve（净值曲线）**:
回测过程中账户净值随时间变化的序列数据。按每根 K 线采样。

**Visualization Report（可视化报告）**:
回测结果的可视化输出，包含 K 线图、净值曲线、交易标注、策略形态标记等。
由 Python 生成 JSON 数据，前端 HTML 渲染器渲染。
Web 服务位于 `src/caisen/web/`，前端位于 `src/caisen/frontend/`，通过 `caisen web` 命令启动。
_Avoid_: 回测图表、报告 HTML

**Annotation（可视化标注）**:
策略在 K 线图上绘制的辅助信息。包含 type（类型）、timestamp（时间）、data（数据）三个核心字段。类型决定渲染方式。
_参见_: ADR-0007 可视化报告架构

**MPA（多页应用）**:
可视化报告采用多页面架构。`index.html` 为 runs 列表页，`report.html` 为回测详情页。两个页面独立，可离线打开。
_参见_: ADR-0007 可视化报告架构

**Frontend Bundle（前端子目录）**:
前端代码独立存放于 `frontend/` 子目录，包含 HTML 页面、JS 模块、CSS 样式、单元测试和 E2E 测试。使用 Vite 构建。
_参见_: ADR-0007 可视化报告架构

## Relationships

- 一个 **BacktestEngine** 执行一次 **Run**，产生一个 **Result**
- 一个 **Result** 包含多个 **Trade**、一个 **Equity Curve**、一组 **Performance Metrics** 和可选的 **Annotation**
- 一个 **Strategy** 在一个 **Session** 中被调用多次（每根 K 线一次）
- 一个 **Strategy** 管理一个 **Portfolio**，Portfolio 包含多个 **Position**
- **Strategy** 分为 **Code Strategy** 和 **LLM Strategy** 两种实现
- **LLM Strategy** 调用 **LLM Provider** 获取决策，响应缓存在 **LLM Cache** 中
- **LLM Strategy** 的决策可能包含 **Annotation**，用于回测报告可视化
- **Code Strategy** 和 **LLM Strategy** 可通过 **Compare Mode** 对比
- **Data Fetcher** 从 **DataSource** 获取数据，写入本地存储；回测时 **BacktestEngine** 从本地加载
- **Checkpoint** 可保存和恢复 **BacktestEngine** 的运行状态，实现断点续传

## Example dialogue

> **Dev:** "策略在 `on_bar` 中返回 **Order**，引擎如何成交？"
> **Domain expert:** "市价单在下一根 K 线开盘价成交。引擎调用撮合逻辑，更新 **Portfolio** 和 **Position**，生成一条 **Trade** 记录。"

> **Dev:** "LLM 策略和代码策略有什么区别？"
> **Domain expert:** "**Code Strategy** 是硬编码的交易逻辑（如 MA 金叉），**LLM Strategy** 通过 Prompt 让大模型自主决策。两者接口一致，都返回 **Order**，但 LLM 策略可能返回额外的 **Annotation** 用于可视化。"

> **Dev:** "回测中断后怎么继续？"
> **Domain expert:** "引擎会定期保存 **Checkpoint**，包含已处理的 K 线索引和 **Portfolio** 状态。使用 `caisen run --resume <checkpoint_file>` 从断点继续。"

## 目录结构规范

项目使用 **六层目录结构**：

```
src/caisen/
├── core/          # 回测引擎核心（Engine、Config、Bar、Order）
├── strategy/      # 策略实现
│   ├── base.py    # 策略基类
│   ├── patterns/  # 形态检测器（W底、M头、三角等）
│   └── llm/       # LLM 策略实现
├── data/          # 数据加载模块
│   ├── source.py  # DataSource 接口
│   └── local_source.py  # 本地数据源实现
├── result/        # 回测结果处理
│   ├── types.py   # 数据类型（BacktestResult）
│   ├── metrics.py # 绩效指标计算
│   └── persistence.py  # 结果持久化
├── visualization/ # 可视化模块
│   ├── web/       # Python Web 服务
│   └── frontend/  # 前端代码（Vite 项目）
└── cli/           # 命令行工具
```

**命名规范**：
- 目录名：`snake_case`（全小写 + 下划线）
- 文件名：`snake_case.py`
- 类名：`PascalCase`
- 函数/变量：`snake_case`

**模块创建检查清单**：
1. 新模块是否属于已有顶层目录？
2. 新目录是否需要 `__init__.py`？
3. 新模块是否需要单元测试？
4. 是否需要更新 `__all__` 导出？

## Flagged ambiguities

- "account" 曾被用来指代 **Portfolio** 和 **User** — resolved：统一使用 **Portfolio** 表示资金账户，用户与策略分离。
- "交易" 可指代 **Order**（下单意图）或 **Trade**（已成交记录）— resolved：下单叫 Order，成交叫 Trade，区分意图与实际。
- "策略" 可指代 **Code Strategy** 或 **LLM Strategy** — resolved：明确上下文时需区分，两者实现方式不同但接口一致。