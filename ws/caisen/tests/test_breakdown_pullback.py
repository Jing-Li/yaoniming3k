"""破底翻检测器 (BreakdownPullbackDetector) 单元测试"""

import pytest
from datetime import datetime

from caisen.core.bar import Bar
from caisen.strategy.algorithm.patterns.breakdown_pullback import BreakdownPullbackDetector


def make_bar(price: float, timestamp_offset: int = 0, volume: float = 1000.0, low=None, high=None) -> Bar:
    """创建测试用K线"""
    return Bar(
        timestamp=datetime(2024, 1, 1 + timestamp_offset),
        symbol="test",
        freq="1d",
        open=price,
        high=high if high is not None else price * 1.005,
        low=low if low is not None else price * 0.995,
        close=price,
        volume=volume,
    )


def make_platform_bars(base_price: float, count: int, start_offset: int = 0) -> list:
    """创建整理平台K线（价格在 base_price ±0.5% 范围内波动）"""
    bars = []
    for i in range(count):
        offset = (i % 3 - 1) * 0.002 * base_price
        bars.append(make_bar(base_price + offset, start_offset + i))
    return bars


class TestBreakdownPullbackDetector:
    """破底翻检测器测试"""

    def test_no_signal_insufficient_bars(self):
        """不足min_bars根K线返回None"""
        detector = BreakdownPullbackDetector(min_bars=15)
        bars = [make_bar(100.0, i) for i in range(10)]
        assert detector.detect(bars) is None

    def test_no_signal_without_platform(self):
        """无明显整理平台时返回None"""
        detector = BreakdownPullbackDetector(min_bars=10, max_amplitude=0.02)
        bars = [make_bar(100.0 + i * 2, i) for i in range(30)]
        assert detector.detect(bars) is None

    def test_breakdown_without_pullback(self):
        """跌破后未翻回，不产生信号"""
        detector = BreakdownPullbackDetector(
            min_bars=10, lookback_period=30, max_amplitude=0.05,
            min_platform_bars=8, max_pullback_bars=3, breakdown_tolerance=0.03,
        )
        bars = make_platform_bars(97.5, 10, 0)
        bars.append(make_bar(92.0, 10, low=91.0))
        bars.append(make_bar(91.0, 11))
        bars.append(make_bar(90.0, 12))
        bars.append(make_bar(89.0, 13))
        assert detector.detect(bars) is None

    def test_deep_breakdown_no_signal(self):
        """跌破太深（超过tolerance），不是破底翻"""
        detector = BreakdownPullbackDetector(
            min_bars=10, lookback_period=30, max_amplitude=0.05,
            min_platform_bars=8, breakdown_tolerance=0.03,
        )
        bars = make_platform_bars(100.0, 10, 0)
        bars.append(make_bar(90.0, 10, low=89.0))
        bars.append(make_bar(99.0, 11))
        bars.append(make_bar(99.5, 12))
        assert detector.detect(bars) is None

    def test_first_buy_point(self):
        """第一买点：站回颈线（平台下沿）时产生信号"""
        detector = BreakdownPullbackDetector(
            min_bars=10, lookback_period=30, max_amplitude=0.05,
            min_platform_bars=8, max_pullback_bars=3, breakdown_tolerance=0.03,
        )
        bars = make_platform_bars(100.0, 10, 0)
        bars.append(make_bar(97.5, 10, low=97.0))
        bars.append(make_bar(99.5, 11))
        bars.append(make_bar(100.5, 12))
        signal = detector.detect(bars)
        assert signal is not None
        assert signal.pattern == "breakdown_pullback"
        assert signal.data.get("buy_point") == 1
        assert signal.data.get("direction") == "long"

    def test_second_buy_point(self):
        """第二买点：突破平台上沿时产生信号"""
        detector = BreakdownPullbackDetector(
            min_bars=10, lookback_period=30, max_amplitude=0.05,
            min_platform_bars=8, max_pullback_bars=3, breakdown_tolerance=0.03,
        )
        bars = make_platform_bars(100.0, 10, 0)
        bars.append(make_bar(97.5, 10, low=97.0))
        bars.append(make_bar(99.5, 11))
        bars.append(make_bar(101.5, 12))
        signal = detector.detect(bars)
        assert signal is not None
        assert signal.data.get("buy_point") == 2

    def test_confidence_factors(self):
        """置信度在合理范围内"""
        detector = BreakdownPullbackDetector(
            min_bars=10, lookback_period=30, max_amplitude=0.05,
            min_platform_bars=8, max_pullback_bars=3, breakdown_tolerance=0.03,
        )
        bars = make_platform_bars(100.0, 10, 0)
        bars.append(make_bar(97.5, 10, low=97.0))
        bars.append(make_bar(100.5, 11))
        signal = detector.detect(bars)
        assert signal is not None
        assert 0.0 <= signal.confidence <= 1.0
        assert signal.confidence > 0

    def test_stop_loss_and_target(self):
        """止损和目标价计算正确"""
        detector = BreakdownPullbackDetector(
            min_bars=10, lookback_period=30, max_amplitude=0.05,
            min_platform_bars=8, max_pullback_bars=3, breakdown_tolerance=0.03,
            stop_loss_factor=0.93,
        )
        bars = make_platform_bars(100.0, 10, 0)
        bars.append(make_bar(97.5, 10, low=97.0))
        bars.append(make_bar(100.5, 11))
        signal = detector.detect(bars)
        assert signal is not None
        assert signal.stop_loss < 97.0
        assert signal.target > 100.0
