# Architecture Issue: DataConfig 类重复定义

## Priority
**Warning** - 代码混乱

## Status
**Resolved** - 2026-05-18

## Problem
存在两个不同的 `DataConfig` 类：
- `src/caisen/core/config.py` - 回测配置
- `src/caisen/data/config.py` - 数据加载配置

## Solution
将 `caisen/core/config.py` 中的 `DataConfig` 重命名为 `RunDataConfig`，避免命名冲突。

## Changes
- `src/caisen/core/config.py` - `DataConfig` → `RunDataConfig`
- `tests/test_config.py` - 更新导入

## Acceptance Criteria
- [x] 配置类命名清晰无歧义
- [x] 类型注解正确
- [x] 测试通过