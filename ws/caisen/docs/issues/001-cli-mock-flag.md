# Architecture Issue: CLI Mock Flag

## Priority
**Critical** - Blocks developer productivity

## Problem
当数据文件不存在时，CLI 直接退出错误，但 `--mock` 标志未实现

## Impact
- 开发者需要先准备数据文件才能运行测试
- 无法在没有真实数据的 CI 环境中运行

## Reference
- **Architecture Review**: 2026-05-15
- **Related Code**: `src/caisen/cli/main.py`

## Recommended Fix
在 CLI 的 `run` 命令中添加 `--mock` 标志

## Acceptance Criteria
- [ ] `--mock` 标志可以生成模拟数据
- [ ] 测试通过