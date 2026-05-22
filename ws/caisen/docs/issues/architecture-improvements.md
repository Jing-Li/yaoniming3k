# 架构改进任务列表

## 背景
基于 ADR-0008 架构深化改进决策，创建以下跟踪任务。

---

## Issue 1: CaiSenStrategy 拆分 ✅
**标签**: `refactor`, `strategy`, `architecture`
**优先级**: High
**状态**: 已完成

### 任务
- [x] 创建 `DetectorFactory` 类
- [x] 创建 `SignalAggregator` 类
- [x] 创建 `PositionManager` 类
- [x] 重构 `CaiSenStrategy` 使用新组件
- [x] 更新测试

### 变更摘要
- 新增 `strategy/algorithm/caisen_components/` 目录
  - `factory.py`: DetectorFactory 检测器工厂
  - `aggregator.py`: SignalAggregator 信号聚合器
  - `position_manager.py`: PositionManager 仓位管理器
- CaiSenStrategy 从 394 行减少到 200 行
- 所有 172 个测试通过

### 验收标准
- [x] `CaiSenStrategy` 代码行数 < 200 行
- [x] 每个组件可独立测试

### 参考
- ADR-0011: CaiSenStrategy 组件拆分

---

## Issue 2: Metrics 计算统一 ✅
**标签**: `refactor`, `result`, `architecture`
**优先级**: Medium
**状态**: 已完成

### 任务
- [x] 创建 `MetricsCalculator` 类
- [x] 删除 `BacktestResult` 计算属性
- [x] 更新 `ResultPersister` 调用
- [x] 更新 `CaiSenOptimizer` 调用
- [x] 更新测试

### 变更摘要
- 新增 `result/calculator.py` - MetricsCalculator + PerformanceMetrics
- 删除 `result/types.py` 中的计算属性
- 更新所有调用点使用 MetricsCalculator

### 验收标准
- [x] 指标计算逻辑只存在于一处
- [x] `PerformanceMetrics` 无计算逻辑
- [x] 173 个测试通过

### 参考
- ADR-0012: Metrics 计算统一

---

## Issue 3: Annotation 提升到 core ✅
**标签**: `refactor`, `core`, `architecture`
**优先级**: Medium
**状态**: 已完成

### 任务
- [x] 创建 `core/annotation.py`
- [x] 移动 `Annotation` 和 `AnnotationType`
- [x] 更新所有导入语句
- [x] 更新测试

### 变更摘要
- 新增 `core/annotation.py` - Annotation + AnnotationType
- 更新 `core/__init__.py` 导出
- 更新 `strategy/base.py` 从 core 导入并重新导出
- 更新 `result/types.py` 从 core 导入
- 更新 `core/engine.py` 从 core 导入

### 验收标准
- [x] `strategy/base.py` 不再定义 `Annotation`
- [x] 无循环导入
- [x] 173 个测试通过

### 参考
- ADR-0013: Annotation 提升到 core

---

## Issue 4: LLM Provider 简化
**标签**: `refactor`, `llm`, `architecture`
**优先级**: Medium

### 任务
- [ ] 简化 `LLMClient` 接口
- [ ] 提取 `PromptBuilder` 类
- [ ] 提取 `ResponseParser` 类
- [ ] 删除 `PromptBuilderClient`
- [ ] 更新测试

### 验收标准
- `LLMClient` 只有 `call()` 方法
- `OpenAIProvider` 无需适配器

---

## Issue 5: PatternDetector 纯函数化 ✅
**标签**: `refactor`, `patterns`, `architecture`, `good-first-issue`
**优先级**: High
**状态**: 已完成

### 任务
- [x] 修改 `PatternDetector.detect()` 为纯函数
- [x] 更新所有检测器实现 (WBottom, MTop, HeadAndShoulders, Triangle, Flag, Rectangle, RoundingBottom, CupHandle, BreakoutPullback)
- [x] 更新 `CaiSenStrategy` 使用新接口
- [x] 更新测试

### 变更摘要
- `detect()` 方法现在接收 `bars: List[Bar]` 参数
- 移除了 `update()`, `reset()`, `_on_update()`, `_on_reset()` 方法
- 移除了 `_bars` 内部状态
- 辅助方法 (`_is_trend_up`, `_volume_ratio` 等) 现在接收 `bars` 参数
- 所有检测器现在是无状态的，可独立测试

### 验收标准
- [x] `detect()` 不依赖内部状态
- [x] 所有检测器可独立测试
- [x] 所有 172 个测试通过

---

## Issue 6: Annotation 渲染单一真相源
**标签**: `refactor`, `frontend`, `architecture`
**优先级**: Low

### 任务
- [ ] 创建 `ANNOTATION_SCHEMA`
- [ ] 统一渲染入口
- [ ] 删除分散的渲染逻辑
- [ ] 更新测试

### 验收标准
- 新增标注类型只需修改一处
- 颜色/形状配置集中管理

---

## Issue 7: LLMStrategy 依赖注入
**标签**: `refactor`, `llm`, `architecture`
**优先级**: Low

### 任务
- [ ] 修改 `LLMStrategy.__init__` 接受 `DataSource`
- [ ] 删除直接导入 `LocalDataSource`
- [ ] 更新 CLI 创建逻辑
- [ ] 更新测试

### 验收标准
- `LLMStrategy` 不直接依赖具体数据源
- 可通过 mock 数据源测试

---

## 依赖关系
```
Issue 5 → Issue 1
Issue 3 → Issue 6
```

## 建议实施顺序
1. Issue 5 (PatternDetector) - 基础改进
2. Issue 1 (CaiSenStrategy) - 依赖 Issue 5
3. Issue 2 (Metrics) - 独立改进
4. Issue 3 (Annotation) - 结构改进
5. Issue 4 (LLM Provider) - 接口改进
6. Issue 7 (LLMStrategy DI) - 依赖 Issue 4
7. Issue 6 (Frontend) - 独立改进
