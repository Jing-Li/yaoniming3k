"""测试 BacktestRunner 带进度回调的回测执行模块"""

import pytest
from pathlib import Path
from datetime import datetime, timedelta

from caisen.core.bar import Bar


def _make_bars(count: int = 150, symbol: str = "TEST") -> list:
    """生成测试用 mock bars"""
    bars = []
    price = 100.0
    base = datetime(2024, 1, 1)
    for i in range(count):
        ts = base + timedelta(days=i)
        bars.append(Bar(
            timestamp=ts,
            symbol=symbol,
            open=round(price, 2),
            high=round(price * 1.01, 2),
            low=round(price * 0.99, 2),
            close=round(price * 1.001, 2),
            volume=1_000_000,
            freq="1d",
        ))
        price = price * 1.001
    return bars


def test_run_backtest_returns_valid_run_id(tmp_path):
    """使用 mock bars 完成端到端回测，返回非空 run_id 字符串"""
    from caisen.backtest.runner import BacktestRunner

    bars = _make_bars(150)
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
    assert (tmp_path / run_id).exists()


def test_on_progress_called_every_100_bars(tmp_path):
    """on_progress 每 100 根 K 线调用一次，250 根时调用 3 次（100/200/249）"""
    from caisen.backtest.runner import BacktestRunner

    calls = []

    def capture(processed, total, current_date):
        calls.append((processed, total, current_date))

    bars = _make_bars(250)
    BacktestRunner.run_backtest(
        strategy_name="CaiSenStrategy",
        symbol="TEST",
        freq="1d",
        start="2024-01-01",
        end="2024-12-31",
        params={},
        on_progress=capture,
        output_dir=str(tmp_path),
        bars=bars,
    )

    # 250 根：第 100、200 根触发，最后一根（index 248，即第 249 根）也触发
    assert len(calls) == 3
    processed_values = [c[0] for c in calls]
    assert 100 in processed_values
    assert 200 in processed_values
    for _, total, date in calls:
        assert total == 250
        assert len(date) == 10  # YYYY-MM-DD 格式


def test_raises_when_bars_empty(tmp_path):
    """K 线数为 0 时抛出明确的 BacktestError"""
    from caisen.backtest.runner import BacktestRunner, BacktestError

    with pytest.raises(BacktestError, match="数据为空"):
        BacktestRunner.run_backtest(
            strategy_name="CaiSenStrategy",
            symbol="TEST",
            freq="1d",
            start="2024-01-01",
            end="2024-12-31",
            params={},
            output_dir=str(tmp_path),
            bars=[],
        )


def test_raises_when_strategy_unknown(tmp_path):
    """策略名不存在时抛出明确的 BacktestError"""
    from caisen.backtest.runner import BacktestRunner, BacktestError

    with pytest.raises(BacktestError, match="策略模块未注册"):
        BacktestRunner.run_backtest(
            strategy_name="NonExistentStrategy",
            symbol="TEST",
            freq="1d",
            start="2024-01-01",
            end="2024-12-31",
            params={},
            output_dir=str(tmp_path),
            bars=_make_bars(10),
        )
