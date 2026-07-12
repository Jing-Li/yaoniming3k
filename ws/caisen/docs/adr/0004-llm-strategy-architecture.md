# LLM 策略架构

LLM 策略（LLMStrategy，即智能蔡森策略）通过大语言模型驱动交易决策。采用**离线预计算 + 信号回放**架构：`on_init` 阶段一次性调用 LLM 分析完整历史数据，`on_bar` 阶段逐帧回放缓存信号，避免逐 bar 调用 LLM 的高延迟。

**为什么**：将 LLM 引入回测，让用户通过 Prompt 描述交易逻辑，实现策略与执行的解耦。

**架构**：
- `on_init`：构建 Prompt → 调用 LLM → 解析信号 → 缓存到 dict
- `on_bar`：根据当前 bar.timestamp 查缓存 → 回放信号 → 生成 BarResult
- 支持 Walk-Forward 递增窗口模式（ADR-0020）

**替代方案考虑**：
- 滑动窗口输入 — LLM 足够智能，自主从完整历史数据中提取相关信息
- 固定交易点 — LLM 可能在多根 K 线后给出决策，不限制为单点
- 逐 bar 实时调用 — LLM 调用成本过高，延迟不可接受

**后果**：LLM 调用成本较高，通过缓存机制优化；Annotation 数据需配套可视化工具渲染。

## Status: Accepted