# ADR-0001: 数据源模块独立为 caisen-data 项目

## 状态

Accepted

## 日期

2026-05-15

## 上下文

回测系统的数据源实现（akshare、tushare 等）需要决定如何与核心回测引擎组织。

## 决策

数据源模块独立为单独的 Python 项目（caisen-data），通过 Entry Points 插件机制注册到 caisen。

**为什么**：
- 回测引擎本身不依赖具体数据源，保持轻量
- 数据源实现依赖繁重（多种外部 API），单独维护可以独立发布节奏
- 避免强制用户安装不需要的数据源

## 项目结构

```
caisen/                    # 回测系统（核心）
├── src/caisen/
│   ├── core/             # 回测引擎
│   ├── strategy/         # 策略接口
│   └── data/             # 数据加载（LocalDataLoader）
└── docs/adr/

caisen-data/               # 数据抓取（独立项目）
├── src/caisen_data/
│   ├── cli.py            # CLI 入口
│   └── sources/          # 数据源实现
│       ├── akshare.py    # AKShare 数据源
│       └── base.py       # 数据源基类
└── data/                 # 本地数据存储
```

## 协作流程

```
┌─────────────┐     fetch      ┌─────────────┐     load       ┌─────────────┐
│ caisen-data │ ──────────────▶ │ 本地Parquet │ ──────────────▶ │   caisen    │
│  (数据源)    │                 │   文件      │                 │  (回测引擎)  │
└─────────────┘                 └─────────────┘                 └─────────────┘
```

### 1. 数据下载（caisen-data）

```bash
# 下载期货数据
caisen-data fetch --symbol ag --start 2023-01-01 --end 2024-12-31 --freq 1d

# 下载 A 股数据
caisen-data fetch --symbol 000001.SZ --start 2023-01-01 --end 2024-12-31 --freq 1d
```

数据保存到：`caisen-data/data/{symbol}/{freq}/{start}_{end}.parquet`

### 2. 数据加载（caisen）

```python
from caisen.data import DataConfig, load_bars

config = DataConfig(
    symbol="ag",
    start="2023-01-01",
    end="2024-12-31",
    data_dir="../caisen-data/data"  # 指向 caisen-data 的数据目录
)
bars = load_bars(config)
```

## 替代方案考虑

| 方案 | 优点 | 缺点 |
|------|------|------|
| **独立项目（选中）** | 轻量、灵活、独立发布 | 需要安装两个包 |
| 合并到 caisen | 单一包安装 | 强制依赖所有数据源 |
| 子命令模式 | 统一 CLI | 不够灵活，无法按需选择 |

## 后果

### 正面

- 回测引擎保持轻量，无外部 API 依赖
- 数据源可独立迭代，不影响核心引擎
- 用户按需安装数据源（如仅需期货数据则只装 akshare）

### 负面

- 用户需要安装两个包才能完整使用：
  ```bash
  pip install caisen caisen-data
  ```
- 需要管理两个项目的版本兼容性

### 使用示例

完整工作流程：

```bash
# 1. 安装两个包
pip install caisen caisen-data

# 2. 下载数据（caisen-data）
caisen-data fetch --symbol ag --start 2023-01-01 --end 2024-12-31

# 3. 运行回测（caisen）
caisen run --strategy examples/cai_sen_backtest.py --symbol ag
```

## 相关文档

- [caisen-data README](../../caisen-data/README.md)
- [ADR-0002: Parquet 数据存储](0002-parquet-data-storage.md)
- [ADR-0007: Data Module Implementation](0007-data-module-implementation.md)
