"""旗形/矩形/圆弧底/杯柄/过前高 检测器"""

from typing import List, Optional, Tuple, TYPE_CHECKING

from ..detector import PatternDetector, PatternSignal

if TYPE_CHECKING:
    from ...core.bar import Bar


class FlagDetector(PatternDetector):
    """旗形整理检测器

    检测旗形整理（短暂整理后延续原趋势）：
    - 上升旗形：向上突破 → 买入
    - 下降旗形：向下跌破 → 卖出
    """

    def __init__(
        self,
        min_bars: int = 8,
        max_bars: int = 20,
        stop_loss_factor: float = 0.93,
        min_profit_pct: float = 0.03,
    ):
        super().__init__(name="flag")
        self.min_bars = min_bars
        self.max_bars = max_bars
        self.stop_loss_factor = stop_loss_factor
        self.min_profit_pct = min_profit_pct

    def detect(self) -> Optional[PatternSignal]:
        if len(self._bars) < self.min_bars:
            return None

        current_bar = self._bars[-1]

        # 找旗杆（最近的大幅涨跌）
        result = self._find_flag_pole()
        if result is None:
            return None

        pole_start_idx, pole_direction, pole_height, pole_avg = result

        # 找旗面（整理区间）
        flag_result = self._find_flag_surface(pole_start_idx, pole_direction, pole_avg)
        if flag_result is None:
            return None

        upper_line, lower_line = flag_result

        # 检查突破
        if pole_direction == "up":
            if current_bar.close > upper_line:
                return self._create_breakout_signal(
                    current_bar, upper_line, lower_line, pole_height, "long"
                )
        else:
            if current_bar.close < lower_line:
                return self._create_breakout_signal(
                    current_bar, upper_line, lower_line, pole_height, "short"
                )

        return None

    def _find_flag_pole(self) -> Optional[Tuple]:
        """寻找旗杆"""
        recent = self._bars[-self.max_bars:-1]

        if len(recent) < 5:
            return None

        # 计算近期波动
        max_high = max(b.high for b in recent)
        min_low = min(b.low for b in recent)
        amplitude = max_high - min_low
        avg_price = (max_high + min_low) / 2

        # 旗杆应该超过平均价格的5%
        if amplitude / avg_price < 0.05:
            return None

        # 判断方向
        if recent[-1].close > recent[0].close:
            direction = "up"
        else:
            direction = "down"

        return (0, direction, amplitude, avg_price)

    def _find_flag_surface(self, pole_start_idx: int, direction: str, avg_price: float) -> Optional[Tuple]:
        """寻找旗面（整理区间）"""
        recent = self._bars[-10:-1]

        if len(recent) < 3:
            return None

        # 简单实现：找高低点
        if direction == "up":
            upper = max(b.high for b in recent)
            lower = min(b.low for b in recent)
        else:
            upper = max(b.high for b in recent)
            lower = min(b.low for b in recent)

        # 旗面应该比旗杆窄
        flag_width = upper - lower
        if flag_width / avg_price > 0.02:  # 振幅太大，不是旗形
            return None

        return (upper, lower)

    def _create_breakout_signal(
        self, bar: "Bar", upper: float, lower: float, pole_height: float, direction: str
    ) -> PatternSignal:
        confidence = 0.6  # 简化实现，固定置信度

        if direction == "long":
            target = bar.close + pole_height
            stop_loss = lower * self.stop_loss_factor
        else:
            target = bar.close - pole_height
            stop_loss = upper * 1.02

        return self._create_signal(
            pattern="flag",
            confidence=confidence,
            stop_loss=stop_loss,
            target=target,
            points=[],
            direction=direction,
        )

    def _on_reset(self) -> None:
        pass


class RectangleDetector(PatternDetector):
    """矩形整理检测器

    检测矩形整理（价格在水平区间内波动）：
    - 向上突破上沿 → 买入
    - 向下跌破下沿 → 卖出
    """

    def __init__(
        self,
        min_bars: int = 10,
        max_amplitude: float = 0.05,
        stop_loss_factor: float = 0.93,
        min_profit_pct: float = 0.03,
    ):
        super().__init__(name="rectangle")
        self.min_bars = min_bars
        self.max_amplitude = max_amplitude
        self.stop_loss_factor = stop_loss_factor
        self.min_profit_pct = min_profit_pct

    def detect(self) -> Optional[PatternSignal]:
        if len(self._bars) < self.min_bars:
            return None

        current_bar = self._bars[-1]
        recent = self._bars[-self.min_bars:-1]

        upper = max(b.high for b in recent)
        lower = min(b.low for b in recent)
        amplitude = upper - lower
        avg_price = (upper + lower) / 2

        # 检查是否满足矩形条件
        if amplitude / avg_price > self.max_amplitude:
            return None

        # 检查突破
        if current_bar.close > upper:
            confidence = self._calculate_confidence(amplitude, avg_price, "up")
            target = bar.close + amplitude
            stop_loss = lower * self.stop_loss_factor

            return self._create_signal(
                pattern="rectangle",
                confidence=confidence,
                stop_loss=stop_loss,
                target=target,
                points=[],
                upper=upper,
                lower=lower,
                direction="long",
            )
        elif current_bar.close < lower:
            confidence = self._calculate_confidence(amplitude, avg_price, "down")
            target = bar.close - amplitude
            stop_loss = upper * 1.02

            return self._create_signal(
                pattern="rectangle",
                confidence=confidence,
                stop_loss=stop_loss,
                target=target,
                points=[],
                upper=upper,
                lower=lower,
                direction="short",
            )

        return None

    def _calculate_confidence(self, amplitude: float, avg_price: float, direction: str) -> float:
        completion = 1.0 - min(1.0, amplitude / avg_price / self.max_amplitude)
        volume = min(1.0, self._volume_ratio() / 2.0)

        if direction == "long":
            trend = 0.7 if self._is_trend_up(20) else 0.3
        else:
            trend = 0.7 if self._is_trend_down(20) else 0.3

        return self._calculate_confidence(completion=completion, volume=volume, trend=trend, momentum=0.5)


class RoundingBottomDetector(PatternDetector):
    """圆弧底检测器

    检测圆弧底形态（缓慢筑底后上涨）：
    - 价格形成圆弧低点
    - 向上突破颈线 → 买入
    """

    def __init__(
        self,
        min_bars: int = 15,
        stop_loss_factor: float = 0.93,
        min_profit_pct: float = 0.03,
    ):
        super().__init__(name="rounding_bottom")
        self.min_bars = min_bars
        self.stop_loss_factor = stop_loss_factor
        self.min_profit_pct = min_profit_pct

    def detect(self) -> Optional[PatternSignal]:
        if len(self._bars) < self.min_bars:
            return None

        current_bar = self._bars[-1]
        result = self._find_rounding_bottom()

        if result is None:
            return None

        low_idx, neckline = result

        if current_bar.close > neckline:
            confidence = 0.7  # 简化实现
            amplitude = neckline - self._bars[low_idx].low
            target = neckline + amplitude
            stop_loss = self._bars[low_idx].low * self.stop_loss_factor

            return self._create_signal(
                pattern="rounding_bottom",
                confidence=confidence,
                stop_loss=stop_loss,
                target=target,
                points=[],
                neckline=neckline,
                direction="long",
            )

        return None

    def _find_rounding_bottom(self) -> Optional[Tuple]:
        """寻找圆弧底"""
        recent = self._bars[-self.min_bars:-1]

        if len(recent) < 10:
            return None

        # 找最低点（应该在中间区域）
        lows = [(i, b.low) for i, b in enumerate(recent)]
        low_idx, low_price = min(lows, key=lambda x: x[1])

        # 最低点应该在中间（不是太靠前或太靠后）
        if low_idx < len(recent) // 3 or low_idx > 2 * len(recent) // 3:
            return None

        # 颈线 = 左侧高点
        left_highs = [b.high for b in recent[:low_idx]]
        if not left_highs:
            return None
        neckline = max(left_highs)

        return (low_idx, neckline)

    def _on_reset(self) -> None:
        pass


class CupHandleDetector(PatternDetector):
    """杯柄形态检测器

    检测杯柄形态（像茶杯一样的走势）：
    - 杯身：圆弧形上涨
    - 柄部：短暂回调
    - 向上突破柄部高点 → 买入
    """

    def __init__(
        self,
        min_bars: int = 20,
        stop_loss_factor: float = 0.93,
        min_profit_pct: float = 0.03,
    ):
        super().__init__(name="cup_handle")
        self.min_bars = min_bars
        self.stop_loss_factor = stop_loss_factor
        self.min_profit_pct = min_profit_pct

    def detect(self) -> Optional[PatternSignal]:
        if len(self._bars) < self.min_bars:
            return None

        current_bar = self._bars[-1]
        result = self._find_cup_handle()

        if result is None:
            return None

        handle_high, cup_bottom, cup_high = result

        if current_bar.close > handle_high:
            confidence = 0.75  # 简化实现
            amplitude = cup_high - cup_bottom
            target = current_bar.close + amplitude
            stop_loss = cup_bottom * self.stop_loss_factor

            return self._create_signal(
                pattern="cup_handle",
                confidence=confidence,
                stop_loss=stop_loss,
                target=target,
                points=[],
                handle_high=handle_high,
                cup_high=cup_high,
                direction="long",
            )

        return None

    def _find_cup_handle(self) -> Optional[Tuple]:
        """寻找杯柄形态"""
        recent = self._bars[-self.min_bars:-1]

        if len(recent) < 15:
            return None

        # 简化：找杯底和柄
        highs = [b.high for b in recent]
        lows = [b.low for b in recent]

        # 找最高点（应该在杯的右侧）
        max_idx = highs.index(max(highs))
        if max_idx < len(recent) // 2:
            return None

        # 找最低点（在最高点之前）
        min_before_max = min(lows[:max_idx])
        min_idx = lows.index(min_before_max)

        # 找柄部高点（在最低点之后，最高点之前）
        handle_candidates = highs[min_idx+1:max_idx]
        if not handle_candidates:
            return None

        handle_high = max(handle_candidates)

        return (handle_high, min_before_max, max(highs))

    def _on_reset(self) -> None:
        pass


class BreakoutPullbackDetector(PatternDetector):
    """过前高检测器

    检测过前高形态（突破历史高点后回调再涨）：
    - 价格突破前期高点
    - 回踩后再次上涨 → 买入
    """

    def __init__(
        self,
        lookback_period: int = 30,
        stop_loss_factor: float = 0.93,
        min_profit_pct: float = 0.03,
    ):
        super().__init__(name="breakout_pullback")
        self.lookback_period = lookback_period
        self.stop_loss_factor = stop_loss_factor
        self.min_profit_pct = min_profit_pct

        self._breakout_high = 0.0
        self._in_pullback = False

    def detect(self) -> Optional[PatternSignal]:
        if len(self._bars) < self.lookback_period:
            return None

        current_bar = self._bars[-1]
        previous = self._bars[-2] if len(self._bars) > 1 else None

        # 找前高
        lookback = self._bars[-self.lookback_period:-1]
        previous_high = max(b.high for b in lookback)

        # 检查突破
        if previous and previous.close > previous_high and self._breakout_high == 0:
            self._breakout_high = previous_high
            self._in_pullback = True

        # 检查回踩后上涨
        if self._in_pullback and current_bar.close > self._breakout_high:
            confidence = 0.7  # 简化实现
            amplitude = current_bar.close - self._breakout_high
            target = current_bar.close + amplitude
            stop_loss = self._breakout_high * self.stop_loss_factor

            self._in_pullback = False

            return self._create_signal(
                pattern="breakout_pullback",
                confidence=confidence,
                stop_loss=stop_loss,
                target=target,
                points=[],
                breakout_high=self._breakout_high,
                direction="long",
            )

        # 如果回调太深，重置
        if self._in_pullback and current_bar.low < self._breakout_high * 0.95:
            self._in_pullback = False

        return None

    def _on_reset(self) -> None:
        self._breakout_high = 0.0
        self._in_pullback = False