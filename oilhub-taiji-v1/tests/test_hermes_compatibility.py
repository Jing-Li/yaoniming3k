"""
Hermes 客户端兼容性验证（标准 OpenAI API）

验证目标：确保本服务对标准 OpenAI API 客户端（如 hermes、openai-python、langchain 等）
的行为与官方 API 一致。

使用 Mock 隔离 taiji 后端，专注验证接口契约。
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
def mock_taiji_ok():
    """模拟 taiji 返回单条 SSE 成功响应。"""
    mock = AsyncMock()
    mock.status_code = 200
    mock.text = 'data: {"id":"1","type":"string","data":"Hello from Taiji","code":0}\n\ndata: [DONE]\n'
    mock.headers = {"content-type": "text/event-stream"}
    return mock


@pytest.fixture
def mock_taiji_stream():
    """模拟 taiji 返回流式 SSE。"""
    mock = AsyncMock()
    mock.status_code = 200
    mock.text = (
        'data: {"id":"1","type":"string","data":"Hello","code":0}\n'
        'data: {"id":"1","type":"string","data":" world","code":0}\n'
        'data: [DONE]\n'
    )
    mock.headers = {"content-type": "text/event-stream"}
    return mock


@pytest.fixture
def mock_taiji_json_ok():
    """模拟 taiji 返回 JSON（非 SSE）成功响应。"""
    mock = AsyncMock()
    mock.status_code = 200
    mock.text = '{"data":"Hello from Taiji","code":0}'
    mock.headers = {"content-type": "application/json"}
    return mock


def _capture_and_return(captured, text_response):
    """辅助函数：捕获请求参数并返回 mock 响应。"""
    async def capture_post(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        mock = AsyncMock()
        mock.status_code = 200
        mock.text = text_response
        mock.headers = {"content-type": "text/event-stream"}
        return mock
    return capture_post


# ---------------------------------------------------------------------------
# 1. 基本非流式 Chat Completion
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hermes_basic_chat_completion(mock_taiji_ok):
    """hermes 最基本调用：model + messages，返回完整响应。"""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_taiji_ok):
        resp = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "Hello"}],
        })

    assert resp.status_code == 200
    data = resp.json()
    assert data["object"] == "chat.completion"
    assert data["model"] == "taiji"
    assert "id" in data
    assert "created" in data
    assert len(data["choices"]) == 1
    assert data["choices"][0]["message"]["role"] == "assistant"
    assert isinstance(data["choices"][0]["message"]["content"], str)
    assert data["choices"][0]["finish_reason"] == "stop"
    assert "usage" in data
    assert data["usage"]["prompt_tokens"] >= 0
    assert data["usage"]["completion_tokens"] >= 0
    assert data["usage"]["total_tokens"] == data["usage"]["prompt_tokens"] + data["usage"]["completion_tokens"]


@pytest.mark.asyncio
async def test_hermes_with_system_message(mock_taiji_ok):
    """hermes 常见用法：system + user 多轮消息。"""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_taiji_ok):
        resp = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What is 2+2?"},
            ],
        })

    assert resp.status_code == 200
    data = resp.json()
    assert data["choices"][0]["message"]["content"] == "Hello from Taiji"


@pytest.mark.asyncio
async def test_hermes_multi_turn_conversation(mock_taiji_ok):
    """hermes 多轮对话：system + user + assistant + user。"""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_taiji_ok):
        resp = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [
                {"role": "system", "content": "You are a math tutor."},
                {"role": "user", "content": "What is derivative of x^2?"},
                {"role": "assistant", "content": "The derivative of x^2 is 2x."},
                {"role": "user", "content": "What about x^3?"},
            ],
        })

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["choices"]) == 1


# ---------------------------------------------------------------------------
# 2. 参数透传验证
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hermes_temperature_param(mock_taiji_ok):
    """temperature 参数应被透传到 taiji 请求体。"""
    captured = {}
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock,
               side_effect=_capture_and_return(captured, mock_taiji_ok.text)):
        resp = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "hi"}],
            "temperature": 0.5,
        })

    assert resp.status_code == 200
    assert captured["kwargs"]["json"]["temperature"] == 0.5


@pytest.mark.asyncio
async def test_hermes_max_tokens_param(mock_taiji_ok):
    """max_tokens 参数应被透传到 taiji 请求体。"""
    captured = {}
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock,
               side_effect=_capture_and_return(captured, mock_taiji_ok.text)):
        resp = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 100,
        })

    assert resp.status_code == 200
    assert captured["kwargs"]["json"]["max_tokens"] == 100


@pytest.mark.asyncio
async def test_hermes_top_p_param(mock_taiji_ok):
    """top_p 参数应被透传到 taiji 请求体。"""
    captured = {}
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock,
               side_effect=_capture_and_return(captured, mock_taiji_ok.text)):
        resp = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "hi"}],
            "top_p": 0.9,
        })

    assert resp.status_code == 200
    assert captured["kwargs"]["json"]["top_p"] == 0.9


@pytest.mark.asyncio
async def test_hermes_presence_penalty_param(mock_taiji_ok):
    """presence_penalty 参数应被透传到 taiji 请求体。"""
    captured = {}
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock,
               side_effect=_capture_and_return(captured, mock_taiji_ok.text)):
        resp = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "hi"}],
            "presence_penalty": 0.5,
        })

    assert resp.status_code == 200
    assert captured["kwargs"]["json"]["presence_penalty"] == 0.5


@pytest.mark.asyncio
async def test_hermes_frequency_penalty_param(mock_taiji_ok):
    """frequency_penalty 参数应被透传到 taiji 请求体。"""
    captured = {}
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock,
               side_effect=_capture_and_return(captured, mock_taiji_ok.text)):
        resp = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "hi"}],
            "frequency_penalty": -0.5,
        })

    assert resp.status_code == 200
    assert captured["kwargs"]["json"]["frequency_penalty"] == -0.5


@pytest.mark.asyncio
async def test_hermes_stop_param_string(mock_taiji_ok):
    """stop 参数（字符串形式）应被接受但当前不强制透传（taiji 不支持）。"""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_taiji_ok):
        resp = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "hi"}],
            "stop": "STOP",
        })

    # 至少不应报错
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_hermes_stop_param_list(mock_taiji_ok):
    """stop 参数（列表形式）应被接受但当前不强制透传（taiji 不支持）。"""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_taiji_ok):
        resp = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "hi"}],
            "stop": ["STOP", "END"],
        })

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_hermes_user_param(mock_taiji_ok):
    """user 参数应被接受（用于追踪），不强制透传。"""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_taiji_ok):
        resp = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "hi"}],
            "user": "user-123",
        })

    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 3. 流式响应兼容性
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_taiji_stream_hermes():
    """模拟 taiji 返回多段流式 SSE，内容无 think 标签。"""
    class MockStreamContext:
        def __init__(self):
            self.status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def aiter_lines(self):
            yield 'data: {"id":"1","type":"string","data":"H","code":0}'
            yield 'data: {"id":"1","type":"string","data":"ello","code":0}'
            yield 'data: [DONE]'

        async def aread(self):
            return b""

    return MockStreamContext()


def test_hermes_streaming(mock_taiji_stream_hermes):
    """hermes 流式调用：stream=true，返回 SSE 格式。"""
    with patch("httpx.AsyncClient.stream", return_value=mock_taiji_stream_hermes):
        resp = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "Say hello"}],
            "stream": True,
        })

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "text/event-stream; charset=utf-8"

    chunks = []
    for line in resp.text.split("\n"):
        line = line.strip()
        if line.startswith("data:"):
            data = line[5:].strip()
            if data == "[DONE]":
                chunks.append("[DONE]")
            elif data:
                chunks.append(json.loads(data))

    # 结构检查
    assert len(chunks) >= 2
    assert chunks[0]["object"] == "chat.completion.chunk"
    assert chunks[0]["choices"][0]["delta"]["role"] == "assistant"
    assert "content" in chunks[0]["choices"][0]["delta"]
    assert chunks[-2]["choices"][0]["finish_reason"] == "stop"
    assert chunks[-1] == "[DONE]"

    # 内容拼接检查
    contents = []
    for chunk in chunks[:-2]:
        content = chunk["choices"][0]["delta"].get("content")
        if content:
            contents.append(content)
    assert "".join(contents) == "Hello"


# ---------------------------------------------------------------------------
# 4. 错误响应兼容性（OpenAI 风格错误体）
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hermes_invalid_request_error():
    """hermes 发送无效请求时，返回 OpenAI 风格的 invalid_request_error。"""
    resp = client.post("/v1/chat/completions", json={
        "model": "taiji",
        # 缺少必填字段 messages
    })

    assert resp.status_code == 400
    data = resp.json()
    assert "error" in data
    assert data["error"]["type"] == "invalid_request_error"
    assert "message" in data["error"]


@pytest.mark.asyncio
async def test_hermes_provider_error_502():
    """taiji 后端异常时，返回 502 + provider_error。"""
    mock_err = AsyncMock()
    mock_err.status_code = 429
    mock_err.text = "Rate limit exceeded"
    mock_err.headers = {"content-type": "text/plain"}

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_err):
        resp = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "hi"}],
        })

    assert resp.status_code == 502
    data = resp.json()
    assert data["error"]["type"] == "provider_error"
    assert "message" in data["error"]


# ---------------------------------------------------------------------------
# 5. 模型列表端点
# ---------------------------------------------------------------------------

def test_hermes_list_models():
    """GET /v1/models 应返回 OpenAI 风格的模型列表。"""
    resp = client.get("/v1/models")
    assert resp.status_code == 200
    data = resp.json()
    assert data["object"] == "list"
    assert isinstance(data["data"], list)
    assert any(m["id"] == "taiji" for m in data["data"])
    for m in data["data"]:
        assert m["object"] == "model"
        assert "id" in m


# ---------------------------------------------------------------------------
# 6. 认证兼容性
# ---------------------------------------------------------------------------

def test_hermes_auth_bearer_token():
    """hermes 使用 Bearer token 认证时应被正确校验。"""
    from openai_provider.config import settings
    original = settings.API_KEY
    settings.API_KEY = "hermes-test-key"
    try:
        # 无 token
        resp = client.get("/v1/models")
        assert resp.status_code == 401

        # 错误 token
        resp = client.get("/v1/models", headers={"Authorization": "Bearer wrong-key"})
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "invalid_api_key"

        # 正确 token
        resp = client.get("/v1/models", headers={"Authorization": "Bearer hermes-test-key"})
        assert resp.status_code == 200
    finally:
        settings.API_KEY = original


# ---------------------------------------------------------------------------
# 7. 边界与异常场景
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hermes_empty_message_content(mock_taiji_ok):
    """hermes 可能发送空 content，应被正确处理。"""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_taiji_ok):
        resp = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": ""}],
        })

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_hermes_message_content_none(mock_taiji_ok):
    """hermes 可能省略 content 字段（None），应被正确处理。"""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_taiji_ok):
        resp = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user"}],
        })

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_hermes_unsupported_model(mock_taiji_ok):
    """hermes 请求不支持的模型时，当前实现仍透传到 taiji（taiji 只有单一模型）。"""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_taiji_ok):
        resp = client.post("/v1/chat/completions", json={
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "hi"}],
        })

    # 当前行为：不校验模型名，直接透传
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_hermes_n_param_ignored(mock_taiji_ok):
    """hermes 可能设置 n > 1，当前实现只返回 1 个 choice（taiji 不支持 n）。"""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_taiji_ok):
        resp = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "hi"}],
            "n": 3,
        })

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["choices"]) == 1
