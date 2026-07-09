"""MetricsCalculator - 绩效指标计算器

唯一的指标计算入口。
"""

from dataclasses import dataclass
from typing import List, TYPE_CHECKING

import pandas as pd
import numpy as np

if TYPE_CHECKING:
    from .types import BacktestResult
    from ..core.order import Side


@dataclass
class PerformanceMetrics:
    """绩效指标

    数据容器，不含计算逻辑。
    """
    annual_return: float  # 年化收益率
    max_drawdown: float  # 最大回撤
    sharpe_ratio: float  # 夏普比率
    win_rate: float  # 胜率
    total_trades: int  # 总交易数
    profit_factor: float  # 盈亏比
    avg_win: float  # 平均盈利
    avg_loss: float  # 平均亏损
    total_return: float  # 总收益率


class MetricsCalculator:
    """绩效指标计算器

    唯一的指标计算入口。

    Example:
        calculator = MetricsCalculator()
        metrics = calculator.calculate(result)
        print(f"年化收益: {metrics.annual_return:.2%}")
    """

    def calculate(self, result: "BacktestResult") -> PerformanceMetrics:
        """计算绩效指标

        Args:
            result: 回测结果

        Returns:
            PerformanceMetrics 绩效指标
        """
        # 总收益率
        total_return = self._calc_total_return(result)

        # 年化收益率
        annual_return = self._calc_annual_return(result)

        # 最大回撤
        max_drawdown = self._calc_max_drawdown(result)

        # 夏普比率
        sharpe_ratio = self._calc_sharpe_ratio(result)

        # 交易统计
        trades_stats = self._calc_trades_stats(result)

        return PerformanceMetrics(
            annual_return=annual_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            win_rate=trades_stats["win_rate"],
            total_trades=trades_stats["total_trades"],
            profit_factor=trades_stats["profit_factor"],
            avg_win=trades_stats["avg_win"],
            avg_loss=trades_stats["avg_loss"],
            total_return=total_return,
        )

    def _calc_total_return(self, result: "BacktestResult") -> float:
        """计算总收益率"""
        if result.initial_capital == 0:
            return 0.0
        return (result.final_equity - result.initial_capital) / result.initial_capital

    def _calc_annual_return(self, result: "BacktestResult") -> float:
        """计算年化收益率（假设每年 250 个交易日）"""
        if not result.equity_curve or result.initial_capital == 0:
            return 0.0

        total_return = self._calc_total_return(result)
        days = len(result.equity_curve)
        years = days / 250

        if years <= 0:
            return 0.0

        return (1 + total_return) ** (1 / years) - 1

    def _calc_max_drawdown(self, result: "BacktestResult") -> float:
        """计算最大回撤"""
        if not result.equity_curve:
            return 0.0

        equity_series = pd.Series([e["equity"] for e in result.equity_curve])
        peak = equity_series.cummax()
        drawdown = (equity_series - peak) / peak
        return drawdown.min()

    def _calc_sharpe_ratio(self, result: "BacktestResult") -> float:
        """计算夏普比率（假设无风险利率为0，年化）"""
        if len(result.equity_curve) < 2:
            return 0.0

        equity_series = pd.Series([e["equity"] for e in result.equity_curve])
        returns = equity_series.pct_change().dropna()

        if len(returns) == 0 or returns.std() == 0:
            return 0.0

        return np.sqrt(250) * returns.mean() / returns.std()

    def _calc_trades_stats(self, result: "BacktestResult") -> dict:
        """计算交易统计（支持多头和空头配对）"""
        from ..core.order import Side

        trades = result.trades
        total_trades = len(trades)

        if total_trades == 0:
            return {
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "total_trades": 0,
            }

        # 配对交易：支持多头（BUY→SELL）和空头（SELL→BUY）
        position = None
        wins = 0
        losses = 0
        total_profit = 0.0
        total_loss = 0.0

        for trade in sorted(trades, key=lambda t: t.timestamp):
            if position is None:
                # 开仓
                position = {
                    "side": trade.side,
                    "price": trade.price,
                    "qty": trade.quantity,
                    "commission": trade.commission,
                }
            else:
                # 平仓：方向相反时配对
                if (position["side"] == Side.BUY and trade.side == Side.SELL) or \
                   (position["side"] == Side.SELL and trade.side == Side.BUY):
                    if position["side"] == Side.BUY:
                        # 多头：卖价 - 买价
                        profit = (trade.price - position["price"]) * position["qty"] \
                                 - trade.commission - position["commission"]
                    else:
                        # 空头：卖价 - 买价（反向）
                        profit = (position["price"] - trade.price) * position["qty"] \
                                 - trade.commission - position["commission"]

                    if profit > 0:
                        wins += 1
                        total_profit += profit
                    else:
                        losses += 1
                        total_loss += abs(profit)
                    position = None

        total_closed = wins + losses

        return {
            "win_rate": wins / total_closed if total_closed > 0 else 0.0,
            "profit_factor": total_profit / total_loss if total_loss > 0 else 0.0,
            "avg_win": total_profit / wins if wins > 0 else 0.0,
            "avg_loss": total_loss / losses if losses > 0 else 0.0,
            "total_trades": total_trades,
        }