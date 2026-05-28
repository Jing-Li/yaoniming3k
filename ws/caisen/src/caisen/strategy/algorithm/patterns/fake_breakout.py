"""假突破检测器 (Fake Breakout Detector)

价格突破整理平台上沿后迅速跌回平台内部，是破底翻的反向关系，
代表顶部或中继陷阱。本质是主力诱多出货。

信号方向：short（看空）
"""

from typing import List, Optional, TYPE_CHECKING

from ..detector import PatternDetector, PatternSignal
from ._platform_utils import find_platform

if TYPE_CHECKING:
    from ....core.bar import Bar


class FakeBreakoutFeatures:
    """蔡森理论假突破五大特征评估

    五大特征：
    1. 突破量能不足 - 突破时成交量低于均量
    2. 快速回返颈线 - 突破后快速回到颈线附近
    3. 回到形态内部 - 价格重新进入整理区间
    4. 跳空缺口无法弥补 - 突破时跳空但未回补
    5. 量价背离 - 价格新高但成交量不创新高
    """

    def __init__(
        self,
        volume_period: int = 20,
        volume_threshold: float = 1.5,
        return_bars: int = 3,
    ):
        """
        Args:
            volume_period: 计算均量的周期
            volume_threshold: 放量倍数阈值（低于此值视为量能不足）
            return_bars: 快速回返的最大K线数
        """
        self.volume_period = volume_period
        self.volume_threshold = volume_threshold
        self.return_bars = return_bars

    def check_volume_insufficient(
        self, bars: List["Bar"], breakout_idx: int
    ) -> tuple:
        """特征1：突破量能不足

        突破当根K线成交量 < volume_threshold倍的前period均量

        Returns:
            (是否触发, 评分0~1)
        """
        if breakout_idx < self.volume_period or breakout_idx >= len(bars):
            return (False, 0.0)

        breakout_volume = bars[breakout_idx].volume
        start = max(0, breakout_idx - self.volume_period)
        period_bars = bars[start:breakout_idx]

        if not period_bars:
            return (False, 0.0)

        avg_volume = sum(b.volume for b in period_bars) / len(period_bars)
        if avg_volume == 0:
            return (False, 0.0)

        ratio = breakout_volume / avg_volume

        # 量能不足：突破量 < threshold倍均量
        if ratio < self.volume_threshold:
            # 评分：量越小越可疑，ratio=0 -> score=1, ratio=threshold -> score=0
            score = 1.0 - (ratio / self.volume_threshold)
            return (True, min(1.0, max(0.0, score)))

        return (False, 0.0)

    def check_quick_return(
        self, bars: List["Bar"], breakout_idx: int, neckline: float
    ) -> tuple:
        """特征2：快速回返颈线

        突破后return_bars根K线内价格回到颈线附近（±1%）

        Returns:
            (是否触发, 评分0~1)
        """
        if breakout_idx >= len(bars) - 1:
            return (False, 0.0)

        check_end = min(breakout_idx + self.return_bars + 1, len(bars))
        tolerance = neckline * 0.01  # ±1%

        for i in range(breakout_idx + 1, check_end):
            close = bars[i].close
            # 价格回到颈线附近或以下
            if close <= neckline + tolerance:
                # 回返越快评分越高
                bars_taken = i - breakout_idx
                score = 1.0 - (bars_taken - 1) / max(1, self.return_bars)
                return (True, min(1.0, max(0.0, score)))

        return (False, 0.0)

    def check_return_to_range(
        self,
        bars: List["Bar"],
        breakout_idx: int,
        range_high: float,
        range_low: float,
    ) -> tuple:
        """特征3：回到形态内部

        价格重新进入 [range_low, range_high] 整理区间

        Returns:
            (是否触发, 评分0~1)
        """
        if breakout_idx >= len(bars) - 1:
            return (False, 0.0)

        check_end = min(breakout_idx + self.return_bars + 2, len(bars))

        for i in range(breakout_idx + 1, check_end):
            close = bars[i].close
            if range_low <= close <= range_high:
                # 回到区间内：越靠近下沿越危险
                range_width = range_high - range_low
                if range_width == 0:
                    score = 0.5
                else:
                    # close越接近range_low，score越高
                    score = 1.0 - (close - range_low) / range_width
                return (True, min(1.0, max(0.0, score)))

        return (False, 0.0)

    def check_unfilled_gap(
        self, bars: List["Bar"], breakout_idx: int
    ) -> tuple:
        """特征4：跳空缺口无法弥补

        突破时存在向上跳空（当根open > 前根high）
        但后续K线未能有效填补缺口

        Returns:
            (是否触发, 评分0~1)
        """
        if breakout_idx < 1 or breakout_idx >= len(bars):
            return (False, 0.0)

        prev_bar = bars[breakout_idx - 1]
        breakout_bar = bars[breakout_idx]

        # 检查是否存在向上跳空
        gap_bottom = prev_bar.high
        gap_top = breakout_bar.open

        if gap_top <= gap_bottom:
            # 无跳空
            return (False, 0.0)

        gap_size = gap_top - gap_bottom

        # 检查后续K线是否填补了缺口
        check_end = min(breakout_idx + self.return_bars + 1, len(bars))
        gap_filled = False

        for i in range(breakout_idx + 1, check_end):
            if bars[i].low <= gap_bottom:
                gap_filled = True
                break

        if not gap_filled:
            # 缺口未填补 — 假突破特征
            # 缺口越大评分越高
            score = min(1.0, gap_size / (gap_bottom * 0.02))
            return (True, min(1.0, max(0.0, score)))

        return (False, 0.0)

    def check_divergence(
        self, bars: List["Bar"], breakout_idx: int, lookback: int = 10
    ) -> tuple:
        """特征5：量价背离

        价格创新高（或接近前高）但成交量未创新高
        对比breakout_idx前lookback根K线的最高量

        Returns:
            (是否触发, 评分0~1)
        """
        if breakout_idx < lookback or breakout_idx >= len(bars):
            return (False, 0.0)

        start = max(0, breakout_idx - lookback)
        lookback_bars = bars[start:breakout_idx]

        if not lookback_bars:
            return (False, 0.0)

        # 找前期最高价和对应的成交量
        max_price = max(b.high for b in lookback_bars)
        max_volume = max(b.volume for b in lookback_bars)

        breakout_bar = bars[breakout_idx]

        # 价格创新高或接近前高（95%以上）
        price_near_high = breakout_bar.high >= max_price * 0.95

        if not price_near_high:
            return (False, 0.0)

        # 成交量是否低于前期最高量
        if max_volume > 0 and breakout_bar.volume < max_volume:
            # 量价背离：价格新高但量不足
            volume_ratio = breakout_bar.volume / max_volume
            # ratio越低背离越严重
            score = 1.0 - volume_ratio
            return (True, min(1.0, max(0.0, score)))

        return (False, 0.0)

    def evaluate(
        self,
        bars: List["Bar"],
        breakout_idx: int,
        neckline: float,
        range_high: float,
        range_low: float,
    ) -> dict:
        """综合评估假突破概率

        Returns:
            {
                'fake_probability': float (0~1),
                'triggered_count': int,
                'features': { ... },
                'recommendation': 'genuine' | 'suspicious' | 'likely_fake'
            }
        """
        # 权重配置
        weights = {
            'volume_insufficient': 0.30,
            'quick_return': 0.25,
            'return_to_range': 0.20,
            'divergence': 0.15,
            'unfilled_gap': 0.10,
        }

        # 检测各特征
        vol_triggered, vol_score = self.check_volume_insufficient(bars, breakout_idx)
        qr_triggered, qr_score = self.check_quick_return(bars, breakout_idx, neckline)
        rr_triggered, rr_score = self.check_return_to_range(
            bars, breakout_idx, range_high, range_low
        )
        gap_triggered, gap_score = self.check_unfilled_gap(bars, breakout_idx)
        div_triggered, div_score = self.check_divergence(bars, breakout_idx)

        features = {
            'volume_insufficient': {'triggered': vol_triggered, 'score': vol_score},
            'quick_return': {'triggered': qr_triggered, 'score': qr_score},
            'return_to_range': {'triggered': rr_triggered, 'score': rr_score},
            'unfilled_gap': {'triggered': gap_triggered, 'score': gap_score},
            'divergence': {'triggered': div_triggered, 'score': div_score},
        }

        # 计算加权概率
        fake_probability = (
            vol_score * weights['volume_insufficient']
            + qr_score * weights['quick_return']
            + rr_score * weights['return_to_range']
            + gap_score * weights['unfilled_gap']
            + div_score * weights['divergence']
        )
        fake_probability = min(1.0, max(0.0, fake_probability))

        triggered_count = sum(
            1 for f in features.values() if f['triggered']
        )

        # 推荐
        if fake_probability >= 0.6:
            recommendation = 'likely_fake'
        elif fake_probability >= 0.3:
            recommendation = 'suspicious'
        else:
            recommendation = 'genuine'

        return {
            'fake_probability': fake_probability,
            'triggered_count': triggered_count,
            'features': features,
            'recommendation': recommendation,
        }


class FakeBreakoutDetector(PatternDetector):
    """假突破检测器

    检测逻辑：
    1. 识别整理平台（上沿/下沿）
    2. 找假突破事件（K线high > platform_upper，但突破幅度不超过 tolerance）
    3. 确认跌回（max_fallback_bars根K线内close回到platform_upper之下）
    4. 使用 FakeBreakoutFeatures 深度评估五大特征
    """

    def __init__(
        self,
        min_bars: int = 15,
        lookback_period: int = 30,
        max_amplitude: float = 0.05,
        min_platform_bars: int = 8,
        max_fallback_bars: int = 3,
        fake_tolerance: float = 0.03,
        stop_loss_factor: float = 1.02,
        min_profit_pct: float = 0.03,
    ):
        super().__init__(name="fake_breakout")
        self.min_bars = min_bars
        self.lookback_period = lookback_period
        self.max_amplitude = max_amplitude
        self.min_platform_bars = min_platform_bars
        self.max_fallback_bars = max_fallback_bars
        self.fake_tolerance = fake_tolerance
        self.stop_loss_factor = stop_loss_factor
        self.min_profit_pct = min_profit_pct
        self.features_evaluator = FakeBreakoutFeatures()

    def detect(self, bars: List["Bar"]) -> Optional[PatternSignal]:
        """检测假突破形态

        Args:
            bars: K线列表

        Returns:
            如果检测到假突破，返回 PatternSignal；否则返回 None
        """
        if len(bars) < self.min_bars:
            return None

        current_bar = bars[-1]

        # 1. 识别整理平台
        platform = find_platform(
            bars,
            lookback_period=self.lookback_period,
            max_amplitude=self.max_amplitude,
            min_platform_bars=self.min_platform_bars,
        )
        if platform is None:
            return None

        platform_upper, platform_lower, plat_start, plat_end = platform

        # 2. 在平台结束后寻找假突破事件
        fake_break = self._find_fake_break(bars, plat_end, platform_upper)
        if fake_break is None:
            return None

        fake_idx, fake_high = fake_break

        # 3. 确认跌回：假突破后 max_fallback_bars 根K线内close回到platform_upper之下
        fallback_idx = self._confirm_fallback(bars, fake_idx, platform_upper)
        if fallback_idx is None:
            return None

        # 4. 判断信号强度
        if current_bar.close < platform_lower:
            # 跌破平台下沿 - 更强的看空信号
            signal_strength = 2
            amplitude = platform_upper - platform_lower
            target = current_bar.close - amplitude
        elif current_bar.close < platform_upper:
            # 跌回平台内 - 基本看空信号
            signal_strength = 1
            target = platform_lower
        else:
            # 还在上沿之上，假突破尚未确认
            return None

        # 止损：假突破最高点 * stop_loss_factor
        stop_loss = fake_high * self.stop_loss_factor

        # 5. 使用五大特征深度评估
        features_result = self.features_evaluator.evaluate(
            bars=bars,
            breakout_idx=fake_idx,
            neckline=platform_upper,
            range_high=platform_upper,
            range_low=platform_lower,
        )

        # 6. 计算置信度（融合五大特征评估）
        confidence = self._calc_confidence(
            bars, platform_upper, fake_high, current_bar.close, signal_strength
        )
        # 五大特征加成：fake_probability 越高，置信度越高
        fake_prob = features_result['fake_probability']
        confidence = min(1.0, confidence + fake_prob * 0.2)

        # 7. 构建关键点
        points = [
            {"timestamp": bars[plat_start].timestamp, "price": platform_upper, "label": "平台上沿"},
            {"timestamp": bars[plat_start].timestamp, "price": platform_lower, "label": "平台下沿"},
            {"timestamp": bars[fake_idx].timestamp, "price": fake_high, "label": "假突破高点"},
            {"timestamp": bars[fallback_idx].timestamp, "price": bars[fallback_idx].close, "label": "跌回确认"},
        ]

        return self._create_signal(
            pattern="fake_breakout",
            confidence=confidence,
            stop_loss=stop_loss,
            target=target,
            points=points,
            direction="short",
            platform_upper=platform_upper,
            platform_lower=platform_lower,
            fake_high=fake_high,
            signal_strength=signal_strength,
            fake_probability=fake_prob,
            features_evaluation=features_result,
        )

    def _find_fake_break(
        self, bars: List["Bar"], plat_end: int, platform_upper: float
    ) -> Optional[tuple]:
        """寻找假突破事件

        在平台结束后到当前K线之间，找K线high突破platform_upper的事件。
        突破幅度不超过fake_tolerance才算假突破（太深就是真突破了）。

        Returns:
            (fake_idx, fake_high) 或 None
        """
        search_start = plat_end + 1
        search_end = len(bars) - 1

        if search_start >= search_end:
            return None

        for i in range(search_start, search_end):
            if bars[i].high > platform_upper:
                # 检查突破幅度是否在容忍范围内
                height = bars[i].high - platform_upper
                if height / platform_upper <= self.fake_tolerance:
                    return (i, bars[i].high)
                # 突破幅度太大，可能是真突破
                return None

        return None

    def _confirm_fallback(
        self, bars: List["Bar"], fake_idx: int, platform_upper: float
    ) -> Optional[int]:
        """确认跌回

        在假突破后 max_fallback_bars 根K线内，close回到platform_upper之下。

        Returns:
            跌回确认的K线索引，或 None
        """
        check_end = min(fake_idx + self.max_fallback_bars + 1, len(bars))

        for i in range(fake_idx + 1, check_end):
            if bars[i].close < platform_upper:
                return i

        return None

    def _calc_confidence(
        self,
        bars: List["Bar"],
        platform_upper: float,
        fake_high: float,
        current_close: float,
        signal_strength: int,
    ) -> float:
        """计算置信度

        四因子：
        - completion: 假突破幅度越浅、跌回越快，完成度越高
        - volume: 假突破时放量（诱多出货特征）
        - trend: 突破前处于上涨趋势（趋势末期）共振更强
        - momentum: 跌回力度
        """
        # completion: 假突破幅度越浅越好
        height = fake_high - platform_upper
        completion = 1.0 - min(1.0, height / platform_upper / self.fake_tolerance)
        # 跌破下沿完成度更高
        if signal_strength == 2:
            completion = min(1.0, completion + 0.2)

        # volume: 假突破放量（诱多出货）
        volume_ratio = self._volume_ratio(bars)
        volume = min(1.0, volume_ratio / 2.0)

        # trend: 突破前上涨趋势（趋势末期）共振
        trend = 0.7 if self._is_trend_up(bars, 20) else 0.3

        # momentum: 跌回力度
        momentum = min(1.0, (platform_upper - current_close) / platform_upper / 0.02)

        return self._calculate_confidence(
            completion=completion,
            volume=volume,
            trend=trend,
            momentum=momentum,
        )
