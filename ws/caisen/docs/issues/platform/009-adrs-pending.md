# Architecture Issue: ADR-0005/0006 状态更新

## Priority
**Warning** - ADR 承诺未兑现

## Status
**Resolved** - 2026-05-18

## Problem
ADR 定义的功能尚未实现：
- **ADR-0005**: Plotly 可视化标注
- **ADR-0006**: Compare Mode (代码/LLM 策略对比)

## Solution
1. **ADR-0005**: 更新为已部分实现，使用 ECharts 替代 Plotly
2. **ADR-0006**: 更新为已延期，等待核心功能完善

## Changes
- `docs/adr/0005-visualization-annotations.md` - 添加状态更新
- `docs/adr/0006-compare-mode-code-llm.md` - 添加延期标记

## Acceptance Criteria
- [x] 明确 ADR-0005/0006 的状态
- [x] ADR-0007 可视化报告架构已创建
- [x] Compare Mode 延期