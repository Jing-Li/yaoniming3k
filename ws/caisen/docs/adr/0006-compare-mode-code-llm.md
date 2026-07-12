# ADR-0006: 对比模式与代码/LLM 双实现

## Status
Partially Implemented

策略支持代码模式（CaiSenStrategy）和 LLM 模式（LLMStrategy / 智能蔡森策略）两种实现。

**为什么**：用户希望验证同一交易逻辑在代码实现和大模型实现下的表现差异，评估 LLM 的决策质量。

**已实现**：
- CaiSenStrategy（代码策略）和 LLMStrategy（智能蔡森策略）各自独立运行
- `scripts/compare_strategies.py` 脚本可一键对比多套配置的绩效指标
- 各策略回测结果独立持久化到 `runs/` 目录

**未实现**：
- [ ] CLI `compare` 子命令（对比功能在独立脚本中，非 CLI 子命令）
- [ ] `modes` 配置（`[code]`、`[llm]`、`[code, llm]`）
- [ ] 双结果对比视图（前端）
- [ ] 净值曲线叠加图

**替代方案考虑**：
- 策略内双实现 — 同一类包含 code 和 llm 两个方法，增加耦合
- 自动选择 — 根据配置自动选择模式，不支持对比

**后果**：需要两份数据存储（code 和 llm 的结果）；对比命令会增加回测时间。