# 可视化标注与报告方案

LLM 策略返回可视化标注（Annotation），与回测结果一起持久化，通过 Plotly 生成 HTML 报告。

**为什么**：用户希望看到策略在 K 线图上的分析结果（支撑线、趋势线、买卖点等），便于理解 LLM 的决策逻辑。

**存储**：`runs/{run_id}/annotations.json`，包含标注类型、位置、颜色等信息。

**渲染**：`caisen show-result --chart <run_id>` 使用 Plotly 生成交互式 K 线图，叠加 Annotation。

**报告**：回测完成后可选自动生成 HTML 报告，包含摘要、净值曲线、交易记录、K 线图+标注。

**替代方案考虑**：
- PDF 报告 — 不支持交互，图表效果差
- 实时预览 — 增加复杂度，第一版不需要

**后果**：依赖 Plotly；Annotation 格式需与 LLM 返回格式保持一致。