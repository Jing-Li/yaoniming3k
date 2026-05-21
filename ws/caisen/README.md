/# caisen 量化回测系统

量化回测系统，支持代码策略和 LLM 策略。可视化报告支持 K 线图、净值曲线、交易标注和形态标记。

## 功能特性

- **代码策略**：继承 `Strategy` 基类实现交易逻辑
- **LLM 策略**：大语言模型驱动的自主决策
- **蔡森形态**：实现蔡森十二形态识别（头肩顶/底、三角、旗形等）
- **可视化报告**：HTML + ECharts 渲染，支持买入/卖出信号、趋势线、形态标注
- **结果持久化**：Parquet 格式存储，自动生成 run_id 标识

## 安装

### 环境要求

- Python 3.10+
- pip

### 安装步骤

```bash
# 克隆项目
git clone https://github.com/your-repo/caisen.git
cd caisen

# 安装依赖（开发模式）
pip install -e .

# 确保 PATH 包含 ~/.local/bin（Linux/Mac）
export PATH="$HOME/.local/bin:$PATH"

# 验证安装
caisen --help
```

> **注意**：如果 `caisen` 命令找不到，添加 `~/.local/bin` 到 PATH 或使用：
> ```bash
> ~/.local/bin/caisen --help
> ```

### 依赖

主要依赖：
- `click` - CLI 框架
- `pandas` - 数据处理
- `pyarrow` - Parquet 支持
- `akshare` - 数据源（如需实时数据）

## 快速开始

### 1. 运行回测（模拟数据）

无需准备数据，使用模拟数据快速测试：

```bash
# 运行均线交叉策略
caisen run -s MACrossStrategy --mock

# 指定回测参数
caisen run -s MACrossStrategy --mock --symbol ag --start 2024-01-01 --end 2024-12-31
```

输出示例：
```
Loaded 365 mock bars for ag
Running backtest with strategy: MACrossStrategy

Backtest Complete!
Run ID: MACrossStrategy_20260518_1
Total Trades: 12
Final Equity: 108542.50
Total Return: 8.54%
```

### 2. 查看回测结果

```bash
# 列出所有回测记录
caisen list-runs

# 查看详细指标
caisen show-result MACrossStrategy_20260518_1
```

### 3. 启动可视化服务

```bash
# 启动 HTTP 服务（端口 8000）
caisen serve

# 指定端口和直接打开某个回测
caisen serve --port 8080 --run-id MACrossStrategy_20260518_1
```

打开浏览器访问 `http://localhost:8000` 查看可视化报告。

### 4. 使用真实数据

需要先通过 [caisen-data](https://github.com/your-repo/caisen-data) 获取数据：

```bash
# 进入 caisen-data 项目
cd ../caisen-data

# 下载期货数据（沪银主力）
caisen-data fetch --symbol ag --start 2023-01-01 --end 2024-12-31 --freq 1d

# 下载分钟数据
caisen-data fetch --symbol ag --start 2024-01-01 --end 2024-12-31 --freq 1h
```

然后回到 caisen 运行回测：

```bash
caisen run -s MACrossStrategy --symbol ag --start 2024-01-01 --end 2024-12-31
```

## CLI 命令

### `caisen run`

运行回测。

```bash
caisen run [OPTIONS]

Options:
  -s, --strategy TEXT    策略名称或文件路径（必需）
  --symbol TEXT          股票/期货代码 [默认: TEST]
  --start TEXT           开始日期 [默认: 2024-01-01]
  --end TEXT             结束日期 [默认: 2024-12-31]
  -c, --config FILE      配置文件路径（YAML）
  --output-dir TEXT      输出目录 [默认: ./runs]
  --mock                 使用模拟数据
  --help                 显示帮助
```

示例：
```bash
# 从策略文件运行
caisen run -s ./strategies/my_strategy.py --symbol ag --mock

# 使用配置文件
caisen run -s MACrossStrategy -c config/backtest.yaml

# 指定输出目录
caisen run -s MACrossStrategy --mock --output-dir /tmp/results
```

### `caisen list-runs`

列出所有回测记录。

```bash
caisen list-runs [OPTIONS]

Options:
  --output-dir TEXT  输出目录 [默认: ./runs]
```

### `caisen show-result`

查看回测结果详情。

```bash
caisen show-result <RUN_ID> [OPTIONS]

Options:
  --output-dir TEXT  输出目录 [默认: ./runs]
```

### `caisen serve`

启动可视化报告服务。

```bash
caisen serve [OPTIONS]

Options:
  -r, --run-id TEXT   直接打开指定回测
  -p, --port INTEGER  服务端口 [默认: 8000]
  --host TEXT         服务地址 [默认: 0.0.0.0]
  --output-dir TEXT    回测结果目录 [默认: ./runs]
```

## 回测结果

回测结果保存在 `./runs/{run_id}/` 目录下：

```
runs/
├── MACrossStrategy_20260518_1/
│   ├── meta.json          # 元数据
│   ├── data.json          # 可视化数据（前端专用）
│   ├── bars.parquet       # K 线数据
│   ├── trades.parquet     # 交易记录
│   ├── equity.parquet     # 净值曲线
│   ├── annotations.json   # 可视化标注
│   └── metrics.json       # 绩效指标
```

### Run ID 格式

`{策略名}_{YYYYMMDD}_{序号}`

- 示例：`MACrossStrategy_20260518_1`
- 同日同名策略重复运行，序号自动递增

### data.json 结构

前端可视化使用的综合数据文件：

```json
{
  "meta": {
    "strategy_name": "MACrossStrategy",
    "symbol": "ag",
    "start": "2024-01-01T00:00:00",
    "end": "2024-12-31T00:00:00",
    "freq": "1d"
  },
  "metrics": {
    "annual_return": 0.0854,
    "max_drawdown": 0.1523,
    "sharpe_ratio": 0.45,
    "win_rate": 0.333,
    "profit_factor": 1.21
  },
  "bars": [...],
  "equity_curve": [...],
  "trades": [...],
  "annotations": [...]
}
```

## 编写策略

### 基本策略

```python
from datetime import datetime
from caisen.core.bar import Bar
from caisen.core.order import Order, Side
from caisen.strategy.base import Strategy

class MyStrategy(Strategy):
    def __init__(self):
        super().__init__()
        self.ma5 = []
        self.ma20 = []

    def on_bar(self, bar: Bar) -> Order | None:
        self.ma5.append(bar.close)
        self.ma20.append(bar.close)

        if len(self.ma5) > 5:
            self.ma5.pop(0)
        if len(self.ma20) > 20:
            self.ma20.pop(0)

        if len(self.ma5) < 20:
            return None

        avg5 = sum(self.ma5) / len(self.ma5)
        avg20 = sum(self.ma20) / len(self.ma20)

        if avg5 > avg20 and self.ma5[-2] <= self.ma20[-2]:
            return Order(symbol=bar.symbol, side=Side.BUY, quantity=10, timestamp=bar.timestamp)
        elif avg5 < avg20 and self.ma5[-2] >= self.ma20[-2]:
            return Order(symbol=bar.symbol, side=Side.SELL, quantity=10, timestamp=bar.timestamp)

        return None
```

### 蔡森形态策略

```python
from caisen.strategy.cai_sen import CaiSenStrategy

# 初始化（可配置参数）
strategy = CaiSenStrategy(
    platform_threshold=0.02,  # 平台判断阈值
    volume_threshold=1.5,      # 成交量倍数
)

# 运行回测
caisen run -s CaiSenStrategy --symbol ag --mock
```

## 项目结构

```
caisen/
├── src/caisen/           # 核心代码
│   ├── cli/              # CLI 入口
│   ├── core/             # 回测引擎
│   │   ├── engine.py     # BacktestEngine
│   │   ├── bar.py        # K 线数据
│   │   ├── order.py      # 订单
│   │   ├── trade.py      # 交易记录
│   │   └── portfolio.py  # 账户
│   ├── data/             # 数据加载
│   │   ├── local.py      # 本地数据
│   │   └── loader.py     # 数据加载器
│   ├── strategy/         # 策略实现
│   │   ├── base.py       # 策略基类
│   │   ├── ma_cross.py   # 均线策略
│   │   └── cai_sen.py    # 蔡森形态
│   ├── result/           # 结果分析
│   │   ├── persistence.py # 结果持久化
│   │   └── metrics.py    # 绩效指标
│   └── visualization/    # 可视化
│       ├── index.html    # 渲染器
│       └── sample/       # 示例数据
├── tests/               # 测试
├── examples/            # 示例策略
├── docs/                # 文档
└── README.md
```

## 数据要求

### 格式

- **存储格式**：Parquet
- **目录结构**：`data/{symbol}/{freq}/{date}.parquet`

### 列名

支持中英文混写：

| 中文列名 | 英文列名 | 类型 | 说明 |
|---------|---------|------|------|
| 日期 | timestamp | datetime | 时间戳 |
| 开盘价 | open | float | 开盘价 |
| 收盘价 | close | float | 收盘价 |
| 最高价 | high | float | 最高价 |
| 最低价 | low | float | 最低价 |
| 成交量 | volume | float | 成交量 |

## 绩效指标

回测完成后，系统计算以下指标：

| 指标 | 说明 |
|------|------|
| annual_return | 年化收益率 |
| max_drawdown | 最大回撤 |
| sharpe_ratio | 夏普比率 |
| win_rate | 胜率 |
| profit_factor | 盈亏比 |
| total_trades | 总交易次数 |

## 可视化标注类型

| 类型 | 说明 | 渲染方式 |
|------|------|----------|
| buy_signal | 买入信号 | 绿色向上三角 |
| sell_signal | 卖出信号 | 红色向下三角 |
| pattern_mark | 形态标记 | 连线+标签 |
| horizontal_line | 水平线 | 水平线段 |
| trend_line | 趋势线 | 斜线段 |
| support_zone | 支撑区 | 绿色虚线 |
| resistance_zone | 阻力区 | 红色虚线 |
| text_label | 文本标注 | 文字标签 |

## 测试

```bash
# 运行所有测试
python -m pytest tests/

# 运行指定测试
python -m pytest tests/test_backtest_engine.py -v

# 生成覆盖率报告
python -m pytest tests/ --cov=src/caisen --cov-report=html
```

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 代码格式化
black src/

# 类型检查
mypy src/
```

## License

MIT