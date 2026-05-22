"""快速测试 LLM 策略"""

import json
from datetime import datetime

from caisen.core.bar import Bar
from caisen.strategy.llm import OpenAIProvider, LLMStrategy, PromptBuilder, ResponseParser


def test_local_llm():
    """测试本地 LLM 服务"""

    # 测试数据（模拟几根 K 线）
    bars = [
        {"timestamp": "2024-01-01", "open": 100, "high": 105, "low": 99, "close": 103, "volume": 1000},
        {"timestamp": "2024-01-02", "open": 103, "high": 108, "low": 102, "close": 106, "volume": 1100},
        {"timestamp": "2024-01-03", "open": 106, "high": 110, "low": 105, "close": 108, "volume": 1200},
    ]

    print("=" * 50)
    print("LLM 策略测试")
    print("=" * 50)

    # 1. 测试 OpenAIProvider
    print("\n[1] 测试 OpenAIProvider (本地端点)...")

    # 使用服务器上可用的模型
    client = OpenAIProvider(
        api_key="dummy",
        model="taiji",  # 可用模型: taiji, taiji-gemini, taiji-model
        base_url="http://localhost:8080/v1"
    )

    print(f"   端点: {client.base_url}")
    print(f"   模型: {client.model}")

    # 2. 测试 Prompt 构建
    print("\n[2] 测试 Prompt 构建...")

    prompt_builder = PromptBuilder(rules="支撑位买入，阻力位卖出")
    prompt = prompt_builder.build(bars)

    print(f"   Prompt 长度: {len(prompt)} 字符")
    print(f"   包含 K 线: {'2024-01-01' in prompt}")

    # 3. 测试 LLM 调用
    print("\n[3] 测试 LLM 调用...")

    try:
        response = client.call(prompt)
        print(f"   响应长度: {len(response)} 字符")
        print(f"   响应预览: {response[:200]}...")
    except Exception as e:
        print(f"   ❌ 调用失败: {e}")
        return

    # 4. 测试响应解析
    print("\n[4] 测试响应解析...")

    try:
        parser = ResponseParser()
        result = parser.parse(response)
        print(f"   Signals: {len(result.signals)}")
        print(f"   Annotations: {len(result.annotations)}")
        if result.signals:
            print(f"   第一个信号: {result.signals[0]}")
    except Exception as e:
        print(f"   ❌ 解析失败: {e}")
        print(f"   原始响应: {response}")

    # 5. 测试完整策略流程
    print("\n[5] 测试完整策略流程...")

    strategy = LLMStrategy(
        llm_client=client,
        prompt_builder=prompt_builder,
        response_parser=parser
    )

    # 模拟 on_init
    strategy.cache.index_signals(result.signals)
    strategy.cache.set_annotations(result.annotations)

    # 模拟 on_bar
    test_bar = Bar(
        timestamp=datetime(2024, 1, 2),
        symbol="ag",
        open=103,
        high=108,
        low=102,
        close=106
    )

    order = strategy.on_bar(test_bar)

    if order:
        print(f"   订单: {order.side.value} {order.symbol}")
    else:
        print("   无订单 (hold 或状态不匹配)")

    print("\n" + "=" * 50)
    print("测试完成!")
    print("=" * 50)


if __name__ == "__main__":
    test_local_llm()