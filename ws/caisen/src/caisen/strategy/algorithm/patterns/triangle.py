"""三角整理形态检测器 - Pure Function Implementation"""

from typing import List, Optional, Tuple, TYPE_CHECKING

from ..detector import PatternDetector, PatternSignal

if TYPE_CHECKING:
    from ...core.bar import Bar


class TriangleDetector(PatternDetector):
    """对称三角形检测器

    检测对称三角形（高点下降、低点上升，收敛）：
    - 向上突破上沿趋势线 → 买入信号
    - 向下跌破下沿趋势线 → 卖出信号

    形成条件：
    1. 至少3个高点，呈下降趋势
    2. 至少3个低点，呈上升趋势
    3. 两趋势线收敛
    """

    def __init__(
        self,
        min_bars: int = 11,
        min_highs: int = 3,
        min_lows: int = 3,
        stop_loss_factor: float = 0.93,
        min_profit_pct: float = 0.03,
    ):
        super().__init__(name="triangle")
        self.min_bars = min_bars
        self.min_highs = min_highs
        self.min_lows = min_lows
        self.stop_loss_factor = stop_loss_factor
        self.min_profit_pct = min_profit_pct

    def detect(self, bars: List["Bar"]) -> Optional[PatternSignal]:
        """检测三角形形态

        Args:
            bars: K线列表，至少min_bars根

        Returns:
            如果检测到突破，返回 PatternSignal
            否则返回 None
        """
        if len(bars) < self.min_bars:
            return None

        current_bar = bars[-1]
        result = self._find_triangle(bars)

        if result is None:
            return None

        upper_trendline, lower_trendline, high_points, low_points, direction = result

        # 检查突破
        if direction == "up" and current_bar.close > upper_trendline:
            return self._create_breakout_signal(
                bars, current_bar, upper_trendline, lower_trendline,
                high_points, low_points, "long"
            )
        elif direction == "down" and current_bar.close < lower_trendline:
            return self._create_breakout_signal(
                bars, current_bar, upper_trendline, lower_trendline,
                high_points, low_points, "short"
            )

        return None

    def _find_triangle(self, bars: List["Bar"]) -> Optional[Tuple]:
        """寻找对称三角形

        Args:
            bars: K线列表

        Returns:
            (upper_trendline, lower_trendline, high_points, low_points, direction) 或 None
        """
        recent = bars[-self.min_bars:-1]  # 不包括当前K线

        # 找高点（下降趋势）
        highs = [(i, b.high) for i, b in enumerate(recent)]
        highs_sorted = sorted(highs, key=lambda x: x[1], reverse=True)[:self.min_highs]
        highs_sorted = sorted(highs_sorted, key=lambda x: x[0])

        if len(highs_sorted) < self.min_highs:
            return None

        # 检查高点是否递减
        if not all(highs_sorted[i][1] > highs_sorted[i+1][1] for i in range(len(highs_sorted)-1)):
            return None

        # 找低点（上升趋势）
        lows = [(i, b.low) for i, b in enumerate(recent)]
        lows_sorted = sorted(lows, key=lambda x: x[1])[:self.min_lows]
        lows_sorted = sorted(lows_sorted, key=lambda x: x[0])

        if len(lows_sorted) < self.min_lows:
            return None

        # 检查低点是否递增
        if not all(lows_sorted[i][1] < lows_sorted[i+1][1] for i in range(len(lows_sorted)-1)):
            return None

        # 计算下降趋势线
        x1_h, y1_h = highs_sorted[0]
        x2_h, y2_h = highs_sorted[-1]
        if x2_h == x1_h:
            return None

        m1 = (y2_h - y1_h) / (x2_h - x1_h)
        b1 = y1_h - m1 * x1_h

        # 计算上升趋势线
        x1_l, y1_l = lows_sorted[0]
        x2_l, y2_l = lows_sorted[-1]
        if x2_l == x1_l:
            return None

        m2 = (y2_l - y1_l) / (x2_l - x1_l)
        b2 = y1_l - m2 * x1_l

        # 检查是否收敛（两线斜率相反）
        if m1 >= 0 or m2 <= 0:
            return None

        # 当前K线索引
        current_idx = len(recent) - 1

        upper_trendline = m1 * current_idx + b1
        lower_trendline = m2 * current_idx + b2

        # 确定突破方向
        direction = "up" if m1 < 0 and m2 > 0 else "down"

        high_points = [(recent[i].timestamp, p) for i, p in highs_sorted]
        low_points = [(recent[i].timestamp, p) for i, p in lows_sorted]

        return (upper_trendline, lower_trendline, high_points, low_points, direction)

    def _create_breakout_signal(
        self, bars: List["Bar"], bar: "Bar",
        upper_trendline: float, lower_trendline: float,
        high_points: List, low_points: List, direction: str
    ) -> PatternSignal:
        """创建突破信号

        Args:
            bars: K线列表
            bar: 当前K线
            upper_trendline: 上趋势线价格
            lower_trendline: 下趋势线价格
            high_points: 高点列表
            low_points: 低点列表
            direction: 突破方向 ("long" or "short")

        Returns:
            PatternSignal
        """
        confidence = self._calculate_triangle_confidence(
            bars, upper_trendline, lower_trendline, direction, bar
        )

        amplitude = upper_trendline - lower_trendline

        if direction == "long":
            target = bar.close + amplitude
            stop_loss = lower_trendline * self.stop_loss_factor
        else:
            target = bar.close - amplitude
            stop_loss = upper_trendline * 1.02

        return self._create_signal(
            pattern="triangle",
            confidence=confidence,
            stop_loss=stop_loss,
            target=target,
            points=[
                {"timestamp": ts, "price": price, "label": label}
                for ts, price in high_points + low_points
            ],
            upper_trendline=upper_trendline,
            lower_trendline=lower_trendline,
            direction=direction,
            amplitude=amplitude,
        )

    def _calculate_triangle_confidence(
        self, bars: List["Bar"],
        upper_trendline: float, lower_trendline: float,
        direction: str, bar: "Bar"
    ) -> float:
        """计算三角形置信度

        Args:
            bars: K线列表
            upper_trendline: 上趋势线价格
            lower_trendline: 下趋势线价格
            direction: 突破方向
            bar: 当前K线

        Returns:
            置信度 0~1
        """
        # 完成度：收敛越紧密越好
        amplitude = upper_trendline - lower_trendline
        # 振幅越小，形态越紧凑，置信度越高
        avg_price = (upper_trendline + lower_trendline) / 2
        completion = 1.0 - min(1.0, amplitude / avg_price)

        # 成交量
        volume = min(1.0, self._volume_ratio(bars) / 2.0)

        # 趋势
        if direction == "long":
            is_uptrend = self._is_trend_up(bars, period=20)
            trend = 0.7 if is_uptrend else 0.3
        else:
            is_downtrend = self._is_trend_down(bars, period=20)
            trend = 0.7 if is_downtrend else 0.3

        # 动量
        if direction == "long":
            breakout_pct = (bar.close - upper_trendline) / upper_trendline
        else:
            breakout_pct = (lower_trendline - bar.close) / lower_trendline
        momentum = min(1.0, breakout_pct / 0.02)

        return self._calculate_confidence(
            completion=completion, volume=volume, trend=trend, momentum=momentum
        )
