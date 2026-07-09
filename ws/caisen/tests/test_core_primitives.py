"""核心数据类型单元测试：Bar, Order, Trade, Position, Portfolio。"""

import pytest
from datetime import datetime

from caisen.core.bar import Bar
from caisen.core.order import Order, Side
from caisen.core.trade import Trade
from caisen.core.position import Position
from caisen.core.portfolio import Portfolio


# ===================================================================
# Bar
# ===================================================================

class TestBar:
    """Bar 数据模型测试。"""

    def test_default_values(self):
        bar = Bar(timestamp=datetime(2024, 1, 1), symbol="TEST")
        assert bar.freq == "1d"
        assert bar.open == 0
        assert bar.volume == 0

    def test_to_dict(self):
        bar = Bar(timestamp=datetime(2024, 6, 15), symbol="AAPL", open=150, high=155, low=148, close=153, volume=1e6)
        d = bar.to_dict()
        assert d["symbol"] == "AAPL"
        assert d["open"] == 150
        assert d["timestamp"] == "2024-06-15T00:00:00"

    def test_from_dict_with_string_timestamp(self):
        data = {"timestamp": "2024-06-15T00:00:00", "symbol": "AAPL", "open": 150, "high": 155, "low": 148, "close": 153, "volume": 1e6}
        bar = Bar.from_dict(data)
        assert isinstance(bar.timestamp, datetime)
        assert bar.symbol == "AAPL"

    def test_from_dict_with_datetime_object(self):
        ts = datetime(2024, 6, 15)
        data = {"timestamp": ts, "symbol": "AAPL"}
        bar = Bar.from_dict(data)
        assert bar.timestamp is ts

    def test_roundtrip_dict(self):
        original = Bar(timestamp=datetime(2024, 3, 1), symbol="X", freq="5m", open=10, high=12, low=9, close=11, volume=500)
        restored = Bar.from_dict(original.to_dict())
        assert restored.symbol == original.symbol
        assert restored.freq == original.freq
        assert restored.close == original.close


# ===================================================================
# Order
# ===================================================================

class TestOrder:
    """Order 数据模型测试。"""

    def test_default_quantity_and_pct(self):
        order = Order(symbol="TEST", side=Side.BUY)
        assert order.quantity == 0
        assert order.position_pct == 0

    def test_timestamp_optional_none(self):
        order = Order(symbol="TEST", side=Side.BUY)
        assert order.timestamp is None

    def test_to_dict_buy(self):
        order = Order(symbol="TEST", side=Side.BUY, quantity=50, timestamp=datetime(2024, 1, 1))
        d = order.to_dict()
        assert d["side"] == "BUY"
        assert d["quantity"] == 50
        assert d["timestamp"] == "2024-01-01T00:00:00"

    def test_to_dict_no_timestamp(self):
        order = Order(symbol="TEST", side=Side.SELL)
        d = order.to_dict()
        assert d["timestamp"] is None

    def test_order_id_unique(self):
        o1 = Order(symbol="A", side=Side.BUY)
        o2 = Order(symbol="A", side=Side.BUY)
        assert o1.order_id != o2.order_id

    def test_side_enum_values(self):
        assert Side.BUY.value == "BUY"
        assert Side.SELL.value == "SELL"


# ===================================================================
# Trade
# ===================================================================

class TestTrade:
    """Trade 数据模型测试。"""

    def test_to_dict(self):
        trade = Trade(
            timestamp=datetime(2024, 1, 1),
            symbol="TEST",
            side=Side.BUY,
            quantity=100,
            price=50.0,
            commission=1.5,
            slippage=0.1,
            order_id="abc",
        )
        d = trade.to_dict()
        assert d["side"] == "BUY"
        assert d["quantity"] == 100
        assert d["commission"] == 1.5
        assert d["order_id"] == "abc"


# ===================================================================
# Position
# ===================================================================

class TestPosition:
    """Position 数据模型测试。"""

    def test_long_position(self):
        pos = Position(symbol="TEST", quantity=100, avg_cost=50)
        assert pos.is_long is True
        assert pos.is_short is False
        assert pos.abs_quantity == 100

    def test_short_position(self):
        pos = Position(symbol="TEST", quantity=-50, avg_cost=50)
        assert pos.is_long is False
        assert pos.is_short is True
        assert pos.abs_quantity == 50

    def test_flat_position(self):
        pos = Position(symbol="TEST", quantity=0, avg_cost=0)
        assert pos.is_long is False
        assert pos.is_short is False
        assert pos.abs_quantity == 0

    def test_to_dict(self):
        pos = Position(symbol="TEST", quantity=100, avg_cost=50)
        d = pos.to_dict()
        assert d == {"symbol": "TEST", "quantity": 100, "avg_cost": 50}


# ===================================================================
# Portfolio
# ===================================================================

class TestPortfolio:
    """Portfolio 数据模型测试。"""

    def test_initial_state(self):
        p = Portfolio(initial_capital=100000, cash=100000)
        assert p.positions == {}
        assert p.cost_value == 100000

    def test_cost_value_with_position(self):
        p = Portfolio(initial_capital=100000, cash=50000)
        p.positions["TEST"] = Position(symbol="TEST", quantity=100, avg_cost=500)
        # 50000 + 100 * 500 = 100000
        assert p.cost_value == 100000

    def test_get_equity_with_prices(self):
        p = Portfolio(initial_capital=100000, cash=50000)
        p.positions["TEST"] = Position(symbol="TEST", quantity=100, avg_cost=500)
        equity = p.get_equity_with_prices({"TEST": 600})
        # 50000 + 100 * 600 = 110000
        assert equity == 110000

    def test_get_equity_with_missing_price_uses_avg_cost(self):
        p = Portfolio(initial_capital=100000, cash=50000)
        p.positions["TEST"] = Position(symbol="TEST", quantity=100, avg_cost=500)
        equity = p.get_equity_with_prices({})  # 无价格，回退到 avg_cost
        assert equity == 100000

    def test_get_available_cash_no_positions(self):
        p = Portfolio(initial_capital=100000, cash=100000)
        assert p.get_available_cash({}) == 100000

    def test_get_available_cash_with_short(self):
        p = Portfolio(initial_capital=100000, cash=80000)
        p.positions["TEST"] = Position(symbol="TEST", quantity=-100, avg_cost=200)
        available = p.get_available_cash({"TEST": 200})
        # 80000 + 100 * 200 = 100000
        assert available == 100000

    def test_to_dict(self):
        p = Portfolio(initial_capital=100000, cash=100000)
        d = p.to_dict()
        assert d["initial_capital"] == 100000
        assert d["cash"] == 100000
        assert d["positions"] == {}
