"""测试 LLM Strategy"""

import json
from datetime import datetime
from caisen.core.bar import Bar
from caisen.core.order import Order, Side
from caisen.core.config import BacktestConfig
from caisen.llm.provider import LLMProvider
from caisen.llm.openai import OpenAIProvider
from caisen.strategy.llm_strategy import LLMStrategy


class MockProvider(LLMProvider):
    """模拟 LLM Provider"""

    def __init__(self, responses=None):
        self.responses = responses or []
        self.call_count = 0

    def call(self, prompt: str) -> str:
        if self.responses:
            response = self.responses[self.call_count % len(self.responses)]
            self.call_count += 1
            return response
        return json.dumps({"action": "HOLD", "reason": "mock", "annotations": []})

    def parse_response(self, response: str):
        return json.loads(response)


def test_llm_strategy_generates_order():
    """LLM 返回 BUY 时生成买入订单"""
    provider = MockProvider([
        json.dumps({"action": "BUY", "reason": "测试买入", "annotations": []})
    ])
    strategy = LLMStrategy(
        prompt_template="分析 {bars}",
        provider=provider
    )

    bar = Bar(timestamp=datetime(2024, 1, 1), symbol="TEST", open=100, high=105, low=95, close=102, volume=1000)
    order = strategy.on_bar(bar)

    assert order is not None
    assert order.side == Side.BUY


def test_llm_strategy_generates_sell_order():
    """LLM 返回 SELL 时生成卖出订单"""
    provider = MockProvider([
        json.dumps({"action": "SELL", "reason": "测试卖出", "annotations": []})
    ])
    strategy = LLMStrategy(
        prompt_template="分析 {bars}",
        provider=provider
    )

    bar = Bar(timestamp=datetime(2024, 1, 1), symbol="TEST", open=100, high=105, low=95, close=102, volume=1000)
    order = strategy.on_bar(bar)

    assert order is not None
    assert order.side == Side.SELL


def test_llm_strategy_hold_returns_none():
    """LLM 返回 HOLD 时返回 None"""
    provider = MockProvider([
        json.dumps({"action": "HOLD", "reason": "等待信号", "annotations": []})
    ])
    strategy = LLMStrategy(
        prompt_template="分析 {bars}",
        provider=provider
    )

    bar = Bar(timestamp=datetime(2024, 1, 1), symbol="TEST", open=100, high=105, low=95, close=102, volume=1000)
    order = strategy.on_bar(bar)

    assert order is None


def test_llm_strategy_caches_responses():
    """相同 bar 不重复调用 LLM"""
    provider = MockProvider([
        json.dumps({"action": "BUY", "reason": "信号", "annotations": []})
    ])
    strategy = LLMStrategy(
        prompt_template="分析 {bars}",
        provider=provider,
        cache_enabled=True
    )

    bar = Bar(timestamp=datetime(2024, 1, 1), symbol="TEST", open=100, high=105, low=95, close=102, volume=1000)

    # 多次调用相同 bar
    strategy.on_bar(bar)
    strategy.on_bar(bar)
    strategy.on_bar(bar)

    # 应该只调用一次
    assert provider.call_count == 1


def test_llm_strategy_collects_annotations():
    """收集可视化标注"""
    provider = MockProvider([
        json.dumps({
            "action": "BUY",
            "reason": "买入",
            "annotations": [
                {"type": "line", "points": [[0, 100], [10, 110]], "label": "支撑线", "color": "blue"}
            ]
        })
    ])
    strategy = LLMStrategy(
        prompt_template="分析 {bars}",
        provider=provider
    )

    bar = Bar(timestamp=datetime(2024, 1, 1), symbol="TEST", open=100, high=105, low=95, close=102, volume=1000)
    strategy.on_bar(bar)

    annotations = strategy.get_annotations()
    assert len(annotations) == 1
    assert annotations[0].type == "line"
    assert annotations[0].label == "支撑线"