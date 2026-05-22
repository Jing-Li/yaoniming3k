import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from openai_provider.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_taiji_tool_call():
    """模拟 taiji 返回 tool_calls JSON。"""
    mock = AsyncMock()
    mock.status_code = 200
    mock.text = (
        'data: {"id":"1","type":"string","data":"{\\"tool_calls\\": [{\\"id\\": \\"call_abc123\\", \\"type\\": \\"function\\", \\"function\\": {\\"name\\": \\"get_weather\\", \\"arguments\\": \\"{\\\\\\"location\\\\\\": \\\\\\"NYC\\\\\\"}\\"}}]}\\n","code":0}\n'
        'data: [DONE]\n'
    )
    mock.headers = {"content-type": "text/event-stream"}
    return mock


@pytest.fixture
def mock_taiji_normal_text_with_tools():
    """模拟 taiji 在有 tools 的情况下返回普通文本。"""
    mock = AsyncMock()
    mock.status_code = 200
    mock.text = (
        'data: {"id":"1","type":"string","data":"I do not need a tool for that. ","code":0}\n'
        'data: {"id":"1","type":"string","data":"Here is the answer.","code":0}\n'
        'data: [DONE]\n'
    )
    mock.headers = {"content-type": "text/event-stream"}
    return mock


@pytest.fixture
def mock_taiji_stream_tool_call():
    """模拟 taiji 流式返回 tool_calls JSON。"""
    class MockStreamContext:
        def __init__(self):
            self.status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def aiter_lines(self):
            yield 'data: {"id":"1","type":"string","data":"{\\"tool_calls\\": [{\\"id\\": \\"call_abc123\\", \\"type\\": \\"function\\", \\"function\\": {\\"name\\": \\"get_weather\\", \\"arguments\\": \\"{\\\\\\"location\\\\\\": \\\\\\"NYC\\\\\\"}\\"}}]}\\n","code":0}'
            yield 'data: [DONE]'

        async def aread(self):
            return b""

    return MockStreamContext()


@pytest.fixture
def mock_taiji_stream_normal_with_tools():
    """模拟 taiji 流式在有 tools 时返回普通文本。"""
    class MockStreamContext:
        def __init__(self):
            self.status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def aiter_lines(self):
            yield 'data: {"id":"1","type":"string","data":"Hello","code":0}'
            yield 'data: {"id":"1","type":"string","data":" world","code":0}'
            yield 'data: [DONE]'

        async def aread(self):
            return b""

    return MockStreamContext()


# ---------------------------------------------------------------------------
# Non-streaming tool call tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_chat_completions_tool_call_parsed(mock_taiji_tool_call):
    """非流式请求：当模型返回 tool_calls JSON 时，应正确解析并返回 OpenAI 格式。"""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_taiji_tool_call):
        payload = {
            "model": "taiji",
            "messages": [{"role": "user", "content": "What's the weather in NYC?"}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get current weather",
                        "parameters": {
                            "type": "object",
                            "properties": {"location": {"type": "string"}},
                            "required": ["location"],
                        },
                    },
                }
            ],
        }
        resp = client.post("/v1/chat/completions", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    assert data["object"] == "chat.completion"
    assert data["choices"][0]["finish_reason"] == "tool_calls"
    # content should be omitted when None (OpenAI-compatible behavior)
    assert "content" not in data["choices"][0]["message"]
    assert data["choices"][0]["message"]["tool_calls"] is not None
    assert len(data["choices"][0]["message"]["tool_calls"]) == 1
    tc = data["choices"][0]["message"]["tool_calls"][0]
    assert tc["id"] == "call_abc123"
    assert tc["type"] == "function"
    assert tc["function"]["name"] == "get_weather"
    assert "NYC" in tc["function"]["arguments"]


@pytest.mark.asyncio
async def test_chat_completions_tools_prompt_injected(mock_taiji_normal_text_with_tools):
    """非流式请求：tools 定义应被注入到发送给 taiji 的 text 中。"""
    captured = {}

    async def capture_post(*args, **kwargs):
        captured["json"] = kwargs.get("json")
        mock = AsyncMock()
        mock.status_code = 200
        mock.text = mock_taiji_normal_text_with_tools.text
        mock.headers = {"content-type": "text/event-stream"}
        return mock

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=capture_post):
        payload = {
            "model": "taiji",
            "messages": [{"role": "user", "content": "hi"}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get weather",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }
            ],
        }
        resp = client.post("/v1/chat/completions", json=payload)

    assert resp.status_code == 200
    text = captured["json"]["text"]
    assert "You have access to the following tools:" in text
    assert "get_weather" in text
    assert "Get weather" in text


@pytest.mark.asyncio
async def test_chat_completions_normal_text_with_tools(mock_taiji_normal_text_with_tools):
    """非流式请求：有 tools 但模型返回普通文本时，finish_reason 应为 stop。"""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_taiji_normal_text_with_tools):
        payload = {
            "model": "taiji",
            "messages": [{"role": "user", "content": "Say hello"}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get weather",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }
            ],
        }
        resp = client.post("/v1/chat/completions", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    assert data["choices"][0]["finish_reason"] == "stop"
    assert data["choices"][0]["message"]["content"] is not None
    # tool_calls should be omitted when None (OpenAI-compatible behavior)
    assert "tool_calls" not in data["choices"][0]["message"]


@pytest.mark.asyncio
async def test_chat_completions_tool_result_message_in_prompt():
    """tool 角色消息应被包含在发送给 taiji 的 text 中。"""
    captured = {}

    async def capture_post(*args, **kwargs):
        captured["json"] = kwargs.get("json")
        mock = AsyncMock()
        mock.status_code = 200
        mock.text = 'data: {"id":"1","type":"string","data":"ok","code":0}\n\ndata: [DONE]\n'
        mock.headers = {"content-type": "text/event-stream"}
        return mock

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=capture_post):
        payload = {
            "model": "taiji",
            "messages": [
                {"role": "user", "content": "What's the weather?"},
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_123",
                            "type": "function",
                            "function": {"name": "get_weather", "arguments": '{"location": "NYC"}'},
                        }
                    ],
                },
                {"role": "tool", "tool_call_id": "call_123", "content": "Sunny, 25C"},
            ],
        }
        resp = client.post("/v1/chat/completions", json=payload)

    assert resp.status_code == 200
    text = captured["json"]["text"]
    assert "[Tool Result for call_123]: Sunny, 25C" in text


# ---------------------------------------------------------------------------
# Streaming tool call tests
# ---------------------------------------------------------------------------

def test_chat_completions_streaming_tool_call(mock_taiji_stream_tool_call):
    """流式请求：当模型返回 tool_calls JSON 时，应缓冲并在最后输出 tool_calls delta。"""
    with patch("httpx.AsyncClient.stream", return_value=mock_taiji_stream_tool_call):
        payload = {
            "model": "taiji",
            "messages": [{"role": "user", "content": "Weather?"}],
            "stream": True,
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get weather",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }
            ],
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

    # 结构：role+tool_calls delta -> finish tool_calls -> [DONE]
    assert len(chunks) >= 3
    assert chunks[0]["object"] == "chat.completion.chunk"
    assert chunks[0]["choices"][0]["delta"]["role"] == "assistant"
    assert chunks[0]["choices"][0]["delta"]["tool_calls"] is not None
    assert len(chunks[0]["choices"][0]["delta"]["tool_calls"]) == 1
    assert chunks[0]["choices"][0]["delta"]["tool_calls"][0]["function"]["name"] == "get_weather"
    assert chunks[-2]["choices"][0]["finish_reason"] == "tool_calls"
    assert chunks[-1] == "[DONE]"


def test_chat_completions_streaming_normal_with_tools(mock_taiji_stream_normal_with_tools):
    """流式请求：有 tools 但模型返回普通文本时，应正常流式输出。"""
    with patch("httpx.AsyncClient.stream", return_value=mock_taiji_stream_normal_with_tools):
        payload = {
            "model": "taiji",
            "messages": [{"role": "user", "content": "Say hello"}],
            "stream": True,
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get weather",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }
            ],
        }
        resp = client.post("/v1/chat/completions", json=payload)

    assert resp.status_code == 200

    chunks = []
    for line in resp.text.split("\n"):
        line = line.strip()
        if line.startswith("data:"):
            data = line[5:].strip()
            if data == "[DONE]":
                chunks.append("[DONE]")
            elif data:
                chunks.append(json.loads(data))

    # 缓冲的内容应在最后统一输出
    assert len(chunks) >= 3
    assert chunks[0]["object"] == "chat.completion.chunk"
    assert chunks[0]["choices"][0]["delta"]["role"] == "assistant"
    assert chunks[0]["choices"][0]["delta"]["content"] == "Hello"
    # _strip_think_tags calls .strip() which removes leading space
    assert chunks[1]["choices"][0]["delta"]["content"] == "world"
    assert chunks[-2]["choices"][0]["finish_reason"] == "stop"
    assert chunks[-1] == "[DONE]"


@pytest.mark.asyncio
async def test_chat_completions_streaming_tools_prompt_injected():
    """流式请求：tools 定义应被注入到发送给 taiji 的 text 中。"""
    captured = {}

    class MockStreamContext:
        def __init__(self):
            self.status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def aiter_lines(self):
            yield 'data: {"id":"1","type":"string","data":"Hello","code":0}'
            yield 'data: [DONE]'

        async def aread(self):
            return b""

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        def stream(self, method, url, *, headers=None, json=None, **kwargs):
            captured["json"] = json
            return MockStreamContext()

        async def aclose(self):
            pass

    with patch("httpx.AsyncClient", MockAsyncClient):
        payload = {
            "model": "taiji",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": True,
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get weather",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }
            ],
        }
        resp = client.post("/v1/chat/completions", json=payload)

    assert resp.status_code == 200
    assert "json" in captured
    text = captured["json"]["text"]
    assert "You have access to the following tools:" in text
    assert "get_weather" in text
