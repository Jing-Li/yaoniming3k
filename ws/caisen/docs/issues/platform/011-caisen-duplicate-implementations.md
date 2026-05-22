# 011-caisen-duplicate-implementations.md

## Status: triaged

## Priority: critical

## Labels: architecture, strategy, needs-decision

---

# Architecture Issue: CaiSenStrategy 双实现问题

## Summary

项目存在两个 CaiSenStrategy 实现（`cai_sen.py` ~1781 行和 `cai_sen_v2.py` ~393 行），且没有明确规范说明哪个是规范实现。这导致：
- 代码维护成本加倍
- 测试覆盖不完整（v2 无测试）
- 文档与实现不一致
- 用户困惑

## Current State

### 导入关系

```
cai_sen.py (单体式)                    cai_sen_v2.py (模块化)
      │                                      │
      ├── tests/test_cai_sen.py              │
      ├── examples/*.py                      ├── cli/main.py (config 加载)
      ├── README.md                          ├── caisen_optimizer.py
      └── strategy/__init__.py → 主导出      └── strategy/__init__.py → CaiSenStrategyV2
```

### 使用统计

| 组件 | 使用版本 | 状态 |
|------|----------|------|
| CLI (config 加载) | v2 | ✅ |
| Optimizer | v2 | ✅ |
| Tests | v1 | ⚠️ 无 v2 测试 |
| Examples | v1 | ⚠️ 未更新 |
| Documentation | v1 | ⚠️ 未更新 |
| `__init__.py` 主导出 | v1 | ⚠️ 顺序错误 |

## Root Cause

1. **渐进式重构未完成**：先创建 v2，但未完成迁移
2. **缺少架构决策记录**：没有 ADR 说明哪个是规范
3. **测试未同步迁移**：只迁移了 CLI/optimizer，未迁移测试

## Impact

- **维护成本**：需要同时维护两套实现
- **测试风险**：v2 无测试覆盖
- **用户困惑**：文档与实际使用不一致
- **技术债务**：问题随时间加重

## Options

### Option A: 完成迁移（推荐）

**Steps**:
1. 创建 ADR-0010 记录决策
2. 迁移测试到 v2
3. 更新所有文档和示例
4. 删除 cai_sen.py
5. 重命名 v2 为正式版本

**Pros**:
- 消除歧义
- 统一代码库
- 更好的可维护性

**Cons**:
- 需要迁移工作
- 需要回归测试

### Option B: 保留双版本（保守）

**Steps**:
1. 在 `__init__.py` 添加明确注释
2. 文档说明使用场景
3. 接受技术债务

**Pros**:
- 降低迁移风险
- 允许并行实验

**Cons**:
- 技术债务持续
- 维护成本加倍

## Decision Required

需要明确：
1. 哪个版本是规范实现？
2. 迁移时间线是什么？
3. 是否需要 ADR 记录？

## Related Issues

- #001: ADR pending (docs/issues/platform/009-adrs-pending.md)
- #010: CLI strategy loading (docs/issues/platform/010-cli-strategy-loading.md)

## Created

2026-05-22

## Assigned

-