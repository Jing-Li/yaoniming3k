"""M头形态检测器"""

from typing import List, Optional, Tuple, TYPE_CHECKING

from ..detector import PatternDetector, PatternSignal

if TYPE_CHECKING:
    from ...core.bar import Bar


class MTopDetector(PatternDetector):
    """M头形态检测器

    检测两个相近高点后的颈线跌破形态（M顶/双顶）。

    M头形成条件：
    1. 两个高点位置接近（±5%容差）
    2. 两个高点之间有明显的高点（颈线/支撑）
    3. 价格跌破颈线时确认形态

    置信度因素：
    - 完成度：两个高点越对称，置信度越高
    - 成交量：跌破时放量增加置信度
    - 趋势：与下降趋势共振增强信号
    - 动量：跌破力度影响置信度
    """

    def __init__(
        self,
        tolerance: float = 0.05,      # 双顶容差 (±5%)
        min_neckline_depth: float = 0.02,  # 颈线最小深度 (2%)
        stop_loss_factor: float = 1.02,    # 止损系数（高于最高点）
        min_profit_pct: float = 0.03,       # 最小盈利目标
    ):
        """初始化M头检测器

        Args:
            tolerance: 双顶容差，两个高点价格差异允许范围
            min_neckline_depth: 颈线最小深度要求
            stop_loss_factor: 止损系数，止损 = 最高点 × factor
            min_profit_pct: 最小盈利目标百分比
        """
        super().__init__(name="m_top")
        self.tolerance = tolerance
        self.min_neckline_depth = min_neckline_depth
        self.stop_loss_factor = stop_loss_factor
        self.min_profit_pct = min_profit_pct

        # 形态数据
        self._first_high_bar = None
        self._second_high_bar = None
        self._neckline = 0.0

    def detect(self) -> Optional[PatternSignal]:
        """检测M头形态

        Returns:
            如果检测到M头跌破，返回 PatternSignal（空头）
            否则返回 None
        """
        if len(self._bars) < 10:
            return None

        current_bar = self._bars[-1]

        # 找M头
        result = self._find_m_top()
        if result is None:
            return None

        first_high_bar, first_high, second_high_bar, second_high, neckline = result

        # 检查是否跌破颈线
        if current_bar.close < neckline:
            return self._create_breakdown_signal(
                current_bar, first_high_bar, first_high,
                second_high_bar, second_high, neckline
            )

        return None

    def _find_m_top(self) -> Optional[Tuple]:
        """寻找M头形态

        Returns:
            (first_high_bar, first_high, second_high_bar, second_high, neckline) 或 None
        """
        recent = self._bars[-10:]
        highs = [b.high for b in recent]

        if len(recent) < 10:
            return None

        # 找第一个高点（前5根）
        first_5_highs = highs[:5]
        first_high_idx = first_5_highs.index(max(first_5_highs))
        first_high = first_5_highs[first_high_idx]
        first_high_bar = recent[first_high_idx]

        # 找第二个高点（后5根，与第一个相近）
        second_high_candidates = [
            (b, b.high) for b in recent[5:]
            if abs(b.high - first_high) / first_high < self.tolerance
        ]
        if not second_high_candidates:
            return None

        second_high_bar, second_high = max(second_high_candidates, key=lambda x: x[1])

        # 找颈线（两个高点之间的低点）
        between_bars = [
            b for b in recent
            if first_high_bar.timestamp < b.timestamp < second_high_bar.timestamp
        ]
        if not between_bars:
            return None

        neckline = min(b.low for b in between_bars)

        # 检查颈线深度
        neckline_depth = (first_high - neckline) / first_high
        if neckline_depth < self.min_neckline_depth:
            return None

        return (first_high_bar, first_high, second_high_bar, second_high, neckline)

    def _create_breakdown_signal(
        self,
        bar: "Bar",
        first_high_bar: "Bar",
        first_high: float,
        second_high_bar: "Bar",
        second_high: float,
        neckline: float,
    ) -> PatternSignal:
        """创建跌破信号

        Args:
            bar: 当前K线
            first_high_bar: 第一个高点K线
            first_high: 第一个高点价格
            second_high_bar: 第二个高点K线
            second_high: 第二个高点价格
            neckline: 颈线价格

        Returns:
            PatternSignal (空头信号)
        """
        confidence = self._calculate_confidence(
            first_high, second_high, neckline, bar
        )

        # 计算止损和目标
        amplitude = max(first_high, second_high) - neckline
        target = neckline - amplitude
        stop_loss = max(first_high, second_high) * self.stop_loss_factor

        return self._create_signal(
            pattern="m_top",
            confidence=confidence,
            stop_loss=stop_loss,
            target=target,
            points=[
                {"timestamp": first_high_bar.timestamp.isoformat(),
                 "price": first_high, "label": "左顶"},
                {"timestamp": second_high_bar.timestamp.isoformat(),
                 "price": second_high, "label": "右顶"},
                {"timestamp": bar.timestamp.isoformat(),
                 "price": neckline, "label": "颈线跌破"},
            ],
            neckline=neckline,
            amplitude=amplitude,
            direction="short",  # 标记为空头信号
        )

    def _calculate_confidence(
        self,
        first_high: float,
        second_high: float,
        neckline: float,
        bar: "Bar",
    ) -> float:
        """计算M头置信度

        综合考虑：
        - 完成度：两个高点越接近，置信度越高
        - 成交量：跌破时放量增加置信度
        - 趋势：与下降趋势共振增强信号
        - 动量：跌破力度影响置信度

        Args:
            first_high: 第一个高点价格
            second_high: 第二个高点价格
            neckline: 颈线价格
            bar: 当前K线

        Returns:
            置信度 0~1
        """
        # 完成度：两个高点越接近越好
        high_diff = abs(first_high - second_high) / first_high
        completion = 1.0 - min(1.0, high_diff / self.tolerance)

        # 成交量因子
        volume_ratio = self._volume_ratio()
        volume = min(1.0, volume_ratio / 2.0)

        # 趋势因子：下降趋势中更可信
        is_downtrend = self._is_trend_down(period=20)
        trend = 0.7 if is_downtrend else 0.3

        # 动量因子：跌破力度
        breakdown_pct = (neckline - bar.close) / neckline
        momentum = min(1.0, breakdown_pct / 0.02)

        return super()._calculate_confidence(
            completion=completion,
            volume=volume,
            trend=trend,
            momentum=momentum,
        )

    def _on_reset(self) -> None:
        """重置检测器状态"""
        self._first_high_bar = None
        self._second_high_bar = None
        self._neckline = 0.0