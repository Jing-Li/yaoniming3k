# ADR-0008: 架构深化改进

## Status
Implemented

## Context
通过架构审查发现7个需要改进的架构问题，涉及模块深度、接缝质量、测试性和知识局部性。

## Decisions

### 1. CaiSenStrategy 拆分
- 提取 `DetectorFactory` 负责检测器创建
- 提取 `SignalAggregator` 负责加权评分
- 提取 `PositionManager` 负责仓位/止损/止盈
- `CaiSenStrategy` 仅保留决策编排逻辑

### 2. Metrics 计算统一
- `MetricsCalculator` 成为唯一计算入口
- `PerformanceMetrics` 仅作为数据容器
- 删除 `BacktestResult` 中的计算属性

### 3. Annotation 提升到 core
- `Annotation` 从 `strategy/base.py` 移到 `core/annotation.py`
- 作为策略、结果、前端之间的共享契约

### 4. LLM Provider 简化
- `LLMClient` 简化为仅 `call(prompt: str) -> str`
- `PromptBuilder` 和 `ResponseParser` 独立为单独模块
- 删除 `PromptBuilderClient` 适配器

### 5. PatternDetector 纯函数化
- `detect(bars: List[Bar])` 改为纯函数接口
- 状态管理移到 `BarBuffer` 类

### 6. Annotation 渲染单一真相源
- JS 端 `ANNOTATION_SCHEMA` 统一定义所有标注类型
- 颜色、形状、渲染逻辑集中管理

### 7. LLMStrategy 依赖注入
- 通过 `DataSource` 协议注入，不直接依赖 `LocalDataSource`

## Consequences

### Positive
- 每个模块职责单一，接口深度增加
- 测试性提升，可独立测试各个组件
- 知识局部性改善，变更影响范围可控

### Negative
- 需要较多重构工作
- 短期内可能引入不稳定性

## References
- 架构审查记录: improve-codebase-architecture (2026-05-22)
