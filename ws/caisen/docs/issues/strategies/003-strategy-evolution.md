# Strategy Issue: 策略进化逻辑未定义

## Priority
**Warning** - 自主 Agent 核心功能缺失

## Problem
策略进化循环缺少明确的进化策略定义：
- ❌ 如何选择进化方向？
- ❌ 如何判断进化成功/失败？
- ❌ 何时终止进化？

## Impact
- 无法实现基于回测结果的策略优化
- Agent 可能陷入局部最优
- 过度拟合风险

## Reference
- **Architecture Review**: 2026-05-15
- **Related ADR**: ADR-0004

## Recommended Fix
定义进化策略：

```python
class EvolutionStrategy:
    """策略进化策略"""

    def should_evolve(self, metrics: PerformanceMetrics) -> bool:
        """判断是否需要进化"""
        return (
            metrics.sharpe_ratio < 1.0 or
            metrics.max_drawdown > 0.2
        )

    def propose_mutations(self, strategy_code: str, metrics: PerformanceMetrics) -> List[str]:
        """提出变异方案"""
        mutations = []

        # 参数调优
        if "MA" in strategy_code:
            mutations.append("Increase MA period")

        # 指标替换
        if "RSI" in strategy_code:
            mutations.append("Replace RSI with MACD")

        # 添加风险管理
        if "stop_loss" not in strategy_code:
            mutations.append("Add stop-loss")

        return mutations

    def should_terminate(self, iteration: int, improvement: float) -> bool:
        """判断是否终止进化"""
        return (
            iteration >= 10 or  # 最大迭代次数
            improvement < 0.01   # 收益改善 < 1%
        )
```

## Acceptance Criteria
- [ ] 进化方向选择逻辑
- [ ] 进化成功/失败判断
- [ ] 终止条件定义
- [ ] 过度拟合检测