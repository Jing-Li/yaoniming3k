"""空头交易统计测试 — 验证 MetricsCalculator 支持 SELL→BUY 配对。"""

import pytest
from datetime import datetime

from caisen.result.calculator import MetricsCalculator
from caisen.result.types import BacktestResult
from caisen.core.order import Side


def _make_result(trades, equity_curve=None):
    return BacktestResult(
        strategy_name="Test",
        bars=[],
        trades=trades,
        equity_curve=equity_curve or [
            {"timestamp": datetime(2024, 1, i + 1), "equity": 100000}
            for i in range(5)
        ],
        annotations=[],
        initial_capital=100000,
        final_equity=100000,
    )


class TestShortTradeStats:
    """验证空头（SELL→BUY）交易配对统计。"""

    def test_short_winning_pair(self, short_winning_pair):
        """空头盈利：卖 12 买 10 → 盈利。"""
        result = _make_result(short_winning_pair)
        calc = MetricsCalculator()
        metrics = calc.calculate(result)
        assert metrics.win_rate == 1.0
        assert metrics.total_trades == 2
        assert metrics.avg_win > 0

    def test_short_losing_pair(self, short_losing_pair):
        """空头亏损：卖 10 买 12 → 亏损。"""
        result = _make_result(short_losing_pair)
        calc = MetricsCalculator()
        metrics = calc.calculate(result)
        assert metrics.win_rate == 0.0
        assert metrics.avg_loss > 0

    def test_mixed_long_and_short_pairs(self, winning_pair, short_winning_pair):
        """混合多头 + 空头盈利配对：胜率应为 100%。"""
        all_trades = winning_pair + short_winning_pair
        result = _make_result(all_trades)
        calc = MetricsCalculator()
        metrics = calc.calculate(result)
        assert metrics.win_rate == 1.0
        assert metrics.total_trades == 4

    def test_mixed_win_loss_long_short(self, winning_pair, short_losing_pair):
        """一多赢 + 一空亏：胜率 50%。"""
        all_trades = winning_pair + short_losing_pair
        result = _make_result(all_trades)
        calc = MetricsCalculator()
        metrics = calc.calculate(result)
        assert metrics.win_rate == 0.5
        assert metrics.total_trades == 4

    def test_profit_factor_short_trades(self, short_winning_pair, short_losing_pair):
        """空头盈亏比：盈利 200 / 亏损 200 = 1.0。"""
        # 构造：空头盈利（卖12买10，盈利200）和空头亏损（卖10买12，亏损200）
        trades = short_winning_pair + short_losing_pair
        result = _make_result(trades)
        calc = MetricsCalculator()
        metrics = calc.calculate(result)
        assert metrics.profit_factor == pytest.approx(1.0, abs=0.1)

    def test_unclosed_position_not_counted(self):
        """未平仓的单独 SELL 不应计入胜率统计。"""
        from tests.conftest import make_trade
        trades = [make_trade(day=1, side=Side.SELL, price=10.0)]
        result = _make_result(trades)
        calc = MetricsCalculator()
        metrics = calc.calculate(result)
        assert metrics.win_rate == 0.0
        assert metrics.total_trades == 1
