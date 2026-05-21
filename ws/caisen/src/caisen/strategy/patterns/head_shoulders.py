"""头肩顶/底形态检测器"""

from typing import List, Optional, Tuple, TYPE_CHECKING

from ..detector import PatternDetector, PatternSignal

if TYPE_CHECKING:
    from ...core.bar import Bar


class HeadAndShouldersBottomDetector(PatternDetector):
    """头肩底形态检测器

    检测左肩、头部（最低点）、右肩后的颈线突破。

    头肩底形成条件：
    1. 头部是三个低点中最低的
    2. 左肩和右肩高度相近（±5%容差）
    3. 价格突破颈线时确认形态

    置信度因素：
    - 完成度：各部分对称性
    - 成交量：突破时放量
    - 趋势：与上升趋势共振
    - 动量：突破力度
    """

    def __init__(
        self,
        shoulder_tolerance: float = 0.05,     # 两肩容差
        shoulder_height_min: float = 0.02,      # 左肩最小高度（相对头部）
        shoulder_height_max: float = 0.10,     # 左肩最大高度（相对头部）
        stop_loss_factor: float = 0.93,
        min_profit_pct: float = 0.03,
    ):
        super().__init__(name="head_and_shoulders_bottom")
        self.shoulder_tolerance = shoulder_tolerance
        self.shoulder_height_min = shoulder_height_min
        self.shoulder_height_max = shoulder_height_max
        self.stop_loss_factor = stop_loss_factor
        self.min_profit_pct = min_profit_pct

        self._left_shoulder = None
        self._head = None
        self._right_shoulder = None
        self._neckline = 0.0

    def detect(self) -> Optional[PatternSignal]:
        if len(self._bars) < 12:
            return None

        current_bar = self._bars[-1]
        result = self._find_pattern()

        if result is None:
            return None

        left_shoulder, head, right_shoulder, neckline = result

        if current_bar.close > neckline:
            confidence = self._calculate_confidence(
                left_shoulder, head, right_shoulder, neckline, current_bar
            )

            amplitude = neckline - head.low
            target = max(neckline + amplitude, current_bar.close * (1 + self.min_profit_pct))
            stop_loss = head.low * self.stop_loss_factor

            return self._create_signal(
                pattern="head_and_shoulders_bottom",
                confidence=confidence,
                stop_loss=stop_loss,
                target=target,
                points=[
                    {"timestamp": left_shoulder.timestamp.isoformat(),
                     "price": left_shoulder.low, "label": "左肩"},
                    {"timestamp": head.timestamp.isoformat(),
                     "price": head.low, "label": "头"},
                    {"timestamp": right_shoulder.timestamp.isoformat(),
                     "price": right_shoulder.low, "label": "右肩"},
                ],
                neckline=neckline,
                amplitude=amplitude,
                direction="long",
            )

        return None

    def _find_pattern(self) -> Optional[Tuple]:
        recent = self._bars[-12:]

        # 找头部（中间区域的最低点）
        middle_lows = [(i, b) for i, b in enumerate(recent[3:9], start=3)]
        if not middle_lows:
            return None

        head_idx, head = min(middle_lows, key=lambda x: x[1].low)

        # 找左肩
        left_candidates = [
            b for b in recent[:head_idx]
            if head.low * (1 + self.shoulder_height_min) < b.low < head.low * (1 + self.shoulder_height_max)
        ]
        if not left_candidates:
            return None
        left_shoulder = max(left_candidates, key=lambda b: b.low)

        # 找右肩
        right_candidates = [
            b for b in recent[head_idx+1:]
            if abs(b.low - left_shoulder.low) / left_shoulder.low < self.shoulder_tolerance
        ]
        if not right_candidates:
            return None
        right_shoulder = max(right_candidates, key=lambda b: b.low)

        # 找颈线
        left_idx = recent.index(left_shoulder)
        right_idx = recent.index(right_shoulder)
        between = recent[left_idx:right_idx+1]
        neckline = max(b.high for b in between)

        return (left_shoulder, head, right_shoulder, neckline)

    def _calculate_confidence(
        self, left_shoulder, head, right_shoulder, neckline, bar
    ) -> float:
        # 完成度：两肩越对称越好
        shoulder_diff = abs(left_shoulder.low - right_shoulder.low) / left_shoulder.low
        completion = 1.0 - min(1.0, shoulder_diff / self.shoulder_tolerance)

        # 成交量
        volume = min(1.0, self._volume_ratio() / 2.0)

        # 趋势
        is_uptrend = self._is_trend_up(period=20)
        trend = 0.7 if is_uptrend else 0.3

        # 动量
        breakout_pct = (bar.close - neckline) / neckline
        momentum = min(1.0, breakout_pct / 0.02)

        return self._calculate_confidence(
            completion=completion, volume=volume, trend=trend, momentum=momentum
        )

    def _on_reset(self) -> None:
        self._left_shoulder = None
        self._head = None
        self._right_shoulder = None
        self._neckline = 0.0


class HeadAndShouldersTopDetector(PatternDetector):
    """头肩顶形态检测器

    检测左肩、头部（最高点）、右肩后的颈线跌破。

    头肩顶形成条件：
    1. 头部是三个高点中最高的
    2. 左肩和右肩高度相近（±5%容差）
    3. 价格跌破颈线时确认形态
    """

    def __init__(
        self,
        shoulder_tolerance: float = 0.05,
        shoulder_height_min: float = 0.02,
        shoulder_height_max: float = 0.10,
        stop_loss_factor: float = 1.02,
        min_profit_pct: float = 0.03,
    ):
        super().__init__(name="head_and_shoulders_top")
        self.shoulder_tolerance = shoulder_tolerance
        self.shoulder_height_min = shoulder_height_min
        self.shoulder_height_max = shoulder_height_max
        self.stop_loss_factor = stop_loss_factor
        self.min_profit_pct = min_profit_pct

    def detect(self) -> Optional[PatternSignal]:
        if len(self._bars) < 12:
            return None

        current_bar = self._bars[-1]
        result = self._find_pattern()

        if result is None:
            return None

        left_shoulder, head, right_shoulder, neckline = result

        if current_bar.close < neckline:
            confidence = self._calculate_confidence(
                left_shoulder, head, right_shoulder, neckline, current_bar
            )

            amplitude = head.high - neckline
            target = neckline - amplitude
            stop_loss = head.high * self.stop_loss_factor

            return self._create_signal(
                pattern="head_and_shoulders_top",
                confidence=confidence,
                stop_loss=stop_loss,
                target=target,
                points=[
                    {"timestamp": left_shoulder.timestamp.isoformat(),
                     "price": left_shoulder.high, "label": "左肩"},
                    {"timestamp": head.timestamp.isoformat(),
                     "price": head.high, "label": "头"},
                    {"timestamp": right_shoulder.timestamp.isoformat(),
                     "price": right_shoulder.high, "label": "右肩"},
                ],
                neckline=neckline,
                amplitude=amplitude,
                direction="short",
            )

        return None

    def _find_pattern(self) -> Optional[Tuple]:
        recent = self._bars[-12:]

        # 找头部（中间区域的最高点）
        middle_highs = [(i, b) for i, b in enumerate(recent[3:9], start=3)]
        if not middle_highs:
            return None

        head_idx, head = max(middle_highs, key=lambda x: x[1].high)

        # 找左肩
        left_candidates = [
            b for b in recent[:head_idx]
            if head.high * (1 - self.shoulder_height_max) < b.high < head.high * (1 - self.shoulder_height_min)
        ]
        if not left_candidates:
            return None
        left_shoulder = min(left_candidates, key=lambda b: b.high)

        # 找右肩
        right_candidates = [
            b for b in recent[head_idx+1:]
            if abs(b.high - left_shoulder.high) / left_shoulder.high < self.shoulder_tolerance
        ]
        if not right_candidates:
            return None
        right_shoulder = min(right_candidates, key=lambda b: b.high)

        # 找颈线
        left_idx = recent.index(left_shoulder)
        right_idx = recent.index(right_shoulder)
        between = recent[left_idx:right_idx+1]
        neckline = min(b.low for b in between)

        return (left_shoulder, head, right_shoulder, neckline)

    def _calculate_confidence(
        self, left_shoulder, head, right_shoulder, neckline, bar
    ) -> float:
        shoulder_diff = abs(left_shoulder.high - right_shoulder.high) / left_shoulder.high
        completion = 1.0 - min(1.0, shoulder_diff / self.shoulder_tolerance)

        volume = min(1.0, self._volume_ratio() / 2.0)

        is_downtrend = self._is_trend_down(period=20)
        trend = 0.7 if is_downtrend else 0.3

        breakdown_pct = (neckline - bar.close) / neckline
        momentum = min(1.0, breakdown_pct / 0.02)

        return self._calculate_confidence(
            completion=completion, volume=volume, trend=trend, momentum=momentum
        )