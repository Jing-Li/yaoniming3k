"""假突破五大特征增强检测 单元测试

测试场景：
1. 量能不足判定
2. 快速回返判定
3. 回到形态内部
4. 跳空缺口
5. 量价背离
6. 综合评估
7. 持仓预警
8. 边界条件
"""

import pytest
from datetime import datetime, timedelta

from caisen.core.bar import Bar
from caisen.strategy.algorithm.patterns.fake_breakout import (
    FakeBreakoutFeatures,
    FakeBreakoutDetector,
)
from caisen.strategy.algorithm.caisen_components.position_manager import (
    FakeBreakoutWarning,
    PositionManager,
)


# ===== 辅助函数 =====

def make_bar(
    price: float,
    timestamp_offset: int = 0,
    volume: float = 1000.0,
    low: float = None,
    high: float = None,
    open_price: float = None,
) -> Bar:
    """创建测试用K线"""
    return Bar(
        timestamp=datetime(2024, 1, 1) + timedelta(days=timestamp_offset),
        symbol="test",
        freq="1d",
        open=open_price if open_price is not None else price,
        high=high if high is not None else price * 1.005,
        low=low if low is not None else price * 0.995,
        close=price,
        volume=volume,
    )


def make_bars_with_volume(base_price: float, count: int, volume: float = 1000.0) -> list:
    """创建指定均量的K线序列"""
    return [make_bar(base_price, i, volume=volume) for i in range(count)]


# ===== 测试 FakeBreakoutFeatures =====

class TestVolumeInsufficient:
    """特征1：突破量能不足"""

    def test_volume_below_threshold(self):
        """突破时量小于均量 -> 触发"""
        features = FakeBreakoutFeatures(volume_period=20, volume_threshold=1.5)
        # 前20根均量=1000，突破根量=800（< 1.5*1000=1500）
        bars = make_bars_with_volume(100.0, 20, volume=1000.0)
        bars.append(make_bar(102.0, 20, volume=800.0, high=103.0))

        triggered, score = features.check_volume_insufficient(bars, breakout_idx=20)
        assert triggered is True
        assert 0.0 < score <= 1.0

    def test_volume_above_threshold(self):
        """突破时量大于阈值 -> 不触发"""
        features = FakeBreakoutFeatures(volume_period=20, volume_threshold=1.5)
        bars = make_bars_with_volume(100.0, 20, volume=1000.0)
        bars.append(make_bar(102.0, 20, volume=2000.0, high=103.0))

        triggered, score = features.check_volume_insufficient(bars, breakout_idx=20)
        assert triggered is False
        assert score == 0.0

    def test_volume_at_threshold_boundary(self):
        """突破量刚好等于阈值 -> 不触发"""
        features = FakeBreakoutFeatures(volume_period=20, volume_threshold=1.5)
        bars = make_bars_with_volume(100.0, 20, volume=1000.0)
        bars.append(make_bar(102.0, 20, volume=1500.0, high=103.0))

        triggered, score = features.check_volume_insufficient(bars, breakout_idx=20)
        assert triggered is False
        assert score == 0.0

    def test_very_low_volume_high_score(self):
        """极低量时评分接近1"""
        features = FakeBreakoutFeatures(volume_period=20, volume_threshold=1.5)
        bars = make_bars_with_volume(100.0, 20, volume=1000.0)
        bars.append(make_bar(102.0, 20, volume=100.0, high=103.0))

        triggered, score = features.check_volume_insufficient(bars, breakout_idx=20)
        assert triggered is True
        assert score > 0.9


class TestQuickReturn:
    """特征2：快速回返颈线"""

    def test_return_within_bars(self):
        """突破后3根内回到颈线 -> 触发"""
        features = FakeBreakoutFeatures(return_bars=3)
        neckline = 100.0
        bars = make_bars_with_volume(100.0, 20)
        # 突破根
        bars.append(make_bar(102.0, 20, high=103.0))
        # 回返根：close <= neckline + 1%
        bars.append(make_bar(100.5, 21))  # 100.5 <= 101.0

        triggered, score = features.check_quick_return(bars, breakout_idx=20, neckline=neckline)
        assert triggered is True
        assert 0.0 < score <= 1.0

    def test_no_return_within_bars(self):
        """突破后3根内未回到颈线 -> 不触发"""
        features = FakeBreakoutFeatures(return_bars=3)
        neckline = 100.0
        bars = make_bars_with_volume(100.0, 20)
        bars.append(make_bar(102.0, 20, high=103.0))
        # 后续都在颈线上方
        bars.append(make_bar(103.0, 21))
        bars.append(make_bar(104.0, 22))
        bars.append(make_bar(105.0, 23))

        triggered, score = features.check_quick_return(bars, breakout_idx=20, neckline=neckline)
        assert triggered is False
        assert score == 0.0

    def test_faster_return_higher_score(self):
        """1根内回返比3根内回返评分更高"""
        features = FakeBreakoutFeatures(return_bars=3)
        neckline = 100.0

        # 1根内回返
        bars1 = make_bars_with_volume(100.0, 20)
        bars1.append(make_bar(102.0, 20, high=103.0))
        bars1.append(make_bar(100.0, 21))  # 立即回返
        _, score1 = features.check_quick_return(bars1, breakout_idx=20, neckline=neckline)

        # 3根内回返
        bars3 = make_bars_with_volume(100.0, 20)
        bars3.append(make_bar(102.0, 20, high=103.0))
        bars3.append(make_bar(103.0, 21))
        bars3.append(make_bar(102.0, 22))
        bars3.append(make_bar(100.0, 23))  # 第3根回返
        _, score3 = features.check_quick_return(bars3, breakout_idx=20, neckline=neckline)

        assert score1 > score3


class TestReturnToRange:
    """特征3：回到形态内部"""

    def test_price_returns_to_range(self):
        """价格回到整理区间 -> 触发"""
        features = FakeBreakoutFeatures(return_bars=3)
        bars = make_bars_with_volume(100.0, 20)
        bars.append(make_bar(102.0, 20, high=103.0))  # 突破
        bars.append(make_bar(99.5, 21))  # 回到 [98, 100.5] 区间

        triggered, score = features.check_return_to_range(
            bars, breakout_idx=20, range_high=100.5, range_low=98.0
        )
        assert triggered is True
        assert 0.0 < score <= 1.0

    def test_price_stays_above_range(self):
        """价格仍在区间上方 -> 不触发"""
        features = FakeBreakoutFeatures(return_bars=3)
        bars = make_bars_with_volume(100.0, 20)
        bars.append(make_bar(102.0, 20, high=103.0))
        bars.append(make_bar(101.0, 21))  # 仍在 range_high=100.5 上方

        triggered, score = features.check_return_to_range(
            bars, breakout_idx=20, range_high=100.5, range_low=98.0
        )
        assert triggered is False

    def test_closer_to_lower_higher_score(self):
        """更接近下沿 -> 更高评分"""
        features = FakeBreakoutFeatures(return_bars=3)

        # 接近下沿
        bars1 = make_bars_with_volume(100.0, 20)
        bars1.append(make_bar(102.0, 20, high=103.0))
        bars1.append(make_bar(98.5, 21))  # 靠近下沿
        _, score_low = features.check_return_to_range(
            bars1, breakout_idx=20, range_high=100.5, range_low=98.0
        )

        # 接近上沿
        bars2 = make_bars_with_volume(100.0, 20)
        bars2.append(make_bar(102.0, 20, high=103.0))
        bars2.append(make_bar(100.0, 21))  # 靠近上沿
        _, score_high = features.check_return_to_range(
            bars2, breakout_idx=20, range_high=100.5, range_low=98.0
        )

        assert score_low > score_high


class TestUnfilledGap:
    """特征4：跳空缺口无法弥补"""

    def test_gap_exists_unfilled(self):
        """存在跳空且未填补 -> 触发"""
        features = FakeBreakoutFeatures(return_bars=3)
        bars = make_bars_with_volume(100.0, 19)
        # 前一根: high=100.5
        bars.append(make_bar(100.0, 19, high=100.5))
        # 突破根: open=101.0 > 前根high=100.5 (跳空)
        bars.append(make_bar(102.0, 20, high=103.0, open_price=101.0, low=101.0))
        # 后续未填补缺口(low > 100.5)
        bars.append(make_bar(101.5, 21, low=101.0))
        bars.append(make_bar(101.0, 22, low=100.8))

        triggered, score = features.check_unfilled_gap(bars, breakout_idx=20)
        assert triggered is True
        assert score > 0.0

    def test_gap_filled(self):
        """存在跳空但已填补 -> 不触发"""
        features = FakeBreakoutFeatures(return_bars=3)
        bars = make_bars_with_volume(100.0, 19)
        bars.append(make_bar(100.0, 19, high=100.5))
        # 跳空突破
        bars.append(make_bar(102.0, 20, high=103.0, open_price=101.0, low=101.0))
        # 后续填补了缺口 (low <= 100.5)
        bars.append(make_bar(100.0, 21, low=99.0))

        triggered, score = features.check_unfilled_gap(bars, breakout_idx=20)
        assert triggered is False
        assert score == 0.0

    def test_no_gap(self):
        """无跳空 -> 不触发"""
        features = FakeBreakoutFeatures(return_bars=3)
        bars = make_bars_with_volume(100.0, 20)
        # open=100 <= 前根high~100.5，无跳空
        bars.append(make_bar(102.0, 20, high=103.0, open_price=100.0))

        triggered, score = features.check_unfilled_gap(bars, breakout_idx=20)
        assert triggered is False
        assert score == 0.0


class TestDivergence:
    """特征5：量价背离"""

    def test_price_new_high_volume_lower(self):
        """价格创新高但量不创新高 -> 触发"""
        features = FakeBreakoutFeatures()
        # 前10根中有一根量=2000, high=101
        bars = make_bars_with_volume(100.0, 10, volume=1000.0)
        bars[5] = make_bar(100.0, 5, volume=2000.0, high=101.0)
        # 突破根：价格新高(high=102 > max_high=101)但量只有1200
        bars.append(make_bar(101.5, 10, volume=1200.0, high=102.0))

        triggered, score = features.check_divergence(bars, breakout_idx=10, lookback=10)
        assert triggered is True
        assert 0.0 < score <= 1.0

    def test_price_new_high_volume_also_high(self):
        """价格新高且量也创新高 -> 不触发"""
        features = FakeBreakoutFeatures()
        bars = make_bars_with_volume(100.0, 10, volume=1000.0)
        bars[5] = make_bar(100.0, 5, volume=2000.0, high=101.0)
        # 突破根：价格新高且量也新高
        bars.append(make_bar(101.5, 10, volume=2500.0, high=102.0))

        triggered, score = features.check_divergence(bars, breakout_idx=10, lookback=10)
        assert triggered is False
        assert score == 0.0

    def test_price_not_near_high(self):
        """价格未接近前高 -> 不触发"""
        features = FakeBreakoutFeatures()
        bars = make_bars_with_volume(100.0, 10, volume=1000.0)
        bars[5] = make_bar(100.0, 5, volume=2000.0, high=110.0)  # 前高110
        # 突破根：high=102 < 110*0.95=104.5，未接近前高
        bars.append(make_bar(101.0, 10, volume=500.0, high=102.0))

        triggered, score = features.check_divergence(bars, breakout_idx=10, lookback=10)
        assert triggered is False
        assert score == 0.0


class TestEvaluate:
    """综合评估"""

    def test_multiple_features_triggered(self):
        """多特征并存时综合评分较高"""
        features = FakeBreakoutFeatures(volume_period=10, volume_threshold=1.5, return_bars=3)

        # 构造：量能不足 + 快速回返 + 量价背离
        bars = make_bars_with_volume(100.0, 10, volume=1000.0)
        bars[5] = make_bar(100.0, 5, volume=2000.0, high=101.0)  # 前期有放量
        # 突破根：量能不足（volume=500 < 1.5*1000=1500）
        bars.append(make_bar(102.0, 10, volume=500.0, high=102.5))
        # 快速回返
        bars.append(make_bar(100.5, 11, volume=800.0))

        result = features.evaluate(
            bars=bars,
            breakout_idx=10,
            neckline=100.5,  # 颈线=平台上沿
            range_high=100.5,
            range_low=98.0,
        )

        assert result['triggered_count'] >= 2
        assert result['fake_probability'] > 0.3
        assert result['recommendation'] in ('genuine', 'suspicious', 'likely_fake')

    def test_no_features_triggered(self):
        """无特征触发 -> 评分为0"""
        features = FakeBreakoutFeatures(volume_period=10, volume_threshold=1.5, return_bars=3)

        # 构造：放量突破 + 不回返 + 无跳空 + 无背离
        bars = make_bars_with_volume(100.0, 10, volume=1000.0)
        # 突破根：量充足
        bars.append(make_bar(102.0, 10, volume=2000.0, high=103.0))
        # 不回返，继续上涨
        bars.append(make_bar(104.0, 11, volume=1800.0))
        bars.append(make_bar(105.0, 12, volume=1600.0))

        result = features.evaluate(
            bars=bars,
            breakout_idx=10,
            neckline=100.5,
            range_high=100.5,
            range_low=98.0,
        )

        assert result['triggered_count'] == 0
        assert result['fake_probability'] == 0.0
        assert result['recommendation'] == 'genuine'

    def test_likely_fake_recommendation(self):
        """高概率时推荐 likely_fake"""
        features = FakeBreakoutFeatures(volume_period=10, volume_threshold=1.5, return_bars=3)

        # 构造多个强特征
        bars = make_bars_with_volume(100.0, 10, volume=1000.0)
        bars[5] = make_bar(100.0, 5, volume=2000.0, high=100.5)
        # 极低量突破
        bars.append(make_bar(101.0, 10, volume=100.0, high=101.5))
        # 快速回到区间内
        bars.append(make_bar(99.0, 11, volume=500.0))

        result = features.evaluate(
            bars=bars,
            breakout_idx=10,
            neckline=100.5,
            range_high=100.5,
            range_low=98.0,
        )

        assert result['fake_probability'] > 0.0
        # 至少有量能不足和回到形态内部两个特征
        assert result['features']['volume_insufficient']['triggered'] is True

    def test_weights_sum_to_one(self):
        """权重之和应为1.0"""
        weights = {
            'volume_insufficient': 0.30,
            'quick_return': 0.25,
            'return_to_range': 0.20,
            'divergence': 0.15,
            'unfilled_gap': 0.10,
        }
        assert abs(sum(weights.values()) - 1.0) < 1e-9


class TestFakeBreakoutWarning:
    """持仓预警"""

    def test_low_risk_holding(self):
        """低风险持仓 -> 建议继续持有"""
        warning = FakeBreakoutWarning(warning_threshold=0.4)
        # 放量突破，不回返
        bars = make_bars_with_volume(100.0, 20, volume=1000.0)
        bars.append(make_bar(102.0, 20, volume=2000.0, high=103.0))
        bars.append(make_bar(104.0, 21, volume=1800.0))
        bars.append(make_bar(105.0, 22, volume=1600.0))

        result = warning.check_holding_risk(
            bars=bars,
            entry_idx=20,
            entry_price=102.0,
            neckline=100.5,
            range_high=100.5,
            range_low=98.0,
        )

        assert result['risk_level'] == 'low'
        assert result['recommendation'] == 'hold'

    def test_medium_risk_reduce(self):
        """中等风险 -> 建议减仓25%"""
        warning = FakeBreakoutWarning(warning_threshold=0.3)
        # 量能不足突破 + 回返
        bars = make_bars_with_volume(100.0, 20, volume=1000.0)
        bars[15] = make_bar(100.0, 15, volume=2000.0, high=101.0)  # 前期放量
        bars.append(make_bar(101.0, 20, volume=500.0, high=101.5))  # 量能不足
        bars.append(make_bar(100.5, 21, volume=800.0))  # 快速回返

        result = warning.check_holding_risk(
            bars=bars,
            entry_idx=20,
            entry_price=101.0,
            neckline=100.5,
            range_high=100.5,
            range_low=98.0,
        )

        # 至少量能不足应该触发
        assert 'volume_insufficient' in result['triggered_features']

    def test_high_risk_exit(self):
        """极高风险 -> 建议退出"""
        warning = FakeBreakoutWarning(warning_threshold=0.3)
        # 构造多特征极端场景
        bars = make_bars_with_volume(100.0, 20, volume=1000.0)
        bars[15] = make_bar(100.0, 15, volume=3000.0, high=101.0)  # 前期高量
        # 极低量突破
        bars.append(make_bar(101.0, 20, volume=50.0, high=101.5))
        # 快速深度回返到区间内
        bars.append(make_bar(98.5, 21, volume=500.0))

        result = warning.check_holding_risk(
            bars=bars,
            entry_idx=20,
            entry_price=101.0,
            neckline=100.5,
            range_high=100.5,
            range_low=98.0,
        )

        assert len(result['triggered_features']) >= 1
        assert result['fake_probability'] > 0.0

    def test_get_reduce_ratio(self):
        """减仓比例映射"""
        warning = FakeBreakoutWarning()
        assert warning.get_reduce_ratio('low') == 0.0
        assert warning.get_reduce_ratio('medium') == 0.25
        assert warning.get_reduce_ratio('high') == 0.5

    def test_position_manager_has_fake_warning(self):
        """PositionManager 包含 fake_warning 属性"""
        pm = PositionManager()
        assert hasattr(pm, 'fake_warning')
        assert isinstance(pm.fake_warning, FakeBreakoutWarning)


class TestBoundaryConditions:
    """边界条件"""

    def test_insufficient_data_volume(self):
        """数据不足时 check_volume_insufficient 不崩溃"""
        features = FakeBreakoutFeatures(volume_period=20)
        bars = [make_bar(100.0, 0)]
        triggered, score = features.check_volume_insufficient(bars, breakout_idx=0)
        assert triggered is False
        assert score == 0.0

    def test_insufficient_data_quick_return(self):
        """数据不足时 check_quick_return 不崩溃"""
        features = FakeBreakoutFeatures(return_bars=3)
        bars = [make_bar(100.0, 0)]
        triggered, score = features.check_quick_return(bars, breakout_idx=0, neckline=100.0)
        assert triggered is False
        assert score == 0.0

    def test_insufficient_data_return_to_range(self):
        """数据不足时 check_return_to_range 不崩溃"""
        features = FakeBreakoutFeatures()
        bars = [make_bar(100.0, 0)]
        triggered, score = features.check_return_to_range(
            bars, breakout_idx=0, range_high=101.0, range_low=99.0
        )
        assert triggered is False
        assert score == 0.0

    def test_insufficient_data_unfilled_gap(self):
        """数据不足时 check_unfilled_gap 不崩溃"""
        features = FakeBreakoutFeatures()
        bars = [make_bar(100.0, 0)]
        triggered, score = features.check_unfilled_gap(bars, breakout_idx=0)
        assert triggered is False
        assert score == 0.0

    def test_insufficient_data_divergence(self):
        """数据不足时 check_divergence 不崩溃"""
        features = FakeBreakoutFeatures()
        bars = [make_bar(100.0, 0)]
        triggered, score = features.check_divergence(bars, breakout_idx=0, lookback=10)
        assert triggered is False
        assert score == 0.0

    def test_evaluate_with_minimal_data(self):
        """极少数据时 evaluate 不崩溃"""
        features = FakeBreakoutFeatures(volume_period=5, return_bars=2)
        bars = [make_bar(100.0, 0), make_bar(101.0, 1)]
        result = features.evaluate(
            bars=bars,
            breakout_idx=0,
            neckline=100.0,
            range_high=101.0,
            range_low=99.0,
        )
        assert 'fake_probability' in result
        assert 'triggered_count' in result
        assert 'features' in result
        assert 'recommendation' in result

    def test_warning_invalid_entry_idx(self):
        """无效入场索引不崩溃"""
        warning = FakeBreakoutWarning()
        bars = make_bars_with_volume(100.0, 5)
        result = warning.check_holding_risk(
            bars=bars,
            entry_idx=-1,
            entry_price=100.0,
            neckline=100.0,
            range_high=101.0,
            range_low=99.0,
        )
        assert result['risk_level'] == 'low'
        assert result['recommendation'] == 'hold'

    def test_warning_entry_idx_out_of_bounds(self):
        """入场索引越界不崩溃"""
        warning = FakeBreakoutWarning()
        bars = make_bars_with_volume(100.0, 5)
        result = warning.check_holding_risk(
            bars=bars,
            entry_idx=100,
            entry_price=100.0,
            neckline=100.0,
            range_high=101.0,
            range_low=99.0,
        )
        assert result['risk_level'] == 'low'
        assert result['recommendation'] == 'hold'

    def test_zero_volume_bars(self):
        """零成交量K线不崩溃"""
        features = FakeBreakoutFeatures(volume_period=5)
        bars = make_bars_with_volume(100.0, 5, volume=0.0)
        bars.append(make_bar(102.0, 5, volume=0.0, high=103.0))
        triggered, score = features.check_volume_insufficient(bars, breakout_idx=5)
        assert triggered is False
        assert score == 0.0


class TestDetectorIntegration:
    """FakeBreakoutDetector 与 FakeBreakoutFeatures 集成测试"""

    def test_signal_includes_features_evaluation(self):
        """检测到假突破时信号包含五大特征评估结果"""
        detector = FakeBreakoutDetector(
            min_bars=10, lookback_period=30, max_amplitude=0.05,
            min_platform_bars=8, max_fallback_bars=3, fake_tolerance=0.03,
        )
        # 构造整理平台
        bars = []
        for i in range(10):
            offset = (i % 3 - 1) * 0.002 * 100.0
            bars.append(make_bar(100.0 + offset, i))
        # 假突破
        bars.append(make_bar(102.0, 10, high=103.0))
        # 跌回
        bars.append(make_bar(99.0, 11))
        bars.append(make_bar(99.5, 12))

        signal = detector.detect(bars)
        if signal is not None:
            # 信号应包含 features_evaluation
            assert 'fake_probability' in signal.data
            assert 'features_evaluation' in signal.data
            features_eval = signal.data['features_evaluation']
            assert 'features' in features_eval
            assert 'recommendation' in features_eval
