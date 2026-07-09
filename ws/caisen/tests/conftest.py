"""共享 pytest fixtures — 所有测试文件可直接引用。"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path

from caisen.core.bar import Bar
from caisen.core.config import BacktestConfig
from caisen.core.engine import BacktestEngine
from caisen.core.order import Order, Side
from caisen.core.trade import Trade
from caisen.strategy.base import Strategy, BarResult


# ---------------------------------------------------------------------------
# K 线数据 fixtures
# ---------------------------------------------------------------------------

def make_bars(count: int = 10, symbol: str = "TEST", start_price: float = 100.0) -> list[Bar]:
    """生成递增型 mock K 线（确定性，无随机）。"""
    bars = []
    price = start_price
    base = datetime(2024, 1, 1)
    for i in range(count):
        ts = base + timedelta(days=i)
        bars.append(Bar(
            timestamp=ts,
            symbol=symbol,
            freq="1d",
            open=round(price, 2),
            high=round(price * 1.02, 2),
            low=round(price * 0.98, 2),
            close=round(price * 1.01, 2),
            volume=1_000_000,
        ))
        price *= 1.01
    return bars


@pytest.fixture
def sample_bars() -> list[Bar]:
    """10 根确定性 K 线。"""
    return make_bars(10)


@pytest.fixture
def short_bars() -> list[Bar]:
    """5 根 K 线（用于快速回测测试）。"""
    return make_bars(5)


# ---------------------------------------------------------------------------
# 配置 fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def backtest_config() -> BacktestConfig:
    """默认回测配置。"""
    return BacktestConfig(
        initial_capital=100_000,
        commission_rate=0.0003,
        slippage=0.001,
    )


@pytest.fixture
def zero_cost_config() -> BacktestConfig:
    """零手续费零滑点配置（便于精确计算）。"""
    return BacktestConfig(
        initial_capital=100_000,
        commission_rate=0.0,
        slippage=0.0,
    )


# ---------------------------------------------------------------------------
# 引擎 fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def engine(backtest_config) -> BacktestEngine:
    """默认配置的 BacktestEngine 实例。"""
    return BacktestEngine(backtest_config)


# ---------------------------------------------------------------------------
# 策略 fixtures
# ---------------------------------------------------------------------------

class BuyOnceStrategy(Strategy):
    """只在第一根 bar 买入 100 股，之后不做任何操作。"""

    def __init__(self):
        self._bought = False

    def on_bar(self, bar: Bar) -> BarResult:
        if not self._bought:
            self._bought = True
            return BarResult.with_order(
                Order(symbol=bar.symbol, side=Side.BUY, quantity=100)
            )
        return BarResult.no_action()


class ShortOnceStrategy(Strategy):
    """只在第一根 bar 卖空 100 股，之后不做任何操作。"""

    def __init__(self):
        self._sold = False

    def on_bar(self, bar: Bar) -> BarResult:
        if not self._sold:
            self._sold = True
            return BarResult.with_order(
                Order(symbol=bar.symbol, side=Side.SELL, quantity=100)
            )
        return BarResult.no_action()


class BuySellStrategy(Strategy):
    """第一根买入，第二根卖出，之后不动。用于测试完整交易配对。"""

    def __init__(self):
        self._step = 0

    def on_bar(self, bar: Bar) -> BarResult:
        self._step += 1
        if self._step == 1:
            return BarResult.with_order(
                Order(symbol=bar.symbol, side=Side.BUY, quantity=100)
            )
        elif self._step == 2:
            return BarResult.with_order(
                Order(symbol=bar.symbol, side=Side.SELL, quantity=100)
            )
        return BarResult.no_action()


class SellBuyStrategy(Strategy):
    """第一根卖空，第二根买入平仓。用于测试空头交易配对。"""

    def __init__(self):
        self._step = 0

    def on_bar(self, bar: Bar) -> BarResult:
        self._step += 1
        if self._step == 1:
            return BarResult.with_order(
                Order(symbol=bar.symbol, side=Side.SELL, quantity=100)
            )
        elif self._step == 2:
            return BarResult.with_order(
                Order(symbol=bar.symbol, side=Side.BUY, quantity=100)
            )
        return BarResult.no_action()


class NoOpStrategy(Strategy):
    """永远不下单。"""

    def on_bar(self, bar: Bar) -> BarResult:
        return BarResult.no_action()


@pytest.fixture
def buy_once_strategy():
    return BuyOnceStrategy()


@pytest.fixture
def no_op_strategy():
    return NoOpStrategy()


# ---------------------------------------------------------------------------
# Trade fixtures
# ---------------------------------------------------------------------------

def make_trade(
    day: int = 1,
    side: Side = Side.BUY,
    price: float = 100.0,
    quantity: float = 100,
    commission: float = 0.0,
) -> Trade:
    """快捷构造 Trade。"""
    return Trade(
        timestamp=datetime(2024, 1, day),
        symbol="TEST",
        side=side,
        quantity=quantity,
        price=price,
        commission=commission,
        slippage=0.0,
        order_id=f"order_{day}",
    )


@pytest.fixture
def winning_pair() -> list[Trade]:
    """一组盈利的 BUY→SELL 配对。"""
    return [
        make_trade(day=1, side=Side.BUY, price=10.0, quantity=100, commission=1.0),
        make_trade(day=2, side=Side.SELL, price=12.0, quantity=100, commission=1.0),
    ]


@pytest.fixture
def losing_pair() -> list[Trade]:
    """一组亏损的 BUY→SELL 配对。"""
    return [
        make_trade(day=1, side=Side.BUY, price=10.0, quantity=100, commission=1.0),
        make_trade(day=2, side=Side.SELL, price=8.0, quantity=100, commission=1.0),
    ]


@pytest.fixture
def short_winning_pair() -> list[Trade]:
    """一组盈利的 SELL→BUY（空头）配对：卖 12 买回 10。"""
    return [
        make_trade(day=1, side=Side.SELL, price=12.0, quantity=100, commission=1.0),
        make_trade(day=2, side=Side.BUY, price=10.0, quantity=100, commission=1.0),
    ]


@pytest.fixture
def short_losing_pair() -> list[Trade]:
    """一组亏损的 SELL→BUY（空头）配对：卖 10 买回 12。"""
    return [
        make_trade(day=1, side=Side.SELL, price=10.0, quantity=100, commission=1.0),
        make_trade(day=2, side=Side.BUY, price=12.0, quantity=100, commission=1.0),
    ]
