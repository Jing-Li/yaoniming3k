"""LLM 策略集成测试"""

import json
import pytest
from datetime import datetime
from unittest.mock import Mock

from caisen.core.bar import Bar
from caisen.core.order import Side
from caisen.strategy.llm.strategy import LLMStrategy
from caisen.strategy.llm.cache import SignalCache
from caisen.strategy.llm.client import LLMResult
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


class TestLLMStrategyIntegration:
    """LLMStrategy 集成测试"""

    def test_complete_backtest_flow(self):
        """测试完整的回测流程"""
        # 准备 K 线数据
        bars = [
            Bar(timestamp=datetime(2024, 1, 1), symbol="ag", open=100, high=105, low=99, close=103, volume=1000),
            Bar(timestamp=datetime(2024, 1, 2), symbol="ag", open=103, high=108, low=102, close=106, volume=1100),
            Bar(timestamp=datetime(2024, 1, 3), symbol="ag", open=106, high=110, low=105, close=108, volume=1200),
            Bar(timestamp=datetime(2024, 1, 4), symbol="ag", open=108, high=112, low=107, close=110, volume=1300),
            Bar(timestamp=datetime(2024, 1, 5), symbol="ag", open=110, high=108, low=103, close=105, volume=1400),
        ]

        # 准备信号：第 2 天买入，第 4 天卖出
        signals = [
            {"timestamp": "2024-01-02", "action": "buy", "confidence": 0.8, "reason": "突破"},
            {"timestamp": "2024-01-04", "action": "sell", "confidence": 0.7, "reason": "回调"},
        ]

        # 准备标注
        annotations = [
            {"timestamp": "2024-01-02", "type": "buy_signal", "data": {"price": 106, "label": "买入"}},
            {"timestamp": "2024-01-04", "type": "sell_signal", "data": {"price": 110, "label": "卖出"}},
        ]

        client = MockLLMClient(signals, annotations)
        strategy = LLMStrategy(
            llm_client=client,
            prompt_builder=PromptBuilder(),
            response_parser=ResponseParser()
        )

        # 模拟 on_init 缓存数据
        strategy.cache.index_signals(signals)
        strategy.cache.set_annotations(annotations)

        # 逐帧执行
        orders = []
        for bar in bars:
            order = strategy.on_bar(bar)
            if order:
                orders.append(order)

        # 验证：2 个订单（买入 + 卖出）
        assert len(orders) == 2
        assert orders[0].side == Side.BUY
        assert orders[1].side == Side.SELL

        # 验证持仓状态
        assert strategy.position == 0  # 最终空仓

    def test_no_signals_returns_empty_orders(self):
        """测试无信号时返回空"""
        bars = [
            Bar(timestamp=datetime(2024, 1, 1), symbol="ag", close=103),
            Bar(timestamp=datetime(2024, 1, 2), symbol="ag", close=105),
        ]

        client = MockLLMClient([])  # 无信号
        strategy = LLMStrategy(
            llm_client=client,
            prompt_builder=PromptBuilder(),
            response_parser=ResponseParser()
        )

        # 模拟 on_init
        strategy.cache.index_signals([])

        orders = []
        for bar in bars:
            order = strategy.on_bar(bar)
            if order:
                orders.append(order)

        assert len(orders) == 0

    def test_get_annotations_returns_cached_annotations(self):
        """测试 get_annotations 返回缓存的标注"""
        annotations = [
            {"timestamp": "2024-01-01", "type": "buy_signal", "data": {"price": 100}},
            {"timestamp": "2024-01-03", "type": "horizontal_line", "data": {"price": 105}},
        ]

        client = MockLLMClient([], annotations)
        strategy = LLMStrategy(
            llm_client=client,
            prompt_builder=PromptBuilder(),
            response_parser=ResponseParser()
        )
        strategy.cache.set_annotations(annotations)

        result = strategy.get_annotations()

        assert len(result) == 2


class TestSignalCacheIntegration:
    """SignalCache 集成测试"""

    def test_continuous_trading_signals(self):
        """测试连续交易信号"""
        cache = SignalCache()

        # 模拟一段行情的信号
        signals = [
            {"timestamp": "2024-01-01", "action": "hold"},
            {"timestamp": "2024-01-02", "action": "buy"},
            {"timestamp": "2024-01-03", "action": "hold"},
            {"timestamp": "2024-01-04", "action": "hold"},
            {"timestamp": "2024-01-05", "action": "sell"},
        ]

        cache.index_signals(signals)

        # 验证每个时间点的信号
        assert cache.get("2024-01-01") == "hold"
        assert cache.get("2024-01-02") == "buy"
        assert cache.get("2024-01-03") == "hold"
        assert cache.get("2024-01-04") == "hold"
        assert cache.get("2024-01-05") == "sell"

        # 验证不存在的时间点默认 hold
        assert cache.get("2024-01-06") == "hold"

    def test_cache_with_confidence_values(self):
        """测试带置信度的信号"""
        cache = SignalCache()

        # 信号带置信度
        signals = [
            {"timestamp": "2024-01-01", "action": "buy", "confidence": 0.9},
            {"timestamp": "2024-01-02", "action": "hold", "confidence": 0.3},
        ]

        cache.index_signals(signals)

        # 验证：cache 只存 action，不存 confidence
        # confidence 由策略在实际下单时参考
        assert cache.get("2024-01-01") == "buy"
        assert cache.get("2024-01-02") == "hold"


class TestEndToEndScenario:
    """端到端场景测试"""

    def test_winning_trade(self):
        """测试盈利交易场景"""
        # 场景：买入价 103，卖出价 108，盈利
        bars = [
            Bar(timestamp=datetime(2024, 1, 1), symbol="ag", close=100),
            Bar(timestamp=datetime(2024, 1, 2), symbol="ag", close=103),  # 买入
            Bar(timestamp=datetime(2024, 1, 3), symbol="ag", close=105),
            Bar(timestamp=datetime(2024, 1, 4), symbol="ag", close=108),  # 卖出
        ]

        signals = [
            {"timestamp": "2024-01-02", "action": "buy"},
            {"timestamp": "2024-01-04", "action": "sell"},
        ]

        client = MockLLMClient(signals)
        strategy = LLMStrategy(
            llm_client=client,
            prompt_builder=PromptBuilder(),
            response_parser=ResponseParser()
        )
        strategy.cache.index_signals(signals)

        orders = []
        for bar in bars:
            order = strategy.on_bar(bar)
            if order:
                orders.append(order)

        assert len(orders) == 2
        assert orders[0].side == Side.BUY
        assert orders[1].side == Side.SELL

    def test_losing_trade(self):
        """测试亏损交易场景"""
        bars = [
            Bar(timestamp=datetime(2024, 1, 1), symbol="ag", close=108),  # 买入
            Bar(timestamp=datetime(2024, 1, 2), symbol="ag", close=105),
            Bar(timestamp=datetime(2024, 1, 3), symbol="ag", close=100),  # 卖出
        ]

        signals = [
            {"timestamp": "2024-01-01", "action": "buy"},
            {"timestamp": "2024-01-03", "action": "sell"},
        ]

        client = MockLLMClient(signals)
        strategy = LLMStrategy(
            llm_client=client,
            prompt_builder=PromptBuilder(),
            response_parser=ResponseParser()
        )
        strategy.cache.index_signals(signals)

        orders = []
        for bar in bars:
            order = strategy.on_bar(bar)
            if order:
                orders.append(order)

        assert len(orders) == 2
        # 亏损场景也能正确执行买入和卖出