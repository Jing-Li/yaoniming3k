"""POST /api/runs 端点集成测试"""

import threading
import time
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from caisen.web.main import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def _valid_payload(**overrides):
    base = {
        "strategy_name": "CaiSenStrategy",
        "symbol": "000001.SZ",
        "freq": "1d",
        "start": "2023-01-01",
        "end": "2024-12-31",
        "params": {"stop_loss_factor": 0.95},
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# 1. tracer bullet：合法参数 → 202 + run_id（BacktestRunner 被 mock）
# ---------------------------------------------------------------------------

def test_post_runs_returns_202_and_run_id(client):
    """合法请求立即返回 202 Accepted，响应体含 run_id 字段。"""
    with patch("caisen.web.main.BacktestRunner.run_backtest", return_value="mock_run_001"):
        resp = client.post("/api/runs", json=_valid_payload())
    assert resp.status_code == 202
    body = resp.json()
    assert "run_id" in body
    assert body["run_id"]  # 非空


# ---------------------------------------------------------------------------
# 2. strategy_name 未注册 → 422
# ---------------------------------------------------------------------------

def test_unknown_strategy_returns_422(client):
    """strategy_name 不在注册表中时，同步返回 422（不启动后台任务）。"""
    resp = client.post("/api/runs", json=_valid_payload(strategy_name="NoSuchStrategy"))
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 3. 日期格式错误 → 422（Pydantic 校验）
# ---------------------------------------------------------------------------

def test_invalid_date_format_returns_422(client):
    """start/end 不符合 YYYY-MM-DD 格式时返回 422。"""
    resp = client.post("/api/runs", json=_valid_payload(start="20230101"))
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 4. 后台任务非阻塞：端点立即返回，BacktestRunner 被异步调用
# ---------------------------------------------------------------------------

def test_background_task_is_called_asynchronously(client):
    """端点立即返回 202，后台线程中调用了 BacktestRunner.run_backtest。"""
    called = threading.Event()

    def fake_run(**kwargs):
        called.set()
        return "bg_run_id"

    with patch("caisen.web.main.BacktestRunner.run_backtest", side_effect=fake_run):
        resp = client.post("/api/runs", json=_valid_payload())

    assert resp.status_code == 202
    # 等待后台线程执行（最多 2 秒）
    assert called.wait(timeout=2), "BacktestRunner.run_backtest 未在后台被调用"
