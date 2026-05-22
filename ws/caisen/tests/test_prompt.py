"""测试 Prompt 输出"""

import json
from datetime import datetime

from caisen.strategy.llm.prompt import PromptBuilder
from caisen.strategy.llm.prompts.default import (
    SYSTEM_PROMPT,
    RULES_FRAMEWORK,
    OUTPUT_FORMAT,
)


# 测试 K 线数据
test_bars = [
    {"timestamp": "2024-01-01", "open": 100, "high": 105, "low": 99, "close": 103, "volume": 1000},
    {"timestamp": "2024-01-02", "open": 103, "high": 108, "low": 102, "close": 106, "volume": 1200},
    {"timestamp": "2024-01-03", "open": 106, "high": 110, "low": 104, "close": 108, "volume": 1500},
    {"timestamp": "2024-01-04", "open": 108, "high": 112, "low": 106, "close": 110, "volume": 1800},
    {"timestamp": "2024-01-05", "open": 110, "high": 108, "low": 100, "close": 102, "volume": 2000},
]


def test_default_prompt():
    """测试默认 Prompt"""
    builder = PromptBuilder()
    prompt = builder.build(test_bars)

    print("=" * 80)
    print("DEFAULT PROMPT OUTPUT")
    print("=" * 80)
    print(prompt)
    print("=" * 80)
    print(f"\nPrompt 长度: {len(prompt)} 字符")


def test_custom_rules():
    """测试自定义规则"""
    custom_rules = """## 自定义规则

### 均线策略
- MA20 > MA60 时做多
- MA20 < MA60 时做空

### 止损
- 亏损 2% 止损
"""
    builder = PromptBuilder(rules=custom_rules)
    prompt = builder.build(test_bars)

    print("\n" + "=" * 80)
    print("CUSTOM RULES PROMPT")
    print("=" * 80)
    print(prompt)
    print("=" * 80)


def test_with_examples():
    """测试 Few-shot 示例"""
    # 添加一个示例
    example_bars = [
        {"timestamp": "2024-12-25", "open": 95, "high": 98, "low": 94, "close": 97, "volume": 800},
        {"timestamp": "2024-12-26", "open": 97, "high": 103, "low": 96, "close": 102, "volume": 1500},
    ]
    example_signals = [
        {"timestamp": "2024-12-26", "action": "buy", "confidence": 0.85, "reason": "放量突破阻力位"}
    ]
    example_annotations = [
        {"timestamp": "2024-12-26", "type": "buy_signal", "data": {"price": 102, "label": "买入"}}
    ]

    builder = PromptBuilder(examples_count=1)
    builder.add_example(example_bars, example_signals, example_annotations)
    prompt = builder.build(test_bars)

    print("\n" + "=" * 80)
    print("FEW-SHOT EXAMPLES PROMPT")
    print("=" * 80)
    print(prompt)
    print("=" * 80)


def test_template_separation():
    """测试模板与逻辑分离"""
    print("\n" + "=" * 80)
    print("TEMPLATE SEPARATION TEST")
    print("=" * 80)

    print("\n【SYSTEM_PROMPT】")
    print(SYSTEM_PROMPT)

    print("\n【RULES_FRAMEWORK】")
    print(RULES_FRAMEWORK[:500] + "...")

    print("\n【OUTPUT_FORMAT】")
    print(OUTPUT_FORMAT[:500] + "...")

    # 验证可以独立修改模板
    print("\n【验证模板可独立修改】")
    from caisen.strategy.llm.prompts.default import PromptTemplate, get_prompt_template

    template = get_prompt_template(system_prompt="自定义系统提示")
    print(f"自定义 system_prompt: {template.system_prompt}")
    print(f"默认 rules: {template.rules[:100]}...")


if __name__ == "__main__":
    test_default_prompt()
    test_custom_rules()
    test_with_examples()
    test_template_separation()

    print("\n✅ 所有测试完成")