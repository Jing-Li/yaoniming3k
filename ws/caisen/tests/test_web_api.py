"""Web API 综合测试 — 覆盖主要端点的正常与异常路径。"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from caisen.web.main import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


class TestHealthEndpoint:
    """健康检查端点。"""

    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestDataSourcesEndpoint:
    """数据源列表端点。"""

    def test_list_data_sources(self, client):
        resp = client.get("/api/data-sources")
        assert resp.status_code == 200
        body = resp.json()
        assert "data_sources" in body
        assert isinstance(body["data_sources"], list)


class TestStrategiesEndpoint:
    """策略列表端点。"""

    def test_list_strategies_returns_list(self, client):
        resp = client.get("/api/strategies")
        assert resp.status_code == 200
        body = resp.json()
        assert "strategies" in body
        assert isinstance(body["strategies"], list)

    def test_strategies_have_required_fields(self, client):
        resp = client.get("/api/strategies")
        strategies = resp.json()["strategies"]
        for s in strategies:
            assert "name" in s
            assert "display_name" in s
            assert "type" in s
            assert "params_schema" in s
            assert "config_presets" in s


class TestRunsListEndpoint:
    """GET /api/runs 端点。"""

    def test_list_runs_empty_dir(self, client, tmp_path):
        """空目录返回空列表。"""
        from caisen.web.main import set_output_dir
        set_output_dir(str(tmp_path))
        resp = client.get("/api/runs")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 0
        assert body["runs"] == []

    def test_list_runs_skips_invalid(self, client, tmp_path):
        """缺少 meta.json 的目录被跳过。"""
        from caisen.web.main import set_output_dir
        (tmp_path / "invalid_run").mkdir()
        set_output_dir(str(tmp_path))
        resp = client.get("/api/runs")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    def test_list_runs_includes_valid(self, client, tmp_path):
        """包含完整 meta.json + data.json 的目录被列入。"""
        from caisen.web.main import set_output_dir
        run_dir = tmp_path / "TestStrategy_20240101_1"
        run_dir.mkdir()
        meta = {
            "run_id": "TestStrategy_20240101_1",
            "strategy_name": "TestStrategy",
            "bar_count": 100,
            "created_at": "2024-01-01T00:00:00",
        }
        (run_dir / "meta.json").write_text(json.dumps(meta))
        (run_dir / "data.json").write_text("{}")
        set_output_dir(str(tmp_path))
        resp = client.get("/api/runs")
        body = resp.json()
        assert body["count"] == 1
        assert body["runs"][0]["run_id"] == "TestStrategy_20240101_1"


class TestRunDetailEndpoint:
    """GET /api/runs/{run_id} 端点。"""

    def test_nonexistent_run_returns_404(self, client, tmp_path):
        from caisen.web.main import set_output_dir
        set_output_dir(str(tmp_path))
        resp = client.get("/api/runs/nonexistent")
        assert resp.status_code in (400, 404)


class TestPostRunsEndpoint:
    """POST /api/runs 端点。"""

    def test_valid_request_returns_202(self, client):
        with patch("caisen.web.main.BacktestRunner.run_backtest", return_value="mock_001"):
            resp = client.post("/api/runs", json={
                "strategy_name": "CaiSenStrategy",
                "symbol": "000001.SZ",
                "freq": "1d",
                "start": "2024-01-01",
                "end": "2024-12-31",
            })
        assert resp.status_code == 202
        assert "run_id" in resp.json()

    def test_unknown_strategy_returns_422(self, client):
        resp = client.post("/api/runs", json={
            "strategy_name": "NoSuchStrategy",
            "symbol": "X",
            "freq": "1d",
            "start": "2024-01-01",
            "end": "2024-12-31",
        })
        assert resp.status_code == 422

    def test_invalid_date_format_returns_422(self, client):
        resp = client.post("/api/runs", json={
            "strategy_name": "CaiSenStrategy",
            "symbol": "X",
            "freq": "1d",
            "start": "20240101",  # 错误格式
            "end": "2024-12-31",
        })
        assert resp.status_code == 422

    def test_missing_required_fields_returns_422(self, client):
        resp = client.post("/api/runs", json={})
        assert resp.status_code == 422
