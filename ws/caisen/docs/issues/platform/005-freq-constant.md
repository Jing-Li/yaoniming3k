# Architecture Issue: supported_freqs 改为类常量

## Priority
**Warning** - 轻微性能问题

## Status
**Resolved** - 2026-05-18

## Problem
`DataConfig.supported_freqs` 使用 `@property` 但行为是静态的，每次实例化创建新 tuple

## Solution
改为模块级常量 `SUPPORTED_FREQS`

## Changes
- `src/caisen/data/config.py` - 移除了 `@property`，改用模块级常量

## Acceptance Criteria
- [x] `SUPPORTED_FREQS` 改为类常量
- [x] 测试通过