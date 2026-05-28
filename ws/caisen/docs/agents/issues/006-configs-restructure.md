# configs 目录重组：策略 YAML 迁移

- **ID**: 006
- **标签**: enhancement, closed
- **优先级**: MEDIUM
- **状态**: closed (2026-05-26)

## Parent

[#004 PRD: 前端触发回测 + 项目全局配置](004-frontend-backtest-trigger.md)

## What to build

将现有 `configs/` 目录下 7 个策略配置 YAML 文件移动到 `configs/strategies/` 子目录，与新建的 `configs/project.yaml`（由 #005 创建）区分清晰。

同步更新所有引用这些策略 YAML 路径的代码、文档、README，确保没有悬挂引用。

## Acceptance criteria

- [x] `configs/strategies/` 目录存在，包含原 7 个策略 YAML 文件
- [x] `configs/` 根目录下不再有策略 YAML 文件（仅保留 `project.yaml`）
- [x] CLI `caisen run --strategy-config` 使用新路径示例运行正常（Python 代码无硬编码策略 YAML 路径）
- [x] CONTEXT.md 目录树描述已更新为 `configs/strategies/`
- [x] 现有测试全部通过（265 passed，3 个预存失败与本次无关）

## Blocked by

- [#005 ProjectConfig：全局配置加载模块](005-project-config.md)
