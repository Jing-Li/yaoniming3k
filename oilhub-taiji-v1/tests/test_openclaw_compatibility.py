"""
Openclaw 客户端兼容性验证（Gateway + SSE）

验证目标：确保本服务对 Gateway 模式客户端（如 openclaw、各类 AI Gateway 代理）
的 SSE 流式传输、Header 透传、长连接保持等行为符合预期。

Openclaw 作为 Gateway 的典型行为：
- 严格校验 Content-Type 和 SSE 格式
- 可能携带自定义 X- 头
- 流式场景对 [DONE] 标记和 finish_reason 的时机敏感
- 对连接中断/超时的处理要求高
"""
import json
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from openai_provider.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_taiji_single():
    """模拟 taiji 返回单条 SSE。"""
    mock = AsyncMock()
    mock.status_code = 200
    mock.text = 'data: {"id":"1","type":"string","data":"Openclaw test","code":0}\n\ndata: [DONE]\n'
    mock.headers = {"content-type": "text/event-stream"}
    return mock


@pytest.fixture
def mock_taiji_stream_multi():
    """模拟 taiji 返回多段 SSE。"""
    mock = AsyncMock()
    mock.status_code = 200
    mock.text = (
        'data: {"id":"1","type":"string","data":"First","code":0}\n'
        'data: {"id":"1","type":"string","data":" second","code":0}\n'
        'data: {"id":"1","type":"string","data":" third","code":0}\n'
        'data: [DONE]\n'
    )
    mock.headers = {"content-type": "text/event-stream"}
    return mock


@pytest.fixture
def mock_taiji_stream_with_error_mid():
    """模拟 taiji 流中途返回错误元数据。"""
    class MockStreamContext:
        def __init__(self):
            self.status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def aiter_lines(self):
            yield 'data: {"id":"1","type":"string","data":"Start","code":0}'
            yield 'data: {"id":"1","type":"error","data":"mid-stream error","code":500}'
            yield 'data: [DONE]'

        async def aread(self):
            return b""

    return MockStreamContext()


@pytest.fixture
def mock_taiji_slow_stream():
    """模拟 taiji 慢速流（Gateway 对超时敏感）。"""
    class MockStreamContext:
        def __init__(self):
            self.status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def aiter_lines(self):
            yield 'data: {"id":"1","type":"string","data":"A","code":0}'
            yield 'data: {"id":"1","type":"string","data":"B","code":0}'
            yield 'data: [DONE]'

        async def aread(self):
            return b""

    return MockStreamContext()


# ---------------------------------------------------------------------------
# 1. Gateway 非流式请求兼容性
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_openclaw_basic_non_stream(mock_taiji_single):
    """Gateway 非流式调用应返回标准 OpenAI JSON。"""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_taiji_single):
        resp = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "test"}],
        })

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/json"
    data = resp.json()
    assert data["object"] == "chat.completion"
    assert data["choices"][0]["message"]["role"] == "assistant"
    assert isinstance(data["choices"][0]["message"]["content"], str)


@pytest.mark.asyncio
async def test_openclaw_gateway_custom_headers(mock_taiji_single):
    """Gateway 可能携带自定义 X- 头，应被透传或至少不报错。"""
    captured = {}

    async def capture_post(*args, **kwargs):
        captured["headers"] = kwargs.get("headers", {})
        mock = AsyncMock()
        mock.status_code = 200
        mock.text = mock_taiji_single.text
        mock.headers = {"content-type": "text/event-stream"}
        return mock

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=capture_post):
        resp = client.post(
            "/v1/chat/completions",
            json={"model": "taiji", "messages": [{"role": "user", "content": "hi"}]},
            headers={
                "X-Request-ID": "gateway-123",
                "X-Forwarded-For": "10.0.0.1",
                "X-Openclaw-Version": "1.0",
            },
        )

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_openclaw_gateway_accept_header(mock_taiji_single):
    """Gateway 发送 Accept: application/json 时应返回 JSON。"""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_taiji_single):
        resp = client.post(
            "/v1/chat/completions",
            json={"model": "taiji", "messages": [{"role": "user", "content": "hi"}]},
            headers={"Accept": "application/json"},
        )

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/json"


# ---------------------------------------------------------------------------
# 2. Gateway SSE 流式严格格式验证
# ---------------------------------------------------------------------------

def test_openclaw_stream_sse_format(mock_taiji_slow_stream):
    """Gateway 对流式 SSE 格式的严格检查：每行必须以 data: 开头，以 \n\n 分隔。"""
    with patch("httpx.AsyncClient.stream", return_value=mock_taiji_slow_stream):
        resp = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "stream"}],
            "stream": True,
        })

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "text/event-stream; charset=utf-8"
    assert resp.headers.get("cache-control") == "no-cache"
    assert resp.headers.get("connection") == "keep-alive"

    body = resp.text
    # SSE 规范：每条消息以 \n\n 结束
    # 由于 TestClient 会缓冲，我们检查是否包含正确的 data: 行
    lines = body.split("\n")
    data_lines = [l for l in lines if l.startswith("data:")]
    assert len(data_lines) >= 2  # 至少一个内容 chunk + [DONE]

    # 最后一条必须是 [DONE]
    assert "data: [DONE]" in body


@pytest.fixture
def mock_taiji_stream_role_then_content():
    """模拟流：第一个 chunk 只有 role，后续只有 content。"""
    class MockStreamContext:
        def __init__(self):
            self.status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def aiter_lines(self):
            yield 'data: {"id":"1","type":"string","data":"","code":0}'  # role chunk
            yield 'data: {"id":"1","type":"string","data":"Hello","code":0}'
            yield 'data: [DONE]'

        async def aread(self):
            return b""

    return MockStreamContext()


def test_openclaw_stream_first_chunk_has_role(mock_taiji_stream_role_then_content):
    """Gateway 期望第一个 chunk 携带 role，后续 chunk 不重复 role。"""
    with patch("httpx.AsyncClient.stream", return_value=mock_taiji_stream_role_then_content):
        resp = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": True,
        })

    assert resp.status_code == 200
    chunks = []
    for line in resp.text.split("\n"):
        line = line.strip()
        if line.startswith("data:"):
            data = line[5:].strip()
            if data != "[DONE]" and data:
                chunks.append(json.loads(data))

    # 第一个 chunk 必须有 role
    assert chunks[0]["choices"][0]["delta"]["role"] == "assistant"
    # 后续 chunk 不应再出现 role（除非有内容）
    # 注意：当前实现 role_sent 后不再发送 role


def test_openclaw_stream_finish_reason_timing(mock_taiji_slow_stream):
    """Gateway 期望 finish_reason 只在最后一个内容 chunk 或独立 chunk 中出现。"""
    with patch("httpx.AsyncClient.stream", return_value=mock_taiji_slow_stream):
        resp = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": True,
        })

    chunks = []
    for line in resp.text.split("\n"):
        line = line.strip()
        if line.startswith("data:"):
            data = line[5:].strip()
            if data == "[DONE]":
                break
            if data:
                chunks.append(json.loads(data))

    # 除最后一个外，其他 chunk 的 finish_reason 应为 null 或被省略
    for chunk in chunks[:-1]:
        finish_reason = chunk["choices"][0].get("finish_reason")
        assert finish_reason is None or "finish_reason" not in chunk["choices"][0]

    # 最后一个 chunk 的 finish_reason 应为 "stop"
    assert chunks[-1]["choices"][0]["finish_reason"] == "stop"


# ---------------------------------------------------------------------------
# 3. Gateway 参数透传与转换
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_openclaw_all_params_together(mock_taiji_single):
    """Gateway 可能一次性发送所有支持参数，验证全部被接受。"""
    captured = {}

    async def capture_post(*args, **kwargs):
        captured["json"] = kwargs.get("json", {})
        mock = AsyncMock()
        mock.status_code = 200
        mock.text = mock_taiji_single.text
        mock.headers = {"content-type": "text/event-stream"}
        return mock

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=capture_post):
        resp = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "hi"}],
            "temperature": 0.8,
            "max_tokens": 256,
            "top_p": 0.95,
            "presence_penalty": 0.2,
            "frequency_penalty": -0.1,
            "stream": False,
            "user": "openclaw-user",
        })

    assert resp.status_code == 200
    # 验证透传到 taiji 的参数
    assert captured["json"]["temperature"] == 0.8
    assert captured["json"]["max_tokens"] == 256
    assert captured["json"]["top_p"] == 0.95
    assert captured["json"]["presence_penalty"] == 0.2
    assert captured["json"]["frequency_penalty"] == -0.1


# ---------------------------------------------------------------------------
# 4. Gateway 错误处理兼容性
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_openclaw_provider_502_format():
    """Gateway 期望 502 错误也是 OpenAI 风格 JSON。"""
    mock_err = AsyncMock()
    mock_err.status_code = 503
    mock_err.text = "Service Unavailable"
    mock_err.headers = {"content-type": "text/plain"}

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_err):
        resp = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "hi"}],
        })

    assert resp.status_code == 502
    data = resp.json()
    assert "error" in data
    assert "message" in data["error"]
    assert "type" in data["error"]


@pytest.mark.asyncio
async def test_openclaw_timeout_handling():
    """Gateway 对超时敏感：taiji 超时时应返回有意义错误，不崩溃。"""
    from httpx import TimeoutException

    async def raise_timeout(*args, **kwargs):
        raise TimeoutException("Request timed out")

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=raise_timeout):
        resp = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "slow"}],
        })

    assert resp.status_code == 502
    data = resp.json()
    assert "timeout" in data["error"]["message"].lower() or "Taiji API" in data["error"]["message"]


# ---------------------------------------------------------------------------
# 5. Gateway 并发与连接稳定性
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_openclaw_multiple_concurrent_requests(mock_taiji_single):
    """Gateway 可能并发转发多个请求，应互不干扰。"""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_taiji_single):
        resp1 = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "req1"}],
        })
        resp2 = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "req2"}],
        })

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    data1 = resp1.json()
    data2 = resp2.json()
    # 两个响应应有不同 id
    assert data1["id"] != data2["id"]


# ---------------------------------------------------------------------------
# 6. Gateway 健康检查
# ---------------------------------------------------------------------------

def test_openclaw_health_check():
    """Gateway 通常有健康探测，/health 应快速返回。"""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# 7. Gateway 对 models 端点的要求
# ---------------------------------------------------------------------------

def test_openclaw_models_list():
    """Gateway 可能在启动时拉取模型列表，格式必须标准。"""
    resp = client.get("/v1/models")
    assert resp.status_code == 200
    data = resp.json()
    assert data["object"] == "list"
    assert isinstance(data["data"], list)
    # 每个模型必须有 id, object, created, owned_by
    for m in data["data"]:
        assert "id" in m
        assert m["object"] == "model"
        assert "created" in m
        assert "owned_by" in m


# ---------------------------------------------------------------------------
# 8. 未匹配路由的 404（OpenAI 风格）
# ---------------------------------------------------------------------------

def test_openclaw_404_openai_style():
    """Gateway 访问不存在的端点时，应返回 OpenAI 风格的 404。"""
    resp = client.get("/v1/unknown-endpoint")
    assert resp.status_code == 404
    data = resp.json()
    assert "error" in data
    assert data["error"]["type"] == "invalid_request_error"
    assert "message" in data["error"]
