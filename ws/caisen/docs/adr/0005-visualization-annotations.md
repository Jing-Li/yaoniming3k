# 可视化标注与报告方案

> **状态更新 (2026-05-18)**:
> 已部分实现。使用纯 HTML + ECharts 替代 Plotly，生成交互式 K 线图。
> 完整报告功能待 CLI 集成。

LLM 策略返回可视化标注（Annotation），与回测结果一起持久化，通过 HTML 生成可视化报告。

**为什么**：用户希望看到策略在 K 线图上的分析结果（支撑线、趋势线、买卖点等），便于理解 LLM 的决策逻辑。

**存储**：`runs/{run_id}/data.json`，包含标注类型、位置、颜色等信息。

**渲染**：`src/caisen/visualization/index.html` 使用 ECharts 生成交互式 K 线图，叠加 Annotation。
- buy_signal: 绿色向上三角
- sell_signal: 红色向下三角
- pattern_mark: 形态连线（头肩底、W 底等）

**报告**：`data.json` 格式（见 ADR-0007），前端渲染器独立。

**替代方案考虑**：
- Plotly — 文件过大（1-5MB），改用纯 HTML + ECharts
- PDF 报告 — 不支持交互，图表效果差

**后果**：前后端分离；Annotation 格式需与 LLM 返回格式保持一致（见 ADR-0007）。

**待实现**：
- [ ] CLI 集成：生成 report 目录和 data.json