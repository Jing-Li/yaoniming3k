"""MA Cross 策略示例"""

from typing import List, Optional
from caisen.core.bar import Bar
from caisen.core.order import Order, Side
from caisen.core.config import BacktestConfig
from caisen.strategy.base import Strategy


class MACrossStrategy(Strategy):
    """移动均线金叉死叉策略"""

    def __init__(self, fast: int = 5, slow: int = 20):
        self.fast = fast
        self.slow = slow
        self.prices: List[float] = []
        self.position = 0  # 0 = 空仓, 1 = 多头, -1 = 空头

    def on_init(self, config: BacktestConfig) -> None:
        """初始化，可从 config 获取参数"""
        pass

    def on_bar(self, bar: Bar) -> Optional[Order]:
        self.prices.append(bar.close)
        if len(self.prices) < self.slow:
            return None

        ma_fast = sum(self.prices[-self.fast:]) / self.fast
        ma_slow = sum(self.prices[-self.slow:]) / self.slow

        # 金叉买入
        if self.position <= 0 and ma_fast > ma_slow:
            self.position = 1
            return Order(symbol=bar.symbol, side=Side.BUY, quantity=0)

        # 死叉卖出
        if self.position >= 0 and ma_fast < ma_slow:
            self.position = -1
            return Order(symbol=bar.symbol, side=Side.SELL, quantity=0)

        return None

    def reset(self) -> None:
        self.prices = []
        self.position = 0