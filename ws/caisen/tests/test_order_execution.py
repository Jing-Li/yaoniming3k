"""测试订单执行"""

from datetime import datetime
import pytest
from caisen.core.bar import Bar
from caisen.core.order import Order, Side
from caisen.core.engine import BacktestEngine
from caisen.core.config import BacktestConfig
from caisen.strategy.base import Strategy, BarResult


class AlwaysBuyStrategy(Strategy):
    """总是买入的策略"""
    def on_bar(self, bar: Bar) -> BarResult:
        return BarResult(order=Order(symbol=bar.symbol, side=Side.BUY, quantity=100))


def test_market_order_executes_at_next_bar_open():
    """市价单在下一根K线开盘价成交"""
    engine = BacktestEngine(BacktestConfig(initial_capital=100000))

    # 当前 bar
    current_bar = Bar(
        timestamp=datetime(2024, 1, 1),
        symbol="TEST",
        open=100,
        high=105,
        low=95,
        close=102,
        volume=1000
    )

    # 下一根 bar
    next_bar = Bar(
        timestamp=datetime(2024, 1, 2),
        symbol="TEST",
        open=103,  # 开盘价
        high=108,
        low=100,
        close=105,
        volume=1200
    )

    order = Order(symbol="TEST", side=Side.BUY, quantity=100)
    trade = engine._execute_order(order, current_bar, next_bar)

    assert trade is not None
    assert trade.side == Side.BUY
    assert trade.quantity == 100
    # 成交价约等于下一根开盘价（考虑滑点）
    assert 100 < trade.price < 110


def test_buy_order_updates_cash():
    """买入订单更新现金"""
    engine = BacktestEngine(BacktestConfig(initial_capital=100000))
    initial_cash = engine.portfolio.cash

    current_bar = Bar(timestamp=datetime(2024, 1, 1), symbol="TEST", open=100, high=105, low=95, close=102)
    next_bar = Bar(timestamp=datetime(2024, 1, 2), symbol="TEST", open=103, high=108, low=100, close=105)

    order = Order(symbol="TEST", side=Side.BUY, quantity=100)
    engine._execute_order(order, current_bar, next_bar)

    # 现金减少
    assert engine.portfolio.cash < initial_cash


def test_buy_order_creates_long_position():
    """买入订单创建多头持仓"""
    engine = BacktestEngine(BacktestConfig(initial_capital=100000))

    current_bar = Bar(timestamp=datetime(2024, 1, 1), symbol="TEST", open=100, high=105, low=95, close=102)
    next_bar = Bar(timestamp=datetime(2024, 1, 2), symbol="TEST", open=103, high=108, low=100, close=105)

    order = Order(symbol="TEST", side=Side.BUY, quantity=100)
    engine._execute_order(order, current_bar, next_bar)

    # 持仓存在
    assert "TEST" in engine.portfolio.positions
    position = engine.portfolio.positions["TEST"]
    assert position.is_long
    assert position.quantity == 100