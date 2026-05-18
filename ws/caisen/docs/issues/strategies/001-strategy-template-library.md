# Strategy Issue: 策略模板库不完整

## Priority
**Critical** - Strategy generation 基础缺失

## Problem
当前只有 MA Cross 示例策略，缺少其他常见策略模板：
- ❌ Mean reversion (RSI, Bollinger Bands)
- ❌ Breakout strategy
- ❌ Risk management (stop-loss, position sizing)

## Impact
- LLM 策略生成缺乏参考模板
- 无法组合不同类型策略
- 回测对比受限

## Reference
- **Architecture Review**: 2026-05-15
- **Related Code**: `src/caisen/strategy/`, `examples/`

## Recommended Fix
创建策略模板目录：

```
src/caisen/strategy/templates/
├── trend/
│   ├── ma_cross.py
│   └── breakout.py
├── mean_reversion/
│   ├── rsi.py
│   └── bollinger_bands.py
└── risk/
    ├── stop_loss.py
    └── position_sizing.py
```

每个模板应包含：
- 清晰的参数定义
- 注释说明买卖逻辑
- 示例配置

## Acceptance Criteria
- [ ] 至少 5 个策略模板
- [ ] 每类策略至少 1 个模板
- [ ] 模板可参数化配置
- [ ] 模板附带文档注释