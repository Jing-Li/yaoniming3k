"""Result types for backtesting."""

from dataclasses import dataclass
from typing import List

from ..strategy.base import Annotation


@dataclass
class BacktestResult:
    """回测结果

    一次 Run 的输出，包含交易记录、净值曲线、绩效指标、可视化标注等结构化数据。

    Attributes:
        strategy_name: 策略名称
        bars: K线数据列表
        trades: 交易记录列表
        equity_curve: 净值曲线数据
        annotations: 可视化标注列表
        initial_capital: 初始资金
        final_equity: 最终净值
    """
    strategy_name: str
    bars: List
    trades: List
    equity_curve: List[dict]
    annotations: List[Annotation]
    initial_capital: float
    final_equity: float

    @property
    def total_return(self) -> float:
        """总收益率"""
        return (self.final_equity - self.initial_capital) / self.initial_capital

    @property
    def max_drawdown(self) -> float:
        """最大回撤 (从峰值到谷底的最大跌幅)"""
        if not self.equity_curve:
            return 0.0

        peak = 0.0
        max_dd = 0.0

        for entry in self.equity_curve:
            equity = entry.get("equity", 0)
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd

        return max_dd

    @property
    def sharpe_ratio(self) -> float:
        """夏普比率 (假设无风险利率为0，年化)"""
        if len(self.equity_curve) < 2:
            return 0.0

        # 计算每日收益率
        returns = []
        for i in range(1, len(self.equity_curve)):
            prev_equity = self.equity_curve[i - 1].get("equity", 0)
            curr_equity = self.equity_curve[i].get("equity", 0)
            if prev_equity > 0:
                returns.append((curr_equity - prev_equity) / prev_equity)

        if not returns or len(returns) < 2:
            return 0.0

        # 平均收益率
        avg_return = sum(returns) / len(returns)

        # 标准差
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        std = variance ** 0.5

        if std == 0:
            return 0.0

        # 年化 (假设252交易日)
        return (avg_return / std) * (252 ** 0.5)

    @property
    def win_rate(self) -> float:
        """胜率 (盈利交易数 / 总交易数)"""
        if not self.trades:
            return 0.0

        # 配对交易：按时间顺序匹配 BUY/SELL
        position = None
        profits = []

        from ..core.order import Side
        for trade in sorted(self.trades, key=lambda t: t.timestamp):
            if trade.side == Side.BUY:
                position = {"price": trade.price, "qty": trade.quantity}
            elif trade.side == Side.SELL and position:
                profit = (trade.price - position["price"]) * position["qty"]
                profits.append(profit)
                position = None

        if not profits:
            return 0.0

        wins = sum(1 for p in profits if p > 0)
        return wins / len(profits)

    @property
    def profit_factor(self) -> float:
        """盈亏比 (总盈利 / 总亏损)"""
        if not self.trades:
            return 0.0

        # 配对交易
        position = None
        gross_profit = 0.0
        gross_loss = 0.0

        from ..core.order import Side
        for trade in sorted(self.trades, key=lambda t: t.timestamp):
            if trade.side == Side.BUY:
                position = {"price": trade.price, "qty": trade.quantity}
            elif trade.side == Side.SELL and position:
                profit = (trade.price - position["price"]) * position["qty"]
                if profit > 0:
                    gross_profit += profit
                else:
                    gross_loss += abs(profit)
                position = None

        if gross_loss == 0:
            return 0.0 if gross_profit == 0 else float('inf')

        return gross_profit / gross_loss