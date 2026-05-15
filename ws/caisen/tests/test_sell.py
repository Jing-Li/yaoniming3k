"""测试卖出/做空"""

from datetime import datetime
from caisen.core.bar import Bar
from caisen.core.order import Order, Side
from caisen.core.engine import BacktestEngine
from caisen.core.config import BacktestConfig
from caisen.strategy.base import Strategy


def test_sell_creates_short_position():
    """卖出订单创建空头持仓"""
    engine = BacktestEngine(BacktestConfig(initial_capital=100000))

    current_bar = Bar(timestamp=datetime(2024, 1, 1), symbol="TEST", open=100, high=105, low=95, close=102)
    next_bar = Bar(timestamp=datetime(2024, 1, 2), symbol="TEST", open=103, high=108, low=100, close=105)

    order = Order(symbol="TEST", side=Side.SELL, quantity=100)
    trade = engine._execute_order(order, current_bar, next_bar)

    assert trade is not None
    assert trade.side == Side.SELL
    assert trade.quantity == 100

    # 空头持仓
    assert "TEST" in engine.portfolio.positions
    position = engine.portfolio.positions["TEST"]
    assert position.is_short
    assert position.quantity == -100


def test_sell_increases_cash():
    """卖出订单增加现金（卖空获得资金）"""
    engine = BacktestEngine(BacktestConfig(initial_capital=100000))
    initial_cash = engine.portfolio.cash

    current_bar = Bar(timestamp=datetime(2024, 1, 1), symbol="TEST", open=100, high=105, low=95, close=102)
    next_bar = Bar(timestamp=datetime(2024, 1, 2), symbol="TEST", open=103, high=108, low=100, close=105)

    order = Order(symbol="TEST", side=Side.SELL, quantity=100)
    engine._execute_order(order, current_bar, next_bar)

    # 现金增加（卖空获得资金）
    assert engine.portfolio.cash > initial_cash


def test_short_covered_by_buy():
    """买入平空仓"""
    engine = BacktestEngine(BacktestConfig(initial_capital=100000))

    # 先卖空
    current_bar1 = Bar(timestamp=datetime(2024, 1, 1), symbol="TEST", open=100, high=105, low=95, close=102)
    next_bar1 = Bar(timestamp=datetime(2024, 1, 2), symbol="TEST", open=103, high=108, low=100, close=105)
    engine._execute_order(Order(symbol="TEST", side=Side.SELL, quantity=100), current_bar1, next_bar1)

    # 再买入平仓
    current_bar2 = Bar(timestamp=datetime(2024, 1, 3), symbol="TEST", open=105, high=110, low=100, close=108)
    next_bar2 = Bar(timestamp=datetime(2024, 1, 4), symbol="TEST", open=106, high=112, low=104, close=110)
    engine._execute_order(Order(symbol="TEST", side=Side.BUY, quantity=100), current_bar2, next_bar2)

    # 持仓应该为 0
    position = engine.portfolio.positions.get("TEST")
    assert position is None or abs(position.quantity) < 1e-6