# Architecture Issue: CLI 策略加载硬编码（已解决）

## Priority
**Suggestion** - 灵活性不足

## Problem
CLI 中的策略加载逻辑曾硬编码 fallback 到 examples 目录：

```python
# cli/main.py (旧代码，已重构)
try:
    from examples.xxx import SomeStrategy
    strat = SomeStrategy()
except ImportError:
    ...
```

## Resolution
已重构为通过 `StrategyRegistry` 动态查找策略模块路径，不再硬编码具体策略名。

## Impact
- 策略发现机制不灵活
- 无法动态发现策略目录
- 与 ADR-0003 的 Strategy Plugin 概念不一致

## Reference
- **Architecture Review**: 2026-05-18
- **Related Code**: `src/caisen/cli/main.py`
- **Related ADR**: ADR-0003

## Recommended Fix
实现策略发现机制：
1. 扫描 `strategies/` 目录
2. 注册到 Strategy Registry
3. CLI 支持 `--list-strategies` 选项

## Acceptance Criteria
- [ ] 支持策略目录扫描
- [ ] CLI `--list-strategies` 列出可用策略
- [ ] 测试通过