# Architecture Issue: CLI Mock Flag

## Priority
**Critical** - Blocks developer productivity

## Status
**Resolved** - 2026-05-18

## Problem
当数据文件不存在时，CLI 直接退出错误，但 `--mock` 标志未实现

## Solution
在 CLI 的 `run` 命令中添加 `--mock` 标志

## Changes
- `src/caisen/cli/main.py` - 添加 `--mock` 选项，使用 `generate_mock_bars()` 生成模拟数据

## Acceptance Criteria
- [x] `--mock` 标志可以生成模拟数据
- [x] 测试通过