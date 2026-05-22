"""Tests for MetricsCalculator"""

import pytest
from datetime import datetime
from caisen.result.types import BacktestResult
from caisen.result.calculator import MetricsCalculator
from caisen.core.trade import Trade
from caisen.core.order import Side


@pytest.fixture
def sample_equity_curve():
    """Sample equity curve for testing."""
    return [
        {"timestamp": "2024-01-01", "equity": 100000, "cash": 100000, "positions": {}},
        {"timestamp": "2024-01-02", "equity": 105000, "cash": 105000, "positions": {}},
        {"timestamp": "2024-01-03", "equity": 110000, "cash": 110000, "positions": {}},
        {"timestamp": "2024-01-04", "equity": 115000, "cash": 115000, "positions": {}},  # Peak
        {"timestamp": "2024-01-05", "equity": 108000, "cash": 108000, "positions": {}},  # Drawdown starts
        {"timestamp": "2024-01-06", "equity": 100000, "cash": 100000, "positions": {}},  # Max drawdown
        {"timestamp": "2024-01-07", "equity": 102000, "cash": 102000, "positions": {}},
        {"timestamp": "2024-01-08", "equity": 120000, "cash": 120000, "positions": {}},  # New peak
    ]


class TestMaxDrawdown:
    """Tests for max_drawdown calculation."""

    def test_max_drawdown_basic(self, sample_equity_curve):
        """Test basic max drawdown calculation."""
        result = BacktestResult(
            strategy_name="Test",
            bars=[],
            trades=[],
            equity_curve=sample_equity_curve,
            annotations=[],
            initial_capital=100000,
            final_equity=120000,
        )

        calculator = MetricsCalculator()
        metrics = calculator.calculate(result)

        # Peak is 115000, trough is 100000
        # Max drawdown = (115000 - 100000) / 115000 = 13.04%
        assert abs(metrics.max_drawdown + 0.1304) < 0.01  # max_drawdown 为负值

    def test_max_drawdown_empty_curve(self):
        """Test with empty equity curve."""
        result = BacktestResult(
            strategy_name="Test",
            bars=[],
            trades=[],
            equity_curve=[],
            annotations=[],
            initial_capital=100000,
            final_equity=100000,
        )

        calculator = MetricsCalculator()
        metrics = calculator.calculate(result)

        assert metrics.max_drawdown == 0.0

    def test_max_drawdown_no_drawdown(self):
        """Test when equity only goes up."""
        result = BacktestResult(
            strategy_name="Test",
            bars=[],
            trades=[],
            equity_curve=[
                {"timestamp": "2024-01-01", "equity": 100000, "cash": 100000, "positions": {}},
                {"timestamp": "2024-01-02", "equity": 105000, "cash": 105000, "positions": {}},
                {"timestamp": "2024-01-03", "equity": 110000, "cash": 110000, "positions": {}},
            ],
            annotations=[],
            initial_capital=100000,
            final_equity=110000,
        )

        calculator = MetricsCalculator()
        metrics = calculator.calculate(result)

        assert metrics.max_drawdown == 0.0


class TestSharpeRatio:
    """Tests for sharpe_ratio calculation."""

    def test_sharpe_ratio_empty_curve(self):
        """Test with empty equity curve."""
        result = BacktestResult(
            strategy_name="Test",
            bars=[],
            trades=[],
            equity_curve=[],
            annotations=[],
            initial_capital=100000,
            final_equity=100000,
        )

        calculator = MetricsCalculator()
        metrics = calculator.calculate(result)

        assert metrics.sharpe_ratio == 0.0

    def test_sharpe_ratio_no_volatility(self):
        """Test when equity is flat (no volatility)."""
        result = BacktestResult(
            strategy_name="Test",
            bars=[],
            trades=[],
            equity_curve=[
                {"timestamp": "2024-01-01", "equity": 100000, "cash": 100000, "positions": {}},
                {"timestamp": "2024-01-02", "equity": 100000, "cash": 100000, "positions": {}},
                {"timestamp": "2024-01-03", "equity": 100000, "cash": 100000, "positions": {}},
            ],
            annotations=[],
            initial_capital=100000,
            final_equity=100000,
        )

        calculator = MetricsCalculator()
        metrics = calculator.calculate(result)

        assert metrics.sharpe_ratio == 0.0


class TestWinRateAndProfitFactor:
    """Tests for win_rate and profit_factor calculations."""

    def test_win_rate_empty_trades(self):
        """Test with no trades."""
        result = BacktestResult(
            strategy_name="Test",
            bars=[],
            trades=[],
            equity_curve=[],
            annotations=[],
            initial_capital=100000,
            final_equity=100000,
        )

        calculator = MetricsCalculator()
        metrics = calculator.calculate(result)

        assert metrics.win_rate == 0.0
        assert metrics.profit_factor == 0.0

    def test_win_rate_mixed_trades(self):
        """Test with winning and losing trades."""
        from datetime import datetime
        from caisen.core.order import Side

        trades = [
            Trade(timestamp=datetime(2024, 1, 1), symbol="AAPL", side=Side.BUY, quantity=100, price=100, commission=1, slippage=0.1, order_id="1"),
            Trade(timestamp=datetime(2024, 1, 2), symbol="AAPL", side=Side.SELL, quantity=100, price=110, commission=1, slippage=0.1, order_id="2"),  # Win +1000
            Trade(timestamp=datetime(2024, 1, 3), symbol="AAPL", side=Side.BUY, quantity=100, price=100, commission=1, slippage=0.1, order_id="3"),
            Trade(timestamp=datetime(2024, 1, 4), symbol="AAPL", side=Side.SELL, quantity=100, price=90, commission=1, slippage=0.1, order_id="4"),   # Loss -1000
        ]

        result = BacktestResult(
            strategy_name="Test",
            bars=[],
            trades=trades,
            equity_curve=[],
            annotations=[],
            initial_capital=100000,
            final_equity=99000,
        )

        calculator = MetricsCalculator()
        metrics = calculator.calculate(result)

        assert metrics.win_rate == 0.5  # 1 win out of 2
        assert abs(metrics.profit_factor - 1.0) < 0.01  # 约等于 1.0 (考虑手续费)


class TestTotalReturn:
    """Tests for total_return calculation."""

    def test_total_return_basic(self):
        """Test total return calculation."""
        result = BacktestResult(
            strategy_name="Test",
            bars=[],
            trades=[],
            equity_curve=[],
            annotations=[],
            initial_capital=100000,
            final_equity=120000,
        )

        calculator = MetricsCalculator()
        metrics = calculator.calculate(result)

        assert metrics.total_return == 0.2  # 20% return


class TestCalculatorIntegration:
    """Integration tests for MetricsCalculator."""

    def test_full_metrics_calculation(self):
        """Test full metrics calculation."""
        result = BacktestResult(
            strategy_name="Test",
            bars=[],
            trades=[
                Trade(timestamp=datetime(2024, 1, 1), symbol="AAPL", side=Side.BUY, quantity=100, price=100, commission=1, slippage=0.1, order_id="1"),
                Trade(timestamp=datetime(2024, 1, 2), symbol="AAPL", side=Side.SELL, quantity=100, price=110, commission=1, slippage=0.1, order_id="2"),
            ],
            equity_curve=[
                {"timestamp": "2024-01-01", "equity": 100000, "cash": 100000, "positions": {}},
                {"timestamp": "2024-01-02", "equity": 109999, "cash": 109999, "positions": {}},
            ],
            annotations=[],
            initial_capital=100000,
            final_equity=109999,
        )

        calculator = MetricsCalculator()
        metrics = calculator.calculate(result)

        # Verify all fields are present
        assert metrics.total_return is not None
        assert metrics.annual_return is not None
        assert metrics.max_drawdown is not None
        assert metrics.sharpe_ratio is not None
        assert metrics.win_rate is not None
        assert metrics.total_trades is not None
        assert metrics.profit_factor is not None
        assert metrics.avg_win is not None
        assert metrics.avg_loss is not None