# Architecture Issue: LocalDataLoader 单元测试

## Priority
**Warning** - 缺少私有方法测试

## Problem
`LocalDataLoader` 的 `_get_files_for_range()` 和 `_dataframe_to_bars()` 没有单元测试

## Impact
- 无法验证边界情况处理
- 重构时可能破坏内部逻辑

## Reference
- **Architecture Review**: 2026-05-15
- **Related Code**: `src/caisen/data/local.py`

## Recommended Fix
添加单元测试

## Acceptance Criteria
- [ ] 测试 `_get_files_for_range()` 边界情况
- [ ] 测试 `_dataframe_to_bars()` 转换正确性
- [ ] 测试通过