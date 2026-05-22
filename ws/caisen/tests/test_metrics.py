"""Tests for Performance Metrics calculation"""

import pytest
from datetime import datetime
from caisen.result.calculator import MetricsCalculator, PerformanceMetrics
from caisen.result.types import BacktestResult
from caisen.core.order import Side, Order
from caisen.core.trade import Trade
from caisen.strategy.base import Annotation, AnnotationType


def create_test_result(
    trades=None,
    equity_curve=None,
    initial_capital=100000.0,
    final_equity=120000.0,
):
    """Create a BacktestResult for testing"""
    return BacktestResult(
        strategy_name="TestStrategy",
        bars=[],
        trades=trades or [],
        equity_curve=equity_curve or [
            {"timestamp": datetime(2024, 1, i + 1), "equity": initial_capital * (1 + i * 0.001)}
            for i in range(10)
        ],
        annotations=[],
        initial_capital=initial_capital,
        final_equity=final_equity,
    )


class TestCalculateMetrics:
    """Tests for MetricsCalculator.calculate()"""

    def test_calculate_metrics_no_trades(self):
        """Test metrics when there are no trades"""
        result = create_test_result(trades=[], equity_curve=[])
        calculator = MetricsCalculator()
        metrics = calculator.calculate(result)

        assert isinstance(metrics, PerformanceMetrics)
        assert metrics.total_trades == 0
        assert metrics.win_rate == 0

    def test_calculate_metrics_with_winning_trades(self):
        """Test metrics with winning trades only"""
        trades = [
            Trade(
                timestamp=datetime(2024, 1, 1),
                symbol="TEST",
                side=Side.BUY,
                quantity=100,
                price=10.0,
                commission=1.0,
                slippage=0.0,
                order_id="1",
            ),
            Trade(
                timestamp=datetime(2024, 1, 2),
                symbol="TEST",
                side=Side.SELL,
                quantity=100,
                price=12.0,
                commission=1.0,
                slippage=0.0,
                order_id="2",
            ),
        ]
        result = create_test_result(trades=trades)
        calculator = MetricsCalculator()
        metrics = calculator.calculate(result)

        # total_trades counts all trades
        assert metrics.total_trades == 2
        # win_rate counts completed pairs
        assert metrics.win_rate == 1.0
        assert metrics.avg_win > 0

    def test_calculate_metrics_with_losing_trades(self):
        """Test metrics with losing trades only"""
        trades = [
            Trade(
                timestamp=datetime(2024, 1, 1),
                symbol="TEST",
                side=Side.BUY,
                quantity=100,
                price=10.0,
                commission=1.0,
                slippage=0.0,
                order_id="1",
            ),
            Trade(
                timestamp=datetime(2024, 1, 2),
                symbol="TEST",
                side=Side.SELL,
                quantity=100,
                price=8.0,
                commission=1.0,
                slippage=0.0,
                order_id="2",
            ),
        ]
        result = create_test_result(trades=trades)
        calculator = MetricsCalculator()
        metrics = calculator.calculate(result)

        # total_trades counts all trades
        assert metrics.total_trades == 2
        # win_rate counts completed pairs
        assert metrics.win_rate == 0.0

    def test_calculate_metrics_mixed_trades(self):
        """Test metrics with mixed winning and losing trades"""
        trades = [
            # Win
            Trade(timestamp=datetime(2024, 1, 1), symbol="TEST", side=Side.BUY, quantity=100, price=10.0, commission=1.0, slippage=0.0, order_id="1"),
            Trade(timestamp=datetime(2024, 1, 2), symbol="TEST", side=Side.SELL, quantity=100, price=12.0, commission=1.0, slippage=0.0, order_id="2"),
            # Loss
            Trade(timestamp=datetime(2024, 1, 3), symbol="TEST", side=Side.BUY, quantity=100, price=10.0, commission=1.0, slippage=0.0, order_id="3"),
            Trade(timestamp=datetime(2024, 1, 4), symbol="TEST", side=Side.SELL, quantity=100, price=8.0, commission=1.0, slippage=0.0, order_id="4"),
        ]
        result = create_test_result(trades=trades)
        calculator = MetricsCalculator()
        metrics = calculator.calculate(result)

        # total_trades counts all trades
        assert metrics.total_trades == 4
        # win_rate counts completed pairs
        assert metrics.win_rate == 0.5

    def test_calculate_metrics_profit_factor(self):
        """Test profit factor calculation"""
        trades = [
            # Win 200
            Trade(timestamp=datetime(2024, 1, 1), symbol="TEST", side=Side.BUY, quantity=100, price=10.0, commission=0.0, slippage=0.0, order_id="1"),
            Trade(timestamp=datetime(2024, 1, 2), symbol="TEST", side=Side.SELL, quantity=100, price=12.0, commission=0.0, slippage=0.0, order_id="2"),
            # Loss 100
            Trade(timestamp=datetime(2024, 1, 3), symbol="TEST", side=Side.BUY, quantity=100, price=10.0, commission=0.0, slippage=0.0, order_id="3"),
            Trade(timestamp=datetime(2024, 1, 4), symbol="TEST", side=Side.SELL, quantity=100, price=9.0, commission=0.0, slippage=0.0, order_id="4"),
        ]
        result = create_test_result(trades=trades)
        calculator = MetricsCalculator()
        metrics = calculator.calculate(result)

        # Profit factor = gross_profit / gross_loss = 200 / 100 = 2.0
        assert metrics.profit_factor == 2.0


class TestPerformanceMetrics:
    """Tests for PerformanceMetrics dataclass"""

    def test_performance_metrics_creation(self):
        """Test creating PerformanceMetrics"""
        metrics = PerformanceMetrics(
            annual_return=0.15,
            max_drawdown=-0.1,
            sharpe_ratio=1.5,
            win_rate=0.6,
            total_trades=10,
            profit_factor=1.8,
            avg_win=200.0,
            avg_loss=100.0,
            total_return=0.2,
        )

        assert metrics.annual_return == 0.15
        assert metrics.total_trades == 10
        assert metrics.win_rate == 0.6
