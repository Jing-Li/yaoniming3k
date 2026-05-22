# ADR-0011: CaiSenStrategy 组件拆分

## Status
Implemented

## Context
ADR-0008 Issue #1 指出 `CaiSenStrategy` (399 行) 承担了太多职责，需要拆分为独立组件以提升可测试性和知识局部性。

## Decisions

### 1. 组件拆分

```
CaiSenStrategy (编排层 ~80 行)
├── DetectorFactory      # 检测器创建
├── SignalAggregator     # 信号聚合评分
└── PositionManager      # 仓位+风控+回调
```

### 2. DetectorFactory

- **职责**：配置驱动创建检测器实例
- **接口**：
  ```python
  class DetectorFactory:
      def create(enabled_patterns: List[str], config: Dict) -> List[PatternDetector]
  ```

### 3. SignalAggregator

- **职责**：收集信号、应用权重、计算综合评分
- **特性**：无状态（纯函数）
- **接口**：
  ```python
  def aggregate(signals: List[PatternSignal], weights: Dict[str, float]) -> AggregatedResult
  ```

### 4. PositionManager

- **职责**：管理持仓状态、止损/止盈判断、回调通知
- **特性**：有状态，包含风控逻辑
- **接口**：
  ```python
  class PositionManager:
      def open(signal: PatternSignal)
      def close()
      def check_stop_loss(bar: Bar) -> bool
      def check_take_profit(bar: Bar) -> bool
      def on_stop_loss(callback)
      def on_take_profit(callback)
  ```

### 5. PatternDetector 缓存

- **对外**：纯函数接口 `detect(bars)`
- **对内**：增量计算 + 结果缓存
- **缓存策略**：基于 bars 长度，命中则直接返回

### 6. 文件组织

```
strategy/algorithm/
├── detector.py
├── patterns/
│   └── ...
├── caisen_components/          # 新目录
│   ├── __init__.py
│   ├── factory.py             # DetectorFactory
│   ├── aggregator.py          # SignalAggregator
│   └── position_manager.py    # PositionManager
└── cai_sen.py                 # 重构后的 CaiSenStrategy
```

## Consequences

### Positive
- CaiSenStrategy 代码行数 < 100 行
- 每个组件可独立测试
- 便于后续扩展（如新检测器、新聚合算法）
- 增量计算避免重复检测

### Negative
- 需要重构现有代码
- 组件间接口需要维护

## References
- ADR-0008: 架构深化改进
- Issue #1: CaiSenStrategy 拆分