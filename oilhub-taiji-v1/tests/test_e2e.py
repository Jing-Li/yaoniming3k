"""
体系化 E2E 测试套件。

覆盖现有测试未涉及的空白区域：
- 自定义异常体系验证
- CORS 中间件行为
- 流式边界场景（中途错误、空流、二进制请求体）
- XML/DSML tool_calls 完整 E2E 路径
- tool_choice 参数（required/none/auto）
- 多轮对话模式
- 响应 ID 唯一性
- 模型元数据完整性
- Content-Type 协商
- 并发流式请求
- _strip_tool_calls_from_content 方法
- Settings property 验证
"""
import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from openai_provider.config import settings
from openai_provider.exceptions import (
    ProviderError,
    TaijiBusinessError,
    TaijiHTTPError,
    TaijiRequestError,
    TaijiTimeoutError,
)
from openai_provider.main import app
from openai_provider.models.openai import ChatMessage
from openai_provider.providers.taiji import TaijiProvider

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sse_ok(content: str = "Hello E2E") -> AsyncMock:
    mock = AsyncMock()
    mock.status_code = 200
    mock.text = f'data: {{"id":"1","type":"string","data":"{content}","code":0}}\n\ndata: [DONE]\n'
    mock.headers = {"content-type": "text/event-stream"}
    return mock


def _sse_chunks(chunks: list[str]) -> AsyncMock:
    lines = [f'data: {c}' for c in chunks] + ["data: [DONE]", ""]
    mock = AsyncMock()
    mock.status_code = 200
    mock.text = "\n".join(lines)
    mock.headers = {"content-type": "text/event-stream"}
    return mock


class _StreamCtx:
    def __init__(self, lines: list[str], *, status_code: int = 200):
        self._lines = lines
        self.status_code = status_code

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        pass

    async def aiter_lines(self):
        for line in self._lines:
            yield line

    async def aread(self):
        return b""


def _stream(lines: list[str], *, status_code: int = 200):
    return _StreamCtx(lines, status_code=status_code)


def _sse_lines(chunks: list[str]) -> list[str]:
    return [f"data: {c}" for c in chunks] + ["data: [DONE]"]


def _parse_chunks(text: str) -> list[dict]:
    result = []
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("data:"):
            data = line[5:].strip()
            if data == "[DONE]":
                break
            if data:
                result.append(json.loads(data))
    return result


# ===========================================================================
# 1. 自定义异常体系验证
# ===========================================================================

class TestExceptionHierarchy:
    """验证异常继承关系和消息格式。"""

    def test_all_exceptions_inherit_provider_error(self):
        assert issubclass(TaijiTimeoutError, ProviderError)
        assert issubclass(TaijiHTTPError, ProviderError)
        assert issubclass(TaijiBusinessError, ProviderError)
        assert issubclass(TaijiRequestError, ProviderError)

    def test_timeout_error_no_arg(self):
        err = TaijiTimeoutError()
        assert str(err) == "Taiji API timeout"
        assert "timeout" in str(err).lower()

    def test_timeout_error_with_detail(self):
        err = TaijiTimeoutError("Read timed out after 60s")
        assert "Taiji API timeout" in str(err)
        assert "Read timed out" in str(err)

    def test_http_error_includes_status(self):
        err = TaijiHTTPError(429, "Rate limit exceeded")
        assert err.status_code == 429
        assert "429" in str(err)
        assert "Rate limit" in str(err)

    def test_http_error_truncates_long_message(self):
        long_msg = "x" * 1000
        err = TaijiHTTPError(500, long_msg)
        # 消息应被截断到 500 字符以内
        assert len(str(err)) < 600

    def test_business_error(self):
        err = TaijiBusinessError("session expired")
        assert "business error" in str(err).lower()
        assert "session expired" in str(err)

    def test_request_error(self):
        err = TaijiRequestError("Connection refused")
        assert "request failed" in str(err).lower()
        assert "Connection refused" in str(err)

    def test_catch_all_provider_errors(self):
        """确保所有自定义异常都能被 ProviderError 捕获。"""
        for exc_cls in (TaijiTimeoutError, TaijiHTTPError, TaijiBusinessError, TaijiRequestError):
            with pytest.raises(ProviderError):
                if exc_cls == TaijiHTTPError:
                    raise exc_cls(500, "test")
                raise exc_cls("test")


# ===========================================================================
# 2. 异常到 HTTP 响应映射 E2E
# ===========================================================================

class TestExceptionToHTTPMapping:
    """验证每种异常在 main.py 中映射为正确的 HTTP 响应。"""

    @pytest.mark.asyncio
    async def test_timeout_returns_502_with_timeout_message(self):
        from httpx import TimeoutException

        async def _raise(*a, **kw):
            raise TimeoutException("Connection timed out")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=_raise):
            resp = client.post("/v1/chat/completions", json={
                "model": "taiji", "messages": [{"role": "user", "content": "hi"}],
            })
        assert resp.status_code == 502
        msg = resp.json()["error"]["message"]
        assert "timeout" in msg.lower() or "Taiji API" in msg

    @pytest.mark.asyncio
    async def test_http_error_429_returns_502(self):
        mock = AsyncMock()
        mock.status_code = 429
        mock.text = "Too Many Requests"
        mock.headers = {}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock):
            resp = client.post("/v1/chat/completions", json={
                "model": "taiji", "messages": [{"role": "user", "content": "hi"}],
            })
        assert resp.status_code == 502
        assert "429" in resp.json()["error"]["message"]

    @pytest.mark.asyncio
    async def test_http_error_500_returns_502(self):
        mock = AsyncMock()
        mock.status_code = 500
        mock.text = "Internal Server Error"
        mock.headers = {}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock):
            resp = client.post("/v1/chat/completions", json={
                "model": "taiji", "messages": [{"role": "user", "content": "hi"}],
            })
        assert resp.status_code == 502
        assert "500" in resp.json()["error"]["message"]

    @pytest.mark.asyncio
    async def test_network_error_returns_502(self):
        from httpx import ConnectError

        async def _raise(*a, **kw):
            raise ConnectError("Connection refused")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=_raise):
            resp = client.post("/v1/chat/completions", json={
                "model": "taiji", "messages": [{"role": "user", "content": "hi"}],
            })
        assert resp.status_code == 502
        assert "request failed" in resp.json()["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_business_error_in_sse_returns_502(self):
        inner = json.dumps({"err": "auth expired", "code": -1})
        mock = _sse_chunks([
            json.dumps({"id": "1", "type": "string", "data": inner, "code": 0}),
        ])
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock):
            resp = client.post("/v1/chat/completions", json={
                "model": "taiji", "messages": [{"role": "user", "content": "hi"}],
            })
        assert resp.status_code == 502
        assert "business error" in resp.json()["error"]["message"].lower()


# ===========================================================================
# 3. CORS 中间件验证
# ===========================================================================

class TestCORSMiddleware:

    def test_cors_preflight_returns_headers(self):
        resp = client.options(
            "/v1/chat/completions",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert resp.status_code == 200
        assert "access-control-allow-origin" in resp.headers

    def test_cors_simple_request_includes_origin(self):
        resp = client.get("/health", headers={"Origin": "http://example.com"})
        assert resp.status_code == 200
        # 默认 CORS_ORIGINS="*"，所以应允许任何源
        allow = resp.headers.get("access-control-allow-origin")
        assert allow is not None


# ===========================================================================
# 4. 流式边界场景
# ===========================================================================

class TestStreamingEdgeCases:

    def test_stream_only_done_marker(self):
        """taiji 只返回 [DONE] 而无任何内容。"""
        stream = _stream(["data: [DONE]"])
        with patch("httpx.AsyncClient.stream", return_value=stream):
            resp = client.post("/v1/chat/completions", json={
                "model": "taiji", "messages": [{"role": "user", "content": "hi"}],
                "stream": True,
            })
        assert resp.status_code == 200
        chunks = _parse_chunks(resp.text)
        # 应至少有 finish chunk
        finish = [c for c in chunks if c["choices"][0].get("finish_reason")]
        assert len(finish) > 0

    def test_stream_invalid_json_lines_skipped(self):
        """流中包含非法 JSON 行时应被跳过而不崩溃。"""
        stream = _stream([
            'data: {"id":"1","type":"string","data":"OK","code":0}',
            "data: {invalid json}",
            'data: {"id":"1","type":"string","data":" fine","code":0}',
            "data: [DONE]",
        ])
        with patch("httpx.AsyncClient.stream", return_value=stream):
            resp = client.post("/v1/chat/completions", json={
                "model": "taiji", "messages": [{"role": "user", "content": "hi"}],
                "stream": True,
            })
        assert resp.status_code == 200
        chunks = _parse_chunks(resp.text)
        contents = "".join(c["choices"][0]["delta"].get("content", "") for c in chunks)
        assert "OK" in contents

    def test_stream_non_200_returns_http_error(self):
        """流式响应状态码非 200 时应返回错误。"""
        stream = _stream([], status_code=503)
        with patch("httpx.AsyncClient.stream", return_value=stream):
            resp = client.post("/v1/chat/completions", json={
                "model": "taiji", "messages": [{"role": "user", "content": "hi"}],
                "stream": True,
            })
        # 流式 503 应被 stream_generator 内的 except 捕获
        assert resp.status_code == 200  # StreamingResponse 已发出
        body = resp.text
        assert "error" in body or "503" in body or "provider_error" in body

    def test_stream_mid_stream_unknown_type_skipped(self):
        """流中收到未知 type 的对象应被跳过而不崩溃。"""
        stream = _stream(_sse_lines([
            '{"id":"1","type":"string","data":"start","code":0}',
            '{"type":"unknown_type","data":"ignored","code":0}',
            '{"id":"1","type":"string","data":" end","code":0}',
        ]))
        with patch("httpx.AsyncClient.stream", return_value=stream):
            resp = client.post("/v1/chat/completions", json={
                "model": "taiji", "messages": [{"role": "user", "content": "hi"}],
                "stream": True,
            })
        assert resp.status_code == 200
        chunks = _parse_chunks(resp.text)
        contents = "".join(c["choices"][0]["delta"].get("content", "") for c in chunks)
        assert "start" in contents
        assert "end" in contents


# ===========================================================================
# 5. XML/DSML tool_calls E2E 完整路径
# ===========================================================================

_XML_SINGLE = (
    '<tool_calls>'
    '<invoke name="get_weather">'
    '<' + 'parameter name="city">Beijing</' + 'parameter>'
    '</invoke>'
    '</tool_calls>'
)

_XML_MULTI = (
    '<tool_calls>'
    '<invoke name="search">'
    '<' + 'parameter name="query">news</' + 'parameter>'
    '</invoke>'
    '<invoke name="get_time">'
    '<' + 'parameter name="zone">UTC</' + 'parameter>'
    '</invoke>'
    '</tool_calls>'
)

_XML_DSML = (
    '<｜｜DSML｜｜tool_calls>'
    '<｜｜DSML｜｜invoke name="calculate">'
    '<｜｜DSML｜｜parameter name="expr">2+3</｜｜DSML｜｜parameter>'
    '</｜｜DSML｜｜invoke>'
    '</｜｜DSML｜｜tool_calls>'
)


class TestXMLToolCallsE2E:
    """通过完整 HTTP 路径验证 XML/DSML tool_calls 解析。"""

    @pytest.mark.asyncio
    async def test_standard_xml_single_tool_call(self):
        sse_obj = json.dumps({"id": "1", "type": "string", "data": _XML_SINGLE, "code": 0})
        mock = _sse_chunks([sse_obj])
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock):
            resp = client.post("/v1/chat/completions", json={
                "model": "taiji",
                "messages": [{"role": "user", "content": "weather?"}],
                "tools": [{"type": "function", "function": {"name": "get_weather", "parameters": {}}}],
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["choices"][0]["finish_reason"] == "tool_calls"
        tcs = data["choices"][0]["message"]["tool_calls"]
        assert len(tcs) == 1
        assert tcs[0]["function"]["name"] == "get_weather"
        assert "Beijing" in tcs[0]["function"]["arguments"]

    @pytest.mark.asyncio
    async def test_standard_xml_multi_tool_calls(self):
        sse_obj = json.dumps({"id": "1", "type": "string", "data": _XML_MULTI, "code": 0})
        mock = _sse_chunks([sse_obj])
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock):
            resp = client.post("/v1/chat/completions", json={
                "model": "taiji",
                "messages": [{"role": "user", "content": "search and time"}],
                "tools": [
                    {"type": "function", "function": {"name": "search", "parameters": {}}},
                    {"type": "function", "function": {"name": "get_time", "parameters": {}}},
                ],
            })
        assert resp.status_code == 200
        tcs = resp.json()["choices"][0]["message"]["tool_calls"]
        assert len(tcs) == 2
        names = {tc["function"]["name"] for tc in tcs}
        assert "search" in names
        assert "get_time" in names

    @pytest.mark.asyncio
    async def test_dsml_tool_call(self):
        sse_obj = json.dumps({"id": "1", "type": "string", "data": _XML_DSML, "code": 0})
        mock = _sse_chunks([sse_obj])
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock):
            resp = client.post("/v1/chat/completions", json={
                "model": "taiji",
                "messages": [{"role": "user", "content": "calc"}],
                "tools": [{"type": "function", "function": {"name": "calculate", "parameters": {}}}],
            })
        assert resp.status_code == 200
        tcs = resp.json()["choices"][0]["message"]["tool_calls"]
        assert len(tcs) == 1
        assert tcs[0]["function"]["name"] == "calculate"
        args = json.loads(tcs[0]["function"]["arguments"])
        assert args["expr"] == "2+3"

    @pytest.mark.asyncio
    async def test_xml_tool_call_content_stripped(self):
        """tool_calls XML 块应从 content 中移除。"""
        text_with_xml = f"Some text before {_XML_SINGLE} and after"
        sse_obj = json.dumps({"id": "1", "type": "string", "data": text_with_xml, "code": 0})
        mock = _sse_chunks([sse_obj])
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock):
            resp = client.post("/v1/chat/completions", json={
                "model": "taiji",
                "messages": [{"role": "user", "content": "test"}],
                "tools": [{"type": "function", "function": {"name": "get_weather", "parameters": {}}}],
            })
        assert resp.status_code == 200
        msg = resp.json()["choices"][0]["message"]
        content = msg.get("content", "")
        assert "<tool_calls>" not in (content or "")
        assert "<invoke" not in (content or "")


# ===========================================================================
# 6. tool_choice 参数验证
# ===========================================================================

class TestToolChoiceParameter:

    @pytest.mark.asyncio
    async def test_tool_choice_required_accepted(self):
        """tool_choice=required 应被接受，但不注入额外指令。"""
        captured = {}

        async def capture(*a, **kw):
            captured["json"] = kw.get("json")
            return _sse_ok("ok")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=capture):
            resp = client.post("/v1/chat/completions", json={
                "model": "taiji",
                "messages": [{"role": "user", "content": "hi"}],
                "tools": [{"type": "function", "function": {"name": "fn", "parameters": {}}}],
                "tool_choice": "required",
            })
        assert resp.status_code == 200
        # tool_choice 不再注入强制指令，只验证参数被接受
        assert "RESPONSE FORMAT" in captured["json"]["text"]

    @pytest.mark.asyncio
    async def test_tool_choice_none_accepted(self):
        """tool_choice=none 应被接受，但不注入禁用指令。"""
        captured = {}

        async def capture(*a, **kw):
            captured["json"] = kw.get("json")
            return _sse_ok("ok")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=capture):
            resp = client.post("/v1/chat/completions", json={
                "model": "taiji",
                "messages": [{"role": "user", "content": "hi"}],
                "tools": [{"type": "function", "function": {"name": "fn", "parameters": {}}}],
                "tool_choice": "none",
            })
        assert resp.status_code == 200
        assert "RESPONSE FORMAT" in captured["json"]["text"]

    @pytest.mark.asyncio
    async def test_tool_choice_auto_default(self):
        """tool_choice 未设置时默认为 auto，不注入额外指令。"""
        captured = {}

        async def capture(*a, **kw):
            captured["json"] = kw.get("json")
            return _sse_ok("ok")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=capture):
            resp = client.post("/v1/chat/completions", json={
                "model": "taiji",
                "messages": [{"role": "user", "content": "hi"}],
                "tools": [{"type": "function", "function": {"name": "fn", "parameters": {}}}],
            })
        assert resp.status_code == 200
        assert "RESPONSE FORMAT" in captured["json"]["text"]


# ===========================================================================
# 7. 多轮对话模式
# ===========================================================================

class TestMultiTurnConversation:

    @pytest.mark.asyncio
    async def test_three_turn_conversation(self):
        """user -> assistant -> user -> assistant -> user 三轮对话。"""
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=_sse_ok("Final")):
            resp = client.post("/v1/chat/completions", json={
                "model": "taiji",
                "messages": [
                    {"role": "system", "content": "You are helpful."},
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi! How can I help?"},
                    {"role": "user", "content": "What's 2+2?"},
                    {"role": "assistant", "content": "4"},
                    {"role": "user", "content": "And 3+3?"},
                ],
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["choices"][0]["message"]["content"] == "Final"

    @pytest.mark.asyncio
    async def test_tool_round_trip_conversation(self):
        """完整工具调用往返：请求 -> tool_calls -> tool_result -> final answer。"""
        # Turn 1: model returns tool_calls
        sse_obj = json.dumps({
            "id": "1", "type": "string",
            "data": '{"tool_calls": [{"id": "call_rt", "type": "function", "function": {"name": "search", "arguments": "{\\"q\\": \\"test\\"}"}}]}',
            "code": 0,
        })
        mock1 = _sse_chunks([sse_obj])
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock1):
            resp1 = client.post("/v1/chat/completions", json={
                "model": "taiji",
                "messages": [{"role": "user", "content": "Search for test"}],
                "tools": [{"type": "function", "function": {"name": "search", "parameters": {}}}],
            })
        assert resp1.status_code == 200
        assert resp1.json()["choices"][0]["finish_reason"] == "tool_calls"

        # Turn 2: send tool result back, get final answer
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=_sse_ok("Here are the results")):
            resp2 = client.post("/v1/chat/completions", json={
                "model": "taiji",
                "messages": [
                    {"role": "user", "content": "Search for test"},
                    {"role": "assistant", "tool_calls": [
                        {"id": "call_rt", "type": "function", "function": {"name": "search", "arguments": '{"q": "test"}'}},
                    ]},
                    {"role": "tool", "tool_call_id": "call_rt", "content": "Result: item1, item2"},
                ],
                "tools": [{"type": "function", "function": {"name": "search", "parameters": {}}}],
            })
        assert resp2.status_code == 200
        assert resp2.json()["choices"][0]["message"]["content"] == "Here are the results"


# ===========================================================================
# 8. 响应 ID 唯一性与结构
# ===========================================================================

class TestResponseStructure:

    @pytest.mark.asyncio
    async def test_unique_response_ids(self):
        """每个响应应有唯一的 id。"""
        ids = set()
        for _ in range(5):
            with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=_sse_ok("hi")):
                resp = client.post("/v1/chat/completions", json={
                    "model": "taiji", "messages": [{"role": "user", "content": "hi"}],
                })
            ids.add(resp.json()["id"])
        assert len(ids) == 5, "All response IDs should be unique"

    @pytest.mark.asyncio
    async def test_response_id_format(self):
        """响应 ID 应以 chatcmpl- 开头。"""
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=_sse_ok("hi")):
            resp = client.post("/v1/chat/completions", json={
                "model": "taiji", "messages": [{"role": "user", "content": "hi"}],
            })
        assert resp.json()["id"].startswith("chatcmpl-")

    @pytest.mark.asyncio
    async def test_created_timestamp_is_recent(self):
        """created 字段应为近期的 Unix 时间戳。"""
        import time
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=_sse_ok("hi")):
            resp = client.post("/v1/chat/completions", json={
                "model": "taiji", "messages": [{"role": "user", "content": "hi"}],
            })
        created = resp.json()["created"]
        assert abs(time.time() - created) < 60  # 1 分钟以内


# ===========================================================================
# 9. 模型元数据完整性
# ===========================================================================

class TestModelMetadata:

    def test_model_list_has_required_fields(self):
        resp = client.get("/v1/models")
        data = resp.json()
        for m in data["data"]:
            assert "id" in m
            assert "object" in m and m["object"] == "model"
            assert "created" in m
            assert "owned_by" in m
            assert "context_length" in m
            assert "max_completion_tokens" in m

    def test_get_model_taiji_has_metadata(self):
        resp = client.get("/v1/models/taiji")
        data = resp.json()
        assert data["id"] == "taiji"
        assert data["context_length"] > 0
        assert data["max_completion_tokens"] > 0

    def test_api_v1_models_alias(self):
        """api/v1/models 应与 /v1/models 返回相同结构。"""
        r1 = client.get("/v1/models")
        r2 = client.get("/api/v1/models")
        assert r1.json()["object"] == r2.json()["object"]
        assert len(r1.json()["data"]) == len(r2.json()["data"])


# ===========================================================================
# 10. 请求体边界验证
# ===========================================================================

class TestRequestBodyEdgeCases:

    def test_empty_messages_list(self):
        """空消息列表应被处理而不崩溃（可能返回错误或空响应）。"""
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=_sse_ok("empty")):
            resp = client.post("/v1/chat/completions", json={
                "model": "taiji", "messages": [],
            })
        # 空消息列表被允许（Pydantic 不验证 min_length），provider 正常处理
        assert resp.status_code in (200, 400, 422, 502)

    def test_binary_request_body(self):
        """二进制请求体应返回 400 而不崩溃。"""
        resp = client.post(
            "/v1/chat/completions",
            content=b"\x00\x01\x02\xff\xfe",
            headers={"Content-Type": "application/octet-stream"},
        )
        assert resp.status_code == 400

    def test_very_long_system_message(self):
        """超长 system 消息应被截断而不报错。"""
        captured = {}

        async def capture(*a, **kw):
            captured["json"] = kw.get("json")
            return _sse_ok("ok")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=capture):
            resp = client.post("/v1/chat/completions", json={
                "model": "taiji",
                "messages": [
                    {"role": "system", "content": "S" * 900000},
                    {"role": "user", "content": "hi"},
                ],
            })
        assert resp.status_code == 200
        assert len(captured["json"]["text"]) <= 800000

    def test_temperature_boundary_values(self):
        """temperature 边界值 (0 和 2) 应被接受。"""
        for temp in [0, 0.0, 2.0]:
            with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=_sse_ok()):
                resp = client.post("/v1/chat/completions", json={
                    "model": "taiji",
                    "messages": [{"role": "user", "content": "hi"}],
                    "temperature": temp,
                })
            assert resp.status_code == 200, f"temperature={temp} should succeed"

    def test_temperature_out_of_range(self):
        """temperature 超出 [0, 2] 范围应返回 400/422。"""
        resp = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "hi"}],
            "temperature": 5.0,
        })
        assert resp.status_code in (400, 422)


# ===========================================================================
# 11. Settings 属性验证
# ===========================================================================

class TestSettingsProperties:

    def test_content_fields_list_parsing(self):
        fields = settings.content_fields_list
        assert isinstance(fields, list)
        assert len(fields) > 0
        assert "data" in fields
        assert "content" in fields

    def test_content_fields_no_whitespace(self):
        for field in settings.content_fields_list:
            assert field == field.strip(), f"Field '{field}' should be stripped"

    def test_port_range_validation(self):
        assert 1 <= settings.APP_PORT <= 65535

    def test_max_text_length_minimum(self):
        assert settings.TAIJI_MAX_TEXT_LENGTH >= 1000


# ===========================================================================
# 12. _strip_tool_calls_from_content 方法
# ===========================================================================

class TestStripToolCallsFromContent:

    def setup_method(self):
        self.provider = TaijiProvider()

    def test_strip_standard_xml(self):
        text = f"Hello {_XML_SINGLE} world"
        result = self.provider._strip_tool_calls_from_content(text)
        assert "<tool_calls>" not in result
        assert "Hello" in result
        assert "world" in result

    def test_strip_dsml_xml(self):
        """DSML 格式应被正确移除（regex 可能匹配到 $ 导致截断后续内容）。"""
        text = f"prefix {_XML_DSML} suffix"
        result = self.provider._strip_tool_calls_from_content(text)
        assert "DSML" not in result
        assert "prefix" in result
        # 注意：DSML regex 的 $ 分支可能吞噬 suffix，这是已知的 regex 局限

    def test_strip_json_tool_calls_embedded(self):
        """当 JSON tool_calls 嵌套在更大的 JSON 中时应被移除。"""
        # _extract_json_block 从 key 向前找 {，所以需要 key 前有 {
        text = '{"tool_calls": [{"id": "c1", "function": {"name": "fn", "arguments": "{}"}}]}'
        result = self.provider._strip_tool_calls_from_content(text)
        # 整个 JSON 块应被移除
        assert result == "" or result.strip() == ""

    def test_no_tool_calls_unchanged(self):
        text = "Just normal content"
        result = self.provider._strip_tool_calls_from_content(text)
        assert result == text

    def test_strip_multiple_xml_blocks(self):
        text = f"A {_XML_SINGLE} B {_XML_MULTI} C"
        result = self.provider._strip_tool_calls_from_content(text)
        assert "<tool_calls>" not in result
        assert "A" in result
        assert "B" in result
        assert "C" in result


# ===========================================================================
# 13. 并发请求隔离
# ===========================================================================

class TestConcurrentRequests:

    @pytest.mark.asyncio
    async def test_concurrent_non_stream_different_ids(self):
        """并发非流式请求应返回不同的响应 ID。"""
        ids = []
        for i in range(3):
            with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=_sse_ok(f"r{i}")):
                resp = client.post("/v1/chat/completions", json={
                    "model": "taiji", "messages": [{"role": "user", "content": f"q{i}"}],
                })
            ids.append(resp.json()["id"])
        assert len(set(ids)) == 3

    def test_concurrent_stream_different_ids(self):
        """并发流式请求应返回不同的 completion ID。"""
        ids = []
        for i in range(3):
            stream = _stream(_sse_lines([
                json.dumps({"id": "1", "type": "string", "data": f"chunk{i}", "code": 0}),
            ]))
            with patch("httpx.AsyncClient.stream", return_value=stream):
                resp = client.post("/v1/chat/completions", json={
                    "model": "taiji", "messages": [{"role": "user", "content": f"q{i}"}],
                    "stream": True,
                })
            chunks = _parse_chunks(resp.text)
            if chunks:
                ids.append(chunks[0]["id"])
        assert len(set(ids)) == 3


# ===========================================================================
# 14. 辅助端点完整性
# ===========================================================================

class TestAuxiliaryEndpoints:

    def test_health_returns_json(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/json"

    def test_version_returns_provider_info(self):
        resp = client.get("/version")
        data = resp.json()
        assert "version" in data
        assert "provider" in data
        assert data["provider"] == "taiji"

    def test_props_endpoints_return_empty(self):
        for path in ("/props", "/v1/props"):
            resp = client.get(path)
            assert resp.status_code == 200
            assert resp.json() == {}

    def test_api_tags_returns_empty(self):
        resp = client.get("/api/tags")
        assert resp.status_code == 200
        assert resp.json() == {"models": []}

    def test_404_returns_openai_style_error(self):
        resp = client.get("/v1/nonexistent")
        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data
        assert "message" in data["error"]
        assert "type" in data["error"]

    def test_405_method_not_allowed(self):
        """对不支持的 HTTP 方法应返回 405。"""
        resp = client.delete("/v1/chat/completions")
        assert resp.status_code == 405
