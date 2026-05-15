"""Performance Metrics (绩效指标) 计算"""

from dataclasses import dataclass
from typing import List
import pandas as pd
import numpy as np

from ..core.engine import BacktestResult
from ..core.order import Side


@dataclass
class PerformanceMetrics:
    """绩效指标"""
    annual_return: float  # 年化收益率
    max_drawdown: float  # 最大回撤
    sharpe_ratio: float  # 夏普比率
    win_rate: float  # 胜率
    total_trades: int  # 总交易数
    profit_factor: float  # 盈亏比
    avg_win: float  # 平均盈利
    avg_loss: float  # 平均亏损
    total_return: float  # 总收益率


def calculate_metrics(result: BacktestResult) -> PerformanceMetrics:
    """计算绩效指标"""
    # 总收益率
    total_return = result.total_return

    # 计算年化收益率（假设每年 250 个交易日）
    days = len(result.equity_curve)
    years = days / 250
    annual_return = (result.final_equity / result.initial_capital) ** (1 / years) - 1 if years > 0 else 0

    # 计算最大回撤
    equity_series = pd.Series([e["equity"] for e in result.equity_curve])
    peak = equity_series.cummax()
    drawdown = (equity_series - peak) / peak
    max_drawdown = drawdown.min()

    # 计算夏普比率
    returns = equity_series.pct_change().dropna()
    if len(returns) > 0 and returns.std() > 0:
        sharpe_ratio = np.sqrt(250) * returns.mean() / returns.std()
    else:
        sharpe_ratio = 0

    # 计算交易统计
    trades = result.trades
    total_trades = len(trades)

    if total_trades == 0:
        return PerformanceMetrics(
            annual_return=annual_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            win_rate=0,
            total_trades=0,
            profit_factor=0,
            avg_win=0,
            avg_loss=0,
            total_return=total_return,
        )

    # 计算胜率（配对买卖）
    buys = [t for t in trades if t.side == Side.BUY]
    sells = [t for t in trades if t.side == Side.SELL]

    wins = 0
    losses = 0
    total_profit = 0
    total_loss = 0

    # 简化计算：假设买入卖出交替
    for i, trade in enumerate(trades):
        if i > 0:
            prev = trades[i - 1]
            if trade.side == Side.BUY:
                # 平空仓
                profit = (prev.price - trade.price) * trade.quantity - trade.commission - prev.commission
            else:
                # 平多仓
                profit = (trade.price - prev.price) * trade.quantity - trade.commission - prev.commission

            if profit > 0:
                wins += 1
                total_profit += profit
            else:
                losses += 1
                total_loss += abs(profit)

    win_rate = wins / (wins + losses) if (wins + losses) > 0 else 0
    avg_win = total_profit / wins if wins > 0 else 0
    avg_loss = total_loss / losses if losses > 0 else 0
    profit_factor = abs(total_profit) / total_loss if total_loss > 0 else 0

    return PerformanceMetrics(
        annual_return=annual_return,
        max_drawdown=max_drawdown,
        sharpe_ratio=sharpe_ratio,
        win_rate=win_rate,
        total_trades=total_trades,
        profit_factor=profit_factor,
        avg_win=avg_win,
        avg_loss=avg_loss,
        total_return=total_return,
    )