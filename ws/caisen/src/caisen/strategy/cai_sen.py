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
from .base import Strategy, Annotation


class PatternType(Enum):
    """形态类型"""
    NONE = auto()
    PLATFORM_FORMING = auto()   # 整理平台形成中
    BREAKDOWN_PULLBACK = auto() # 破底翻（第一买点）
    BREAKOUT = auto()           # 突破平台上沿（第二买点）
    FAKE_BREAKOUT = auto()      # 假突破（空头信号）
    W_BOTTOM = auto()           # W底
    M_TOP = auto()              # M头


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
    蔡森十二形态策略
    
    参数:
        platform_min_bars: 整理平台最少K线数（默认10）
        platform_max_amplitude: 整理平台最大振幅（默认5%）
        breakdown_max_pct: 破底最大幅度（默认2%）
        pullback_max_bars: 破底后最大拉回K线数（默认3）
        volume_confirm: 是否启用成交量确认（默认True）
    """
    
    def __init__(self, 
                 platform_min_bars: int = 10,
                 platform_max_amplitude: float = 0.05,
                 breakdown_max_pct: float = 0.02,
                 pullback_max_bars: int = 3,
                 volume_confirm: bool = True):
        
        self.platform_min_bars = platform_min_bars
        self.platform_max_amplitude = platform_max_amplitude
        self.breakdown_max_pct = breakdown_max_pct
        self.pullback_max_bars = pullback_max_bars
        self.volume_confirm = volume_confirm
        
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
        
        # 持仓状态
        self.position = 0  # 0=空仓, 1=第一买点持仓, 2=第二买点持仓
        self.entry_price = 0.0
        self.stop_loss = 0.0
        
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
                return Order(symbol=bar.symbol, side=Side.BUY, quantity=0)

            # 破底后超过N根K线未拉回，失效，重新检测平台
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
                    return Order(symbol=bar.symbol, side=Side.BUY, quantity=0)
        
        # 5. 检测假突破（空头信号）
        if self.state == PatternType.PLATFORM_FORMING:
            fake_breakout = self._detect_fake_breakout(bar)
            if fake_breakout:
                self.signals.append(fake_breakout)
                self._add_annotation(bar, "假突破", "orange")
                return Order(symbol=bar.symbol, side=Side.SELL, quantity=0)
        
        # 持仓中：检查止损
        if self.position > 0 and bar.low < self.stop_loss:
            self.position = 0
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
        upper = min(highs)  # 上沿 = 近期高点中的最低（阻力）
        lower = max(lows)   # 下沿 = 近期低点中的最高（支撑）
        
        # 检查振幅
        if lower <= 0:
            return False
        amplitude = (upper - lower) / lower
        if amplitude > self.platform_max_amplitude:
            return False
        
        # 记录平台平均成交量（用于后续确认）
        self.platform_avg_volume = sum(volumes) / len(volumes)
        
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
        
        标准：
        - 收盘价跌破平台下沿
        - 跌破幅度不超过breakdown_max_pct（刺破而非真突破）
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
        current_index = len(self.bars) - 1
        self.annotations.append(Annotation(
            bar_index=current_index,
            type="marker",
            points=[(current_index, bar.close)],
            label=label,
            color=color
        ))
    
    def get_annotations(self) -> List[Annotation]:
        """获取可视化标注"""
        return self.annotations
    
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
