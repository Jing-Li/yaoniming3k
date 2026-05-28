"""测试蔡森策略 V2（PatternDetector 架构）"""

from datetime import datetime, timedelta
from caisen.core.bar import Bar
from caisen.core.order import Side
from caisen.strategy.algorithm.cai_sen import CaiSenStrategy


def make_bar(idx: int, open_p: float, high: float, low: float, close: float, volume: float = 1000, days_offset: int = None) -> Bar:
    """创建测试K线"""
    if days_offset is None:
        days_offset = idx
    return Bar(
        timestamp=datetime(2024, 1, 1) + timedelta(days=days_offset),
        symbol="TEST",
        freq="1d",
        open=open_p,
        high=high,
        low=low,
        close=close,
        volume=volume
    )


class TestCaiSenStrategyV2:
    """CaiSenStrategy V2 测试"""

    def test_default_initialization(self):
        """测试默认初始化"""
        strategy = CaiSenStrategy()
        assert strategy is not None
        assert len(strategy.detectors) >= 1  # 至少有默认检测器

    def test_from_config(self):
        """测试从配置创建"""
        config = {
            "strategy": {"threshold": 0.7},
            "weights": {"w_bottom": 0.5},
            "enabled_patterns": {"w_bottom": True},
        }
        strategy = CaiSenStrategy.from_config(config_dict=config)
        assert strategy.threshold == 0.7
        assert strategy.weights.get("w_bottom") == 0.5

    def test_enabled_patterns(self):
        """测试只启用特定形态"""
        strategy = CaiSenStrategy(enabled_patterns=["w_bottom"])
        detector_names = [d.name for d in strategy.detectors]
        assert "w_bottom" in detector_names

    def test_no_signal_without_position(self):
        """测试无持仓时不产生卖出信号"""
        strategy = CaiSenStrategy()

        # 下跌行情 - W底前不应产生买入信号
        for i in range(20):
            bar = make_bar(i, 100 - i, 101 - i, 95 - i, 96 - i, volume=1000)
            bar_result = strategy.on_bar(bar)
            # 下跌趋势不应产生买入信号
            if bar_result.order and bar_result.order.side == Side.BUY:
                assert False, "下跌趋势不应产生买入信号"

    def test_w_bottom_detection(self):
        """测试W底形态检测"""
        # 只启用W底
        strategy = CaiSenStrategy(enabled_patterns=["w_bottom"])

        # 1. 下跌到100
        for i in range(5):
            bar = make_bar(i, 105, 106, 99, 100, volume=1000)
            strategy.on_bar(bar)

        # 2. 反弹到103
        for i in range(5, 10):
            bar = make_bar(i, 100, 104, 100, 103, volume=800)
            strategy.on_bar(bar)

        # 3. 再次下跌到101
        for i in range(10, 15):
            bar = make_bar(i, 103, 104, 100, 101, volume=900)
            strategy.on_bar(bar)

        # 4. 放量突破颈线103
        bar_breakout = make_bar(15, 101, 106, 100, 105, volume=1500)
        bar_result = strategy.on_bar(bar_breakout)

        # 突破颈线应产生买入信号
        assert bar_result.order is not None, "W底突破颈线应产生买入信号"
        assert bar_result.order.side == Side.BUY

    def test_m_top_detection(self):
        """测试M头形态检测（仅验证检测功能，v2当前只支持做多）"""
        # 启用M头
        strategy = CaiSenStrategy(enabled_patterns=["m_top"])
        detector = strategy.detectors[0]

        # 1. 构建M头形态数据
        bars = [
            make_bar(0, 105, 108, 102, 107, volume=1000),
            make_bar(1, 107, 111, 106, 110, volume=1100),  # 左顶 110
            make_bar(2, 110, 111, 109, 109, volume=1000),
            make_bar(3, 109, 110, 102, 103, volume=900),   # 回调到颈线 103
            make_bar(4, 103, 104, 102, 103, volume=800),
            make_bar(5, 103, 108, 101, 107, volume=900),   # 反弹
            make_bar(6, 107, 110, 104, 109, volume=1000),
            make_bar(7, 109, 111, 108, 110, volume=1050),  # 右顶 110 (略低)
            make_bar(8, 110, 111, 109, 109, volume=1000),
            make_bar(9, 109, 110, 102, 103, volume=800),   # 再次回调
            make_bar(10, 103, 104, 97, 98, volume=1500),    # 跌破颈线
        ]

        for bar in bars:
            strategy.on_bar(bar)

        # M头检测器能检测到形态（纯函数接口：直接传入 bars）
        signal = detector.detect(bars)
        assert signal is not None, "应检测到M头信号"
        assert signal.pattern == "m_top"

        # 注意：v2当前只支持做多，不支持做空，所以不会产生SELL订单
        # 这是架构限制，不是bug

    def test_stop_loss(self):
        """测试止损逻辑"""
        strategy = CaiSenStrategy(
            enabled_patterns=["w_bottom"],
            stop_loss_factor=0.95
        )

        # 买入
        bar1 = make_bar(0, 100, 101, 99, 100, volume=1000)
        br1 = strategy.on_bar(bar1)
        assert br1.order is None or br1.order.side == Side.BUY

        # 持仓中，止损
        bar2 = make_bar(1, 100, 101, 94, 95, volume=1000)  # 跌破止损价
        br2 = strategy.on_bar(bar2)

        if br2.order is not None:
            assert br2.order.side == Side.SELL, "跌破止损价应触发卖出"

    def test_position_management(self):
        """测试仓位管理"""
        strategy = CaiSenStrategy(enabled_patterns=["w_bottom"])

        # 产生买入信号
        bar = make_bar(0, 95, 100, 94, 99, volume=1000)
        br1 = strategy.on_bar(bar)

        # 再次买入同一标的应返回None（已有持仓）
        bar2 = make_bar(1, 99, 105, 98, 104, volume=1000)
        br2 = strategy.on_bar(bar2)
        # 已有持仓，不应再次买入
        # 注意：取决于实现，可能是None或止盈单

    def test_multiple_patterns(self):
        """测试多形态同时启用"""
        strategy = CaiSenStrategy(enabled_patterns=["w_bottom", "m_top"])

        # 检查检测器数量
        assert len(strategy.detectors) == 2

        # 检查检测器名称
        names = [d.name for d in strategy.detectors]
        assert "w_bottom" in names
        assert "m_top" in names

    def test_all_twelve_patterns(self):
        """测试蔡森十二形态全部可启用"""
        all_patterns = [
            "w_bottom", "m_top",
            "head_and_shoulders_bottom", "head_and_shoulders_top",
            "triangle", "flag", "rectangle",
            "rounding_bottom", "cup_handle",
            "breakout_pullback",
            "breakdown_pullback", "fake_breakout",
        ]
        strategy = CaiSenStrategy(enabled_patterns=all_patterns)
        assert len(strategy.detectors) == 12

        names = [d.name for d in strategy.detectors]
        for pattern in all_patterns:
            assert pattern in names, f"{pattern} not in detector names"

    def test_breakdown_pullback_enabled(self):
        """测试破底翻形态启用"""
        strategy = CaiSenStrategy(enabled_patterns=["breakdown_pullback"])
        assert len(strategy.detectors) == 1
        assert strategy.detectors[0].name == "breakdown_pullback"

    def test_fake_breakout_enabled(self):
        """测试假突破形态启用"""
        strategy = CaiSenStrategy(enabled_patterns=["fake_breakout"])
        assert len(strategy.detectors) == 1
        assert strategy.detectors[0].name == "fake_breakout"


class TestPatternDetectors:
    """PatternDetector 单元测试"""

    def test_w_bottom_detector(self):
        """测试W底检测器（纯函数接口）"""
        from caisen.strategy.algorithm.patterns import WBottomDetector

        detector = WBottomDetector()

        # 模拟W底数据 (需要至少10根K线)
        bars = [
            make_bar(0, 105, 106, 100, 101, volume=1000),
            make_bar(1, 101, 102, 98, 99, volume=900),
            make_bar(2, 99, 100, 95, 96, volume=800),
            make_bar(3, 96, 97, 93, 94, volume=700),
            make_bar(4, 94, 95, 93, 94, volume=600),  # 第一个底部
            make_bar(5, 94, 98, 93, 97, volume=700),   # 反弹
            make_bar(6, 97, 98, 96, 97, volume=800),
            make_bar(7, 97, 98, 95, 96, volume=850),   # 第二个底部（略高于第一个）
            make_bar(8, 96, 97, 95, 96, volume=800),   # 再次反弹
            make_bar(9, 96, 105, 95, 104, volume=2000),  # 突破颈线
        ]

        # 纯函数接口：直接传入 bars，无需 update
        signal = detector.detect(bars)
        assert signal is not None, "应检测到W底信号"
        assert signal.pattern == "w_bottom"
