"""
蔡森十二形态策略

基于蔡森《多空转折一手抓》理论实现：
- 整理平台检测
- 破底翻/假突破识别
- 两加码点进场
- 等幅测距目标价
"""

from typing import List, Optional, Dict
from dataclasses import dataclass, field
from enum import Enum, auto

from ..core.bar import Bar
from ..core.order import Order, Side
from ..core.config import BacktestConfig
from .base import Strategy, Annotation, AnnotationType


class PatternType(Enum):
    """形态类型"""
    NONE = auto()
    PLATFORM_FORMING = auto()   # 整理平台形成中
    BREAKDOWN_PULLBACK = auto() # 破底翻（第一买点）
    BREAKOUT = auto()           # 突破平台上沿（第二买点）
    FAKE_BREAKOUT = auto()      # 假突破（空头信号）
    W_BOTTOM = auto()           # W底
    M_TOP = auto()              # M头
    HEAD_AND_SHOULDERS_BOTTOM = auto()  # 头肩底
    HEAD_AND_SHOULDERS_TOP = auto()     # 头肩顶
    TRIANGLE = auto()           # 三角整理
    FLAG = auto()               # 旗形整理
    RECTANGLE = auto()          # 矩形整理
    ROUNDING_BOTTOM = auto()    # 圆弧底
    CUP_HANDLE = auto()         # 杯柄形态
    BREAKOUT_PULLBACK = auto()  # 过前高


@dataclass
class Platform:
    """整理平台"""
    start_bar_index: int
    end_bar_index: int
    upper: float      # 上沿颈线（阻力）
    lower: float      # 下沿颈线（支撑）
    bars: List[Bar] = field(default_factory=list)

    def duration(self) -> int:
        return len(self.bars)

    def amplitude_pct(self) -> float:
        """振幅百分比"""
        return (self.upper - self.lower) / self.lower if self.lower > 0 else 0

    def mid_price(self) -> float:
        return (self.upper + self.lower) / 2


@dataclass
class PatternSignal:
    """形态信号"""
    bar_index: int
    pattern: PatternType
    action: str           # "BUY_1", "BUY_2", "SELL"
    price: float
    stop_loss: float
    target: float
    reason: str


class CaiSenStrategy(Strategy):
    """
    蔡森十二形态策略（Code Strategy）

    基于蔡森《多空转折一手抓》理论实现的硬编码策略，通过整理平台检测、
    破底翻/假突破识别等形态学方法生成交易信号。

    参数:
        platform_min_bars: 整理平台最少K线数（默认10）
        platform_max_amplitude: 整理平台最大振幅（默认5%）
        breakdown_max_pct: 破底最大幅度（默认2%）
        pullback_max_bars: 破底后最大拉回K线数（默认3）
        volume_confirm: 是否启用成交量确认（默认True）
        first_position_pct: 第一买点仓位比例（默认0.3，即30%）
        second_position_pct: 第二买点仓位比例（默认0.7，即70%）
    """

    # 蔡森理论参数范围（类常量）
    PLATFORM_MIN_BARS_RANGE = (5, 50)      # 平台最少K线数范围
    PLATFORM_MAX_AMPLITUDE_RANGE = (0.02, 0.15)  # 平台最大振幅范围（2%-15%）
    BREAKDOWN_MAX_PCT_RANGE = (0.005, 0.05)      # 破底幅度范围（0.5%-5%）
    PULLBACK_MAX_BARS_RANGE = (2, 5)       # 拉回最大K线数范围
    POSITION_PCT_RANGE = (0.1, 1.0)        # 仓位比例范围

    def __init__(self,
                 platform_min_bars: int = 10,
                 platform_max_amplitude: float = 0.05,
                 breakdown_max_pct: float = 0.02,
                 pullback_max_bars: int = 3,
                 volume_confirm: bool = True,
                 first_position_pct: float = 0.3,
                 second_position_pct: float = 0.7,
                 w_bottom_enabled: bool = True,
                 m_top_enabled: bool = True,
                 head_and_shoulders_bottom_enabled: bool = True,
                 head_and_shoulders_top_enabled: bool = True,
                 platform_volume_decline: bool = True,  # 量能退潮确认
                 breakdown_max_bars: int = 2,  # 瞬间破底最大K线数
                 triangle_enabled: bool = True,  # 三角整理启用
                 flag_enabled: bool = True,  # 旗形整理启用
                 rectangle_enabled: bool = True,  # 矩形整理启用
rounding_bottom_enabled: bool = True,  # 圆弧底启用
cup_handle_enabled: bool = True,  # 杯柄形态启用
breakout_pullback_enabled: bool = True):  # 过前高启用

        # 参数验证（蔡森理论标准）
        self._validate_params(
            platform_min_bars, platform_max_amplitude,
            breakdown_max_pct, pullback_max_bars,
            first_position_pct, second_position_pct
        )

        self.platform_min_bars = platform_min_bars
        self.platform_max_amplitude = platform_max_amplitude
        self.breakdown_max_pct = breakdown_max_pct
        self.pullback_max_bars = pullback_max_bars
        self.volume_confirm = volume_confirm
        self.first_position_pct = first_position_pct
        self.second_position_pct = second_position_pct
        self.w_bottom_enabled = w_bottom_enabled
        self.m_top_enabled = m_top_enabled
        self.head_and_shoulders_bottom_enabled = head_and_shoulders_bottom_enabled
        self.head_and_shoulders_top_enabled = head_and_shoulders_top_enabled
        self.platform_volume_decline = platform_volume_decline
        self.breakdown_max_bars = breakdown_max_bars
        self.triangle_enabled = triangle_enabled
        self.flag_enabled = flag_enabled
        self.rectangle_enabled = rectangle_enabled
        self.rounding_bottom_enabled = rounding_bottom_enabled
        self.cup_handle_enabled = cup_handle_enabled
        self.breakout_pullback_enabled = breakout_pullback_enabled

    def _validate_params(self,
                         platform_min_bars: int,
                         platform_max_amplitude: float,
                         breakdown_max_pct: float,
                         pullback_max_bars: int,
                         first_position_pct: float,
                         second_position_pct: float) -> None:
        """
        验证蔡森策略参数是否符合理论标准

        蔡森理论要求：
        - 整理平台至少5根K线（太短无法形成有效平台）
        - 整理平台不超过50根K线（太长失去时效性）
        - 平台振幅2%-15%（太小无利润，太大是趋势）
        - 破底幅度0.5%-5%（太小无法洗盘，太大是真突破）
        """
        min_bars, max_bars = self.PLATFORM_MIN_BARS_RANGE
        if not (min_bars <= platform_min_bars <= max_bars):
            raise ValueError(
                f"蔡森理论：整理平台K线数应在{min_bars}-{max_bars}之间，"
                f"当前{platform_min_bars}"
            )

        min_amp, max_amp = self.PLATFORM_MAX_AMPLITUDE_RANGE
        if not (min_amp <= platform_max_amplitude <= max_amp):
            raise ValueError(
                f"蔡森理论：整理平台振幅应在{min_amp*100:.0f}%-{max_amp*100:.0f}%之间，"
                f"当前{platform_max_amplitude*100:.0f}%"
            )

        min_break, max_break = self.BREAKDOWN_MAX_PCT_RANGE
        if not (min_break <= breakdown_max_pct <= max_break):
            raise ValueError(
                f"蔡森理论：破底幅度应在{min_break*100:.1f}%-{max_break*100:.0f}%之间，"
                f"当前{breakdown_max_pct*100:.1f}%"
            )

        min_pull, max_pull = self.PULLBACK_MAX_BARS_RANGE
        if not (min_pull <= pullback_max_bars <= max_pull):
            raise ValueError(
                f"蔡森理论：拉回K线数应在{min_pull}-{max_pull}之间，"
                f"当前{pullback_max_bars}"
            )

        min_pos, max_pos = self.POSITION_PCT_RANGE
        if not (min_pos <= first_position_pct <= max_pos):
            raise ValueError(
                f"第一买点仓位比例应在{min_pos*100:.0f}%-{max_pos*100:.0f}%之间，"
                f"当前{first_position_pct*100:.0f}%"
            )

        if not (min_pos <= second_position_pct <= max_pos):
            raise ValueError(
                f"第二买点仓位比例应在{min_pos*100:.0f}%-{max_pos*100:.0f}%之间，"
                f"当前{second_position_pct*100:.0f}%"
            )

        if first_position_pct + second_position_pct > max_pos:
            raise ValueError(
                f"两买点仓位总和不应超过{max_pos*100:.0f}%，"
                f"当前{(first_position_pct + second_position_pct)*100:.0f}%"
            )

        # 蔡森理论：第一买点仓位应小于第二买点
        if first_position_pct >= second_position_pct:
            raise ValueError(
                "蔡森理论：第一买点仓位应小于第二买点，"
                "遵循'试单轻仓、确认重仓'原则"
            )

        
        # 状态
        self.bars: List[Bar] = []
        self.platform: Optional[Platform] = None
        self.state = PatternType.NONE
        self.signals: List[PatternSignal] = []
        self.annotations: List[Annotation] = []
        
        # 破底翻跟踪
        self.breakdown_bar: Optional[Bar] = None
        self.breakdown_low: float = 0
        self.platform_avg_volume: float = 0
        self.platform_volume_trend: float = 0  # 量能趋势（负值表示退潮）
        
        # 持仓状态
        self.position = 0  # 0=空仓, 1=第一买点持仓, 2=第二买点持仓
        self.entry_price = 0.0
        self.stop_loss = 0.0
        self.target_price = 0.0  # 目标价（止盈）

        # W底跟踪
        self.w_bottom_first_low: Optional[Bar] = None
        self.w_bottom_neckline: float = 0
        self.w_bottom_second_low: Optional[Bar] = None

        # M头跟踪
        self.m_top_first_high: Optional[Bar] = None
        self.m_top_neckline: float = 0
        self.m_top_second_high: Optional[Bar] = None

        # 头肩底跟踪
        self.hs_bottom_left_shoulder: Optional[Bar] = None
        self.hs_bottom_head: Optional[Bar] = None
        self.hs_bottom_right_shoulder: Optional[Bar] = None
        self.hs_bottom_neckline: float = 0

        # 头肩顶跟踪
        self.hs_top_left_shoulder: Optional[Bar] = None
        self.hs_top_head: Optional[Bar] = None
        self.hs_top_right_shoulder: Optional[Bar] = None
        self.hs_top_neckline: float = 0
        
    def on_init(self, config: BacktestConfig) -> None:
        """初始化，可从config获取参数"""
        pass
    
    def on_bar(self, bar: Bar) -> Optional[Order]:
        """
        每根K线调用，返回订单或None
        
        逻辑流程:
        1. 收集K线，检测整理平台
        2. 检测破底（跌破平台下沿）
        3. 检测拉回（破底翻确认，第一买点）
        4. 检测突破平台上沿（第二买点）
        5. 检测假突破（空头信号）
        """
        self.bars.append(bar)

        # 0. 检测W底（无平台时，优先于平台检测）
        if self.position == 0 and self.w_bottom_enabled and self.state == PatternType.NONE:
            w_signal = self._detect_w_bottom(bar)
            if w_signal:
                self.signals.append(w_signal)
                self._add_annotation(bar, "W底突破", "green")
                self.position = 1
                self.entry_price = w_signal.price
                self.stop_loss = w_signal.stop_loss
                self.target_price = w_signal.target
                return Order(symbol=bar.symbol, side=Side.BUY, position_pct=self.first_position_pct)

        # 0.5 检测M头（无持仓时）
        if self.position == 0 and self.m_top_enabled and self.state == PatternType.NONE:
            m_signal = self._detect_m_top(bar)
            if m_signal:
                self.signals.append(m_signal)
                self._add_annotation(bar, "M头跌破", "red")
                self.position = -1  # 空头持仓标记
                self.entry_price = m_signal.price
                self.stop_loss = m_signal.stop_loss
                self.target_price = m_signal.target
                return Order(symbol=bar.symbol, side=Side.SELL, position_pct=self.first_position_pct)

        # 0.6 检测头肩底（无持仓时）
        if self.position == 0 and self.head_and_shoulders_bottom_enabled and self.state == PatternType.NONE:
            hs_signal = self._detect_head_and_shoulders_bottom(bar)
            if hs_signal:
                self.signals.append(hs_signal)
                self._add_annotation(bar, "头肩底突破", "green")
                self.position = 1
                self.entry_price = hs_signal.price
                self.stop_loss = hs_signal.stop_loss
                self.target_price = hs_signal.target
                return Order(symbol=bar.symbol, side=Side.BUY, position_pct=self.first_position_pct)

        # 0.7 检测头肩顶（无持仓时）
        if self.position == 0 and self.head_and_shoulders_top_enabled and self.state == PatternType.NONE:
            hs_signal = self._detect_head_and_shoulders_top(bar)
            if hs_signal:
                self.signals.append(hs_signal)
                self._add_annotation(bar, "头肩顶跌破", "red")
                self.position = -1
                self.entry_price = hs_signal.price
                self.stop_loss = hs_signal.stop_loss
                self.target_price = hs_signal.target
                return Order(symbol=bar.symbol, side=Side.SELL, position_pct=self.first_position_pct)

        # 0.8 检测三角整理（无持仓时）
        if self.position == 0 and self.triangle_enabled and self.state == PatternType.NONE:
            triangle_signal = self._detect_triangle(bar)
            if triangle_signal:
                self.signals.append(triangle_signal)
                if triangle_signal.action == "BUY":
                    self._add_annotation(bar, "三角整理突破", "green")
                    self.position = 1
                    self.entry_price = triangle_signal.price
                    self.stop_loss = triangle_signal.stop_loss
                    self.target_price = triangle_signal.target
                    return Order(symbol=bar.symbol, side=Side.BUY, position_pct=self.first_position_pct)
                else:
                    self._add_annotation(bar, "三角整理跌破", "red")
                    self.position = -1
                    self.entry_price = triangle_signal.price
                    self.stop_loss = triangle_signal.stop_loss
                    self.target_price = triangle_signal.target
                    return Order(symbol=bar.symbol, side=Side.SELL, position_pct=self.first_position_pct)

        # 0.9 检测旗形整理（无持仓时）
        if self.position == 0 and self.flag_enabled and self.state == PatternType.NONE:
            flag_signal = self._detect_flag(bar)
            if flag_signal:
                self.signals.append(flag_signal)
                if flag_signal.action == "BUY":
                    self._add_annotation(bar, "旗形突破", "green")
                    self.position = 1
                    self.entry_price = flag_signal.price
                    self.stop_loss = flag_signal.stop_loss
                    self.target_price = flag_signal.target
                    return Order(symbol=bar.symbol, side=Side.BUY, position_pct=self.first_position_pct)
                else:
                    self._add_annotation(bar, "旗形跌破", "red")
                    self.position = -1
                    self.entry_price = flag_signal.price
                    self.stop_loss = flag_signal.stop_loss
                    self.target_price = flag_signal.target
                    return Order(symbol=bar.symbol, side=Side.SELL, position_pct=self.first_position_pct)

        # 0.10 检测矩形整理（无持仓时）
        if self.position == 0 and self.rectangle_enabled and self.state == PatternType.NONE:
            rectangle_signal = self._detect_rectangle(bar)
            if rectangle_signal:
                self.signals.append(rectangle_signal)
                if rectangle_signal.action == "BUY":
                    self._add_annotation(bar, "矩形突破", "green")
                    self.position = 1
                    self.entry_price = rectangle_signal.price
                    self.stop_loss = rectangle_signal.stop_loss
                    self.target_price = rectangle_signal.target
                    return Order(symbol=bar.symbol, side=Side.BUY, position_pct=self.first_position_pct)
                else:
                    self._add_annotation(bar, "矩形跌破", "red")
                    self.position = -1
                    self.entry_price = rectangle_signal.price
                    self.stop_loss = rectangle_signal.stop_loss
                    self.target_price = rectangle_signal.target
                    return Order(symbol=bar.symbol, side=Side.SELL, position_pct=self.first_position_pct)

        # 0.11 检测圆弧底（无持仓时）
        if self.position == 0 and self.rounding_bottom_enabled and self.state == PatternType.NONE:
            rounding_signal = self._detect_rounding_bottom(bar)
            if rounding_signal:
                self.signals.append(rounding_signal)
                self._add_annotation(bar, "圆弧底突破", "green")
                self.position = 1
                self.entry_price = rounding_signal.price
                self.stop_loss = rounding_signal.stop_loss
                self.target_price = rounding_signal.target
                return Order(symbol=bar.symbol, side=Side.BUY, position_pct=self.first_position_pct)

        # 0.12 检测杯柄形态（无持仓时）
        if self.position == 0 and self.cup_handle_enabled and self.state == PatternType.NONE:
            cup_signal = self._detect_cup_handle(bar)
            if cup_signal:
                self.signals.append(cup_signal)
                self._add_annotation(bar, "杯柄突破", "green")
                self.position = 1
                self.entry_price = cup_signal.price
                self.stop_loss = cup_signal.stop_loss
                self.target_price = cup_signal.target
                return Order(symbol=bar.symbol, side=Side.BUY, position_pct=self.first_position_pct)

        # 0.13 检测过前高（无持仓时）
        if self.position == 0 and self.breakout_pullback_enabled and self.state == PatternType.NONE:
            breakout_signal = self._detect_breakout_pullback(bar)
            if breakout_signal:
                self.signals.append(breakout_signal)
                self._add_annotation(bar, "过前高", "green")
                self.position = 1
                self.entry_price = breakout_signal.price
                self.stop_loss = breakout_signal.stop_loss
                self.target_price = breakout_signal.target
                return Order(symbol=bar.symbol, side=Side.BUY, position_pct=self.first_position_pct)

        # 1. 检测整理平台
        if self.state == PatternType.NONE:
            self._detect_platform()
            return None
        
        # 2. 检测破底
        if self.state == PatternType.PLATFORM_FORMING:
            if self._detect_breakdown(bar):
                self.state = PatternType.BREAKDOWN_PULLBACK
                self.breakdown_bar = bar
                self.breakdown_low = bar.low
                self._add_annotation(bar, "破底", "red")
            return None
        
        # 3. 检测拉回（破底翻确认 - 第一买点）
        if self.state == PatternType.BREAKDOWN_PULLBACK and self.position == 0:
            signal = self._detect_pullback(bar)
            if signal:
                self.signals.append(signal)
                self._add_annotation(bar, "破底翻-第一买点", "green")
                self.position = 1
                self.entry_price = signal.price
                self.stop_loss = signal.stop_loss
                self.target_price = signal.target
                return Order(symbol=bar.symbol, side=Side.BUY, position_pct=self.first_position_pct)

            # 破底后超过N根K线未拉回，失效，重新检测平台
            if self.breakdown_bar and self.breakdown_bar in self.bars:
                breakdown_index = self.bars.index(self.breakdown_bar)
                current_index = len(self.bars) - 1
                if current_index - breakdown_index > self.pullback_max_bars:
                    self.state = PatternType.PLATFORM_FORMING
                    self.breakdown_bar = None
            return None
        
        # 4. 检测突破平台上沿（第二买点）
        if self.state == PatternType.BREAKDOWN_PULLBACK and self.position == 1:
            if bar.close > self.platform.upper:
                # 成交量确认：突破需放量
                if self._volume_confirm(bar, True):
                    current_index = len(self.bars) - 1
                    signal = PatternSignal(
                        bar_index=current_index,
                        pattern=PatternType.BREAKOUT,
                        action="BUY_2",
                        price=bar.close,
                        stop_loss=self.breakdown_low * 0.99,
                        target=self._calculate_target(),
                        reason="突破平台上沿，第二买点"
                    )
                    self.signals.append(signal)
                    self._add_annotation(bar, "第二买点", "blue")
                    self.position = 2
                    self.target_price = signal.target
                    return Order(symbol=bar.symbol, side=Side.BUY, position_pct=self.second_position_pct)

        # 5. 检测假突破（空头信号）
        if self.state == PatternType.PLATFORM_FORMING:
            fake_breakout = self._detect_fake_breakout(bar)
            if fake_breakout:
                self.signals.append(fake_breakout)
                self._add_annotation(bar, "假突破", "orange")
                return Order(symbol=bar.symbol, side=Side.SELL, quantity=0)

        # 持仓中：检查止盈止损
        if self.position > 0:
            # 止盈：到达目标价
            if bar.high >= self.target_price:
                self._reset_position()
                return Order(symbol=bar.symbol, side=Side.SELL, quantity=0)
            # 止损：跌破止损位
            if bar.low <= self.stop_loss:
                self._reset_position()
                return Order(symbol=bar.symbol, side=Side.SELL, quantity=0)
        
        return None
    
    def _detect_platform(self) -> bool:
        """
        检测整理平台
        
        标准：
        - 持续时间≥platform_min_bars
        - 振幅≤platform_max_amplitude
        - 成交量逐步萎缩（可选）
        - 均线交织（简化：价格在区间内）
        """
        if len(self.bars) < self.platform_min_bars:
            return False
        
        # 取最近N根K线
        recent = self.bars[-self.platform_min_bars:]
        highs = [b.high for b in recent]
        lows = [b.low for b in recent]
        volumes = [b.volume for b in recent]
        
        # 计算平台边界
        upper = max(highs)  # 上沿 = 近期高点中的最高（阻力）
        lower = min(lows)   # 下沿 = 近期低点中的最低（支撑）
        
        # 检查振幅
        if lower <= 0:
            return False
        amplitude = (upper - lower) / lower
        if amplitude > self.platform_max_amplitude:
            return False
        
        # 记录平台平均成交量（用于后续确认）
        self.platform_avg_volume = sum(volumes) / len(volumes)
        
        # 蔡森：量能退潮判断 - 平台后半段成交量应小于前半段
        if self.platform_volume_decline and len(volumes) >= 6:
            mid = len(volumes) // 2
            first_half_avg = sum(volumes[:mid]) / mid
            second_half_avg = sum(volumes[mid:]) / (len(volumes) - mid)
            self.platform_volume_trend = (second_half_avg - first_half_avg) / first_half_avg
            # 量能退潮：后半段成交量比前半段减少10%以上
            if self.platform_volume_trend > -0.1:
                return False  # 量能未退潮，不是有效的整理平台
        
        current_index = len(self.bars) - 1
        start_index = current_index - self.platform_min_bars + 1
        self.platform = Platform(
            start_bar_index=start_index,
            end_bar_index=current_index,
            upper=upper,
            lower=lower,
            bars=recent.copy()
        )
        self.state = PatternType.PLATFORM_FORMING
        return True
    
    def _detect_breakdown(self, bar: Bar) -> bool:
        """
        检测破底

        蔡森标准：
        - 收盘价跌破平台下沿
        - 跌破幅度不超过breakdown_max_pct（刺破而非真突破，1-3%）
        - 瞬间破底：1-2根K线完成跌破
        - 破底时可能放量（止损盘涌出）
        """
        if not self.platform:
            return False

        # 收盘价跌破平台下沿
        if bar.close >= self.platform.lower:
            return False

        # 检查跌破幅度
        breakdown_pct = (self.platform.lower - bar.close) / self.platform.lower
        if breakdown_pct > self.breakdown_max_pct:
            return False  # 真跌破，不是洗盘

        # 蔡森：瞬间破底判断 - 破底应在1-2根K线内完成
        # 检查平台形成后的K线数
        if len(self.bars) > self.platform.end_bar_index + self.breakdown_max_bars:
            # 平台形成后超过breakdown_max_bars根K线才破底，不是"瞬间"破底
            return False

        return True
    
    def _detect_pullback(self, bar: Bar) -> Optional[PatternSignal]:
        """
        检测拉回（破底翻确认）
        
        标准：
        - 收盘价站回平台下沿之上
        - 拉回时放量（主力吸筹）
        
        返回第一买点信号
        """
        if not self.platform or not self.breakdown_bar:
            return None
        
        # 收盘价站回平台下沿之上
        if bar.close <= self.platform.lower:
            return None
        
        # 成交量确认：拉回需放量
        if self.volume_confirm and not self._volume_confirm(bar, True):
            return None
        
        # 第一买点
        stop_loss = self.breakdown_low * 0.995
        target = self._calculate_target()
        
        current_index = len(self.bars) - 1
        return PatternSignal(
            bar_index=current_index,
            pattern=PatternType.BREAKDOWN_PULLBACK,
            action="BUY_1",
            price=bar.close,
            stop_loss=stop_loss,
            target=target,
            reason="破底翻确认，第一买点（站回颈线）"
        )
    
    def _detect_fake_breakout(self, bar: Bar) -> Optional[PatternSignal]:
        """
        检测假突破
        
        标准：
        - 价格突破平台上沿
        - 但收盘价跌回平台内部
        - 突破时放量（散户追入），跌回时更放量（主力出货）
        """
        if not self.platform:
            return None
        
        # 必须有足够的历史K线判断
        if len(self.bars) < 2:
            return None
        
        prev_bar = self.bars[-2]
        
        # 前一根突破平台上沿
        if prev_bar.close <= self.platform.upper:
            return None
        
        # 当前跌回平台内部
        if bar.close >= self.platform.upper:
            return None
        
        current_index = len(self.bars) - 1
        return PatternSignal(
            bar_index=current_index,
            pattern=PatternType.FAKE_BREAKOUT,
            action="SELL",
            price=bar.close,
            stop_loss=prev_bar.high * 1.01,
            target=self.platform.lower,
            reason="假突破确认，主力诱多出货"
        )
    
    def _volume_confirm(self, bar: Bar, need_high: bool) -> bool:
        """成交量确认"""
        if not self.volume_confirm or self.platform_avg_volume <= 0:
            return True
        
        if need_high:
            # 需要放量：当前成交量 > 平台平均的1.5倍
            return bar.volume > self.platform_avg_volume * 1.5
        else:
            # 需要缩量：当前成交量 < 平台平均
            return bar.volume < self.platform_avg_volume
    
    def _detect_head_and_shoulders_bottom(self, bar: Bar) -> Optional[PatternSignal]:
        """
        检测头肩底形态

        简化实现：检测左肩、头（最低）、右肩后的颈线突破
        """
        if len(self.bars) < 12:
            return None

        # 获取最近12根K线
        recent = self.bars[-12:]
        lows = [b.low for b in recent]

        # 找头部（最低点，在中间区域）
        head_idx = 3 + lows[3:9].index(min(lows[3:9]))
        head = recent[head_idx].low

        # 找左肩（头部左侧，比头部高）
        left_shoulder_candidates = [b for b in recent[:head_idx] if b.low > head * 1.02 and b.low < head * 1.1]
        if not left_shoulder_candidates:
            return None
        left_shoulder = max(left_shoulder_candidates, key=lambda b: b.low)

        # 找右肩（头部右侧，与左肩相近）
        right_shoulder_candidates = [b for b in recent[head_idx+1:] if abs(b.low - left_shoulder.low) / left_shoulder.low < 0.05]
        if not right_shoulder_candidates:
            return None
        right_shoulder = max(right_shoulder_candidates, key=lambda b: b.low)

        # 找颈线（左肩和右肩之间的高点）
        left_idx = recent.index(left_shoulder)
        right_idx = recent.index(right_shoulder)
        between_bars = recent[left_idx:right_idx+1]
        neckline = max(b.high for b in between_bars)

        # 检查是否突破颈线
        if bar.close > neckline:
            # 头肩底确认
            amplitude = neckline - head
            target = neckline + amplitude
            stop_loss = head * 0.99

            return PatternSignal(
                bar_index=len(self.bars) - 1,
                pattern=PatternType.HEAD_AND_SHOULDERS_BOTTOM,
                action="BUY_1",
                price=bar.close,
                stop_loss=stop_loss,
                target=target,
                reason="头肩底形态确认，突破颈线"
            )

        return None

    def _detect_head_and_shoulders_top(self, bar: Bar) -> Optional[PatternSignal]:
        """
        检测头肩顶形态

        简化实现：检测左肩、头（最高）、右肩后的颈线跌破
        """
        if len(self.bars) < 12:
            return None

        # 获取最近12根K线
        recent = self.bars[-12:]
        highs = [b.high for b in recent]

        # 找头部（最高点，在中间区域）
        head_idx = 3 + highs[3:9].index(max(highs[3:9]))
        head = recent[head_idx].high

        # 找左肩（头部左侧，比头部低但不要太低）
        left_shoulder_candidates = [b for b in recent[:head_idx] if b.high < head * 0.99 and b.high > head * 0.9]
        if not left_shoulder_candidates:
            return None
        left_shoulder = max(left_shoulder_candidates, key=lambda b: b.high)

        # 找右肩（头部右侧，与左肩相近）
        right_shoulder_candidates = [b for b in recent[head_idx+1:] if abs(b.high - left_shoulder.high) / left_shoulder.high < 0.05]
        if not right_shoulder_candidates:
            return None
        right_shoulder = max(right_shoulder_candidates, key=lambda b: b.high)

        # 找颈线（左肩和右肩之间的低点）
        left_idx = recent.index(left_shoulder)
        right_idx = recent.index(right_shoulder)
        between_bars = recent[left_idx:right_idx+1]
        neckline = min(b.low for b in between_bars)

        # 检查是否跌破颈线
        if bar.close < neckline:
            # 头肩顶确认
            amplitude = head - neckline
            target = neckline - amplitude
            stop_loss = head * 1.01

            return PatternSignal(
                bar_index=len(self.bars) - 1,
                pattern=PatternType.HEAD_AND_SHOULDERS_TOP,
                action="SELL",
                price=bar.close,
                stop_loss=stop_loss,
                target=target,
                reason="头肩顶形态确认，跌破颈线"
            )

        return None

    def _detect_m_top(self, bar: Bar) -> Optional[PatternSignal]:
        """
        检测M头形态

        简化实现：检测两个相近高点后的颈线跌破
        """
        if len(self.bars) < 10:
            return None

        # 获取最近10根K线
        recent = self.bars[-10:]
        highs = [b.high for b in recent]

        # 找两个高点
        # 第一个高点在前5根
        first_high_idx = highs[:5].index(max(highs[:5]))
        first_high = recent[first_high_idx].high

        # 第二个高点在后5根，与第一个相近（±5%）
        second_high_candidates = [b for b in recent[5:] if abs(b.high - first_high) / first_high < 0.05]
        if not second_high_candidates:
            return None

        second_high_bar = max(second_high_candidates, key=lambda b: b.high)
        second_high = second_high_bar.high

        # 找颈线（两个高点之间的低点）
        first_high_bar = recent[first_high_idx]
        between_bars = [b for b in recent if b.timestamp > first_high_bar.timestamp and b.timestamp < second_high_bar.timestamp]
        if not between_bars:
            return None

        neckline = min(b.low for b in between_bars)

        # 检查是否跌破颈线
        if bar.close < neckline:
            # M头确认
            amplitude = first_high - neckline
            target = neckline - amplitude
            stop_loss = max(first_high, second_high) * 1.01

            return PatternSignal(
                bar_index=len(self.bars) - 1,
                pattern=PatternType.M_TOP,
                action="SELL",
                price=bar.close,
                stop_loss=stop_loss,
                target=target,
                reason="M头形态确认，跌破颈线"
            )

        return None

    def _detect_w_bottom(self, bar: Bar) -> Optional[PatternSignal]:
        """
        检测W底形态

        简化实现：检测两个相近低点后的颈线突破
        """
        if len(self.bars) < 10:
            return None

        # 获取最近10根K线
        recent = self.bars[-10:]
        lows = [b.low for b in recent]

        # 找两个低点
        # 第一个低点在前5根
        first_low_idx = lows[:5].index(min(lows[:5]))
        first_low = recent[first_low_idx].low

        # 第二个低点在后5根，与第一个相近（±5%）
        second_low_candidates = [b for b in recent[5:] if abs(b.low - first_low) / first_low < 0.05]
        if not second_low_candidates:
            return None

        second_low_bar = min(second_low_candidates, key=lambda b: b.low)
        second_low = second_low_bar.low

        # 找颈线（两个低点之间的高点）
        first_low_bar = recent[first_low_idx]
        between_bars = [b for b in recent if b.timestamp > first_low_bar.timestamp and b.timestamp < second_low_bar.timestamp]
        if not between_bars:
            return None

        neckline = max(b.high for b in between_bars)

        # 检查是否突破颈线
        if bar.close > neckline:
            # W底确认
            amplitude = neckline - first_low
            target = neckline + amplitude
            stop_loss = min(first_low, second_low) * 0.99

            return PatternSignal(
                bar_index=len(self.bars) - 1,
                pattern=PatternType.W_BOTTOM,
                action="BUY_1",
                price=bar.close,
                stop_loss=stop_loss,
                target=target,
                reason="W底形态确认，突破颈线"
            )

        return None

    def _calculate_target(self) -> float:
        """
        等幅测距计算目标价

        方法：从颈线到形态极值点的垂直距离，突破后向上投射
        破底翻：从平台下沿到破底低点的距离，加到平台上沿
        """
        if not self.platform:
            return 0

        # 等幅距离 = 平台下沿 - 破底低点
        amplitude = self.platform.lower - self.breakdown_low

        # 目标价 = 平台上沿 + 等幅距离
        target = self.platform.upper + amplitude

        return target
    
    def _add_annotation(self, bar: Bar, label: str, color: str):
        """添加可视化标注"""
        ann_type = AnnotationType.BUY_SIGNAL if "买入" in label else AnnotationType.SELL_SIGNAL
        self.annotations.append(Annotation(
            type=ann_type,
            timestamp=bar.timestamp,
            data={
                "label": label,
                "color": color,
                "price": bar.close,
            }
        ))
    
    def get_annotations(self) -> List[Annotation]:
        """获取可视化标注"""
        return self.annotations

    def _reset_position(self) -> None:
        """平仓后重置持仓相关状态，但保留平台检测历史"""
        self.position = 0
        self.entry_price = 0.0
        self.stop_loss = 0.0
        self.target_price = 0.0
        # 重置形态状态，等待新的平台形成
        self.state = PatternType.NONE
        self.platform = None
        self.breakdown_bar = None
        self.breakdown_low = 0

    def _detect_triangle(self, bar: Bar) -> Optional[PatternSignal]:
        """
        检测三角整理形态

        简化实现：检测对称三角形（高点下降、低点上升，收敛）
        突破上沿趋势线 → 买入，跌破下沿趋势线 → 卖出
        """
        if len(self.bars) < 11:
            return None

        # 获取最近10根历史K线（不包括当前K线）
        recent = self.bars[-11:-1]

        # 找3个高点（下降）
        highs = [(i, b.high) for i, b in enumerate(recent)]
        highs_sorted = sorted(highs, key=lambda x: x[1], reverse=True)[:3]
        highs_sorted = sorted(highs_sorted, key=lambda x: x[0])  # 按时间排序

        # 找3个低点（上升）
        lows = [(i, b.low) for i, b in enumerate(recent)]
        lows_sorted = sorted(lows, key=lambda x: x[1])[:3]
        lows_sorted = sorted(lows_sorted, key=lambda x: x[0])  # 按时间排序

        if len(highs_sorted) < 3 or len(lows_sorted) < 3:
            return None

        # 检查高点是否递减
        if not (highs_sorted[0][1] > highs_sorted[1][1] > highs_sorted[2][1]):
            return None

        # 检查低点是否递增
        if not (lows_sorted[0][1] < lows_sorted[1][1] < lows_sorted[2][1]):
            return None

        # 计算趋势线
        # 下降趋势线（高点连线）：y = m1 * x + b1
        x1_high = highs_sorted[0][0]
        y1_high = highs_sorted[0][1]
        x2_high = highs_sorted[2][0]
        y2_high = highs_sorted[2][1]

        if x2_high == x1_high:
            return None

        m1 = (y2_high - y1_high) / (x2_high - x1_high)
        b1 = y1_high - m1 * x1_high

        # 上升趋势线（低点连线）：y = m2 * x + b2
        x1_low = lows_sorted[0][0]
        y1_low = lows_sorted[0][1]
        x2_low = lows_sorted[2][0]
        y2_low = lows_sorted[2][1]

        if x2_low == x1_low:
            return None

        m2 = (y2_low - y1_low) / (x2_low - x1_low)
        b2 = y1_low - m2 * x1_low

        # 检查是否收敛（两线斜率相反）
        if m1 >= 0 or m2 <= 0:
            return None

        # 当前K线索引（相对于recent）
        current_idx = len(recent) - 1

        # 计算当前位置的趋势线值
        upper_trend = m1 * current_idx + b1
        lower_trend = m2 * current_idx + b2

        # 检查突破
        if bar.close > upper_trend:
            # 向上突破
            amplitude = upper_trend - lower_trend
            target = bar.close + amplitude
            stop_loss = lower_trend * 0.99

            return PatternSignal(
                bar_index=len(self.bars) - 1,
                pattern=PatternType.TRIANGLE,
                action="BUY",
                price=bar.close,
                stop_loss=stop_loss,
                target=target,
                reason="对称三角形向上突破"
            )

        if bar.close < lower_trend:
            # 向下跌破
            amplitude = upper_trend - lower_trend
            target = bar.close - amplitude
            stop_loss = upper_trend * 1.01

            return PatternSignal(
                bar_index=len(self.bars) - 1,
                pattern=PatternType.TRIANGLE,
                action="SELL",
                price=bar.close,
                stop_loss=stop_loss,
                target=target,
                reason="对称三角形向下跌破"
            )

        return None

    def _detect_flag(self, bar: Bar) -> Optional[PatternSignal]:
        """
        检测旗形整理形态

        简化实现：检测上升旗形（高点下降、低点下降，平行或略收敛）
        突破上沿趋势线 → 买入（趋势继续）
        跌破下沿趋势线 → 卖出（趋势继续下跌）
        """
        if len(self.bars) < 11:
            return None

        # 获取最近10根历史K线（不包括当前K线）
        recent = self.bars[-11:-1]

        # 找3个高点（下降）
        highs = [(i, b.high) for i, b in enumerate(recent)]
        highs_sorted = sorted(highs, key=lambda x: x[1], reverse=True)[:3]
        highs_sorted = sorted(highs_sorted, key=lambda x: x[0])  # 按时间排序

        # 找3个低点（下降）
        lows = [(i, b.low) for i, b in enumerate(recent)]
        lows_sorted = sorted(lows, key=lambda x: x[1], reverse=True)[:3]
        lows_sorted = sorted(lows_sorted, key=lambda x: x[0])  # 按时间排序

        if len(highs_sorted) < 3 or len(lows_sorted) < 3:
            return None

        # 检查高点是否递减
        if not (highs_sorted[0][1] > highs_sorted[1][1] > highs_sorted[2][1]):
            return None

        # 检查低点是否递减（与三角形的关键区别）
        if not (lows_sorted[0][1] > lows_sorted[1][1] > lows_sorted[2][1]):
            return None

        # 计算趋势线
        # 下降趋势线（高点连线）：y = m1 * x + b1
        x1_high = highs_sorted[0][0]
        y1_high = highs_sorted[0][1]
        x2_high = highs_sorted[2][0]
        y2_high = highs_sorted[2][1]

        if x2_high == x1_high:
            return None

        m1 = (y2_high - y1_high) / (x2_high - x1_high)
        b1 = y1_high - m1 * x1_high

        # 下降趋势线（低点连线）：y = m2 * x + b2
        x1_low = lows_sorted[0][0]
        y1_low = lows_sorted[0][1]
        x2_low = lows_sorted[2][0]
        y2_low = lows_sorted[2][1]

        if x2_low == x1_low:
            return None

        m2 = (y2_low - y1_low) / (x2_low - x1_low)
        b2 = y1_low - m2 * x1_low

        # 检查是否同向下降（旗形特征）
        if m1 >= 0 or m2 >= 0:
            return None

        # 当前K线索引（相对于recent）
        current_idx = len(recent) - 1

        # 计算当前位置的趋势线值
        upper_trend = m1 * current_idx + b1
        lower_trend = m2 * current_idx + b2

        # 检查突破
        if bar.close > upper_trend:
            # 向上突破（上升旗形突破，趋势继续）
            amplitude = upper_trend - lower_trend
            target = bar.close + amplitude
            stop_loss = lower_trend * 0.99

            return PatternSignal(
                bar_index=len(self.bars) - 1,
                pattern=PatternType.FLAG,
                action="BUY",
                price=bar.close,
                stop_loss=stop_loss,
                target=target,
                reason="上升旗形突破，趋势继续"
            )

        if bar.close < lower_trend:
            # 向下跌破（下降旗形跌破，趋势继续下跌）
            amplitude = upper_trend - lower_trend
            target = bar.close - amplitude
            stop_loss = upper_trend * 1.01

            return PatternSignal(
                bar_index=len(self.bars) - 1,
                pattern=PatternType.FLAG,
                action="SELL",
                price=bar.close,
                stop_loss=stop_loss,
                target=target,
                reason="下降旗形跌破，趋势继续"
            )

        return None

    def _detect_rectangle(self, bar: Bar) -> Optional[PatternSignal]:
        """
        检测矩形整理形态

        简化实现：检测水平整理区间（高点水平、低点水平）
        突破阻力线 → 买入，跌破支撑线 → 卖出
        """
        if len(self.bars) < 11:
            return None

        # 获取最近10根历史K线（不包括当前K线）
        recent = self.bars[-11:-1]

        # 找3个最高点（阻力线候选）
        highs = sorted([b.high for b in recent], reverse=True)[:3]
        # 找3个最低点（支撑线候选）
        lows = sorted([b.low for b in recent])[:3]

        if len(highs) < 3 or len(lows) < 3:
            return None

        # 检查高点是否水平（波动在2%以内）
        high_avg = sum(highs) / len(highs)
        high_variance = max(abs(h - high_avg) for h in highs) / high_avg
        if high_variance > 0.02:  # 2%容差
            return None

        # 检查低点是否水平（波动在2%以内）
        low_avg = sum(lows) / len(lows)
        low_variance = max(abs(l - low_avg) for l in lows) / low_avg
        if low_variance > 0.02:  # 2%容差
            return None

        # 检查是否有足够的振幅（矩形高度）
        rectangle_height = high_avg - low_avg
        if rectangle_height / low_avg < 0.03:  # 至少3%振幅
            return None

        # 当前K线突破检测
        if bar.close > high_avg:
            # 向上突破阻力线
            target = bar.close + rectangle_height
            stop_loss = low_avg * 0.99

            return PatternSignal(
                bar_index=len(self.bars) - 1,
                pattern=PatternType.RECTANGLE,
                action="BUY",
                price=bar.close,
                stop_loss=stop_loss,
                target=target,
                reason="矩形整理向上突破"
            )

        if bar.close < low_avg:
            # 向下跌破支撑线
            target = bar.close - rectangle_height
            stop_loss = high_avg * 1.01

            return PatternSignal(
                bar_index=len(self.bars) - 1,
                pattern=PatternType.RECTANGLE,
                action="SELL",
                price=bar.close,
                stop_loss=stop_loss,
                target=target,
                reason="矩形整理向下跌破"
            )

        return None

    def _detect_rounding_bottom(self, bar: Bar) -> Optional[PatternSignal]:
        """
        检测圆弧底形态

        简化实现：检测价格先降后升的圆弧形状
        - 至少15根K线形成形态
        - 价格先下跌后上涨，形成圆弧
        - 突破颈线（起点水平）买入
        """
        if len(self.bars) < 16:
            return None

        # 获取最近15根历史K线（不包括当前K线）
        recent = self.bars[-16:-1]

        # 颈线 = 形态起点价格
        neckline = recent[0].high

        # 找最低点（应在形态中间区域）
        lows = [(i, b.low) for i, b in enumerate(recent)]
        min_idx, min_low = min(lows, key=lambda x: x[1])

        # 最低点应在中间区域（避免在两端）
        if min_idx < 5 or min_idx > 10:
            return None

        # 检查前半段是否整体下降（从起点到最低点）
        first_half = recent[:min_idx]
        if len(first_half) < 3:
            return None

        # 起点应高于最低点
        if recent[0].high <= min_low * 1.05:  # 至少5%跌幅
            return None

        # 检查后半段是否整体上升（从最低点到终点）
        second_half = recent[min_idx:]
        if len(second_half) < 3:
            return None

        # 终点应接近颈线（在颈线下方5%以内）
        if recent[-1].high < neckline * 0.95:
            return None

        # 检查突破
        if bar.close > neckline:
            # 向上突破颈线
            amplitude = neckline - min_low
            target = bar.close + amplitude
            stop_loss = min_low * 0.99

            return PatternSignal(
                bar_index=len(self.bars) - 1,
                pattern=PatternType.ROUNDING_BOTTOM,
                action="BUY",
                price=bar.close,
                stop_loss=stop_loss,
                target=target,
                reason="圆弧底突破颈线"
            )

        return None

    def _detect_cup_handle(self, bar: Bar) -> Optional[PatternSignal]:
        """
        检测杯柄形态

        简化实现：杯部（圆弧底）+ 柄部（小幅回调）
        - 杯部：15-20根K线，圆弧形下跌上涨
        - 柄部：5-10根K线，小幅回调（不超过杯深1/3）
        - 突破杯口买入
        """
        if len(self.bars) < 25:
            return None

        # 获取最近24根历史K线（不包括当前K线）
        recent = self.bars[-25:-1]

        # 杯口水平（阻力位）= 形态起点
        cup_rim = recent[0].high

        # 找杯底最低点（应在杯部区域）
        cup_section = recent[:19]  # 前19根为杯部
        cup_lows = [(i, b.low) for i, b in enumerate(cup_section)]
        cup_min_idx, cup_min_low = min(cup_lows, key=lambda x: x[1])

        # 杯底应在杯部中间区域
        if cup_min_idx < 7 or cup_min_idx > 12:
            return None

        # 杯深至少5%
        cup_depth = cup_rim - cup_min_low
        if cup_depth < cup_rim * 0.05:
            return None

        # 检查杯部终点是否回到杯口附近（在杯口下方3%以内）
        cup_end_idx = 18  # 杯部结束索引
        if recent[cup_end_idx].high < cup_rim * 0.97:
            return None

        # 柄部区域（后5根K线）
        handle_section = recent[19:]
        if len(handle_section) < 5:
            return None

        # 找柄部最低点
        handle_lows = [b.low for b in handle_section]
        handle_min_low = min(handle_lows)

        # 柄部回调不应超过杯深的1/3
        handle_retracement = cup_rim - handle_min_low
        if handle_retracement > cup_depth / 3:
            return None

        # 柄部终点应接近杯口（在杯口下方2%以内）
        if recent[-1].high < cup_rim * 0.98:
            return None

        # 检查突破杯口
        if bar.close > cup_rim:
            # 向上突破杯口
            target = bar.close + cup_depth
            stop_loss = handle_min_low * 0.99

            return PatternSignal(
                bar_index=len(self.bars) - 1,
                pattern=PatternType.CUP_HANDLE,
                action="BUY",
                price=bar.close,
                stop_loss=stop_loss,
                target=target,
                reason="杯柄形态突破杯口"
            )

        return None

    def _detect_breakout_pullback(self, bar: Bar) -> Optional[PatternSignal]:
        """
        检测过前高形态

        简化实现：
        - 记录最近10根K线的高点作为前期高点
        - 突破前期高点后，3-5根K线内回踩不破前高
        - 再突破买入
        """
        if len(self.bars) < 20:
            return None

        # 获取最近20根历史K线（不包括当前K线）
        recent = self.bars[-20:-1]

        # 前期高点 = 前10根K线的最高点（突破前的整理区间）
        prior_section = recent[:10]
        prior_high = max(b.high for b in prior_section)

        # 找突破点（在后10根K线中找收盘价突破前期高点的位置）
        breakout_section = recent[10:]
        breakout_idx = None
        for i, b in enumerate(breakout_section):
            if b.close > prior_high:
                breakout_idx = 10 + i
                break

        if breakout_idx is None:
            return None

        # 突破后需要有回踩（至少2根K线）
        if len(recent) - breakout_idx < 3:
            return None

        # 检查回踩是否跌破前高
        pullback_section = recent[breakout_idx + 1:]
        for b in pullback_section:
            if b.low < prior_high * 0.99:  # 允许1%误差
                return None

        # 检查当前是否再次突破（收盘价高于突破点）
        breakout_price = recent[breakout_idx].close
        if bar.close > breakout_price:
            # 计算目标价（等幅测距）
            amplitude = breakout_price - prior_high
            target = bar.close + amplitude
            stop_loss = prior_high * 0.99

            return PatternSignal(
                bar_index=len(self.bars) - 1,
                pattern=PatternType.BREAKOUT_PULLBACK,
                action="BUY",
                price=bar.close,
                stop_loss=stop_loss,
                target=target,
                reason="过前高形态确认"
            )

        return None

    def reset(self) -> None:
        """重置策略状态"""
        self.bars = []
        self.platform = None
        self.state = PatternType.NONE
        self.signals = []
        self.annotations = []
        self.breakdown_bar = None
        self.breakdown_low = 0
        self.platform_avg_volume = 0
        self.position = 0
        self.entry_price = 0.0
        self.stop_loss = 0.0
        self.target_price = 0.0
