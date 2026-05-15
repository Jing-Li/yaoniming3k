"""测试 Portfolio 成本计算方法"""

from caisen.core.portfolio import Portfolio
from caisen.core.position import Position


def test_cost_value_uses_avg_cost():
    """成本价值使用 avg_cost 计算，而非市场价"""
    portfolio = Portfolio(initial_capital=100000, cash=90000)
    portfolio.positions["TEST"] = Position(symbol="TEST", quantity=100, avg_cost=100)

    # cost_value = cash + quantity * avg_cost
    # = 90000 + 100 * 100 = 100000
    cost_value = portfolio.cost_value

    assert abs(cost_value - 100000) < 0.01


def test_cost_value_reflects_unchanged_cost():
    """成本价值在价格上涨时不增加"""
    portfolio = Portfolio(initial_capital=100000, cash=90000)
    portfolio.positions["TEST"] = Position(symbol="TEST", quantity=100, avg_cost=100)

    cost_value = portfolio.cost_value

    # 即使市场价涨到 120，成本价值仍然按 avg_cost 计算
    market_value = portfolio.get_equity_with_prices({"TEST": 120})

    assert cost_value < market_value, "成本价值应该小于市值"
    assert abs(cost_value - 100000) < 0.01  # 仍然是 100 * 100 + 90000


def test_cost_value_empty_positions():
    """无持仓时成本价值等于现金"""
    portfolio = Portfolio(initial_capital=100000, cash=100000)

    cost_value = portfolio.cost_value

    assert abs(cost_value - 100000) < 0.01


def test_market_value_calculation():
    """市值使用传入的价格"""
    portfolio = Portfolio(initial_capital=100000, cash=90000)
    portfolio.positions["TEST"] = Position(symbol="TEST", quantity=100, avg_cost=100)

    market_value = portfolio.get_equity_with_prices({"TEST": 120})

    # 现金 90000 + 市值 100 * 120 = 102000
    assert abs(market_value - 102000) < 0.01


def test_cost_value_and_market_value_differ():
    """成本价值和市值计算结果应该不同（当价格变化时）"""
    portfolio = Portfolio(initial_capital=100000, cash=90000)
    portfolio.positions["TEST"] = Position(symbol="TEST", quantity=100, avg_cost=100)

    cost_value = portfolio.cost_value
    market_value = portfolio.get_equity_with_prices({"TEST": 120})

    # 两个值应该不同
    assert cost_value != market_value, "成本价值和市值应该不同"


def test_cost_value_with_multiple_positions():
    """多持仓的成本价值"""
    portfolio = Portfolio(initial_capital=200000, cash=180000)
    portfolio.positions["A"] = Position(symbol="A", quantity=100, avg_cost=50)
    portfolio.positions["B"] = Position(symbol="B", quantity=50, avg_cost=100)

    cost_value = portfolio.cost_value

    # 现金 180000 + A: 100*50 + B: 50*100 = 180000 + 5000 + 5000 = 190000
    assert abs(cost_value - 190000) < 0.01