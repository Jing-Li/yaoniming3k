"""旗形/矩形/圆弧底/杯柄/过前高 检测器 - Pure Function Implementation"""

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

    def detect(self, bars: List["Bar"]) -> Optional[PatternSignal]:
        """检测旗形形态

        Args:
            bars: K线列表

        Returns:
            如果检测到突破，返回 PatternSignal
            否则返回 None
        """
        if len(bars) < self.min_bars:
            return None

        self._last_bars = bars  # 保存引用用于量能分析
        current_bar = bars[-1]

        # 找旗杆（最近的大幅涨跌）
        result = self._find_flag_pole(bars)
        if result is None:
            return None

        pole_start_idx, pole_direction, pole_height, pole_avg = result

        # 找旗面（整理区间）
        flag_result = self._find_flag_surface(bars, pole_start_idx, pole_direction, pole_avg)
        if flag_result is None:
            return None

        upper_line, lower_line = flag_result

        # 检查突破
        pole_start_bar = bars[-self.max_bars] if len(bars) >= self.max_bars else bars[0]
        if pole_direction == "up":
            if current_bar.close > upper_line:
                return self._create_breakout_signal(
                    current_bar, upper_line, lower_line, pole_height, "long",
                    pole_start_bar=pole_start_bar,
                )
        else:
            if current_bar.close < lower_line:
                return self._create_breakout_signal(
                    current_bar, upper_line, lower_line, pole_height, "short",
                    pole_start_bar=pole_start_bar,
                )

        return None

    def _find_flag_pole(self, bars: List["Bar"]) -> Optional[Tuple]:
        """寻找旗杆

        Args:
            bars: K线列表

        Returns:
            (pole_start_idx, pole_direction, pole_height, pole_avg) 或 None
        """
        recent = bars[-self.max_bars:-1]

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

    def _find_flag_surface(self, bars: List["Bar"], pole_start_idx: int, direction: str, avg_price: float) -> Optional[Tuple]:
        """寻找旗面（整理区间）

        Args:
            bars: K线列表
            pole_start_idx: 旗杆起始索引
            direction: 旗杆方向
            avg_price: 平均价格

        Returns:
            (upper_line, lower_line) 或 None
        """
        recent = bars[-10:-1]

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
        self, bar: "Bar", upper: float, lower: float, pole_height: float, direction: str,
        pole_start_bar: "Bar" = None,
    ) -> PatternSignal:
        """创建突破信号

        Args:
            bar: 当前K线
            upper: 上边界
            lower: 下边界
            pole_height: 旗杆高度
            direction: 方向
            pole_start_bar: 旗杆起始K线

        Returns:
            PatternSignal
        """
        # 量能确认：旗形突破应放量
        volume_grade = self.volume_analyzer.grade(self._last_bars, len(self._last_bars) - 1) if hasattr(self, '_last_bars') else 'normal'
        if volume_grade == 'strong':
            confidence = 0.75
        elif volume_grade == 'normal':
            confidence = 0.6
        else:
            confidence = 0.45

        if direction == "long":
            target = bar.close + pole_height
            stop_loss = lower * self.stop_loss_factor
        else:
            target = bar.close - pole_height
            stop_loss = upper * 1.02

        # 构造可视化关键点
        points = []
        if pole_start_bar is not None:
            points.append({"timestamp": pole_start_bar.timestamp.isoformat(),
                           "price": pole_start_bar.close, "label": "旗杆起点"})
        points.append({"timestamp": bar.timestamp.isoformat(),
                       "price": bar.close, "label": "突破点"})

        return self._create_signal(
            pattern="flag",
            confidence=confidence,
            stop_loss=stop_loss,
            target=target,
            points=points,
            direction=direction,
            volume_grade=volume_grade,
        )


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

    def detect(self, bars: List["Bar"]) -> Optional[PatternSignal]:
        """检测矩形形态

        Args:
            bars: K线列表

        Returns:
            如果检测到突破，返回 PatternSignal
            否则返回 None
        """
        if len(bars) < self.min_bars:
            return None

        current_bar = bars[-1]
        recent = bars[-self.min_bars-1:-1]

        upper = max(b.high for b in recent)
        lower = min(b.low for b in recent)
        amplitude = upper - lower
        avg_price = (upper + lower) / 2

        # 检查是否满足矩形条件
        if amplitude / avg_price > self.max_amplitude:
            return None

        # 找上下边界对应的K线（用于可视化关键点）
        upper_bar = max(recent, key=lambda b: b.high)
        lower_bar = min(recent, key=lambda b: b.low)

        # 检查突破
        if current_bar.close > upper:
            confidence = self._calculate_rect_confidence(bars, amplitude, avg_price, "up")
            target = current_bar.close + amplitude
            stop_loss = lower * self.stop_loss_factor

            return self._create_signal(
                pattern="rectangle",
                confidence=confidence,
                stop_loss=stop_loss,
                target=target,
                points=[
                    {"timestamp": upper_bar.timestamp.isoformat(),
                     "price": upper, "label": "上沿"},
                    {"timestamp": lower_bar.timestamp.isoformat(),
                     "price": lower, "label": "下沿"},
                    {"timestamp": current_bar.timestamp.isoformat(),
                     "price": current_bar.close, "label": "突破"},
                ],
                upper=upper,
                lower=lower,
                direction="long",
            )
        elif current_bar.close < lower:
            confidence = self._calculate_rect_confidence(bars, amplitude, avg_price, "down")
            target = current_bar.close - amplitude
            stop_loss = upper * 1.02

            return self._create_signal(
                pattern="rectangle",
                confidence=confidence,
                stop_loss=stop_loss,
                target=target,
                points=[
                    {"timestamp": upper_bar.timestamp.isoformat(),
                     "price": upper, "label": "上沿"},
                    {"timestamp": lower_bar.timestamp.isoformat(),
                     "price": lower, "label": "下沿"},
                    {"timestamp": current_bar.timestamp.isoformat(),
                     "price": current_bar.close, "label": "跌破"},
                ],
                upper=upper,
                lower=lower,
                direction="short",
            )

        return None

    def _calculate_rect_confidence(self, bars: List["Bar"], amplitude: float, avg_price: float, direction: str) -> float:
        """计算矩形置信度

        Args:
            bars: K线列表
            amplitude: 振幅
            avg_price: 平均价格
            direction: 方向

        Returns:
            置信度 0~1
        """
        completion = 1.0 - min(1.0, amplitude / avg_price / self.max_amplitude)

        # 量能确认：矩形突破应放量
        volume_grade = self.volume_analyzer.grade(bars, len(bars) - 1)
        if volume_grade == 'strong':
            volume = 0.9
        elif volume_grade == 'normal':
            volume = 0.6
        else:
            volume = 0.3

        if direction == "long":
            trend = 0.7 if self._is_trend_up(bars, 20) else 0.3
        else:
            trend = 0.7 if self._is_trend_down(bars, 20) else 0.3

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

    def detect(self, bars: List["Bar"]) -> Optional[PatternSignal]:
        """检测圆弧底形态

        Args:
            bars: K线列表

        Returns:
            如果检测到突破，返回 PatternSignal
            否则返回 None
        """
        if len(bars) < self.min_bars:
            return None

        current_bar = bars[-1]
        result = self._find_rounding_bottom(bars)

        if result is None:
            return None

        low_idx, neckline = result

        if current_bar.close > neckline:
            # 量能确认：圆弧底完成期应逐步放量
            # 检查后半段K线量能是否递增
            recent_bars = bars[-self.min_bars:]
            mid_point = len(recent_bars) // 2
            indices = list(range(mid_point, len(recent_bars)))
            # 简化：取几个关键点检查递增
            key_indices = [len(bars) - self.min_bars + mid_point,
                          len(bars) - self.min_bars + (mid_point + len(recent_bars)) // 2,
                          len(bars) - 1]
            key_indices = [i for i in key_indices if 0 <= i < len(bars)]
            is_progressive = self.volume_analyzer.progressive_volume(bars, key_indices)

            volume_grade = self.volume_analyzer.grade(bars, len(bars) - 1)
            if is_progressive and volume_grade == 'strong':
                confidence = 0.85
            elif is_progressive or volume_grade != 'weak':
                confidence = 0.7
            else:
                confidence = 0.5

            amplitude = neckline - bars[-self.min_bars + low_idx].low
            target = neckline + amplitude
            stop_loss = bars[-self.min_bars + low_idx].low * self.stop_loss_factor

            # 构造圆弧底可视化关键点
            left_rim_bar = bars[-self.min_bars - 1] if len(bars) > self.min_bars else bars[0]
            bottom_bar = bars[-self.min_bars + low_idx]
            round_points = [
                {"timestamp": left_rim_bar.timestamp.isoformat(),
                 "price": left_rim_bar.high, "label": "左沿"},
                {"timestamp": bottom_bar.timestamp.isoformat(),
                 "price": bottom_bar.low, "label": "弧底"},
                {"timestamp": current_bar.timestamp.isoformat(),
                 "price": current_bar.close, "label": "突破颈线"},
            ]

            return self._create_signal(
                pattern="rounding_bottom",
                confidence=confidence,
                stop_loss=stop_loss,
                target=target,
                points=round_points,
                neckline=neckline,
                direction="long",
                volume_progressive=is_progressive,
                volume_grade=volume_grade,
            )

        return None

    def _find_rounding_bottom(self, bars: List["Bar"]) -> Optional[Tuple]:
        """寻找圆弧底

        Args:
            bars: K线列表

        Returns:
            (low_idx, neckline) 或 None
        """
        recent = bars[-self.min_bars-1:-1]

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

    def detect(self, bars: List["Bar"]) -> Optional[PatternSignal]:
        """检测杯柄形态

        Args:
            bars: K线列表

        Returns:
            如果检测到突破，返回 PatternSignal
            否则返回 None
        """
        if len(bars) < self.min_bars:
            return None

        current_bar = bars[-1]
        result = self._find_cup_handle(bars)

        if result is None:
            return None

        handle_high, cup_bottom, cup_high = result

        if current_bar.close > handle_high:
            # 量能确认：杯柄突破应放量
            volume_grade = self.volume_analyzer.grade(bars, len(bars) - 1)
            if volume_grade == 'strong':
                confidence = 0.85
            elif volume_grade == 'normal':
                confidence = 0.7
            else:
                confidence = 0.55

            amplitude = cup_high - cup_bottom
            target = current_bar.close + amplitude
            stop_loss = cup_bottom * self.stop_loss_factor

            # 构造杯柄形态可视化关键点
            recent = bars[-self.min_bars-1:-1]
            left_rim_bar = recent[0]
            max_idx = [b.high for b in recent].index(max(b.high for b in recent))
            min_before_max = min(b.low for b in recent[:max_idx]) if max_idx > 0 else cup_bottom
            min_idx = [b.low for b in recent[:max_idx+1]].index(min_before_max) if max_idx > 0 else 0
            cup_bottom_bar = bars[-self.min_bars - 1 + min_idx]
            cup_right_bar = bars[-self.min_bars - 1 + max_idx]
            cup_points = [
                {"timestamp": left_rim_bar.timestamp.isoformat(),
                 "price": left_rim_bar.high, "label": "左沿"},
                {"timestamp": cup_bottom_bar.timestamp.isoformat(),
                 "price": cup_bottom_bar.low, "label": "杯底"},
                {"timestamp": cup_right_bar.timestamp.isoformat(),
                 "price": cup_right_bar.high, "label": "右沿"},
                {"timestamp": current_bar.timestamp.isoformat(),
                 "price": current_bar.close, "label": "突破"},
            ]

            return self._create_signal(
                pattern="cup_handle",
                confidence=confidence,
                stop_loss=stop_loss,
                target=target,
                points=cup_points,
                handle_high=handle_high,
                cup_high=cup_high,
                direction="long",
                volume_grade=volume_grade,
            )

        return None

    def _find_cup_handle(self, bars: List["Bar"]) -> Optional[Tuple]:
        """寻找杯柄形态

        Args:
            bars: K线列表

        Returns:
            (handle_high, cup_bottom, cup_high) 或 None
        """
        recent = bars[-self.min_bars-1:-1]

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

    def detect(self, bars: List["Bar"]) -> Optional[PatternSignal]:
        """检测过前高形态

        Args:
            bars: K线列表

        Returns:
            如果检测到信号，返回 PatternSignal
            否则返回 None
        """
        if len(bars) < self.lookback_period + 1:
            return None

        current_bar = bars[-1]
        previous = bars[-2]

        # 找前高
        lookback = bars[-self.lookback_period:-1]
        previous_high = max(b.high for b in lookback)

        # 检查突破前高后的回踩再涨
        # 简化实现：当前价格突破前高
        if current_bar.close > previous_high:
            # 量能确认：过前高时应放量
            volume_grade = self.volume_analyzer.grade(bars, len(bars) - 1)
            if volume_grade == 'strong':
                confidence = 0.8
            elif volume_grade == 'normal':
                confidence = 0.65
            else:
                confidence = 0.5

            amplitude = current_bar.close - previous_high
            target = current_bar.close + amplitude
            stop_loss = previous_high * self.stop_loss_factor

            # 构造过前高可视化关键点
            prev_high_bar = max(lookback, key=lambda b: b.high)
            breakout_points = [
                {"timestamp": prev_high_bar.timestamp.isoformat(),
                 "price": prev_high_bar.high, "label": "前高"},
                {"timestamp": current_bar.timestamp.isoformat(),
                 "price": current_bar.close, "label": "突破"},
            ]

            return self._create_signal(
                pattern="breakout_pullback",
                confidence=confidence,
                stop_loss=stop_loss,
                target=target,
                points=breakout_points,
                breakout_high=previous_high,
                direction="long",
                volume_grade=volume_grade,
            )

        return None
