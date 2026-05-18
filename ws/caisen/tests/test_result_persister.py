"""Tests for ResultPersister"""

import json
import pytest
from datetime import datetime
from pathlib import Path
import shutil

from caisen.core.engine import BacktestEngine, BacktestResult
from caisen.core.config import BacktestConfig
from caisen.core.bar import Bar
from caisen.core.order import Order, Side
from caisen.core.trade import Trade
from caisen.strategy.base import Strategy, Annotation, AnnotationType
from caisen.result.persistence import ResultPersister, _generate_run_id


@pytest.fixture
def temp_output_dir(tmp_path):
    """临时输出目录"""
    output_dir = tmp_path / "runs"
    output_dir.mkdir()
    yield str(output_dir)
    # 清理
    if output_dir.exists():
        shutil.rmtree(output_dir)


@pytest.fixture
def sample_bars():
    """样本 K 线数据"""
    return [
        Bar(timestamp=datetime(2024, 1, i), symbol="TEST", freq="1h",
            open=100, high=105, low=99, close=103, volume=1000)
        for i in range(1, 6)
    ]


@pytest.fixture
def sample_result(sample_bars):
    """样本回测结果"""
    trades = [
        Trade(
            timestamp=datetime(2024, 1, 2),
            symbol="TEST",
            side=Side.BUY,
            quantity=10,
            price=103,
            commission=0.3,
            slippage=0.1,
            order_id="order_1"
        )
    ]
    equity_curve = [
        {"timestamp": "2024-01-01", "equity": 100000, "cash": 100000, "positions": {}},
        {"timestamp": "2024-01-02", "equity": 103000, "cash": 97000, "positions": {"TEST": 10}},
        {"timestamp": "2024-01-03", "equity": 105000, "cash": 97000, "positions": {"TEST": 10}},
    ]
    annotations = [
        Annotation(
            type=AnnotationType.BUY_SIGNAL,
            timestamp=datetime(2024, 1, 2),
            data={"price": 103, "label": "买入信号"}
        )
    ]
    return BacktestResult(
        strategy_name="TestStrategy",
        bars=sample_bars,
        trades=trades,
        equity_curve=equity_curve,
        annotations=annotations,
        initial_capital=100000,
        final_equity=105000,
    )


class TestRunIdGeneration:
    """测试 run_id 生成"""

    def test_run_id_format(self, temp_output_dir):
        """run_id 格式为 {策略名}_{YYYYMMDD}_{序号}"""
        run_id = _generate_run_id("TestStrategy", temp_output_dir)

        parts = run_id.split("_")
        assert len(parts) == 3, f"Expected 3 parts, got {parts}"
        assert parts[0] == "TestStrategy"
        assert parts[1] == datetime.now().strftime("%Y%m%d")
        assert parts[2] == "1"  # 第一个序号

    def test_run_id_increments_for_same_strategy(self, temp_output_dir, sample_result):
        """同名策略重复运行，序号递增"""
        # 需要实际保存才能递增，因为序号来自目录名
        run_id_1 = ResultPersister.save(sample_result, temp_output_dir)
        run_id_2 = ResultPersister.save(sample_result, temp_output_dir)
        run_id_3 = ResultPersister.save(sample_result, temp_output_dir)

        assert run_id_1.endswith("_1")
        assert run_id_2.endswith("_2")
        assert run_id_3.endswith("_3")

    def test_run_id_different_for_different_strategies(self, temp_output_dir):
        """不同策略有独立的序号序列"""
        run_id_1 = _generate_run_id("StrategyA", temp_output_dir)
        run_id_2 = _generate_run_id("StrategyB", temp_output_dir)

        # 序号都是 1
        assert run_id_1.endswith("_1")
        assert run_id_2.endswith("_1")
        # 但策略名不同
        assert "StrategyA" in run_id_1
        assert "StrategyB" in run_id_2


class TestResultPersisterSave:
    """测试 save() 方法"""

    def test_save_creates_run_directory(self, temp_output_dir, sample_result):
        """save() 创建运行目录"""
        run_id = ResultPersister.save(sample_result, temp_output_dir)

        run_dir = Path(temp_output_dir) / run_id
        assert run_dir.exists()
        assert run_dir.is_dir()

    def test_save_generates_meta_json(self, temp_output_dir, sample_result):
        """save() 生成 meta.json"""
        run_id = ResultPersister.save(sample_result, temp_output_dir)

        meta_path = Path(temp_output_dir) / run_id / "meta.json"
        assert meta_path.exists()

        with open(meta_path) as f:
            meta = json.load(f)

        assert meta["run_id"] == run_id
        assert meta["strategy_name"] == "TestStrategy"
        assert meta["symbol"] == "TEST"
        assert meta["freq"] == "1h"
        assert "start" in meta
        assert "end" in meta

    def test_save_generates_data_json(self, temp_output_dir, sample_result):
        """save() 生成 data.json（前端可视化用）"""
        run_id = ResultPersister.save(sample_result, temp_output_dir)

        data_path = Path(temp_output_dir) / run_id / "data.json"
        assert data_path.exists()

        with open(data_path) as f:
            data = json.load(f)

        assert "meta" in data
        assert "metrics" in data
        assert "bars" in data
        assert "equity_curve" in data
        assert "trades" in data
        assert "annotations" in data

    def test_save_generates_bars_parquet(self, temp_output_dir, sample_result):
        """save() 生成 bars.parquet"""
        run_id = ResultPersister.save(sample_result, temp_output_dir)

        bars_path = Path(temp_output_dir) / run_id / "bars.parquet"
        assert bars_path.exists()

    def test_save_generates_trades_parquet(self, temp_output_dir, sample_result):
        """save() 生成 trades.parquet"""
        run_id = ResultPersister.save(sample_result, temp_output_dir)

        trades_path = Path(temp_output_dir) / run_id / "trades.parquet"
        assert trades_path.exists()

    def test_save_generates_equity_parquet(self, temp_output_dir, sample_result):
        """save() 生成 equity.parquet"""
        run_id = ResultPersister.save(sample_result, temp_output_dir)

        equity_path = Path(temp_output_dir) / run_id / "equity.parquet"
        assert equity_path.exists()

    def test_save_generates_metrics_json(self, temp_output_dir, sample_result):
        """save() 生成 metrics.json"""
        run_id = ResultPersister.save(sample_result, temp_output_dir)

        metrics_path = Path(temp_output_dir) / run_id / "metrics.json"
        assert metrics_path.exists()

        with open(metrics_path) as f:
            metrics = json.load(f)

        assert "total_return" in metrics
        assert "max_drawdown" in metrics
        assert "sharpe_ratio" in metrics


class TestSaveVisualization:
    """测试 save_visualization() 方法"""

    def test_save_visualization_creates_data_json(self, temp_output_dir, sample_result):
        """save_visualization() 生成 data.json"""
        # 先保存
        run_id = ResultPersister.save(sample_result, temp_output_dir)

        # 重新生成 data.json（模拟单独调用）
        ResultPersister.save_visualization(run_id, temp_output_dir)

        data_path = Path(temp_output_dir) / run_id / "data.json"
        assert data_path.exists()

        with open(data_path) as f:
            data = json.load(f)

        assert data["meta"]["strategy_name"] == "TestStrategy"
        assert data["meta"]["symbol"] == "TEST"

    def test_data_json_contains_all_required_keys(self, temp_output_dir, sample_result):
        """data.json 包含所有必需字段（ADR-0007 定义）"""
        run_id = ResultPersister.save(sample_result, temp_output_dir)

        with open(Path(temp_output_dir) / run_id / "data.json") as f:
            data = json.load(f)

        # meta
        assert "strategy_name" in data["meta"]
        assert "symbol" in data["meta"]
        assert "start" in data["meta"]
        assert "end" in data["meta"]
        assert "freq" in data["meta"]

        # bars
        assert len(data["bars"]) == 5  # sample_bars 有 5 根

        # trades
        assert len(data["trades"]) >= 1

        # annotations
        assert len(data["annotations"]) >= 1


class TestResultPersisterLoad:
    """测试 load() 方法"""

    def test_load_returns_meta(self, temp_output_dir, sample_result):
        """load() 返回元数据"""
        run_id = ResultPersister.save(sample_result, temp_output_dir)
        loaded = ResultPersister.load(run_id, temp_output_dir)

        assert loaded is not None
        assert loaded["run_id"] == run_id
        assert loaded["strategy_name"] == "TestStrategy"

    def test_load_returns_bars(self, temp_output_dir, sample_result):
        """load() 返回 K 线数据"""
        run_id = ResultPersister.save(sample_result, temp_output_dir)
        loaded = ResultPersister.load(run_id, temp_output_dir)

        assert "bars" in loaded
        assert len(loaded["bars"]) == 5

    def test_load_returns_trades(self, temp_output_dir, sample_result):
        """load() 返回交易记录"""
        run_id = ResultPersister.save(sample_result, temp_output_dir)
        loaded = ResultPersister.load(run_id, temp_output_dir)

        assert "trades" in loaded

    def test_load_returns_equity_curve(self, temp_output_dir, sample_result):
        """load() 返回净值曲线"""
        run_id = ResultPersister.save(sample_result, temp_output_dir)
        loaded = ResultPersister.load(run_id, temp_output_dir)

        assert "equity_curve" in loaded
        assert len(loaded["equity_curve"]) == 3

    def test_load_returns_metrics(self, temp_output_dir, sample_result):
        """load() 返回绩效指标"""
        run_id = ResultPersister.save(sample_result, temp_output_dir)
        loaded = ResultPersister.load(run_id, temp_output_dir)

        assert "metrics" in loaded

    def test_load_nonexistent_returns_none(self, temp_output_dir):
        """load() 不存在的 run_id 返回 None"""
        result = ResultPersister.load("nonexistent_id", temp_output_dir)
        assert result is None


class TestLoadVisualization:
    """测试 load_visualization() 方法"""

    def test_load_visualization_returns_data_json(self, temp_output_dir, sample_result):
        """load_visualization() 返回 data.json 内容"""
        run_id = ResultPersister.save(sample_result, temp_output_dir)
        data = ResultPersister.load_visualization(run_id, temp_output_dir)

        assert data is not None
        assert "meta" in data
        assert "bars" in data
        assert "trades" in data

    def test_load_visualization_nonexistent_returns_none(self, temp_output_dir):
        """load_visualization() 不存在时返回 None"""
        result = ResultPersister.load_visualization("nonexistent", temp_output_dir)
        assert result is None


class TestDuplicateRunId:
    """测试重复运行生成递增序号"""

    def test_duplicate_runs_increment_sequence(self, temp_output_dir, sample_result):
        """重复运行同名策略，序号递增"""
        run_id_1 = ResultPersister.save(sample_result, temp_output_dir)
        run_id_2 = ResultPersister.save(sample_result, temp_output_dir)
        run_id_3 = ResultPersister.save(sample_result, temp_output_dir)

        assert run_id_1.endswith("_1")
        assert run_id_2.endswith("_2")
        assert run_id_3.endswith("_3")

    def test_duplicate_runs_create_separate_directories(self, temp_output_dir, sample_result):
        """重复运行创建独立的目录"""
        run_id_1 = ResultPersister.save(sample_result, temp_output_dir)
        run_id_2 = ResultPersister.save(sample_result, temp_output_dir)

        assert (Path(temp_output_dir) / run_id_1).exists()
        assert (Path(temp_output_dir) / run_id_2).exists()
        assert run_id_1 != run_id_2