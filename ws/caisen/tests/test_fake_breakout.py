"""假突破检测器 (FakeBreakoutDetector) 单元测试"""

import pytest
from datetime import datetime

from caisen.core.bar import Bar
from caisen.strategy.algorithm.patterns.fake_breakout import FakeBreakoutDetector


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
    """创建整理平台K线"""
    bars = []
    for i in range(count):
        offset = (i % 3 - 1) * 0.002 * base_price
        bars.append(make_bar(base_price + offset, start_offset + i))
    return bars


class TestFakeBreakoutDetector:
    """假突破检测器测试"""

    def test_no_signal_insufficient_bars(self):
        """不足min_bars根K线返回None"""
        detector = FakeBreakoutDetector(min_bars=15)
        bars = [make_bar(100.0, i) for i in range(10)]
        assert detector.detect(bars) is None

    def test_no_signal_without_platform(self):
        """无明显整理平台时返回None"""
        detector = FakeBreakoutDetector(min_bars=10, max_amplitude=0.02)
        bars = [make_bar(100.0 + i * 2, i) for i in range(30)]
        assert detector.detect(bars) is None

    def test_real_breakout_no_signal(self):
        """真突破（突破幅度太大）不触发假突破"""
        detector = FakeBreakoutDetector(
            min_bars=10, lookback_period=30, max_amplitude=0.05,
            min_platform_bars=8, max_fallback_bars=3, fake_tolerance=0.03,
        )
        bars = make_platform_bars(100.0, 10, 0)
        bars.append(make_bar(108.0, 10, high=109.0))
        bars.append(make_bar(99.0, 11))
        bars.append(make_bar(99.5, 12))
        assert detector.detect(bars) is None

    def test_shallow_fake_break(self):
        """上影线刺破后回落，产生假突破信号"""
        detector = FakeBreakoutDetector(
            min_bars=10, lookback_period=30, max_amplitude=0.05,
            min_platform_bars=8, max_fallback_bars=3, fake_tolerance=0.03,
        )
        bars = make_platform_bars(100.0, 10, 0)
        bars.append(make_bar(102.0, 10, high=103.0))
        bars.append(make_bar(99.0, 11))
        bars.append(make_bar(99.5, 12))
        signal = detector.detect(bars)
        assert signal is not None
        assert signal.pattern == "fake_breakout"

    def test_fall_below_lower(self):
        """跌破平台下沿，更强的看空信号"""
        detector = FakeBreakoutDetector(
            min_bars=10, lookback_period=30, max_amplitude=0.05,
            min_platform_bars=8, max_fallback_bars=3, fake_tolerance=0.03,
        )
        bars = make_platform_bars(100.0, 10, 0)
        bars.append(make_bar(102.0, 10, high=103.0))
        bars.append(make_bar(99.0, 11))
        bars.append(make_bar(96.0, 12))
        signal = detector.detect(bars)
        assert signal is not None
        assert signal.data.get("signal_strength") == 2

    def test_confidence_factors(self):
        """置信度在合理范围内"""
        detector = FakeBreakoutDetector(
            min_bars=10, lookback_period=30, max_amplitude=0.05,
            min_platform_bars=8, max_fallback_bars=3, fake_tolerance=0.03,
        )
        bars = make_platform_bars(100.0, 10, 0)
        bars.append(make_bar(102.0, 10, high=103.0))
        bars.append(make_bar(99.0, 11))
        signal = detector.detect(bars)
        assert signal is not None
        assert 0.0 <= signal.confidence <= 1.0
        assert signal.confidence > 0

    def test_direction_is_short(self):
        """假突破方向为short"""
        detector = FakeBreakoutDetector(
            min_bars=10, lookback_period=30, max_amplitude=0.05,
            min_platform_bars=8, max_fallback_bars=3, fake_tolerance=0.03,
        )
        bars = make_platform_bars(100.0, 10, 0)
        bars.append(make_bar(102.0, 10, high=103.0))
        bars.append(make_bar(99.0, 11))
        signal = detector.detect(bars)
        assert signal is not None
        assert signal.data.get("direction") == "short"
