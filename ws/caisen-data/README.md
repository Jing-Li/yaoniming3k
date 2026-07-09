# caisen-data

数据抓取模块，为 [caisen](https://github.com/yaoniming3k/caisen) 回测系统提供数据源。

从外部 API（AKShare）获取 A 股 / 期货 K 线数据，清洗后保存为本地 Parquet 文件，支持增量抓取与自动合并。

## 安装

```bash
# 开发模式安装
pip install -e .

# 仅安装运行依赖（不需要 caisen 回测引擎时）
pip install akshare pandas pyarrow click
```

> **环境要求**: Python >= 3.10

## 快速开始

### CLI 下载数据

```bash
# 期货数据（白银主力合约，日线）
caisen-data fetch --symbol ag --start 2023-01-01 --end 2024-12-31 --freq 1d

# A 股数据
caisen-data fetch --symbol 000001.SZ --start 2023-01-01 --end 2024-12-31 --freq 1d

# 分钟线（5 分钟 / 15 分钟 / 30 分钟 / 60 分钟）
caisen-data fetch --symbol ag --start 2023-01-01 --end 2024-12-31 --freq 5m

# 强制重新下载（覆盖已有文件）
caisen-data fetch --symbol ag --start 2023-01-01 --end 2024-12-31 --force

# 指定输出目录
caisen-data fetch --symbol ag --start 2023-01-01 --end 2024-12-31 --output-dir ./my_data
```

### 增量抓取

数据默认保存到 `~/data`（可通过 `--output-dir` 修改）。

**增量行为**:
- 自动检测已有数据的日期范围（基于文件名，零 IO 开销）
- 精确计算缺失区间，只下载缺失部分
- 新数据与已有数据自动合并为单个文件
- 合并后旧文件自动清理

**示例**:
```bash
# 第一次下载 1~6 月
caisen-data fetch --symbol ag --start 2024-01-01 --end 2024-06-30
# → data/ag/1d/20240101_20240630.parquet

# 第二次扩展到 12 月（仅下载 7~12 月缺失部分）
caisen-data fetch --symbol ag --start 2024-01-01 --end 2024-12-31
# → data/ag/1d/20240101_20241231.parquet（合并后）

# 再次执行相同命令（数据已覆盖，直接跳过）
caisen-data fetch --symbol ag --start 2024-01-01 --end 2024-12-31
# → "数据已是最新，无需更新"
```

### 其他命令

```bash
# 列出可用标的（A 股）
caisen-data list-symbols

# 列出支持的数据源
caisen-data list-sources
```

### Python API

#### DataFrame 接口（推荐，无需 caisen 依赖）

```python
from caisen_data.sources.akshare import AKShareDataSource
from datetime import date

ds = AKShareDataSource()

# 期货数据 → DataFrame
df = ds.load_futures_df("ag", date(2023, 1, 1), date(2024, 12, 31), freq="1d")
print(f"加载了 {len(df)} 根K线")
print(df.head())
#    timestamp symbol freq   open   high    low  close  volume
# 0 2023-01-03    ag   1d  5320.0  5372.0  5298.0  5360.0   12345

# 股票数据 → DataFrame
df = ds.load_stock_df("000001.SZ", date(2023, 1, 1), date(2024, 12, 31))

# 分钟线
df = ds.load_futures_df("ag", date(2026, 5, 10), date(2026, 5, 15), freq="5m")
```

#### Bar 对象接口（需要 caisen 回测引擎）

```python
from caisen_data.sources.akshare import AKShareDataSource
from datetime import date

ds = AKShareDataSource()

bars = ds.load(
    symbol="ag",
    start=date(2023, 1, 1),
    end=date(2024, 12, 31),
    freq="1d",
)
print(f"加载了 {len(bars)} 根K线")
print(f"第一根: {bars[0].timestamp} close={bars[0].close}")
```

## 支持的标的

### 期货主力合约

| 代码 | 品种 | 交易所 |
|------|------|--------|
| `ag` | 沪银 | 上期所 |
| `m` | 豆粕 | 大商所 |
| `lh` | 生猪 | 大商所 |

期货支持频率：`1d`、`5m`、`15m`、`30m`、`60m`

### A 股

使用股票代码 + 交易所后缀，如 `000001.SZ`（深市）、`600519.SH`（沪市）。

A 股仅支持日线（`1d`）。

## 数据格式

保存为 Parquet 格式，目录结构：

```
~/data/
├── {symbol}/              # 标的代码（如 ag, 000001.SZ）
│   └── {freq}/            # 频率（1d, 5m, 15m, 30m, 60m）
│       └── {start}_{end}.parquet
```

Parquet 文件列定义：

| 列名 | 类型 | 说明 |
|------|------|------|
| `timestamp` | datetime | 时间戳 |
| `symbol` | string | 标的代码 |
| `freq` | string | 数据频率 |
| `open` | float | 开盘价 |
| `high` | float | 最高价 |
| `low` | float | 最低价 |
| `close` | float | 收盘价 |
| `volume` | float | 成交量 |

## CLI 参考

```
caisen-data fetch [OPTIONS]

选项:
  -s, --symbol TEXT    标的代码（必填）
  --start TEXT         开始日期 YYYY-MM-DD（必填）
  --end TEXT           结束日期 YYYY-MM-DD（必填）
  --freq TEXT          频率: 1d, 5m, 15m, 30m, 60m（默认 1d）
  --output-dir TEXT    输出目录（默认 ~/data）
  --source TEXT        数据源（默认 akshare）
  --force              强制重新下载，覆盖已有文件
```

## 与 caisen 回测系统的协作

```
┌─────────────┐     fetch      ┌─────────────┐     load       ┌─────────────┐
│ caisen-data │ ──────────────▶ │ 本地Parquet │ ──────────────▶ │   caisen    │
│  (数据源)    │                 │   文件      │                 │  (回测引擎)  │
└─────────────┘                 └─────────────┘                 └─────────────┘
```

1. **caisen-data** 从外部 API（AKShare）获取原始行情数据
2. 数据清洗后保存为本地 Parquet 文件
3. **caisen** 通过 `LocalDataLoader` 或 `load_bars()` 加载本地数据
4. 运行回测并生成结果

caisen-data 通过 `entry-points` 机制注册为 caisen 的数据源插件，两个包可独立安装使用。

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
PYTHONPATH=src python3 -m pytest tests/ -v
```

### 项目结构

```
src/caisen_data/
├── __init__.py           # 包入口，日志配置
├── cli.py                # CLI 命令（fetch / list-symbols / list-sources）
└── sources/
    ├── __init__.py
    ├── base.py           # DataSource 抽象基类
    └── akshare.py        # AKShare 数据源实现
tests/
└── test_cli_increment.py # 增量抓取逻辑的单元测试
docs/adr/
└── 0001-incremental-fetch.md  # ADR: 增量抓取设计决策
```

## 蔡森理论的数据建议

根据蔡森《多空转折一手抓》：

- **时间框架**: 日线或周线（避免小周期杂讯）
- **数据长度**: 半年以上（用于趋势判断）
- **整理平台**: 至少 10-20 根 K 线形成有效平台

```bash
# 下载 2 年日线数据（符合蔡森建议）
caisen-data fetch --symbol ag --start 2023-01-01 --end 2024-12-31 --freq 1d
```
# caisen-data

数据抓取模块，为 caisen 回测系统提供数据源。

## 安装

```bash
pip install -e .
```

## 快速开始

### CLI 使用

**下载数据**:
```bash
# 期货数据（白银主力合约）
caisen-data fetch --symbol ag --start 2023-01-01 --end 2024-12-31 --freq 1d

# A 股数据
caisen-data fetch --symbol 000001.SZ --start 2023-01-01 --end 2024-12-31 --freq 1d

# 指定频率（日线/5分钟/15分钟/30分钟/60分钟）
caisen-data fetch --symbol ag --start 2023-01-01 --end 2024-12-31 --freq 5m

# 强制更新（重新下载，覆盖已有文件）
caisen-data fetch --symbol ag --start 2023-01-01 --end 2024-12-31 --force
```

### 增量抓取

数据默认保存到 `/home/user/data`（可通过 `--output-dir` 修改）。

**增量行为**:
- 文件存在则跳过（假设历史数据不变）
- 新数据与已有数据自动合并
- 多文件合并为单个文件

**示例**:
```bash
# 第一次下载
caisen-data fetch --symbol ag --start 2024-01-01 --end 2024-06-30
# 生成: data/ag/1d/20240101_20240630.parquet

# 扩展范围（自动增量）
caisen-data fetch --symbol ag --start 2024-01-01 --end 2024-12-31
# 合并为: data/ag/1d/20240101_20241231.parquet
```

### 文件清理

下载新数据后，被合并的旧文件会自动删除，保持目录整洁。

**列出可用标的**:
```bash
caisen-data list-symbols
```

**列出数据源**:
```bash
caisen-data list-sources
```

### Python API

```python
from caisen_data.sources.akshare import AKShareDataSource
from datetime import date

# 创建数据源
ds = AKShareDataSource()

# 加载数据
bars = ds.load(
    symbol="ag",              # 期货代码
    start=date(2023, 1, 1),
    end=date(2024, 12, 31),
    freq="1d"                 # 日线
)

print(f"加载了 {len(bars)} 根K线")
```

## 支持的数据源

| 数据源 | 类型 | 说明 |
|--------|------|------|
| `akshare` | A股/期货 | 免费数据源，支持股票和期货主力合约 |

## 数据保存

下载的数据保存为 Parquet 格式，目录结构：

```
data/
├── {symbol}/              # 标的代码（如 ag, 000001.SZ）
│   └── {freq}/            # 频率（1d, 5m, 15m, 30m, 60m）
│       └── {start}_{end}.parquet
```

例如：`data/ag/1d/20230101_20241231.parquet`

## 与 caisen 回测系统的协作

```
┌─────────────┐     fetch      ┌─────────────┐     load       ┌─────────────┐
│ caisen-data │ ──────────────▶ │ 本地Parquet │ ──────────────▶ │   caisen    │
│  (数据源)    │                 │   文件      │                 │  (回测引擎)  │
└─────────────┘                 └─────────────┘                 └─────────────┘
```

1. **caisen-data** 从外部 API（如 AKShare）获取原始数据
2. 数据清洗后保存为本地 Parquet 文件
3. **caisen** 通过 `LocalDataLoader` 或 `load_bars()` 加载本地数据
4. 运行回测并生成结果

## 数据格式

Parquet 文件包含以下列：

| 列名（中文） | 列名（英文） | 类型 | 说明 |
|-------------|-------------|------|------|
| 日期 | timestamp | datetime | 时间戳 |
| 开盘价 | open | float | 开盘价 |
| 最高价 | high | float | 最高价 |
| 最低价 | low | float | 最低价 |
| 收盘价 | close | float | 收盘价 |
| 成交量 | volume | float | 成交量 |
| 标的 | symbol | string | 标的代码 |
| 频率 | freq | string | 数据频率 |

## 蔡森理论的数据建议

根据蔡森《多空转折一手抓》：

- **时间框架**: 日线或周线（避免小周期杂讯）
- **数据长度**: 半年以上（用于趋势判断）
- **整理平台**: 至少10-20根K线形成有效平台

示例下载（符合蔡森要求的2年数据）：
```bash
caisen-data fetch --symbol ag --start 2023-01-01 --end 2024-12-31 --freq 1d
```
