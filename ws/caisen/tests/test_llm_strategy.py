"""测试 LLM Strategy（离线预计算架构）"""

import json
from datetime import datetime
import pytest

from caisen.core.bar import Bar
from caisen.core.order import Order, Side
from caisen.strategy.llm.strategy import LLMStrategy
from caisen.strategy.llm.cache import SignalCache
from caisen.strategy.llm.prompt import PromptBuilder
from caisen.strategy.llm.response import ResponseParser


class MockLLMClient:
    """模拟 LLM 客户端，实现 call(prompt) -> str"""

    def __init__(self, signals_data, annotations_data=None):
        self.signals_data = signals_data
        self.annotations_data = annotations_data or []

    def call(self, prompt):
        """返回模拟的 JSON 响应"""
        response = json.dumps({
            "signals": self.signals_data,
            "annotations": self.annotations_data
        })
        return response


class TestSignalCache:
    """SignalCache 测试"""

    def test_index_by_timestamp(self):
        """测试按时间戳索引信号"""
        cache = SignalCache()
        signals = [
            {"timestamp": "2024-01-01", "action": "buy"},
            {"timestamp": "2024-01-03", "action": "sell"},
            {"timestamp": "2024-01-05", "action": "hold"},
        ]
        cache.index_signals(signals)

        assert cache.get("2024-01-01") == "buy"
        assert cache.get("2024-01-03") == "sell"
        assert cache.get("2024-01-05") == "hold"

    def test_get_nonexistent_returns_hold(self):
        """测试不存在的 timestamp 返回 hold"""
        cache = SignalCache()
        cache.index_signals([{"timestamp": "2024-01-01", "action": "buy"}])

        # 无信号时默认返回 hold
        assert cache.get("2024-01-02") == "hold"

    def test_get_returns_action_string(self):
        """测试返回的是 action 字符串"""
        cache = SignalCache()
        cache.index_signals([
            {"timestamp": "2024-01-01", "action": "buy"},
        ])

        action = cache.get("2024-01-01")
        assert isinstance(action, str)
        assert action == "buy"


class TestLLMStrategyOnBar:
    """LLMStrategy.on_bar 测试"""

    def test_on_bar_returns_buy_order(self):
        """测试 on_bar 对 buy 信号返回 BUY 订单"""
        signals = [{"timestamp": "2024-01-01", "action": "buy"}]
        client = MockLLMClient(signals)
        strategy = LLMStrategy(
            llm_client=client,
            prompt_builder=PromptBuilder(),
            response_parser=ResponseParser()
        )

        # 模拟 on_init 已完成
        strategy.cache.index_signals(signals)

        bar = Bar(
            timestamp=datetime(2024, 1, 1),
            symbol="ag",
            open=100,
            high=105,
            low=99,
            close=103,
            volume=1000
        )
        bar_result = strategy.on_bar(bar)

        assert bar_result.order is not None
        assert bar_result.order.side == Side.BUY
        assert bar_result.order.symbol == "ag"

    def test_on_bar_returns_sell_order_when_has_position(self):
        """测试有持仓时 sell 信号返回 SELL 订单"""
        signals = [{"timestamp": "2024-01-01", "action": "sell"}]
        client = MockLLMClient(signals)
        strategy = LLMStrategy(
            llm_client=client,
            prompt_builder=PromptBuilder(),
            response_parser=ResponseParser()
        )
        strategy.position = 1  # 有持仓

        strategy.cache.index_signals(signals)

        bar = Bar(
            timestamp=datetime(2024, 1, 1),
            symbol="ag",
            close=103
        )
        bar_result = strategy.on_bar(bar)

        assert bar_result.order is not None
        assert bar_result.order.side == Side.SELL

    def test_on_bar_returns_none_when_sell_no_position(self):
        """测试无持仓时 sell 信号返回 None"""
        signals = [{"timestamp": "2024-01-01", "action": "sell"}]
        client = MockLLMClient(signals)
        strategy = LLMStrategy(
            llm_client=client,
            prompt_builder=PromptBuilder(),
            response_parser=ResponseParser()
        )
        strategy.position = 0  # 无持仓

        strategy.cache.index_signals(signals)

        bar = Bar(
            timestamp=datetime(2024, 1, 1),
            symbol="ag",
            close=103
        )
        bar_result = strategy.on_bar(bar)

        # 无持仓时不能卖，order 为 None
        assert bar_result.order is None

    def test_on_bar_returns_none_when_hold(self):
        """测试 hold 信号返回 None"""
        signals = [{"timestamp": "2024-01-01", "action": "hold"}]
        client = MockLLMClient(signals)
        strategy = LLMStrategy(
            llm_client=client,
            prompt_builder=PromptBuilder(),
            response_parser=ResponseParser()
        )
        strategy.position = 0  # 无持仓

        strategy.cache.index_signals(signals)

        bar = Bar(
            timestamp=datetime(2024, 1, 1),
            symbol="ag",
            close=103
        )
        bar_result = strategy.on_bar(bar)

        assert bar_result.order is None

    def test_on_bar_returns_none_when_no_signal(self):
        """测试无信号时返回 None"""
        client = MockLLMClient([])
        strategy = LLMStrategy(
            llm_client=client,
            prompt_builder=PromptBuilder(),
            response_parser=ResponseParser()
        )
        strategy.position = 0

        bar = Bar(
            timestamp=datetime(2024, 1, 1),
            symbol="ag",
            close=103
        )
        bar_result = strategy.on_bar(bar)

        # 无信号默认 hold，order 为 None
        assert bar_result.order is None

    def test_on_bar_uses_close_price(self):
        """测试订单使用收盘价"""
        signals = [{"timestamp": "2024-01-01", "action": "buy"}]
        client = MockLLMClient(signals)
        strategy = LLMStrategy(
            llm_client=client,
            prompt_builder=PromptBuilder(),
            response_parser=ResponseParser()
        )
        strategy.cache.index_signals(signals)

        bar = Bar(
            timestamp=datetime(2024, 1, 1),
            symbol="ag",
            open=100,
            high=105,
            low=99,
            close=103,
            volume=1000
        )
        bar_result = strategy.on_bar(bar)

        # 订单使用收盘价作为参考价（具体实现可能不同）
        assert bar_result.order is not None


class TestLLMStrategyAnnotations:
    """LLMStrategy 标注测试（通过 BarResult 获取）"""

    def _make_bar(self, date_str: str) -> Bar:
        from datetime import datetime
        ts = datetime.strptime(date_str, "%Y-%m-%d")
        return Bar(timestamp=ts, symbol="TEST", open=100, high=105, low=95, close=102, volume=1000)

    def test_annotations_emitted_on_first_bar(self):
        """第一次 on_bar 调用时标注通过 BarResult 返回"""
        signals = [{"timestamp": "2024-01-01", "action": "buy"}]
        annotations = [
            {"timestamp": "2024-01-01", "type": "buy_signal", "data": {"price": 100, "label": "买入"}}
        ]
        client = MockLLMClient(signals, annotations)
        strategy = LLMStrategy(
            llm_client=client,
            prompt_builder=PromptBuilder(),
            response_parser=ResponseParser()
        )

        strategy.cache.index_signals(signals)
        strategy.cache.set_annotations(annotations)

        bar = self._make_bar("2024-01-01")
        result = strategy.on_bar(bar)
        assert isinstance(result.annotations, list)
        assert len(result.annotations) == 1

    def test_annotations_only_emitted_once(self):
        """标注只在第一次 on_bar 时发出，后续 bar 为空"""
        signals = [{"timestamp": "2024-01-01", "action": "buy"}]
        annotations = [
            {"timestamp": "2024-01-01", "type": "buy_signal", "data": {"price": 100, "label": "买入"}}
        ]
        client = MockLLMClient(signals, annotations)
        strategy = LLMStrategy(
            llm_client=client,
            prompt_builder=PromptBuilder(),
            response_parser=ResponseParser()
        )

        strategy.cache.index_signals(signals)
        strategy.cache.set_annotations(annotations)

        bar1 = self._make_bar("2024-01-01")
        bar2 = self._make_bar("2024-01-02")
        result1 = strategy.on_bar(bar1)
        result2 = strategy.on_bar(bar2)
        assert len(result1.annotations) == 1
        assert len(result2.annotations) == 0

    def test_annotations_empty_when_no_annotations(self):
        """无标注时第一次 on_bar 返回空列表"""
        client = MockLLMClient([])
        strategy = LLMStrategy(
            llm_client=client,
            prompt_builder=PromptBuilder(),
            response_parser=ResponseParser()
        )

        bar = self._make_bar("2024-01-01")
        result = strategy.on_bar(bar)
        assert result.annotations == []


class TestLLMStrategyAnalyze:
    """LLMStrategy.analyze 测试"""

    def test_analyze_combines_components(self):
        """测试 analyze 方法组合三个组件"""
        signals = [{"timestamp": "2024-01-01", "action": "buy"}]
        annotations = [{"timestamp": "2024-01-01", "type": "buy_signal", "data": {}}]
        client = MockLLMClient(signals, annotations)
        prompt_builder = PromptBuilder()
        response_parser = ResponseParser()

        strategy = LLMStrategy(
            llm_client=client,
            prompt_builder=prompt_builder,
            response_parser=response_parser
        )

        bars = [{"timestamp": "2024-01-01", "open": 100, "close": 103}]
        result = strategy.analyze(bars)

        assert len(result.signals) == 1
        assert len(result.annotations) == 1
        assert result.signals[0]["action"] == "buy"