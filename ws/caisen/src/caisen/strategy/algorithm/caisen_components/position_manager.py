"""PositionManager - 仓位管理器

管理持仓状态、止损/止盈判断、回调通知。
"""

from dataclasses import dataclass
from typing import Optional, Callable, TYPE_CHECKING

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