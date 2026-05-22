"""MA Cross 策略示例"""

from typing import List, Optional
from ..core.bar import Bar
from ..core.order import Order, Side
from ..core.config import BacktestConfig
from .base import Strategy, Annotation


class MACrossStrategy(Strategy):
    """移动均线金叉死叉策略"""

    def __init__(self, fast: int = 5, slow: int = 20):
        self.fast = fast
        self.slow = slow
        self.prices: List[float] = []
        self.ma_fast_values: List[float] = []
        self.ma_slow_values: List[float] = []
        self.position = 0  # 0 = 空仓, 1 = 多头, -1 = 空头
        self._annotations: List[Annotation] = []

    def on_init(self, config: BacktestConfig) -> None:
        """初始化，可从 config 获取参数"""
        if config and hasattr(config, 'params'):
            self.fast = config.params.get('fast', self.fast)
            self.slow = config.params.get('slow', self.slow)
        self._annotations = []

    def on_bar(self, bar: Bar) -> Optional[Order]:
        self.prices.append(bar.close)

        if len(self.prices) < self.slow:
            self.ma_fast_values.append(0)
            self.ma_slow_values.append(0)
            return None

        # 计算均线
        ma_fast = sum(self.prices[-self.fast:]) / self.fast
        ma_slow = sum(self.prices[-self.slow:]) / self.slow
        self.ma_fast_values.append(ma_fast)
        self.ma_slow_values.append(ma_slow)

        order = None

        # 金叉买入
        if self.position <= 0 and ma_fast > ma_slow:
            self.position = 1
            order = Order(symbol=bar.symbol, side=Side.BUY, quantity=0)
            self._annotations.append(
                Annotation.buy_signal(bar.timestamp, bar.open, "MA金叉买入")
            )

        # 死叉卖出
        elif self.position >= 0 and ma_fast < ma_slow:
            self.position = -1
            order = Order(symbol=bar.symbol, side=Side.SELL, quantity=0)
            self._annotations.append(
                Annotation.sell_signal(bar.timestamp, bar.open, "MA死叉卖出")
            )

        return order

    def get_annotations(self) -> List[Annotation]:
        """获取可视化标注"""
        return self._annotations.copy()

    def reset(self) -> None:
        self.prices = []
        self.ma_fast_values = []
        self.ma_slow_values = []
        self.position = 0
        self._annotations = []