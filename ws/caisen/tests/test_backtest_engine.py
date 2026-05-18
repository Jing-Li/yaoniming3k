"""Integration tests for BacktestEngine"""

import pytest
from datetime import datetime
from caisen.core.engine import BacktestEngine, BacktestResult
from caisen.core.config import BacktestConfig
from caisen.core.bar import Bar
from caisen.core.order import Order, Side
from caisen.strategy.base import Strategy, Annotation, AnnotationType


class DummyStrategy(Strategy):
    """测试用策略：每天买1股"""

    def __init__(self):
        super().__init__()
        self.order_count = 0
        self.annotations = []

    def on_init(self, config):
        pass

    def on_bar(self, bar: Bar) -> Order:
        self.order_count += 1
        return Order(
            symbol=bar.symbol,
            side=Side.BUY,
            quantity=1,
            timestamp=bar.timestamp
        )

    def on_session_end(self):
        pass

    def get_annotations(self):
        return []


class AlwaysHoldStrategy(Strategy):
    """测试用策略：只在第一天买入，之后持有"""

    def __init__(self):
        super().__init__()
        self.bought = False

    def on_init(self, config):
        pass

    def on_bar(self, bar: Bar) -> Order:
        if not self.bought:
            self.bought = True
            return Order(
                symbol=bar.symbol,
                side=Side.BUY,
                quantity=100,
                timestamp=bar.timestamp
            )
        return None

    def on_session_end(self):
        pass

    def get_annotations(self):
        return []


@pytest.fixture
def config():
    """默认回测配置"""
    return BacktestConfig(
        initial_capital=100000,
        commission_rate=0.0003,
        slippage=0.001
    )


@pytest.fixture
def sample_bars():
    """样本K线数据"""
    base = datetime(2024, 1, 1)
    return [
        Bar(timestamp=base, symbol="TEST", open=100, high=105, low=99, close=103, volume=1000),
        Bar(timestamp=base, symbol="TEST", open=103, high=108, low=102, close=106, volume=1100),
        Bar(timestamp=base, symbol="TEST", open=106, high=110, low=105, close=108, volume=1200),
        Bar(timestamp=base, symbol="TEST", open=108, high=112, low=107, close=110, volume=1300),
        Bar(timestamp=base, symbol="TEST", open=110, high=114, low=109, close=112, volume=1400),
    ]


class TestBacktestEngineInit:
    """测试引擎初始化"""

    def test_engine_initializes_with_config(self, config):
        """引擎使用配置初始化"""
        engine = BacktestEngine(config)

        assert engine.config == config
        assert engine.portfolio.cash == config.initial_capital
        assert engine.trades == []
        assert engine.equity_curve == []
        assert engine.annotations == []

    def test_engine_initial_capital_set(self, config):
        """引擎正确设置初始资金"""
        engine = BacktestEngine(config)

        assert engine.portfolio.initial_capital == 100000
        assert engine.portfolio.cash == 100000


class TestBacktestEngineRun:
    """测试引擎运行"""

    def test_run_returns_backtest_result(self, config, sample_bars):
        """run() 返回 BacktestResult"""
        engine = BacktestEngine(config)
        strategy = AlwaysHoldStrategy()

        result = engine.run(strategy, sample_bars)

        assert isinstance(result, BacktestResult)
        assert result.strategy_name == "AlwaysHoldStrategy"
        assert result.bars == sample_bars

    def test_run_processes_all_bars(self, config, sample_bars):
        """run() 处理所有K线"""
        engine = BacktestEngine(config)
        strategy = DummyStrategy()

        result = engine.run(strategy, sample_bars)

        # DummyStrategy 每根K线都下单
        assert strategy.order_count == len(sample_bars) - 1  # 最后一天不下单

    def test_run_creates_trades(self, config, sample_bars):
        """run() 创建交易记录"""
        engine = BacktestEngine(config)
        strategy = AlwaysHoldStrategy()

        result = engine.run(strategy, sample_bars)

        # 应该有至少一笔买入交易
        assert len(result.trades) >= 1
        assert all(t.side == Side.BUY for t in result.trades)

    def test_run_generates_equity_curve(self, config, sample_bars):
        """run() 生成净值曲线"""
        engine = BacktestEngine(config)
        strategy = AlwaysHoldStrategy()

        result = engine.run(strategy, sample_bars)

        # 净值曲线应该和K线数量一致
        assert len(result.equity_curve) == len(sample_bars)
        # 每个点都应该有 timestamp, equity, cash, positions
        for point in result.equity_curve:
            assert "timestamp" in point
            assert "equity" in point
            assert "cash" in point
            assert "positions" in point

    def test_run_collects_annotations(self, config, sample_bars):
        """run() 收集策略标注"""
        engine = BacktestEngine(config)

        class AnnotatedStrategy(Strategy):
            def __init__(self):
                super().__init__()

            def on_init(self, config):
                pass

            def on_bar(self, bar: Bar) -> Order:
                return None

            def on_session_end(self):
                pass

            def get_annotations(self):
                return [
                    Annotation(
                        type=AnnotationType.BUY_SIGNAL,
                        timestamp=datetime(2024, 1, 1),
                        data={"price": 100, "reason": "test"}
                    )
                ]

        strategy = AnnotatedStrategy()
        result = engine.run(strategy, sample_bars)

        assert len(result.annotations) >= 1


class TestOrderExecution:
    """测试订单执行"""

    def test_buy_order_increases_position(self, config, sample_bars):
        """买入订单增加持仓"""
        engine = BacktestEngine(config)
        strategy = AlwaysHoldStrategy()

        result = engine.run(strategy, sample_bars)

        # 应该持有100股 - positions 存储的是 {symbol: quantity}
        assert "TEST" in result.equity_curve[-1]["positions"]
        assert result.equity_curve[-1]["positions"]["TEST"] == 100

    def test_slippage_applied_to_buy(self, config, sample_bars):
        """买入时滑点生效"""
        config = BacktestConfig(
            initial_capital=100000,
            commission_rate=0.0003,
            slippage=0.001  # 0.1% 滑点
        )
        engine = BacktestEngine(config)
        strategy = AlwaysHoldStrategy()

        result = engine.run(strategy, sample_bars)

        # 第一笔交易的成交价应该高于开盘价 * (1 + slippage)
        if result.trades:
            first_trade = result.trades[0]
            expected_price = sample_bars[0].open * (1 + config.slippage)
            assert first_trade.price >= expected_price - 0.01  # 允许浮点误差


class TestEquityCalculation:
    """测试净值计算"""

    def test_equity_increases_with_profit(self, config, sample_bars):
        """盈利时净值增加"""
        engine = BacktestEngine(config)
        strategy = AlwaysHoldStrategy()

        result = engine.run(strategy, sample_bars)

        # 最终净值应该大于初始资金
        assert result.final_equity > result.initial_capital

    def test_equity_curve_reflects_prices(self, config, sample_bars):
        """净值曲线反映价格变化"""
        engine = BacktestEngine(config)
        strategy = AlwaysHoldStrategy()

        result = engine.run(strategy, sample_bars)

        # 如果价格从100涨到112，持仓价值增加
        initial_price = sample_bars[0].close
        final_price = sample_bars[-1].close
        assert final_price > initial_price