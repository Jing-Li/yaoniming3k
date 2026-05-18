# Architecture Issue: supported_freqs 改为类常量

## Priority
**Warning** - 轻微性能问题

## Problem
`DataConfig.supported_freqs` 使用 `@property` 但行为是静态的，每次实例化创建新 tuple

## Impact
- 轻微的内存开销
- 代码语义不清晰

## Reference
- **Architecture Review**: 2026-05-15
- **Related Code**: `src/caisen/data/config.py`

## Recommended Fix
改为类常量 `SUPPORTED_FREQS`

## Acceptance Criteria
- [ ] `SUPPORTED_FREQS` 改为类常量
- [ ] 测试通过