# ADR-0020: 网格智能蔡森参数法

## Status
Accepted (规划中，未实现)

## Context

现有网格暴力参数法（Grid Search）存在以下问题：

1. **暴力穷举**：2160 组参数笛卡尔积，大量计算浪费在明显不合理的参数组合上
2. **参数值人为设定**：网格的离散值由人工硬编码，缺乏理论依据
3. **无学习能力**：每轮回测独立，不利用历史结果反馈
4. **计算成本高**：2160 次全量回测，单线程耗时数小时

蔡森理论本身蕴含丰富的参数推理知识（止损原则、量价关系、形态可靠性），LLM 可以理解这些理论并直接推理出合理的参数值，结合回测反馈进行迭代优化。

### 替代方案

1. **保留网格暴力参数法**（ADR-0019 原计划用 Optuna TPE）：纯数学优化，不理解交易理论
2. **网格智能蔡森参数法**：LLM 理解蔡森理论，智能推理参数 + 反馈迭代
3. **遗传算法**：实现复杂，收益有限

## Decision

采用方案 2：网格智能蔡森参数法，与网格暴力参数法互补。

### 1. 三条优化路径

| 方案 | 命名 | 策略 | 优化方式 | 状态 |
|------|------|------|---------|------|
| A | 蔡森策略 + 网格暴力参数法 | CaiSenStrategy | Grid Search | 已实现 |
| B | 蔡森策略 + **网格智能蔡森参数法** | CaiSenStrategy | LLM Param Optimizer | 规划中 |
| C | 智能蔡森策略 | LLMStrategy | Prompt Evolution | 已实现 |

A 和 B 共享 CaiSenStrategy 形态检测代码，只是参数寻找方式不同。C 是纯 LLM 驱动，不使用蔡森检测器。

### 2. 迭代闭环

```
Round 1: LLM 根据蔡森理论 + 参数 Schema + 品种特征 → 提出初始参数
         → 回测 → 得到指标 → 评分

Round N: LLM 看到历史（参数 + 指标 + 评分）→ 分析原因 → 提出调整参数
         → 回测 → 评分

收敛: 达到 max_rounds 或目标评分或连续 3 轮无改善 → 输出最优参数
```

### 3. 参数 Schema（8 个可调维度）

| 参数 | 类型 | 范围 | 含义 |
|------|------|------|------|
| stop_loss_factor | float | [0.90, 0.99] | 止损因子 |
| min_profit_pct | float | [0.01, 0.10] | 最小止盈比例 |
| trailing_stop_pct | float | [0.02, 0.10] | 追踪止损幅度 |
| platform_min_bars | int | [5, 20] | 整理平台最少 K 线数 |
| volume_threshold | float | [1.0, 3.0] | 成交量放大倍数 |
| enabled_patterns | list | 12 种形态 | 启用的形态检测器 |
| first_position_pct | float | [0.10, 0.50] | 首次建仓比例 |
| second_position_pct | float | [0.20, 0.70] | 加仓比例 |

### 4. LLM 交互协议

- **系统 Prompt**：注入蔡森理论核心知识（量价结构、形态优先、止损第一、趋势为王）
- **参数 Schema**：告诉 LLM 可调的旋钮及其范围和含义
- **反馈 Prompt**：每轮回测后发送完整指标 + 历史对比，LLM 输出调整参数 + reasoning
- **输出格式**：结构化 JSON（params + reasoning + changes_from_last）

### 5. 收敛策略

停止条件（满足任一即停）：
1. 达到 max_rounds（默认 10）
2. 评分 >= target_score
3. 连续 3 轮无改善

评分公式（与网格暴力参数法一致）：
```
score = 收益×0.4 + |回撤|×0.2 + 夏普×0.2 + 胜率×0.2
```

### 6. CLI 命令

```bash
caisen llm-optimize --symbol ag --freq 60m --llm-config configs/strategies/config_llm_local.yaml --rounds 10
```

输出：`configs/strategies/caisen_llm_optimized.yaml`

### 7. 与网格暴力参数法的关系

- 网格暴力参数法保留，作为"精细调参"工具
- 网格智能蔡森参数法作为"智能搜索"主入口
- 两者互补：LLM 先找方向，Grid Search 可小范围微调

## Consequences

### Positive
- LLM 理解蔡森理论，参数推理有理论支撑
- 10~20 轮收敛 vs 2160 次盲搜，计算成本大幅降低
- 每轮有 reasoning 输出，参数选择可解释
- 反馈闭环实现自适应学习

### Negative
- 非确定性结果（LLM 每次输出可能不同）
- 依赖 LLM 服务可用性
- 需要验证 LLM 输出参数的合法性

## References
- ADR-0004: LLM 策略架构（智能蔡森策略）
- ADR-0011: CaiSenStrategy 组件拆分
- ADR-0017: 四因子置信度模型
- ADR-0019: 自适应参数优化引擎（已 Superseded）
