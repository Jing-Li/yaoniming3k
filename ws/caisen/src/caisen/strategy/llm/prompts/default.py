"""默认 Prompt 模板

分离 Prompt 内容与代码逻辑，便于微调。
"""

# =============================================================================
# 系统提示
# =============================================================================

SYSTEM_PROMPT = """你是一个专业的量化交易策略分析师。根据 K 线数据分析并输出交易信号和可视化标注。"""


# =============================================================================
# 交易规则框架
# =============================================================================

RULES_FRAMEWORK = """## 交易规则

### 买入信号
- 支撑位反弹：价格触及历史支撑位后放量反弹
- 趋势确认：上升趋势中回调至均线支撑后继续上涨
- 形态突破：关键形态（如 W 底、三角形）向上突破

### 卖出信号
- 阻力位滞涨：价格触及历史阻力位后无力突破
- 趋势反转：下降趋势中反弹至均线阻力后继续下跌
- 形态破位：关键形态向下破位

### 持仓条件
- 买入后持有至出现明确卖出信号
- 不频繁交易，避免过度买卖"""


# =============================================================================
# 输出格式说明
# =============================================================================

OUTPUT_FORMAT = """## 输出格式要求

输出 **严格 JSON 格式**，不要包含任何额外文本。

```json
{
  "signals": [
    {
      "timestamp": "YYYY-MM-DD",
      "action": "buy|sell|hold",
      "confidence": 0.0-1.0,
      "reason": "信号理由简述"
    }
  ],
  "annotations": [
    {
      "timestamp": "YYYY-MM-DD",
      "type": "buy_signal|sell_signal|pattern_mark|horizontal_line|trend_line",
      "data": {
        "price": 1234.56,
        "label": "显示标签",
        "description": "详细描述"
      }
    }
  ]
}
```

### 规则
- signals: 每个有信号的时间点都要记录，无信号时用 hold
- annotations: 标注关键形态、支撑阻力位
- confidence: 置信度 0.0-1.0，1.0 表示高确定性"""


# =============================================================================
# Few-shot 示例模板
# =============================================================================

EXAMPLES_TEMPLATE = """## 示例

### 示例 1：趋势确认买入
**K线数据**:
[{"timestamp": "2024-01-01", "open": 100, "high": 105, "low": 99, "close": 103, "volume": 1000}, ...]

**输出**:
```json
{
  "signals": [
    {"timestamp": "2024-01-01", "action": "buy", "confidence": 0.85, "reason": "支撑位反弹放量"}
  ],
  "annotations": [
    {"timestamp": "2024-01-01", "type": "buy_signal", "data": {"price": 103, "label": "买入", "description": "支撑位反弹"}}
  ]
}
```
"""


# =============================================================================
# PromptTemplate 类
# =============================================================================

class PromptTemplate:
    """可组合的 Prompt 模板"""

    def __init__(
        self,
        system_prompt: str = SYSTEM_PROMPT,
        rules: str = RULES_FRAMEWORK,
        output_format: str = OUTPUT_FORMAT,
        examples: str = EXAMPLES_TEMPLATE,
    ):
        self.system_prompt = system_prompt
        self.rules = rules
        self.output_format = output_format
        self.examples = examples

    def build(self) -> str:
        """构建完整的系统提示"""
        parts = [
            self.system_prompt,
            self.rules,
            self.examples,
            self.output_format,
        ]
        return "\n\n".join(filter(None, parts))

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "system_prompt": self.system_prompt,
            "rules": self.rules,
            "output_format": self.output_format,
            "examples": self.examples,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PromptTemplate":
        """从字典创建"""
        return cls(
            system_prompt=data.get("system_prompt", SYSTEM_PROMPT),
            rules=data.get("rules", RULES_FRAMEWORK),
            output_format=data.get("output_format", OUTPUT_FORMAT),
            examples=data.get("examples", EXAMPLES_TEMPLATE),
        )


def get_prompt_template(**kwargs) -> PromptTemplate:
    """获取 Prompt 模板实例"""
    return PromptTemplate(**kwargs)


# =============================================================================
# 默认模板实例
# =============================================================================

DEFAULT_TEMPLATE = PromptTemplate()