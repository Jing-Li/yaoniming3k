"""W底形态检测器 - Pure Function Implementation"""

from typing import List, Optional, TYPE_CHECKING

from ..detector import PatternDetector, PatternSignal

if TYPE_CHECKING:
    from ...core.bar import Bar


class WBottomDetector(PatternDetector):
    """W底形态检测器

    检测两个相近低点后的颈线突破形态。

    W底形成条件：
    1. 两个低点位置接近（±5%容差）
    2. 两个低点之间有明显的高点（颈线）
    3. 价格突破颈线时确认形态

    置信度因素：
    - 完成度：两个低点越对称，置信度越高
    - 成交量：突破时放量增加置信度
    - 趋势：与上升趋势共振增强信号
    - 动量：突破力度影响置信度
    """

    def __init__(
        self,
        tolerance: float = 0.05,      # 双底容差 (±5%)
        min_neckline_height: float = 0.02,  # 颈线最小高度 (2%)
        stop_loss_factor: float = 0.93,    # 止损系数
        min_profit_pct: float = 0.03,       # 最小盈利目标
    ):
        """初始化W底检测器

        Args:
            tolerance: 双底容差，两个低点价格差异允许范围
            min_neckline_height: 颈线最小高度要求
            stop_loss_factor: 止损系数，止损 = 最低点 × factor
            min_profit_pct: 最小盈利目标百分比
        """
        super().__init__(name="w_bottom")
        self.tolerance = tolerance
        self.min_neckline_height = min_neckline_height
        self.stop_loss_factor = stop_loss_factor
        self.min_profit_pct = min_profit_pct

    def detect(self, bars: List["Bar"]) -> Optional[PatternSignal]:
        """检测W底形态

        Args:
            bars: K线列表，至少10根

        Returns:
            如果检测到W底突破，返回 PatternSignal
            否则返回 None
        """
        if len(bars) < 10:
            return None

        # 获取当前K线
        current_bar = bars[-1]

        # 找W底
        result = self._find_w_bottom(bars)
        if result is None:
            return None

        first_low_bar, first_low, second_low_bar, second_low, neckline = result

        # 检查是否突破颈线
        if current_bar.close > neckline:
            return self._create_breakout_signal(
                bars, current_bar, first_low_bar, first_low,
                second_low_bar, second_low, neckline
            )

        return None

    def _find_w_bottom(self, bars: List["Bar"]) -> Optional[tuple]:
        """寻找W底形态

        Args:
            bars: K线列表

        Returns:
            (first_low_bar, first_low, second_low_bar, second_low, neckline) 或 None
        """
        recent = bars[-10:]
        lows = [b.low for b in recent]

        if len(lows) < 10:
            return None

        # 找第一个低点（前5根）
        first_5_lows = lows[:5]
        first_low_idx = first_5_lows.index(min(first_5_lows))
        first_low = first_5_lows[first_low_idx]
        first_low_bar = recent[first_low_idx]

        # 找第二个低点（后5根，与第一个相近）
        second_low_candidates = [
            (b, b.low) for b in recent[5:]
            if abs(b.low - first_low) / first_low < self.tolerance
        ]
        if not second_low_candidates:
            return None

        second_low_bar, second_low = min(second_low_candidates, key=lambda x: x[1])

        # 找颈线（两个低点之间的高点）
        between_bars = [
            b for b in recent
            if first_low_bar.timestamp < b.timestamp < second_low_bar.timestamp
        ]
        if not between_bars:
            return None

        neckline = max(b.high for b in between_bars)

        # 检查颈线高度
        neckline_height = (neckline - first_low) / first_low
        if neckline_height < self.min_neckline_height:
            return None

        return (first_low_bar, first_low, second_low_bar, second_low, neckline)

    def _create_breakout_signal(
        self,
        bars: List["Bar"],
        bar: "Bar",
        first_low_bar: "Bar",
        first_low: float,
        second_low_bar: "Bar",
        second_low: float,
        neckline: float,
    ) -> PatternSignal:
        """创建突破信号

        Args:
            bars: K线列表
            bar: 当前K线
            first_low_bar: 第一个低点K线
            first_low: 第一个低点价格
            second_low_bar: 第二个低点K线
            second_low: 第二个低点价格
            neckline: 颈线价格

        Returns:
            PatternSignal
        """
        # 计算置信度
        confidence = self._calculate_w_confidence(
            bars, first_low, second_low, neckline, bar
        )

        # 计算止损和目标
        amplitude = neckline - min(first_low, second_low)
        target = max(neckline + amplitude, bar.close * (1 + self.min_profit_pct))
        stop_loss = min(first_low, second_low) * self.stop_loss_factor

        return self._create_signal(
            pattern="w_bottom",
            confidence=confidence,
            stop_loss=stop_loss,
            target=target,
            points=[
                {"timestamp": first_low_bar.timestamp.isoformat(),
                 "price": first_low, "label": "左底"},
                {"timestamp": second_low_bar.timestamp.isoformat(),
                 "price": second_low, "label": "右底"},
                {"timestamp": bar.timestamp.isoformat(),
                 "price": neckline, "label": "颈线突破"},
            ],
            neckline=neckline,
            amplitude=amplitude,
        )

    def _calculate_w_confidence(
        self,
        bars: List["Bar"],
        first_low: float,
        second_low: float,
        neckline: float,
        bar: "Bar",
    ) -> float:
        """计算W底置信度

        综合考虑：
        - 完成度：两个低点越接近，置信度越高
        - 成交量：突破时放量增加置信度
        - 趋势：与上升趋势共振增强信号
        - 动量：突破力度影响置信度

        Args:
            bars: K线列表
            first_low: 第一个低点价格
            second_low: 第二个低点价格
            neckline: 颈线价格
            bar: 当前K线

        Returns:
            置信度 0~1
        """
        # 完成度：两个低点越接近越好
        low_diff = abs(first_low - second_low) / first_low
        completion = 1.0 - min(1.0, low_diff / self.tolerance)

        # 成交量因子
        volume_ratio = self._volume_ratio(bars)
        volume = min(1.0, volume_ratio / 2.0)  # 归一化到0~1

        # 趋势因子：上升趋势中更可信
        is_uptrend = self._is_trend_up(bars, period=20)
        trend = 0.7 if is_uptrend else 0.3

        # 动量因子：突破力度
        breakout_pct = (bar.close - neckline) / neckline
        momentum = min(1.0, breakout_pct / 0.02)  # 2%以上算强突破

        return self._calculate_confidence(
            completion=completion,
            volume=volume,
            trend=trend,
            momentum=momentum,
        )
