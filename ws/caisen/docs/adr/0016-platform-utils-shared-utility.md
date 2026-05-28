# ADR-0016: PlatformUtils 共享工具模式

## Status
Implemented

## Context
BreakdownPullbackDetector（破底翻）和 FakeBreakoutDetector（假突破）都需要识别整理平台（Platform）：价格在一段时间内在某个区间内来回波动，既不创新高也不创新低。两个检测器的平台识别逻辑几乎相同，仅后续的破位方向和确认条件不同。

### 替代方案

1. **代码重复**：两个检测器各自实现 `find_platform()` 逻辑
2. **共享工具模块**：提取 `_platform_utils.py`，两个检测器共同引用

## Decision

采用方案 2：创建 `_platform_utils.py` 共享工具模块。

理由：
- 平台识别算法（滑动窗口评分）逻辑复杂（约 40 行），重复实现会增加维护成本和不一致风险
- 两个检测器对平台的定义一致（lookback_period、max_amplitude、min_platform_bars），共享后可保证行为一致
- 以下划线前缀（`_platform_utils`）标识为内部模块，不作为公共 API 导出

### 接口

```python
def find_platform(bars, lookback_period=30, max_amplitude=0.05, min_platform_bars=8) -> Optional[Tuple[float, float, int, int]]:
    """返回 (upper, lower, start_idx, end_idx) 或 None"""
```

## Consequences

### Positive
- 平台识别逻辑单一真相源，修改一处即生效
- 两个检测器对平台的定义保证一致
- 未来若有其他基于平台的检测器，可直接复用

### Negative
- 增加模块间依赖（检测器 → _platform_utils）
- 需要确保共享参数（如 max_amplitude）对不同检测器语义一致

## References
- `src/caisen/strategy/algorithm/patterns/_platform_utils.py`
- `src/caisen/strategy/algorithm/patterns/breakdown_pullback.py`
- `src/caisen/strategy/algorithm/patterns/fake_breakout.py`
