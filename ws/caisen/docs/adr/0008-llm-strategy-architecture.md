# ADR-0008: LLM 策略架构

## Status
Accepted

## Context

回测系统需要支持 LLM（大语言模型）驱动的策略，实现方式需满足：
- 遵循 `Strategy` 接口（`on_bar` 返回 `Optional[Order]`）
- 利用 LLM 的分析能力进行行情标注和信号生成
- 不改变引擎逻辑，策略内部完成 LLM → 引擎的适配

### 核心约束

1. **接口不变**：LLM 策略继承 `Strategy` 基类，`on_bar` 逐帧返回 Order
2. **引擎独立**：回测引擎逻辑保持不变，不感知 LLM 存在
3. **离线预计算**：历史数据一次性喂给 LLM，结果缓存后逐帧回放

### 技术背景

1. **实时 vs 离线**
   - 实时调用：每根 K 线调用一次 LLM，成本高
   - 离线预计算：一次性分析完整历史，回放执行
   - 选择：离线预计算（成本可控，结果可复现）

2. **输入设计**
   - 全量历史：最简单，2 年日线约 500 根
   - 滑动窗口：需要多次调用
   - 选择：全量历史一次性调用

3. **输出设计**
   - 仅 Order：丢失 LLM 的分析优势
   - Order + 标注分离：信号和标注解耦
   - 选择：分离设计（signals + annotations）

4. **Prompt 策略**
   - 规则外置 + Few-shot 示例：LLM 有方向但不僵化
   - 选择：轻量规则框架 + 2-3 个示例

## Decision

### 1. 架构设计

```
行情数据 → LLM一次性分析 → 返回结构化数据 → 缓存 → 逐帧回放给引擎
```

**核心原则**：
- LLM 负责分析和标注
- 策略负责缓存和回放
- 引擎只负责执行（不变）

### 2. 数据结构

#### Signals（信号）

```json
{
  "signals": [
    {
      "timestamp": "YYYY-MM-DD",
      "action": "buy" | "sell" | "hold",
      "confidence": 0.8,
      "reason": "突破颈线"
    }
  ]
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `timestamp` | string | 是 | 日期，格式 YYYY-MM-DD |
| `action` | string | 是 | buy/sell/hold |
| `confidence` | float | 否 | 置信度 0.0-1.0 |
| `reason` | string | 否 | 判断理由 |

#### Annotations（标注）

```json
{
  "annotations": [
    {
      "timestamp": "YYYY-MM-DD",
      "type": "buy_signal" | "sell_signal" | "pattern_mark" | "horizontal_line" | ...,
      "data": {}
    }
  ]
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `timestamp` | string | 是 | 日期 |
| `type` | string | 是 | AnnotationType 枚举值 |
| `data` | object | 是 | 类型相关数据 |

### 3. Prompt 设计

```
Prompt = 任务说明 + 数据格式 + 规则框架 + Few-shot 示例 + K线数据
```

- **任务说明**：你是一个量化交易策略分析师，根据 K 线数据输出交易信号和标注
- **数据格式**：K线包含 timestamp, open, high, low, close, volume
- **规则框架**：轻量级原则（如"支撑位买入、阻力位卖出"），不强制
- **Few-shot 示例**：2-3 个案例，展示期望的输出格式
- **K线数据**：实际行情数据

### 4. 解析与校验

1. **强约束 JSON**：Prompt 要求 LLM 只输出 JSON
2. **Schema 校验**：返回后用 JSON Schema 验证格式
3. **容错处理**：校验失败记录错误，继续回放（默认 hold）

### 5. 回放逻辑

```python
class LLMStrategy(Strategy):
    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.signals = {}      # timestamp -> signal
        self.annotations = []  # all annotations
        self.position = 0     # 0=空仓, 1=持仓

    def on_init(self, config):
        # 一次性获取所有数据
        bars = self.get_all_bars(config)
        result = self.llm_client.analyze(bars)
        self.signals = index_by_timestamp(result.signals)
        self.annotations = result.annotations

    def on_bar(self, bar) -> Optional[Order]:
        # 查缓存，无信号默认 hold
        signal = self.signals.get(bar.timestamp, default_hold)
        return signal_to_order(signal, bar.close)

    def get_annotations(self) -> List[Annotation]:
        return self.annotations
```

### 6. 模块划分

```
src/caisen/strategy/
├── base.py                 # Strategy 基类（已存在）
├── llm/
│   ├── __init__.py
│   ├── client.py           # LLMClient: 调用大模型，解析结果
│   ├── prompt.py           # PromptBuilder: 构建 Prompt
│   ├── cache.py            # SignalCache: 缓存和索引
│   └── strategy.py         # LLMStrategy: 策略实现
```

#### LLMStrategy

- 继承 `Strategy`
- 负责与引擎交互（`on_bar` 逐帧回放）
- 维护持仓状态

#### LLMClient

- 封装 LLM API 调用
- 处理错误和重试
- 返回结构化结果

#### PromptBuilder

- 构建 Prompt
- 管理规则框架和示例
- 验证数据格式

#### SignalCache

- 索引 signals（timestamp → signal）
- 管理 annotations
- 提供快速查找

### 7. 配置

```yaml
strategy:
  name: LLMStrategy
  llm:
    provider: openai  # openai / anthropic / 本地模型
    model: gpt-4o
    api_key: ${OPENAI_API_KEY}
  prompt:
    rules: "轻量规则..."  # 或配置文件路径
    examples: 3  # Few-shot 数量
  cache:
    enabled: true
    path: ./cache/{run_id}.json  # 缓存路径
```

## Consequences

### Positive

- 引擎逻辑完全不变，保持稳定性
- LLM 一次性调用，成本可控
- signals + annotations 分离，便于分析和可视化
- 模块化设计，便于替换 LLM provider

### Negative

- 离线预计算，无法实时调整
- LLM 输出格式可能不稳定，需要健壮的校验
- 缓存占用空间（但 JSON 体积小）

### Risks

- LLM 输出格式错误导致回放失败
- 长历史数据 token 消耗高
- 多 Bar 信号冲突（如连续 buy）

## References

- Strategy 基类: `src/caisen/strategy/base.py`
- Annotation 类型: `src/caisen/strategy/base.py`
- 回测引擎: `src/caisen/core/engine.py`