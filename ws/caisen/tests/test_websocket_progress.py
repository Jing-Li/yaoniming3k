"""WS /ws/runs/{run_id}/progress 端点集成测试"""

import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from caisen.web.main import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def _ws_url(run_id="test_run_001", **params):
    """构造 WebSocket URL，附带回测参数（query string）。"""
    base = f"/ws/runs/{run_id}/progress"
    qs = "&".join(
        f"{k}={v}"
        for k, v in {
            "strategy_name": "CaiSenStrategy",
            "symbol": "000001.SZ",
            "freq": "1d",
            "start": "2023-01-01",
            "end": "2024-12-31",
            **params,
        }.items()
    )
    return f"{base}?{qs}"


def _collect_messages(ws):
    """收集所有 WebSocket 消息直到连接关闭。"""
    messages = []
    try:
        while True:
            messages.append(ws.receive_json())
    except Exception:
        pass
    return messages


# ---------------------------------------------------------------------------
# 1. tracer bullet：WS 连接后收到 done 消息（BacktestRunner 立即返回）
# ---------------------------------------------------------------------------

def test_ws_receives_done_message(client):
    """连接 WebSocket 后，BacktestRunner 完成时推送 done 消息。"""
    with patch("caisen.web.main.BacktestRunner.run_backtest", return_value="mocked_run_001"):
        with client.websocket_connect(_ws_url()) as ws:
            messages = _collect_messages(ws)

    done_msgs = [m for m in messages if m.get("status") == "done"]
    assert done_msgs, f"未收到 done 消息，收到：{messages}"
    assert done_msgs[0]["run_id"] == "mocked_run_001"


# ---------------------------------------------------------------------------
# 2. 进度回调触发 running 消息
# ---------------------------------------------------------------------------

def test_ws_receives_running_messages(client):
    """BacktestRunner 触发 on_progress 时，客户端收到 running 消息。"""
    def fake_run(on_progress=None, **kwargs):
        if on_progress:
            on_progress(100, 250, "2023-05-01")
            on_progress(200, 250, "2023-10-01")
        return "run_with_progress"

    with patch("caisen.web.main.BacktestRunner.run_backtest", side_effect=fake_run):
        with client.websocket_connect(_ws_url()) as ws:
            messages = _collect_messages(ws)

    running_msgs = [m for m in messages if m.get("status") == "running"]
    assert len(running_msgs) >= 2, f"期望 ≥2 条 running 消息，收到：{messages}"
    assert running_msgs[0]["processed"] == 100
    assert running_msgs[0]["total"] == 250
    assert running_msgs[0]["current_date"] == "2023-05-01"


# ---------------------------------------------------------------------------
# 3. BacktestError 触发 error 消息
# ---------------------------------------------------------------------------

def test_ws_receives_error_on_backtest_failure(client):
    """BacktestRunner 抛出异常时，客户端收到 error 消息。"""
    from caisen.backtest.runner import BacktestError

    with patch(
        "caisen.web.main.BacktestRunner.run_backtest",
        side_effect=BacktestError("数据为空：000001.SZ"),
    ):
        with client.websocket_connect(_ws_url()) as ws:
            messages = _collect_messages(ws)

    error_msgs = [m for m in messages if m.get("status") == "error"]
    assert error_msgs, f"期望 error 消息，收到：{messages}"
    assert "数据为空" in error_msgs[0]["message"]


# ---------------------------------------------------------------------------
# 4. 终态消息后连接自动关闭（done 后不再有消息可读）
# ---------------------------------------------------------------------------

def test_ws_connection_closes_after_done(client):
    """done 消息发送后，服务端关闭连接，客户端下一次 receive 抛出异常。"""
    with patch("caisen.web.main.BacktestRunner.run_backtest", return_value="close_test_run"):
        with client.websocket_connect(_ws_url()) as ws:
            # 读到 done 消息
            done_seen = False
            for _ in range(20):  # 最多读 20 条
                try:
                    msg = ws.receive_json()
                    if msg.get("status") == "done":
                        done_seen = True
                        break
                except Exception:
                    break
            assert done_seen, "未收到 done 消息"
            # 下一次读应该触发 disconnect（连接已关闭）
            closed = False
            try:
                ws.receive_json()
            except Exception:
                closed = True
            assert closed, "done 消息后连接未关闭"
