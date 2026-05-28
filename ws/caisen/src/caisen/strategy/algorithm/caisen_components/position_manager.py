"""PositionManager - 仓位管理器

管理持仓状态、止损/止盈判断、回调通知、假突破预警。
"""

from dataclasses import dataclass
from typing import List, Optional, Callable, TYPE_CHECKING

from ..detector import PatternSignal

if TYPE_CHECKING:
    from ....core.bar import Bar


@dataclass
class Position:
    """持仓信息"""
    entry_price: float
    stop_loss: float
    target: float
    entry_bar: "Bar"


class PositionManager:
    """仓位管理器

    管理持仓状态，包含风控判断。

    有状态，包含回调机制。

    Example:
        pm = PositionManager()
        pm.on_stop_loss(lambda bar: print(f"止损: {bar.close}"))

        pm.open(signal=signal)
        if pm.check_stop_loss(bar):
            pm.close()
    """

    def __init__(self):
        """初始化"""
        self._position: Optional[Position] = None
        self._stop_callback: Optional[Callable] = None
        self._profit_callback: Optional[Callable] = None
        self._reset_callback: Optional[Callable] = None
        self._fake_warning: Optional["FakeBreakoutWarning"] = None

    @property
    def fake_warning(self) -> "FakeBreakoutWarning":
        """Lazy-initialized 假突破预警器"""
        if self._fake_warning is None:
            self._fake_warning = FakeBreakoutWarning()
        return self._fake_warning

    @property
    def has_position(self) -> bool:
        """是否有持仓"""
        return self._position is not None

    @property
    def position(self) -> Optional[Position]:
        """获取持仓信息"""
        return self._position

    def on_stop_loss(self, callback: Callable[["Bar"], None]) -> None:
        """注册止损回调

        Args:
            callback: 回调函数，接收当前 bar
        """
        self._stop_callback = callback

    def on_take_profit(self, callback: Callable[["Bar"], None]) -> None:
        """注册止盈回调

        Args:
            callback: 回调函数，接收当前 bar
        """
        self._profit_callback = callback

    def on_reset(self, callback: Callable[[], None]) -> None:
        """注册重置回调（平仓后触发）

        Args:
            callback: 回调函数
        """
        self._reset_callback = callback

    def open(self, signal: PatternSignal, bar: "Bar") -> None:
        """开仓

        Args:
            signal: 信号
            bar: 当前 K 线
        """
        self._position = Position(
            entry_price=bar.close,
            stop_loss=signal.stop_loss,
            target=signal.target,
            entry_bar=bar,
        )

    def close(self) -> None:
        """平仓"""
        self._position = None
        if self._reset_callback:
            self._reset_callback()

    def check_stop_loss(self, bar: "Bar") -> bool:
        """检查是否触发止损

        Args:
            bar: 当前 K 线

        Returns:
            是否触发止损
        """
        if not self._position:
            return False

        # 最低价跌破止损价
        if bar.low < self._position.stop_loss:
            if self._stop_callback:
                self._stop_callback(bar)
            return True

        return False

    def check_take_profit(self, bar: "Bar") -> bool:
        """检查是否触发止盈

        Args:
            bar: 当前 K 线

        Returns:
            是否触发止盈
        """
        if not self._position:
            return False

        # 最高价达到目标价
        if bar.high >= self._position.target:
            if self._profit_callback:
                self._profit_callback(bar)
            return True

        return False

    def get_stop_loss(self) -> Optional[float]:
        """获取当前止损价"""
        if self._position:
            return self._position.stop_loss
        return None

    def get_target(self) -> Optional[float]:
        """获取当前目标价"""
        if self._position:
            return self._position.target
        return None

    def get_entry_price(self) -> Optional[float]:
        """获取入场价"""
        if self._position:
            return self._position.entry_price
        return None

    def reset(self) -> None:
        """重置管理器状态"""
        self._position = None


class FakeBreakoutWarning:
    """持仓期间假突破预警

    在入场后的K线上逐步评估假突破特征，
    当风险等级超过阈值时发出预警信号。
    """

    def __init__(self, warning_threshold: float = 0.4):
        """
        Args:
            warning_threshold: 触发预警的概率阈值
        """
        from ..patterns.fake_breakout import FakeBreakoutFeatures

        self.features = FakeBreakoutFeatures()
        self.warning_threshold = warning_threshold

    def check_holding_risk(
        self,
        bars: List["Bar"],
        entry_idx: int,
        entry_price: float,
        neckline: float,
        range_high: float,
        range_low: float,
    ) -> dict:
        """检查持仓是否面临假突破风险

        在入场后的K线上逐步评估假突破特征。

        Args:
            bars: K线列表
            entry_idx: 入场的K线索引
            entry_price: 入场价
            neckline: 颈线价格
            range_high: 整理区间上沿
            range_low: 整理区间下沿

        Returns:
            {
                'risk_level': 'low' | 'medium' | 'high',
                'fake_probability': float,
                'triggered_features': list[str],
                'recommendation': 'hold' | 'reduce_25' | 'reduce_50' | 'exit'
            }
        """
        if entry_idx < 0 or entry_idx >= len(bars):
            return {
                'risk_level': 'low',
                'fake_probability': 0.0,
                'triggered_features': [],
                'recommendation': 'hold',
            }

        # 使用入场点作为突破点进行评估
        evaluation = self.features.evaluate(
            bars=bars,
            breakout_idx=entry_idx,
            neckline=neckline,
            range_high=range_high,
            range_low=range_low,
        )

        fake_prob = evaluation['fake_probability']
        triggered_features = [
            name for name, info in evaluation['features'].items()
            if info['triggered']
        ]

        # 判断风险等级
        if fake_prob >= 0.6:
            risk_level = 'high'
        elif fake_prob >= self.warning_threshold:
            risk_level = 'medium'
        else:
            risk_level = 'low'

        # 决策建议
        recommendation = self._get_recommendation(risk_level, fake_prob)

        return {
            'risk_level': risk_level,
            'fake_probability': fake_prob,
            'triggered_features': triggered_features,
            'recommendation': recommendation,
        }

    def _get_recommendation(self, risk_level: str, fake_prob: float) -> str:
        """根据风险等级给出操作建议"""
        if risk_level == 'low':
            return 'hold'
        elif risk_level == 'medium':
            return 'reduce_25'
        else:
            # high
            if fake_prob >= 0.8:
                return 'exit'
            return 'reduce_50'

    def get_reduce_ratio(self, risk_level: str) -> float:
        """根据风险等级返回建议减仓比例

        Args:
            risk_level: 'low' | 'medium' | 'high'

        Returns:
            减仓比例 (0 ~ 1.0)
        """
        ratios = {
            'low': 0.0,
            'medium': 0.25,
            'high': 0.5,
        }
        return ratios.get(risk_level, 0.0)