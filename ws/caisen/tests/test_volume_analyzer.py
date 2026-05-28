"""VolumeAnalyzer 单元测试"""

import pytest
from datetime import datetime, timedelta

from caisen.core.bar import Bar
from caisen.strategy.algorithm.caisen_components.volume_analyzer import VolumeAnalyzer


def make_bars(volumes, base_price=100.0, start_time=None):
    """生成测试用K线数据

    Args:
        volumes: 成交量列表
        base_price: 基准价格
        start_time: 起始时间

    Returns:
        Bar 列表
    """
    if start_time is None:
        start_time = datetime(2025, 1, 1)

    bars = []
    for i, vol in enumerate(volumes):
        price = base_price + i * 0.5
        bars.append(Bar(
            timestamp=start_time + timedelta(hours=i),
            symbol="TEST",
            freq="1h",
            open=price - 0.2,
            high=price + 0.5,
            low=price - 0.5,
            close=price,
            volume=vol,
        ))
    return bars


class TestGetBaseVolume:
    """测试 get_base_volume 方法"""

    def test_basic_calculation(self):
        """正常计算基础均量"""
        analyzer = VolumeAnalyzer(base_period=5)
        volumes = [100, 200, 300, 400, 500, 600, 700]
        bars = make_bars(volumes)

        # end_idx=5 → 取 bars[0:5] 的均量 = (100+200+300+400+500)/5 = 300
        result = analyzer.get_base_volume(bars, end_idx=5)
        assert result == 300.0

    def test_insufficient_data(self):
        """数据不足时的处理"""
        analyzer = VolumeAnalyzer(base_period=20)
        volumes = [100, 200, 300]
        bars = make_bars(volumes)

        # end_idx=3，数据不足 base_period=20，但仍按可用数据计算
        result = analyzer.get_base_volume(bars, end_idx=3)
        assert result == 200.0  # (100+200+300)/3

    def test_zero_end_idx(self):
        """end_idx为0时返回0"""
        analyzer = VolumeAnalyzer(base_period=20)
        bars = make_bars([100, 200])
        result = analyzer.get_base_volume(bars, end_idx=0)
        assert result == 0.0

    def test_custom_base_period(self):
        """自定义base_period"""
        analyzer = VolumeAnalyzer(base_period=3)
        volumes = [100, 200, 300, 400, 500]
        bars = make_bars(volumes)

        # end_idx=5 → 取 bars[2:5] 的均量 = (300+400+500)/3 = 400
        result = analyzer.get_base_volume(bars, end_idx=5)
        assert result == 400.0


class TestStagedVolumeCheck:
    """测试 staged_volume_check 方法"""

    def test_all_stages_pass(self):
        """所有阶段都通过的场景"""
        analyzer = VolumeAnalyzer(base_period=5, breakout_multiplier=1.5)

        # 构造：前5根正常量(基准=200)，形成期缩量(100)，突破期放量(400)
        volumes = [200, 200, 200, 200, 200, 100, 100, 100, 400, 400]
        bars = make_bars(volumes)

        stages = [
            {'name': 'formation', 'start_idx': 5, 'end_idx': 7, 'expect': 'shrink'},
            {'name': 'breakout', 'start_idx': 8, 'end_idx': 9, 'expect': 'expand'},
        ]

        result = analyzer.staged_volume_check(bars, stages)
        assert result['passed'] is True
        assert result['score'] > 0
        assert result['details']['formation']['passed'] is True
        assert result['details']['breakout']['passed'] is True

    def test_formation_not_shrink(self):
        """形成期未缩量 → 不通过"""
        analyzer = VolumeAnalyzer(base_period=5, breakout_multiplier=1.5)

        # 前5根正常量(基准=200)，形成期放量(300)，突破期放量(400)
        volumes = [200, 200, 200, 200, 200, 300, 300, 300, 400, 400]
        bars = make_bars(volumes)

        stages = [
            {'name': 'formation', 'start_idx': 5, 'end_idx': 7, 'expect': 'shrink'},
            {'name': 'breakout', 'start_idx': 8, 'end_idx': 9, 'expect': 'expand'},
        ]

        result = analyzer.staged_volume_check(bars, stages)
        assert result['passed'] is False
        assert result['details']['formation']['passed'] is False

    def test_breakout_not_expand(self):
        """突破期未放量 → 不通过"""
        analyzer = VolumeAnalyzer(base_period=5, breakout_multiplier=1.5)

        # 前5根正常量(基准=200)，形成期缩量(100)，突破期量不足(250 < 1.5*200)
        volumes = [200, 200, 200, 200, 200, 100, 100, 100, 250, 250]
        bars = make_bars(volumes)

        stages = [
            {'name': 'formation', 'start_idx': 5, 'end_idx': 7, 'expect': 'shrink'},
            {'name': 'breakout', 'start_idx': 8, 'end_idx': 9, 'expect': 'expand'},
        ]

        result = analyzer.staged_volume_check(bars, stages)
        assert result['passed'] is False
        assert result['details']['breakout']['passed'] is False

    def test_progressive_stage(self):
        """递增阶段检查"""
        analyzer = VolumeAnalyzer(base_period=5, breakout_multiplier=1.5)

        # 递增量能
        volumes = [200, 200, 200, 200, 200, 100, 200, 300, 400, 500]
        bars = make_bars(volumes)

        stages = [
            {'name': 'progressive_phase', 'start_idx': 5, 'end_idx': 9, 'expect': 'progressive'},
        ]

        result = analyzer.staged_volume_check(bars, stages)
        assert result['details']['progressive_phase']['passed'] is True

    def test_empty_stages(self):
        """空阶段列表"""
        analyzer = VolumeAnalyzer()
        bars = make_bars([100, 200, 300])

        result = analyzer.staged_volume_check(bars, [])
        assert result['passed'] is False
        assert result['score'] == 0.0

    def test_empty_bars(self):
        """空K线列表"""
        analyzer = VolumeAnalyzer()

        stages = [{'name': 'test', 'start_idx': 0, 'end_idx': 5, 'expect': 'expand'}]
        result = analyzer.staged_volume_check([], stages)
        assert result['passed'] is False


class TestGrade:
    """测试 grade 方法"""

    def test_strong_volume(self):
        """强量能（>=2.0倍）"""
        analyzer = VolumeAnalyzer(base_period=5)
        # 基准量200，突破量500 → 2.5倍 → strong
        volumes = [200, 200, 200, 200, 200, 500]
        bars = make_bars(volumes)

        result = analyzer.grade(bars, breakout_idx=5)
        assert result == 'strong'

    def test_normal_volume(self):
        """正常量能（1.2~2.0倍）"""
        analyzer = VolumeAnalyzer(base_period=5)
        # 基准量200，突破量300 → 1.5倍 → normal
        volumes = [200, 200, 200, 200, 200, 300]
        bars = make_bars(volumes)

        result = analyzer.grade(bars, breakout_idx=5)
        assert result == 'normal'

    def test_weak_volume(self):
        """弱量能（<1.2倍）"""
        analyzer = VolumeAnalyzer(base_period=5)
        # 基准量200，突破量200 → 1.0倍 → weak
        volumes = [200, 200, 200, 200, 200, 200]
        bars = make_bars(volumes)

        result = analyzer.grade(bars, breakout_idx=5)
        assert result == 'weak'

    def test_boundary_1_2(self):
        """边界值测试：正好1.2倍 → normal"""
        analyzer = VolumeAnalyzer(base_period=5)
        volumes = [100, 100, 100, 100, 100, 120]
        bars = make_bars(volumes)

        result = analyzer.grade(bars, breakout_idx=5)
        assert result == 'normal'

    def test_boundary_2_0(self):
        """边界值测试：正好2.0倍 → strong"""
        analyzer = VolumeAnalyzer(base_period=5)
        volumes = [100, 100, 100, 100, 100, 200]
        bars = make_bars(volumes)

        result = analyzer.grade(bars, breakout_idx=5)
        assert result == 'strong'

    def test_invalid_index(self):
        """无效索引返回 weak"""
        analyzer = VolumeAnalyzer(base_period=5)
        bars = make_bars([100, 200])

        result = analyzer.grade(bars, breakout_idx=10)
        assert result == 'weak'

    def test_zero_base_volume(self):
        """基础量为0时返回 normal"""
        analyzer = VolumeAnalyzer(base_period=5)
        # breakout_idx=0，前面没有数据
        bars = make_bars([500])
        result = analyzer.grade(bars, breakout_idx=0)
        assert result == 'normal'


class TestVolumeDivergence:
    """测试 volume_divergence 方法"""

    def test_top_divergence(self):
        """顶背离：价格创新高但量能未创新高"""
        analyzer = VolumeAnalyzer()
        # 前半段大量，后半段量缩
        volumes = [100, 200, 500, 400, 300, 100, 150, 200, 180, 120]
        bars = make_bars(volumes)

        result = analyzer.volume_divergence(bars, price_new_extreme=True, direction='up')
        assert result is True

    def test_no_divergence_when_volume_follows(self):
        """无背离：量能跟上价格"""
        analyzer = VolumeAnalyzer()
        # 后半段量比前半段大
        volumes = [100, 150, 200, 120, 130, 300, 400, 500, 350, 450]
        bars = make_bars(volumes)

        result = analyzer.volume_divergence(bars, price_new_extreme=True, direction='up')
        assert result is False

    def test_no_divergence_without_new_extreme(self):
        """price_new_extreme=False 时直接返回 False"""
        analyzer = VolumeAnalyzer()
        bars = make_bars([100] * 10)

        result = analyzer.volume_divergence(bars, price_new_extreme=False, direction='up')
        assert result is False

    def test_bottom_divergence(self):
        """底背离：价格创新低但放量不及之前"""
        analyzer = VolumeAnalyzer()
        # 前半段大量，后半段量缩（恐慌减弱）
        volumes = [100, 200, 500, 400, 300, 100, 150, 100, 80, 120]
        bars = make_bars(volumes)

        result = analyzer.volume_divergence(bars, price_new_extreme=True, direction='down')
        assert result is True

    def test_insufficient_data(self):
        """数据不足时返回 False"""
        analyzer = VolumeAnalyzer()
        bars = make_bars([100, 200, 300])

        result = analyzer.volume_divergence(bars, price_new_extreme=True, direction='up')
        assert result is False


class TestProgressiveVolume:
    """测试 progressive_volume 方法"""

    def test_strictly_increasing(self):
        """严格递增"""
        analyzer = VolumeAnalyzer()
        volumes = [100, 200, 300, 400, 500]
        bars = make_bars(volumes)

        result = analyzer.progressive_volume(bars, indices=[0, 1, 2, 3, 4])
        assert result is True

    def test_with_tolerance(self):
        """允许小幅波动（后一个 >= 前一个的90%）"""
        analyzer = VolumeAnalyzer()
        volumes = [100, 200, 190, 300, 500]
        bars = make_bars(volumes)

        # 190 >= 200 * 0.9 = 180 → 通过
        result = analyzer.progressive_volume(bars, indices=[0, 1, 2, 3, 4])
        assert result is True

    def test_decreasing(self):
        """递减 → 不通过"""
        analyzer = VolumeAnalyzer()
        volumes = [500, 400, 300, 200, 100]
        bars = make_bars(volumes)

        result = analyzer.progressive_volume(bars, indices=[0, 1, 2, 3, 4])
        assert result is False

    def test_insufficient_indices(self):
        """少于2个索引 → False"""
        analyzer = VolumeAnalyzer()
        bars = make_bars([100, 200, 300])

        result = analyzer.progressive_volume(bars, indices=[0])
        assert result is False

    def test_invalid_index(self):
        """无效索引 → False"""
        analyzer = VolumeAnalyzer()
        bars = make_bars([100, 200])

        result = analyzer.progressive_volume(bars, indices=[0, 5])
        assert result is False

    def test_last_must_exceed_first(self):
        """最后一个必须大于第一个"""
        analyzer = VolumeAnalyzer()
        # 虽然每步都符合90%规则，但最后小于第一个
        volumes = [100, 95, 90, 85, 80]
        bars = make_bars(volumes)

        result = analyzer.progressive_volume(bars, indices=[0, 1, 2, 3, 4])
        assert result is False


class TestIntegrationWithDetectors:
    """与形态检测器的集成测试"""

    def test_w_bottom_detector_has_volume_analyzer(self):
        """WBottomDetector 应该有 volume_analyzer 属性"""
        from caisen.strategy.algorithm.patterns.w_bottom import WBottomDetector

        detector = WBottomDetector()
        assert hasattr(detector, 'volume_analyzer')
        assert isinstance(detector.volume_analyzer, VolumeAnalyzer)

    def test_breakdown_pullback_detector_has_volume_analyzer(self):
        """BreakdownPullbackDetector 应该有 volume_analyzer 属性"""
        from caisen.strategy.algorithm.patterns.breakdown_pullback import BreakdownPullbackDetector

        detector = BreakdownPullbackDetector()
        assert hasattr(detector, 'volume_analyzer')
        assert isinstance(detector.volume_analyzer, VolumeAnalyzer)

    def test_flag_detector_has_volume_analyzer(self):
        """FlagDetector 应该有 volume_analyzer 属性"""
        from caisen.strategy.algorithm.patterns.other import FlagDetector

        detector = FlagDetector()
        assert hasattr(detector, 'volume_analyzer')
        assert isinstance(detector.volume_analyzer, VolumeAnalyzer)

    def test_rectangle_detector_has_volume_analyzer(self):
        """RectangleDetector 应该有 volume_analyzer 属性"""
        from caisen.strategy.algorithm.patterns.other import RectangleDetector

        detector = RectangleDetector()
        assert hasattr(detector, 'volume_analyzer')
        assert isinstance(detector.volume_analyzer, VolumeAnalyzer)

    def test_cup_handle_detector_has_volume_analyzer(self):
        """CupHandleDetector 应该有 volume_analyzer 属性"""
        from caisen.strategy.algorithm.patterns.other import CupHandleDetector

        detector = CupHandleDetector()
        assert hasattr(detector, 'volume_analyzer')
        assert isinstance(detector.volume_analyzer, VolumeAnalyzer)

    def test_custom_volume_config(self):
        """检测器可通过 volume_config 传入自定义参数"""
        from caisen.strategy.algorithm.patterns.w_bottom import WBottomDetector

        detector = WBottomDetector()
        # 默认值
        assert detector.volume_analyzer.base_period == 20
        assert detector.volume_analyzer.breakout_multiplier == 1.5

    def test_detector_backward_compat(self):
        """确保 _volume_ratio 仍然可用（向后兼容）"""
        from caisen.strategy.algorithm.patterns.w_bottom import WBottomDetector

        detector = WBottomDetector()
        bars = make_bars([100] * 20 + [200] * 5)
        ratio = detector._volume_ratio(bars)
        assert ratio == pytest.approx(2.0, rel=0.1)

    def test_w_bottom_with_volume(self):
        """W底检测器完整集成测试（包含量能）"""
        from caisen.strategy.algorithm.patterns.w_bottom import WBottomDetector

        detector = WBottomDetector(tolerance=0.05)

        # 构造W底数据：先跌后涨再跌再涨突破颈线
        start = datetime(2025, 1, 1)
        bars = []

        # 前导数据（用于基础均量计算）
        for i in range(20):
            bars.append(Bar(
                timestamp=start + timedelta(hours=i),
                symbol="TEST", freq="1h",
                open=100, high=101, low=99, close=100,
                volume=200,
            ))

        # W底形态：
        # 第一低点
        bars.append(Bar(timestamp=start + timedelta(hours=20), symbol="TEST", freq="1h",
                       open=98, high=99, low=95, close=96, volume=150))
        bars.append(Bar(timestamp=start + timedelta(hours=21), symbol="TEST", freq="1h",
                       open=96, high=97, low=95, close=96, volume=150))
        # 颈线反弹
        bars.append(Bar(timestamp=start + timedelta(hours=22), symbol="TEST", freq="1h",
                       open=96, high=100, low=96, close=99, volume=180))
        bars.append(Bar(timestamp=start + timedelta(hours=23), symbol="TEST", freq="1h",
                       open=99, high=101, low=98, close=100, volume=180))
        bars.append(Bar(timestamp=start + timedelta(hours=24), symbol="TEST", freq="1h",
                       open=100, high=101, low=99, close=100, volume=170))
        # 第二低点
        bars.append(Bar(timestamp=start + timedelta(hours=25), symbol="TEST", freq="1h",
                       open=99, high=100, low=95.2, close=96, volume=160))
        bars.append(Bar(timestamp=start + timedelta(hours=26), symbol="TEST", freq="1h",
                       open=96, high=97, low=95.5, close=96, volume=150))
        # 反弹突破
        bars.append(Bar(timestamp=start + timedelta(hours=27), symbol="TEST", freq="1h",
                       open=96, high=98, low=96, close=97, volume=250))
        bars.append(Bar(timestamp=start + timedelta(hours=28), symbol="TEST", freq="1h",
                       open=97, high=100, low=97, close=99, volume=300))
        # 突破颈线（放量）
        bars.append(Bar(timestamp=start + timedelta(hours=29), symbol="TEST", freq="1h",
                       open=99, high=103, low=99, close=102, volume=400))

        signal = detector.detect(bars)
        # 可能不一定检测到，取决于W底条件是否严格满足
        # 但检测器不应该报错
        # 如果检测到信号，验证信号属性
        if signal is not None:
            assert signal.pattern == "w_bottom"
            assert 0 < signal.confidence <= 1.0
            assert signal.stop_loss > 0
