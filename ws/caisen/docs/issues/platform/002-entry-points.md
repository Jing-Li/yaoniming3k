# Architecture Issue: Entry Points 配置

## Priority
**Critical** - 插件系统核心功能缺失

## Problem
ADR-0001 和 ADR-0007 规划了 `caisen.datasources` 插件机制，但未配置 entry_points

## Impact
- ADR 承诺的插件架构无法落地
- 外部数据源必须硬编码注册

## Reference
- **Architecture Review**: 2026-05-15
- **Related ADR**: ADR-0001, ADR-0007

## Recommended Fix
在 `pyproject.toml` 中添加 entry_points 配置

## Acceptance Criteria
- [ ] pyproject.toml 配置了 entry_points
- [ ] 测试通过