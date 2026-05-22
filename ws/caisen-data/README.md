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
