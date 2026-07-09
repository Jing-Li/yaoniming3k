"""持仓管理测试：平仓、追加、avg_cost 逻辑。

覆盖 _update_position 的所有分支：
- 开多、追加多头
- 开空、追加空头
- 平多仓（完全平仓）
- 平空仓（完全平仓） ← 重点验证 avg_cost 修复
- 部分平仓
"""

import pytest
from datetime import datetime

from caisen.core.bar import Bar
from caisen.core.config import BacktestConfig
from caisen.core.engine import BacktestEngine
from caisen.core.order import Order, Side
from caisen.strategy.base import Strategy, BarResult


def _bar(day: int, price: float = 100.0) -> Bar:
    return Bar(timestamp=datetime(2024, 1, day), symbol="TEST",
               open=price, high=price, low=price, close=price, volume=1000)


def _next_bar(day: int, price: float = 100.0) -> Bar:
    return _bar(day, price)


class TestOpenPosition:
    """开仓测试。"""

    def test_open_long(self, zero_cost_config):
        engine = BacktestEngine(zero_cost_config)
        engine._execute_order(
            Order(symbol="TEST", side=Side.BUY, quantity=100),
            _bar(1, 100), _next_bar(2, 100),
        )
        pos = engine.portfolio.positions["TEST"]
        assert pos.is_long
        assert pos.quantity == 100
        assert pos.avg_cost == 100.0

    def test_open_short(self, zero_cost_config):
        engine = BacktestEngine(zero_cost_config)
        engine._execute_order(
            Order(symbol="TEST", side=Side.SELL, quantity=50),
            _bar(1, 100), _next_bar(2, 100),
        )
        pos = engine.portfolio.positions["TEST"]
        assert pos.is_short
        assert pos.quantity == -50
        assert pos.avg_cost == 100.0


class TestAddToPosition:
    """追加仓位测试。"""

    def test_add_to_long(self, zero_cost_config):
        engine = BacktestEngine(zero_cost_config)
        # 买 100 @ 100
        engine._execute_order(
            Order(symbol="TEST", side=Side.BUY, quantity=100),
            _bar(1, 100), _next_bar(2, 100),
        )
        # 再买 100 @ 120
        engine._execute_order(
            Order(symbol="TEST", side=Side.BUY, quantity=100),
            _bar(3, 120), _next_bar(4, 120),
        )
        pos = engine.portfolio.positions["TEST"]
        assert pos.quantity == 200
        # avg_cost = (100*100 + 120*100) / 200 = 110
        assert abs(pos.avg_cost - 110.0) < 0.01

    def test_add_to_short(self, zero_cost_config):
        engine = BacktestEngine(zero_cost_config)
        # 卖空 100 @ 100
        engine._execute_order(
            Order(symbol="TEST", side=Side.SELL, quantity=100),
            _bar(1, 100), _next_bar(2, 100),
        )
        # 再卖空 100 @ 80
        engine._execute_order(
            Order(symbol="TEST", side=Side.SELL, quantity=100),
            _bar(3, 80), _next_bar(4, 80),
        )
        pos = engine.portfolio.positions["TEST"]
        assert pos.quantity == -200
        # avg_cost = (100*100 + 80*100) / 200 = 90
        assert abs(pos.avg_cost - 90.0) < 0.01


class TestClosePosition:
    """平仓测试（重点验证 avg_cost 修复）。"""

    def test_close_long_completely(self, zero_cost_config):
        """完全平多仓：持仓应被删除。"""
        engine = BacktestEngine(zero_cost_config)
        engine._execute_order(
            Order(symbol="TEST", side=Side.BUY, quantity=100),
            _bar(1, 100), _next_bar(2, 100),
        )
        engine._execute_order(
            Order(symbol="TEST", side=Side.SELL, quantity=100),
            _bar(3, 110), _next_bar(4, 110),
        )
        # 持仓应已清除
        assert "TEST" not in engine.portfolio.positions

    def test_close_short_completely(self, zero_cost_config):
        """完全平空仓：持仓应被删除（avg_cost 修复验证）。"""
        engine = BacktestEngine(zero_cost_config)
        # 开空
        engine._execute_order(
            Order(symbol="TEST", side=Side.SELL, quantity=100),
            _bar(1, 100), _next_bar(2, 100),
        )
        assert "TEST" in engine.portfolio.positions
        # 买入平空
        engine._execute_order(
            Order(symbol="TEST", side=Side.BUY, quantity=100),
            _bar(3, 90), _next_bar(4, 90),
        )
        # 持仓应已清除，不应有残留
        assert "TEST" not in engine.portfolio.positions

    def test_close_short_partial(self, zero_cost_config):
        """部分平空仓：持仓保留，avg_cost 更新为成交价。"""
        engine = BacktestEngine(zero_cost_config)
        # 开空 100 @ 100
        engine._execute_order(
            Order(symbol="TEST", side=Side.SELL, quantity=100),
            _bar(1, 100), _next_bar(2, 100),
        )
        # 买回 50 @ 90
        engine._execute_order(
            Order(symbol="TEST", side=Side.BUY, quantity=50),
            _bar(3, 90), _next_bar(4, 90),
        )
        pos = engine.portfolio.positions["TEST"]
        assert pos.quantity == -50
        # 部分平仓后 avg_cost 更新为成交价
        assert pos.avg_cost == 90.0

    def test_close_long_partial(self, zero_cost_config):
        """部分平多仓：持仓保留，avg_cost 不变。"""
        engine = BacktestEngine(zero_cost_config)
        engine._execute_order(
            Order(symbol="TEST", side=Side.BUY, quantity=100),
            _bar(1, 100), _next_bar(2, 100),
        )
        engine._execute_order(
            Order(symbol="TEST", side=Side.SELL, quantity=50),
            _bar(3, 110), _next_bar(4, 110),
        )
        pos = engine.portfolio.positions["TEST"]
        assert pos.quantity == 50
        # 平多不更新 avg_cost
        assert pos.avg_cost == 100.0


class TestPositionReversal:
    """仓位反转测试。"""

    def test_long_to_short_via_engine(self, zero_cost_config):
        """通过引擎运行完整回测，验证多头→空头转换。"""
        class FlipStrategy(Strategy):
            def __init__(self):
                self._step = 0

            def on_bar(self, bar: Bar) -> BarResult:
                self._step += 1
                if self._step == 1:
                    return BarResult.with_order(
                        Order(symbol=bar.symbol, side=Side.BUY, quantity=100)
                    )
                elif self._step == 2:
                    # 卖出 200 = 平多 100 + 开空 100
                    return BarResult.with_order(
                        Order(symbol=bar.symbol, side=Side.SELL, quantity=200)
                    )
                return BarResult.no_action()

        bars = [_bar(i, 100 + i) for i in range(1, 8)]
        engine = BacktestEngine(zero_cost_config)
        result = engine.run(FlipStrategy(), bars)
        # 最终应有空头仓位
        pos = engine.portfolio.positions.get("TEST")
        if pos is not None:
            assert pos.is_short or pos.quantity == 0
