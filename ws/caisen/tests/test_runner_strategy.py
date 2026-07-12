"""策略发现统一机制测试 — 验证 StrategyRegistry.get_module_path 和 runner 集成。"""

import pytest
from caisen.strategy.registry import StrategyRegistry
from caisen.backtest.runner import BacktestRunner, BacktestError, _instantiate_strategy


class TestGetModulePath:
    """StrategyRegistry.get_module_path 测试。"""

    def test_builtin_caisen(self):
        path = StrategyRegistry.get_module_path("CaiSenStrategy")
        assert path == "caisen.strategy.algorithm.cai_sen"

    def test_builtin_llm(self):
        path = StrategyRegistry.get_module_path("LLMStrategy")
        assert path == "caisen.strategy.llm.strategy"

    def test_unknown_returns_none(self):
        path = StrategyRegistry.get_module_path("NonExistentStrategy")
        assert path is None


class TestInstantiateStrategy:
    """_instantiate_strategy 测试。"""

    def test_instantiate_caisen(self):
        strategy = _instantiate_strategy("CaiSenStrategy", {})
        assert strategy is not None
        assert type(strategy).__name__ == "CaiSenStrategy"

    def test_instantiate_with_params(self):
        """传入参数时，只传递 __init__ 接受的参数。"""
        strategy = _instantiate_strategy("CaiSenStrategy", {
            "fast_period": 10,
            "slow_period": 30,
            "nonexistent_param": 999,  # 应被过滤
        })
        assert strategy is not None

    def test_instantiate_unknown_raises(self):
        with pytest.raises(BacktestError, match="策略模块未注册"):
            _instantiate_strategy("FakeStrategy", {})


class TestRunnerIntegration:
    """BacktestRunner 集成测试（使用 get_module_path）。"""

    def test_runner_uses_registry_for_module_path(self, tmp_path):
        """runner 通过 StrategyRegistry 查找模块路径，不使用硬编码映射。"""
        from datetime import datetime, timedelta
        from caisen.core.bar import Bar

        bars = []
        price = 100.0
        for i in range(20):
            bars.append(Bar(
                timestamp=datetime(2024, 1, 1) + timedelta(days=i),
                symbol="TEST", freq="1d",
                open=price, high=price * 1.01, low=price * 0.99, close=price, volume=1e6,
            ))

        run_id = BacktestRunner.run_backtest(
            strategy_name="CaiSenStrategy",
            symbol="TEST",
            freq="1d",
            start="2024-01-01",
            end="2024-12-31",
            params={},
            output_dir=str(tmp_path),
            bars=bars,
        )
        assert isinstance(run_id, str)
        assert len(run_id) > 0
