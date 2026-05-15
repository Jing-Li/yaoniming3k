"""测试净值计算使用市场价"""

from datetime import datetime
from caisen.core.bar import Bar
from caisen.core.order import Order, Side
from caisen.core.engine import BacktestEngine
from caisen.core.config import BacktestConfig


class BuyAndHoldStrategy:
    """买入后持有到最后的简单策略"""

    def __init__(self):
        self.bought = False

    def on_init(self, config):
        pass

    def on_bar(self, bar: Bar):
        if not self.bought and bar.timestamp == datetime(2024, 1, 2):
            self.bought = True
            return Order(symbol="TEST", side=Side.BUY, quantity=100)
        return None

    def on_session_end(self):
        pass

    def get_annotations(self):
        return []


def test_final_equity_uses_market_price():
    """最终净值应该使用市场价计算，而非成本估算"""
    engine = BacktestEngine(BacktestConfig(initial_capital=100000))

    # 创建 K 线数据，价格从 100 涨到 120
    bars = [
        Bar(timestamp=datetime(2024, 1, 1), symbol="TEST", open=100, high=100, low=100, close=100, volume=1000),
        Bar(timestamp=datetime(2024, 1, 2), symbol="TEST", open=100, high=100, low=100, close=100, volume=1000),
        Bar(timestamp=datetime(2024, 1, 3), symbol="TEST", open=110, high=115, low=105, close=120, volume=1000),  # 价格涨了20%
    ]

    strategy = BuyAndHoldStrategy()
    result = engine.run(strategy, bars)

    # 验证: final_equity 应该等于净值曲线最后一点
    # (这是核心断言，验证两者一致性)
    last_curve_point = result.equity_curve[-1]
    assert abs(result.final_equity - last_curve_point["equity"]) < 0.01, (
        f"final_equity ({result.final_equity}) 应该等于净值曲线最后一点 ({last_curve_point['equity']})"
    )

    # 额外验证: 最终价格是 120，而不是成本价
    # 净值应该高于成本估算（因为价格上涨）
    cost_based_equity = result.initial_capital - result.trades[0].price * result.trades[0].quantity - result.trades[0].commission
    assert result.final_equity > cost_based_equity, (
        f"final_equity ({result.final_equity}) 应该高于成本估算 ({cost_based_equity})，因为价格上涨"
    )


def test_final_equity_matches_last_equity_curve_point():
    """最终净值应该与净值曲线最后一点一致"""
    engine = BacktestEngine(BacktestConfig(initial_capital=100000))

    bars = [
        Bar(timestamp=datetime(2024, 1, 1), symbol="TEST", open=100, high=100, low=100, close=100, volume=1000),
        Bar(timestamp=datetime(2024, 1, 2), symbol="TEST", open=100, high=100, low=100, close=100, volume=1000),
        Bar(timestamp=datetime(2024, 1, 3), symbol="TEST", open=110, high=115, low=105, close=120, volume=1000),
    ]

    strategy = BuyAndHoldStrategy()
    result = engine.run(strategy, bars)

    # 净值曲线最后一点
    last_curve_point = result.equity_curve[-1]

    # final_equity 应该等于最后一点记录的 equity
    assert abs(result.final_equity - last_curve_point["equity"]) < 0.01, (
        f"final_equity ({result.final_equity}) 应该等于净值曲线最后一点 ({last_curve_point['equity']})"
    )


def test_total_return_reflects_market_value():
    """总收益率应该反映市场价计算的真实收益"""
    engine = BacktestEngine(BacktestConfig(initial_capital=100000))

    bars = [
        Bar(timestamp=datetime(2024, 1, 1), symbol="TEST", open=100, high=100, low=100, close=100, volume=1000),
        Bar(timestamp=datetime(2024, 1, 2), symbol="TEST", open=100, high=100, low=100, close=100, volume=1000),
        Bar(timestamp=datetime(2024, 1, 3), symbol="TEST", open=100, high=100, low=100, close=100, volume=1000),
    ]

    strategy = BuyAndHoldStrategy()
    result = engine.run(strategy, bars)

    # 如果没有交易，总收益应该为 0
    # 如果有交易，收益基于最终市场价
    expected_return = (result.final_equity - result.initial_capital) / result.initial_capital
    assert abs(result.total_return - expected_return) < 0.0001, (
        f"total_return ({result.total_return}) 应该等于 (final_equity - initial_capital) / initial_capital"
    )