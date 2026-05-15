# caisen

量化回测系统，支持代码策略和 LLM 策略。

## 安装

```bash
pip install -e .
```

## 快速开始

### 1. 准备数据

caisen 需要从本地加载数据。使用 [caisen-data](../caisen-data/) 项目下载数据：

```bash
# 进入 caisen-data 项目
cd ../caisen-data

# 下载期货数据（以白银为例）
caisen-data fetch --symbol ag --start 2023-01-01 --end 2024-12-31 --freq 1d

# 下载 A 股数据
caisen-data fetch --symbol 000001.SZ --start 2023-01-01 --end 2024-12-31 --freq 1d
```

数据将保存到 `caisen-data/data/{symbol}/{freq}/` 目录下。

### 2. 运行回测

```bash
# 运行示例策略
caisen run --strategy examples/ma_cross.py --symbol ag

# 查看回测结果
caisen list-runs
caisen show-result <run_id>
```

### 3. 使用蔡森策略

```bash
caisen run --strategy examples/cai_sen_backtest.py --symbol ag
```

## 项目架构

```
caisen/                 # 回测系统
├── src/caisen/
│   ├── core/          # 核心引擎
│   ├── strategy/      # 策略实现
│   ├── data/          # 数据加载
│   └── result/        # 结果分析
└── examples/          # 示例策略

caisen-data/           # 数据抓取（独立项目）
├── src/caisen_data/
│   └── sources/       # 数据源实现
└── data/              # 本地数据存储
```

**协作流程**:
1. `caisen-data` 从外部 API 获取数据，保存为本地 Parquet
2. `caisen` 通过 `LocalDataLoader` 加载本地数据运行回测

## 数据要求

- **格式**: Parquet 文件
- **目录结构**: `data/{symbol}/{freq}/{date_range}.parquet`
- **列名**: 支持中英文（`timestamp/日期`, `open/开盘价` 等）
- **时间框架**: 日线或周线（推荐半年以上数据）

## 编写自定义策略

```python
from caisen.core.bar import Bar
from caisen.core.order import Order, Side
from caisen.strategy.base import Strategy

class MyStrategy(Strategy):
    def on_bar(self, bar: Bar) -> Optional[Order]:
        # 实现交易逻辑
        if self.should_buy(bar):
            return Order(symbol=bar.symbol, side=Side.BUY, quantity=0)
        return None
```

## 更多示例

- `examples/ma_cross.py` - 均线金叉死叉策略
- `examples/cai_sen_backtest.py` - 蔡森十二形态策略
- `examples/cai_sen_real_data.py` - 真实数据回测示例
