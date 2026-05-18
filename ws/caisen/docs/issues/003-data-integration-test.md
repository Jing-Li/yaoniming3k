# Architecture Issue: Data 模块集成测试

## Priority
**Warning** - 缺少关键测试覆盖

## Problem
缺少 data 模块端到端集成测试

## Impact
- 无法验证 DataConfig → LocalDataLoader → List[Bar] 完整流程
- 数据加载错误无法提前发现

## Reference
- **Architecture Review**: 2026-05-15
- **Related Code**: `src/caisen/data/`

## Recommended Fix
添加端到端集成测试

## Acceptance Criteria
- [ ] 测试完整数据加载流程
- [ ] 测试通过