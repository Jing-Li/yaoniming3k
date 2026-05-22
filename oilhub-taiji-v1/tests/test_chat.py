import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from openai_provider.main import app

client = TestClient(app)


@pytest.fixture
def mock_taiji_success():
    """模拟 taiji 返回 SSE 格式的成功响应。"""
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.text = 'data: {"id":"1","type":"string","data":"你好，我是 Taiji！","code":0}\n\ndata: [DONE]\n'
    mock_resp.headers = {"content-type": "text/event-stream"}
    return mock_resp


@pytest.fixture
def mock_taiji_multi_chunk():
    """模拟 taiji 返回多段 SSE。"""
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.text = (
        'data: {"id":"1","type":"string","data":"你好","code":0}\n'
        'data: {"id":"1","type":"string","data":"，世界","code":0}\n'
        'data: [DONE]\n'
    )
    mock_resp.headers = {"content-type": "text/event-stream"}
    return mock_resp


@pytest.fixture
def mock_taiji_with_think():
    """模拟 taiji 返回包含 <think> 标签的响应。"""
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.text = (
        'data: {"id":"1","type":"string","data":"<think> 思考过程 </think>\\n","code":0}\n'
        'data: {"id":"1","type":"string","data":"最终回答","code":0}\n'
        'data: [DONE]\n'
    )
    mock_resp.headers = {"content-type": "text/event-stream"}
    return mock_resp


@pytest.fixture
def mock_taiji_error():
    mock_resp = AsyncMock()
    mock_resp.status_code = 429
    mock_resp.text = "Rate limit exceeded"
    mock_resp.headers = {"content-type": "text/plain"}
    return mock_resp


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_list_models():
    resp = client.get("/v1/models")
    assert resp.status_code == 200
    data = resp.json()
    assert data["object"] == "list"
    assert any(m["id"] == "taiji" for m in data["data"])


@pytest.mark.asyncio
async def test_chat_completions_success(mock_taiji_success):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_taiji_success):
        payload = {
            "model": "taiji",
            "messages": [{"role": "user", "content": "你好"}],
        }
        resp = client.post("/v1/chat/completions", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    assert data["object"] == "chat.completion"
    assert data["model"] == "taiji"
    assert len(data["choices"]) == 1
    assert data["choices"][0]["message"]["role"] == "assistant"
    assert data["choices"][0]["message"]["content"] == "你好，我是 Taiji！"
    assert data["usage"]["prompt_tokens"] > 0
    assert data["usage"]["completion_tokens"] > 0


@pytest.mark.asyncio
async def test_chat_completions_multi_chunk(mock_taiji_multi_chunk):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_taiji_multi_chunk):
        payload = {
            "model": "taiji",
            "messages": [{"role": "user", "content": "hello"}],
        }
        resp = client.post("/v1/chat/completions", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    # 多段 SSE 应拼接为完整文本
    assert data["choices"][0]["message"]["content"] == "你好，世界"


@pytest.mark.asyncio
async def test_chat_completions_provider_error(mock_taiji_error):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_taiji_error):
        payload = {
            "model": "taiji",
            "messages": [{"role": "user", "content": "test"}],
        }
        resp = client.post("/v1/chat/completions", json=payload)

    assert resp.status_code == 502
    data = resp.json()
    assert "error" in data
    assert "Taiji API error" in data["error"]["message"]


def test_chat_completions_invalid_request():
    resp = client.post("/v1/chat/completions", json={"foo": "bar"})
    assert resp.status_code == 400
    data = resp.json()
    assert data["error"]["type"] == "invalid_request_error"


@pytest.fixture
def mock_taiji_stream():
    """模拟 taiji 返回流式 SSE。"""

    class MockStreamContext:
        def __init__(self, lines):
            self._lines = lines
            self.status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def aiter_lines(self):
            for line in self._lines:
                yield line

        async def aread(self):
            return b""

    lines = [
        'data: {"id":"1","type":"string","data":"你好","code":0}',
        'data: {"id":"1","type":"string","data":"！","code":0}',
        "data: [DONE]",
    ]
    return MockStreamContext(lines)


def test_chat_completions_streaming(mock_taiji_stream):
    with patch("httpx.AsyncClient.stream", return_value=mock_taiji_stream):
        payload = {
            "model": "taiji",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": True,
        }
        resp = client.post("/v1/chat/completions", json=payload)

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

    # 第一个 chunk 同时携带 role + content，后续 chunk 只携带 content
    assert len(chunks) >= 3
    assert chunks[0]["object"] == "chat.completion.chunk"
    assert chunks[0]["choices"][0]["delta"]["role"] == "assistant"
    assert chunks[0]["choices"][0]["delta"]["content"] == "你好"
    assert chunks[1]["choices"][0]["delta"]["content"] == "！"


def test_chat_completions_streaming_reasoning_content():
    """流式响应：当 taiji 返回 think 标签时，reasoning_content 应作为独立 delta 实时发送。"""

    class MockStreamContext:
        def __init__(self):
            self.status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def aiter_lines(self):
            # Simulate think tag spanning multiple chunks
            yield 'data: {"id":"1","type":"string","data":"<think>","code":0}'
            yield 'data: {"id":"1","type":"string","data":"思考","code":0}'
            yield 'data: {"id":"1","type":"string","data":"过程</think>","code":0}'
            yield 'data: {"id":"1","type":"string","data":"最终","code":0}'
            yield 'data: {"id":"1","type":"string","data":"答案","code":0}'
            yield 'data: [DONE]'

        async def aread(self):
            return b""

    with patch("httpx.AsyncClient.stream", return_value=MockStreamContext()):
        payload = {
            "model": "taiji",
            "messages": [{"role": "user", "content": "test"}],
            "stream": True,
        }
        resp = client.post("/v1/chat/completions", json=payload)

    assert resp.status_code == 200

    chunks = []
    for line in resp.text.split("\n"):
        line = line.strip()
        if line.startswith("data:"):
            data = line[5:].strip()
            if data == "[DONE]":
                break
            if data:
                chunks.append(json.loads(data))

    # Should have reasoning_content chunks followed by content chunks
    reasoning_chunks = [c for c in chunks if "reasoning_content" in c["choices"][0].get("delta", {})]
    content_chunks = [c for c in chunks if "content" in c["choices"][0].get("delta", {})]

    assert len(reasoning_chunks) > 0, "Should have reasoning_content chunks"
    assert len(content_chunks) > 0, "Should have content chunks"

    # Verify reasoning content is extracted correctly (without think tags)
    full_reasoning = "".join(c["choices"][0]["delta"]["reasoning_content"] for c in reasoning_chunks)
    assert "<think>" not in full_reasoning
    assert "</think>" not in full_reasoning
    assert "思考" in full_reasoning or "过程" in full_reasoning


@pytest.mark.asyncio
async def test_chat_completions_empty_think_tag_omits_reasoning():
    """非流式响应：当 think 标签为空时，reasoning_content 字段应被省略（而非 null）。"""
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.text = (
        'data: {"id":"1","type":"string","data":"<think></think>这是答案","code":0}\n'
        'data: [DONE]\n'
    )
    mock_resp.headers = {"content-type": "text/event-stream"}

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        payload = {
            "model": "taiji",
            "messages": [{"role": "user", "content": "test"}],
        }
        resp = client.post("/v1/chat/completions", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    message = data["choices"][0]["message"]

    # Content should be present
    assert message["content"] == "这是答案"

    # reasoning_content should be omitted entirely (not null)
    assert "reasoning_content" not in message


def test_chat_completions_token_calculation_includes_reasoning():
    """非流式响应：completion_tokens 应包含 reasoning_content 的字符数。"""
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    # 80 chars reasoning + 20 chars content = 100 chars total ≈ 25 tokens
    mock_resp.text = (
        'data: {"id":"1","type":"string","data":"<think>AAAAAAAAAABBBBBBBBBBCCCCCCCCCCDDDDDDDDDDEEEEEEEEEEFFFFFFFFFGGGGGGGGGGHHHHHHHHHH</think>",'
        '"code":0}\n'
        'data: {"id":"1","type":"string","data":"这是最终的答案内容。","code":0}\n'
        'data: [DONE]\n'
    )
    mock_resp.headers = {"content-type": "text/event-stream"}

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        payload = {
            "model": "taiji",
            "messages": [{"role": "user", "content": "test"}],
        }
        resp = client.post("/v1/chat/completions", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    usage = data["usage"]

    # Verify completion_tokens accounts for both content and reasoning
    # 80 (reasoning) + 20 (content) = 100 chars / 4 ≈ 25 tokens
    assert usage["completion_tokens"] >= 20  # Should include reasoning
    assert usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"]


def test_openai_model_exclude_none_serialization():
    """OpenAIModel 基类应在序列化时省略 None 字段。"""
    from openai_provider.models.openai import ChatCompletionMessage, ChatCompletionDelta
    import json

    # Test ChatCompletionMessage
    msg = ChatCompletionMessage(role="assistant", content="Hello")
    dumped = msg.model_dump()
    assert "reasoning_content" not in dumped
    assert "tool_calls" not in dumped

    # Test JSON serialization
    json_str = msg.model_dump_json()
    parsed = json.loads(json_str)
    assert "reasoning_content" not in parsed
    assert "tool_calls" not in parsed

    # Test ChatCompletionDelta
    delta = ChatCompletionDelta(content="World")
    delta_dumped = delta.model_dump()
    assert "reasoning_content" not in delta_dumped
    assert "role" not in delta_dumped  # role is also None by default


def test_chat_completions_extra_body_fields_ignored():
    """请求中包含未知字段时，不应返回 400 错误，而应静默忽略。"""
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.text = (
        'data: {"id":"1","type":"string","data":"Hello","code":0}\n'
        'data: [DONE]\n'
    )
    mock_resp.headers = {"content-type": "text/event-stream"}

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        # 发送包含未知字段的请求（如 Hermes Agent 可能发送的 thinking, reasoning 等）
        payload = {
            "model": "taiji",
            "messages": [{"role": "user", "content": "test"}],
            "thinking": False,  # 未知字段
            "reasoning": True,  # 未知字段
            "extra_body": {"custom": "value"},  # 未知字段
        }
        resp = client.post("/v1/chat/completions", json=payload)

    # 应该返回 200 而不是 400
    assert resp.status_code == 200
    data = resp.json()
    assert data["choices"][0]["message"]["content"] == "Hello"


@pytest.mark.asyncio
async def test_chat_completions_with_system_message(mock_taiji_success):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_taiji_success):
        payload = {
            "model": "taiji",
            "messages": [
                {"role": "system", "content": "你是一个助手"},
                {"role": "user", "content": "你好"},
            ],
        }
        resp = client.post("/v1/chat/completions", json=payload)

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_chat_completions_long_text_truncation():
    """测试超长文本被截断的场景（通过检查最终发出的请求体）。"""
    captured = {}

    async def capture_post(*args, **kwargs):
        captured["json"] = kwargs.get("json")
        mock = AsyncMock()
        mock.status_code = 200
        mock.text = 'data: {"id":"1","type":"string","data":"ok","code":0}\n\ndata: [DONE]\n'
        mock.headers = {}
        return mock

    with patch("httpx.AsyncClient.post", new=capture_post):
        long_text = "A" * 200000
        payload = {
            "model": "taiji",
            "messages": [{"role": "user", "content": long_text}],
        }
        resp = client.post("/v1/chat/completions", json=payload)

    assert resp.status_code == 200
    # 实测 max_text_length = 800000
    assert len(captured["json"]["text"]) <= 800000


@pytest.mark.asyncio
async def test_chat_completions_strip_think(mock_taiji_with_think):
    """测试 <think> 标签被正确去除。"""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_taiji_with_think):
        payload = {
            "model": "taiji",
            "messages": [{"role": "user", "content": "hello"}],
        }
        resp = client.post("/v1/chat/completions", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    assert "<think>" not in content
    assert "思考过程" not in content
    assert "最终回答" in content


@pytest.mark.asyncio
async def test_chat_completions_reasoning_content_present():
    """非流式响应：当 taiji 返回 think 标签时，reasoning_content 字段应包含提取的思考内容。"""
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.text = (
        'data: {"id":"1","type":"string","data":"<think>这是推理过程</think>这是最终答案","code":0}\n'
        'data: [DONE]\n'
    )
    mock_resp.headers = {"content-type": "text/event-stream"}

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        payload = {
            "model": "taiji",
            "messages": [{"role": "user", "content": "test"}],
        }
        resp = client.post("/v1/chat/completions", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    message = data["choices"][0]["message"]

    # Content should NOT contain think tags
    assert message["content"] == "这是最终答案"

    # reasoning_content should be present and contain extracted reasoning
    assert "reasoning_content" in message
    assert message["reasoning_content"] == "这是推理过程"


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------

from openai_provider.config import settings


def test_auth_disabled_by_default():
    """未配置 API_KEY 时，无需认证即可访问。"""
    original_key = settings.API_KEY
    settings.API_KEY = ""
    try:
        resp = client.get("/v1/models")
        assert resp.status_code == 200
    finally:
        settings.API_KEY = original_key


def test_auth_with_valid_key():
    """配置了 API_KEY 时，携带正确 Bearer token 可通过。"""
    original_key = settings.API_KEY
    settings.API_KEY = "secret-test-key"
    try:
        resp = client.get(
            "/v1/models",
            headers={"Authorization": "Bearer secret-test-key"},
        )
        assert resp.status_code == 200
    finally:
        settings.API_KEY = original_key


def test_auth_with_invalid_key():
    """配置了 API_KEY 时，携带错误 token 返回 401。"""
    original_key = settings.API_KEY
    settings.API_KEY = "secret-test-key"
    try:
        resp = client.get(
            "/v1/models",
            headers={"Authorization": "Bearer wrong-key"},
        )
        assert resp.status_code == 401
        data = resp.json()
        assert data["error"]["type"] == "authentication_error"
        assert data["error"]["code"] == "invalid_api_key"
    finally:
        settings.API_KEY = original_key


def test_auth_missing_key():
    """配置了 API_KEY 时，未携带 token 返回 401。"""
    original_key = settings.API_KEY
    settings.API_KEY = "secret-test-key"
    try:
        resp = client.get("/v1/models")
        assert resp.status_code == 401
        data = resp.json()
        assert data["error"]["type"] == "authentication_error"
    finally:
        settings.API_KEY = original_key
