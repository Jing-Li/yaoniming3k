"""测试净值计算和手续费"""

from datetime import datetime
from caisen.core.bar import Bar
from caisen.core.order import Order, Side
from caisen.core.engine import BacktestEngine
from caisen.core.config import BacktestConfig


def test_equity_calculation():
    """净值计算 = 现金 + 持仓市值"""
    engine = BacktestEngine(BacktestConfig(initial_capital=100000))

    # 买入100股，价格103（含滑点）
    current_bar = Bar(timestamp=datetime(2024, 1, 1), symbol="TEST", open=100, high=105, low=95, close=102)
    next_bar = Bar(timestamp=datetime(2024, 1, 2), symbol="TEST", open=103, high=108, low=100, close=105)

    engine._execute_order(Order(symbol="TEST", side=Side.BUY, quantity=100), current_bar, next_bar)

    # 当前价格 105
    equity = engine.portfolio.get_equity_with_prices({"TEST": 105})

    # 持仓：100股 * 105 = 10500
    # 现金：约 89400（100000 - 10300 - 手续费）
    expected_position_value = 100 * 105
    assert abs(equity - engine.portfolio.cash - expected_position_value) < 1


def test_commission_calculation():
    """手续费按成交金额比例计算"""
    engine = BacktestEngine(BacktestConfig(initial_capital=100000, commission_rate=0.0003))

    current_bar = Bar(timestamp=datetime(2024, 1, 1), symbol="TEST", open=100, high=105, low=95, close=102)
    next_bar = Bar(timestamp=datetime(2024, 1, 2), symbol="TEST", open=103, high=108, low=100, close=105)

    order = Order(symbol="TEST", side=Side.BUY, quantity=100)
    trade = engine._execute_order(order, current_bar, next_bar)

    # 成交价约 103，手续费 = 103 * 100 * 0.0003 ≈ 3.09
    expected_commission = 103 * 100 * 0.0003
    assert abs(trade.commission - expected_commission) < 0.1


def test_slippage_added_to_cost():
    """滑点增加买入成本"""
    engine = BacktestEngine(BacktestConfig(initial_capital=100000, slippage=0.001))

    current_bar = Bar(timestamp=datetime(2024, 1, 1), symbol="TEST", open=100, high=105, low=95, close=102)
    next_bar = Bar(timestamp=datetime(2024, 1, 2), symbol="TEST", open=103, high=108, low=100, close=105)

    order = Order(symbol="TEST", side=Side.BUY, quantity=100)
    trade = engine._execute_order(order, current_bar, next_bar)

    # 滑点 0.1%，成交价 = 103 * 1.001 ≈ 103.103
    assert abs(trade.price - 103.103) < 0.01
    assert trade.slippage > 0


def test_full_position_quantity_calculation():
    """全仓买入时数量计算"""
    engine = BacktestEngine(BacktestConfig(initial_capital=100000, commission_rate=0.0003))

    current_bar = Bar(timestamp=datetime(2024, 1, 1), symbol="TEST", open=100, high=105, low=95, close=102)
    next_bar = Bar(timestamp=datetime(2024, 1, 2), symbol="TEST", open=100, high=105, low=95, close=102)

    # quantity = 0 表示全仓
    order = Order(symbol="TEST", side=Side.BUY, quantity=0)
    trade = engine._execute_order(order, current_bar, next_bar)

    # 可用资金约 100000，手续费 0.03%，实际可买
    assert trade is not None
    assert trade.quantity > 0
    # 数量约为 100000 / 100 / 1.0003 ≈ 996
    assert 990 < trade.quantity < 1000