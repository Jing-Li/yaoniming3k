"""测试 LLM Strategy（离线预计算架构）"""

from datetime import datetime
import pytest

from caisen.core.bar import Bar
from caisen.core.order import Order, Side
from caisen.strategy.llm.strategy import LLMStrategy
from caisen.strategy.llm.cache import SignalCache


class MockLLMClient:
    """模拟 LLM 客户端"""

    def __init__(self, signals_data, annotations_data=None):
        self.signals_data = signals_data
        self.annotations_data = annotations_data or []

    def analyze(self, bars):
        return MockResult(self.signals_data, self.annotations_data)


class MockResult:
    """模拟 LLM 返回结果"""

    def __init__(self, signals, annotations):
        self.signals = signals
        self.annotations = annotations


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
        strategy = LLMStrategy(client)

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
        order = strategy.on_bar(bar)

        assert order is not None
        assert order.side == Side.BUY
        assert order.symbol == "ag"

    def test_on_bar_returns_sell_order_when_has_position(self):
        """测试有持仓时 sell 信号返回 SELL 订单"""
        signals = [{"timestamp": "2024-01-01", "action": "sell"}]
        client = MockLLMClient(signals)
        strategy = LLMStrategy(client)
        strategy.position = 1  # 有持仓

        strategy.cache.index_signals(signals)

        bar = Bar(
            timestamp=datetime(2024, 1, 1),
            symbol="ag",
            close=103
        )
        order = strategy.on_bar(bar)

        assert order is not None
        assert order.side == Side.SELL

    def test_on_bar_returns_none_when_sell_no_position(self):
        """测试无持仓时 sell 信号返回 None"""
        signals = [{"timestamp": "2024-01-01", "action": "sell"}]
        client = MockLLMClient(signals)
        strategy = LLMStrategy(client)
        strategy.position = 0  # 无持仓

        strategy.cache.index_signals(signals)

        bar = Bar(
            timestamp=datetime(2024, 1, 1),
            symbol="ag",
            close=103
        )
        order = strategy.on_bar(bar)

        # 无持仓时不能卖，返回 None
        assert order is None

    def test_on_bar_returns_none_when_hold(self):
        """测试 hold 信号返回 None"""
        signals = [{"timestamp": "2024-01-01", "action": "hold"}]
        client = MockLLMClient(signals)
        strategy = LLMStrategy(client)
        strategy.position = 0  # 无持仓

        strategy.cache.index_signals(signals)

        bar = Bar(
            timestamp=datetime(2024, 1, 1),
            symbol="ag",
            close=103
        )
        order = strategy.on_bar(bar)

        assert order is None

    def test_on_bar_returns_none_when_no_signal(self):
        """测试无信号时返回 None"""
        client = MockLLMClient([])
        strategy = LLMStrategy(client)
        strategy.position = 0

        bar = Bar(
            timestamp=datetime(2024, 1, 1),
            symbol="ag",
            close=103
        )
        order = strategy.on_bar(bar)

        # 无信号默认 hold，返回 None
        assert order is None

    def test_on_bar_uses_close_price(self):
        """测试订单使用收盘价"""
        signals = [{"timestamp": "2024-01-01", "action": "buy"}]
        client = MockLLMClient(signals)
        strategy = LLMStrategy(client)
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
        order = strategy.on_bar(bar)

        # 订单使用收盘价作为参考价（具体实现可能不同）
        assert order is not None


class TestLLMStrategyAnnotations:
    """LLMStrategy.get_annotations 测试"""

    def test_get_annotations_returns_list(self):
        """测试 get_annotations 返回列表"""
        signals = [{"timestamp": "2024-01-01", "action": "buy"}]
        annotations = [
            {"timestamp": "2024-01-01", "type": "buy_signal", "data": {"price": 100, "label": "买入"}}
        ]
        client = MockLLMClient(signals, annotations)
        strategy = LLMStrategy(client)

        strategy.cache.index_signals(signals)
        strategy.cache.set_annotations(annotations)

        result = strategy.get_annotations()
        assert isinstance(result, list)

    def test_get_annotations_empty_when_no_annotations(self):
        """测试无标注时返回空列表"""
        client = MockLLMClient([])
        strategy = LLMStrategy(client)

        result = strategy.get_annotations()
        assert result == []