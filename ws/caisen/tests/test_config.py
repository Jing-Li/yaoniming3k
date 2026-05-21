"""测试配置解析"""

import tempfile
from pathlib import Path

from caisen.core.config import Config, BacktestConfig, StrategyConfig
from caisen.data.config import DataConfig


def test_default_config():
    """默认配置"""
    config = Config()

    assert config.backtest.initial_capital == 100000
    assert config.backtest.commission_rate == 0.0003
    assert config.backtest.slippage == 0.001


def test_config_from_dict():
    """从字典创建配置"""
    data = {
        "backtest": {
            "initial_capital": 50000,
            "commission_rate": 0.001,
            "slippage": 0.002
        },
        "strategy": {
            "name": "ma_cross",
            "file": "./strategies/ma_cross.py"
        },
        "data": {
            "symbol": "TEST",
            "freq": "1d"
        }
    }

    config = Config._from_dict(data)

    assert config.backtest.initial_capital == 50000
    assert config.backtest.commission_rate == 0.001
    assert config.strategy.name == "ma_cross"
    assert config.data.symbol == "TEST"


def test_config_to_dict():
    """配置转字典"""
    config = Config(
        backtest=BacktestConfig(initial_capital=80000),
        strategy=StrategyConfig(name="test"),
        data=DataConfig(symbol="TEST")
    )

    d = config.to_dict()

    assert d["backtest"]["initial_capital"] == 80000
    assert d["strategy"]["name"] == "test"


def test_yaml_config_roundtrip():
    """YAML 配置读写"""
    import yaml

    config_data = {
        "backtest": {
            "initial_capital": 100000,
            "commission_rate": 0.0003
        },
        "strategy": {
            "name": "ma_cross"
        },
        "data": {
            "symbol": "TEST",
            "freq": "1d"
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        path = f.name

    # 加载
    with open(path) as f:
        loaded = yaml.safe_load(f)

    config = Config._from_dict(loaded)

    assert config.backtest.initial_capital == 100000
    assert config.strategy.name == "ma_cross"

    # 清理
    Path(path).unlink()