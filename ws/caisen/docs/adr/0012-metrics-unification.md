# ADR-0012: Metrics 计算统一

## Status
Implemented

## Context
ADR-0008 Issue #2 指出 `BacktestResult` 和 `PerformanceMetrics` 中存在重复的指标计算逻辑，需要统一到 `MetricsCalculator`。

## Decisions

### 1. MetricsCalculator 作为唯一计算入口

```python
class MetricsCalculator:
    def calculate(self, result: BacktestResult) -> PerformanceMetrics:
        """计算绩效指标"""
        ...
```

### 2. BacktestResult 成为纯数据容器

- 删除所有计算属性 (`total_return`, `max_drawdown`, `sharpe_ratio`, `win_rate`, `profit_factor`)
- 只保留原始数据字段

### 3. PerformanceMetrics 只作为数据容器

- 移动到 `result/calculator.py`
- 不含任何计算逻辑

### 4. 文件结构

```
result/
├── types.py         # BacktestResult (纯数据)
├── calculator.py   # MetricsCalculator + PerformanceMetrics
├── persistence.py   # ResultPersister
└── __init__.py
```

### 5. 调用更新

- `ResultPersister.save()`: 使用 `MetricsCalculator.calculate()`
- `CaiSenOptimizer._run_single_backtest()`: 使用 `MetricsCalculator.calculate()`
- `cli/main.py`: 直接计算 `total_return`
- Examples: 使用 `MetricsCalculator`

## Consequences

### Positive
- 每个指标只有一处计算逻辑
- 便于单元测试 MetricsCalculator
- 单一真相源

### Negative
- 需要更新所有调用点
- BacktestResult 不再直接提供计算属性

## References
- ADR-0008: 架构深化改进
- Issue #2: Metrics 计算统一