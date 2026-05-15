# ADR-0007: Data Module Implementation

## Status

Accepted

## Date

2026-05-15

## Context

项目需要从 mock data fallback 转向正式的 data 模块，以支持 AI Agent 平台的架构需求。

### 原有方案的问题

ADR-0001 规划数据源独立为 caisen-data 项目，但：
1. `caisen-data` 项目尚未实现
2. CLI 中的 `load_bars_from_parquet` 函数在找不到数据时默默生成 mock 数据
3. 无明确的错误提示，导致用户不知道数据缺失

### 新方案的需求

1. 定义 `DataLoader` 接口，支持插件化数据源
2. 实现 `LocalDataLoader` 作为默认实现
3. 支持从 Parquet 文件加载数据
4. 提供明确的异常处理，不再静默 fallback
5. 支持通过 Entry Points 注册外部数据源

## Decision

### 模块结构

```
src/caisen/data/
├── __init__.py         # 统一导出
├── config.py           # DataConfig 配置类
├── loader.py           # DataLoader Protocol + BaseDataLoader
├── local.py            # LocalDataLoader 实现
├── registry.py         # 数据源注册表
└── exceptions.py       # 自定义异常
```

### 核心接口

```python
class DataLoader(Protocol):
    """数据加载器协议"""
    def load(self, config: DataConfig) -> List[Bar]: ...

class DataConfig:
    """数据加载配置"""
    symbol: str
    freq: str
    start: Optional[str]
    end: Optional[str]
    data_dir: str
```

### 异常设计

| 异常 | 使用场景 |
|------|----------|
| `DataNotFoundError` | 找不到数据文件 |
| `DataSourceNotAvailableError` | 数据源不可用 |
| `InvalidDateRangeError` | 日期范围无效 |
| `DataValidationError` | 数据格式校验失败 |

### 目录结构

数据按 `data/{symbol}/{freq}/{date}.parquet` 存储，符合 ADR-0002 规范。

### 数据源注册

```python
from caisen.data import register_datasource, set_active_datasource

# 注册自定义数据源
register_datasource("akshare", AkshareDataLoader)
set_active_datasource("akshare")
```

## Consequences

### 正面

- 清晰的接口定义，便于扩展
- 明确的错误提示，不再静默失败
- 支持插件化数据源架构
- 与 ADR-0001/ADR-0002 保持一致

### 负面

- 需要用户自行准备数据或安装数据源插件
- 移除 mock data fallback 后，测试时需要生成测试数据

### 需要更新

- `src/caisen/data/__init__.py` ✓
- `src/caisen/data/config.py` ✓
- `src/caisen/data/exceptions.py` ✓
- `src/caisen/data/loader.py` ✓
- `src/caisen/data/local.py` ✓
- `src/caisen/data/registry.py` ✓
- `src/caisen/cli/main.py` - 更新使用新模块