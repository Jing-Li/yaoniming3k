# ADR-0015: LLMStrategy 依赖注入

## Status
Accepted

## Context
ADR-0008 Issue #7 指出 `LLMStrategy` 直接依赖 `LocalDataSource`，导致：
- 无法使用其他数据源
- 难以测试
- 违反了依赖倒置原则

## Decision

### 1. DataSource 协议定义

已有的 `DataSource` 协议（`caisen/data/source.py`）定义了数据源的抽象接口：

```python
class DataSource(Protocol):
    def load(self, config: DataConfig) -> List[Bar]: ...
    @property
    def name(self) -> str: ...
```

### 2. LLMStrategy 接受 DataSource 注入

`LLMStrategy.__init__` 新增 `data_source` 参数：

```python
def __init__(
    self,
    llm_client=None,
    config: "LLMStrategyConfig" = None,
    prompt_builder=None,
    response_parser=None,
    data_source: DataSource = None  # 新增
):
```

### 3. on_init 中优先使用注入的数据源

```python
def on_init(self, config: BacktestConfig) -> None:
    if not self._bars:
        # 优先使用注入的数据源
        if self.data_source is not None:
            self._bars = self.data_source.load(data_config)
        # 回退到默认的 LocalDataSource
        elif hasattr(config, 'data_dir') and hasattr(config, 'symbol'):
            data_source = LocalDataSource(config.data_dir)
            self._bars = data_source.load(data_config)
```

## Consequences

### Positive
- **可测试性**：测试时可以注入 MockDataSource
- **可扩展性**：支持自定义数据源（数据库、API 等）
- **灵活性**：可以在 config 和注入之间选择

### Negative
- 参数增多，需要维护 data_source 的生命周期

## Files Changed
- `src/caisen/strategy/llm/strategy.py` - 支持 data_source 注入

## References
- ADR-0008: 架构深化改进
- `caisen/data/source.py` - DataSource 协议定义