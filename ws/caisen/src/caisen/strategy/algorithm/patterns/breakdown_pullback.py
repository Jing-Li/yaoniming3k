"""破底翻检测器 (Breakdown Pullback Detector)

价格跌破整理平台下沿（破底）后迅速拉回并站回平台内部（翻），形成强烈底部反转信号。
- 第一买点：站回颈线（下沿）时
- 第二买点：突破平台上沿时，置信度更高
"""

from typing import List, Optional, TYPE_CHECKING

from ..detector import PatternDetector, PatternSignal
from ._platform_utils import find_platform

if TYPE_CHECKING:
    from ...core.bar import Bar


class BreakdownPullbackDetector(PatternDetector):
    """破底翻检测器

    检测逻辑：
    1. 识别整理平台（上沿/下沿）
    2. 找破底事件（K线low < platform_lower，但跌幅不超过 tolerance）
    3. 确认翻回（max_pullback_bars根K线内close回到platform_lower之上）
    """

    def __init__(
        self,
        min_bars: int = 15,
        lookback_period: int = 30,
        max_amplitude: float = 0.05,
        min_platform_bars: int = 8,
        max_pullback_bars: int = 3,
        breakdown_tolerance: float = 0.03,
        stop_loss_factor: float = 0.93,
        min_profit_pct: float = 0.03,
    ):
        super().__init__(name="breakdown_pullback")
        self.min_bars = min_bars
        self.lookback_period = lookback_period
        self.max_amplitude = max_amplitude
        self.min_platform_bars = min_platform_bars
        self.max_pullback_bars = max_pullback_bars
        self.breakdown_tolerance = breakdown_tolerance
        self.stop_loss_factor = stop_loss_factor
        self.min_profit_pct = min_profit_pct

    def detect(self, bars: List["Bar"]) -> Optional[PatternSignal]:
        """检测破底翻形态

        Args:
            bars: K线列表

        Returns:
            如果检测到破底翻，返回 PatternSignal；否则返回 None
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

        # 2. 在平台结束后寻找破底事件
        breakdown = self._find_breakdown(bars, plat_end, platform_lower)
        if breakdown is None:
            return None

        breakdown_idx, breakdown_low = breakdown

        # 3. 确认翻回：破底后 max_pullback_bars 根K线内close站回platform_lower之上
        pullback = self._confirm_pullback(bars, breakdown_idx, platform_lower)
        if pullback is None:
            return None

        pullback_idx = pullback

        # 4. 判断买点类型
        if current_bar.close > platform_upper:
            # 第二买点：突破平台上沿
            buy_point = 2
            amplitude = platform_upper - platform_lower
            target = current_bar.close + amplitude
        elif current_bar.close > platform_lower:
            # 第一买点：站回颈线
            buy_point = 1
            target = platform_upper
        else:
            return None

        # 止损：破底最低点 * stop_loss_factor
        stop_loss = breakdown_low * self.stop_loss_factor

        # 5. 计算置信度
        confidence = self._calc_confidence(
            bars, platform_lower, breakdown_low, current_bar.close, buy_point,
            breakdown_idx, pullback_idx
        )

        # 6. 构建关键点
        points = [
            {"timestamp": bars[plat_start].timestamp, "price": platform_upper, "label": "平台上沿"},
            {"timestamp": bars[plat_start].timestamp, "price": platform_lower, "label": "平台下沿"},
            {"timestamp": bars[breakdown_idx].timestamp, "price": breakdown_low, "label": "破底低点"},
            {"timestamp": bars[pullback_idx].timestamp, "price": bars[pullback_idx].close, "label": "翻回确认"},
        ]

        return self._create_signal(
            pattern="breakdown_pullback",
            confidence=confidence,
            stop_loss=stop_loss,
            target=target,
            points=points,
            direction="long",
            platform_upper=platform_upper,
            platform_lower=platform_lower,
            breakdown_low=breakdown_low,
            buy_point=buy_point,
        )

    def _find_breakdown(
        self, bars: List["Bar"], plat_end: int, platform_lower: float
    ) -> Optional[tuple]:
        """寻找破底事件

        在平台结束后到当前K线之间，找K线low跌破platform_lower的事件。
        跌幅不超过breakdown_tolerance才算破底翻（太深就是破位了）。

        Returns:
            (breakdown_idx, breakdown_low) 或 None
        """
        # 从平台结束后开始搜索
        search_start = plat_end + 1
        search_end = len(bars) - 1  # 不包含当前K线（当前K线用于确认翻回）

        if search_start >= search_end:
            return None

        for i in range(search_start, search_end):
            if bars[i].low < platform_lower:
                # 检查跌幅是否在容忍范围内
                depth = platform_lower - bars[i].low
                if depth / platform_lower <= self.breakdown_tolerance:
                    return (i, bars[i].low)
                # 跌幅太深，不是破底翻
                return None

        return None

    def _confirm_pullback(
        self, bars: List["Bar"], breakdown_idx: int, platform_lower: float
    ) -> Optional[int]:
        """确认翻回

        在破底后 max_pullback_bars 根K线内，close回到platform_lower之上。

        Returns:
            翻回确认的K线索引，或 None
        """
        check_end = min(breakdown_idx + self.max_pullback_bars + 1, len(bars))

        for i in range(breakdown_idx + 1, check_end):
            if bars[i].close > platform_lower:
                return i

        return None

    def _calc_confidence(
        self,
        bars: List["Bar"],
        platform_lower: float,
        breakdown_low: float,
        current_close: float,
        buy_point: int,
        breakdown_idx: int = None,
        pullback_idx: int = None,
    ) -> float:
        """计算置信度

        四因子：
        - completion: 破底深度越浅、翻回越快，完成度越高
        - volume: 分阶段量能确认（破底放量、拉回缩量、突破放量）
        - trend: 破底前处于下跌趋势共振更强
        - momentum: 翻回力度
        """
        # completion: 破底深度越浅越好
        depth = platform_lower - breakdown_low
        completion = 1.0 - min(1.0, depth / platform_lower / self.breakdown_tolerance)
        # 第二买点完成度更高
        if buy_point == 2:
            completion = min(1.0, completion + 0.2)

        # volume: 分阶段量能确认
        volume = self._staged_volume_score(bars, breakdown_idx, pullback_idx)

        # trend: 前期下跌趋势共振
        trend = 0.7 if self._is_trend_down(bars, 20) else 0.3

        # momentum: 翻回力度
        momentum = min(1.0, (current_close - platform_lower) / platform_lower / 0.02)

        return self._calculate_confidence(
            completion=completion,
            volume=volume,
            trend=trend,
            momentum=momentum,
        )

    def _staged_volume_score(self, bars: List["Bar"], breakdown_idx: int = None, pullback_idx: int = None) -> float:
        """破底翻分阶段量能评分

        - 破底阶段：可以放量（恐慌抛售）
        - 拉回阶段：应缩量（卖压枯竭）
        - 突破阶段：应放量>=1.5倍

        Returns:
            量能评分 0~1
        """
        if breakdown_idx is None or pullback_idx is None:
            volume_ratio = self._volume_ratio(bars)
            return min(1.0, volume_ratio / 2.0)

        breakout_idx = len(bars) - 1
        stages = []

        # 拉回阶段：应缩量（卖压枯竭）
        if pullback_idx > breakdown_idx + 1:
            stages.append({
                'name': 'pullback',
                'start_idx': breakdown_idx + 1,
                'end_idx': pullback_idx,
                'expect': 'shrink',
            })

        # 突破阶段：应放量
        if breakout_idx > pullback_idx:
            stages.append({
                'name': 'breakout',
                'start_idx': pullback_idx,
                'end_idx': breakout_idx,
                'expect': 'expand',
            })

        if not stages:
            volume_ratio = self._volume_ratio(bars)
            return min(1.0, volume_ratio / 2.0)

        result = self.volume_analyzer.staged_volume_check(bars, stages)
        return result['score']
