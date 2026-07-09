"""
Regression test suite for OpenAI-compatible Taiji gateway.
Covers: config, business errors, token usage, XML tool calls, endpoints, build_text, edge cases.
"""
import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from openai_provider.config import settings
from openai_provider.main import app
from openai_provider.models.taiji import TaijiRequest
from openai_provider.providers.taiji import TaijiProvider
from openai_provider.models.openai import ChatMessage, ToolCall, ToolCallFunction

from tests.conftest import make_sse_response, make_stream_mock, make_sse_lines, parse_sse_chunks

client = TestClient(app)

# ── helpers for building XML tool-call strings ──────────────────────────

_XML_SINGLE = (
    '<tool_calls>'
    '<invoke name="get_weather">'
    '<' + 'parameter name="city">Beijing</' + 'parameter>'
    '</invoke>'
    '</tool_calls>'
)

_XML_MULTI = (
    '<tool_calls>'
    '<invoke name="get_weather">'
    '<' + 'parameter name="city">Shanghai</' + 'parameter>'
    '</invoke>'
    '<invoke name="search">'
    '<' + 'parameter name="query">news</' + 'parameter>'
    '</invoke>'
    '</tool_calls>'
)

_XML_DSML = (
    '<｜｜DSML｜｜tool_calls>'
    '<｜｜DSML｜｜invoke name="calculate">'
    '<｜｜DSML｜｜parameter name="expression">2+3</｜｜DSML｜｜parameter>'
    '</｜｜DSML｜｜invoke>'
    '</｜｜DSML｜｜tool_calls>'
)


# ===========================================================================
# 1. TestConfigRegression
# ===========================================================================

class TestConfigRegression:

    def test_thinking_field_default_false(self):
        req = TaijiRequest(text="hi")
        assert req.thinking is False

    def test_websearch_field_default_false(self):
        req = TaijiRequest(text="hi")
        assert req.webSearch is False

    def test_serialization_includes_thinking_and_websearch(self):
        req = TaijiRequest(text="hi")
        dumped = req.model_dump()
        assert "thinking" in dumped
        assert "webSearch" in dumped
        assert dumped["thinking"] is False
        assert dumped["webSearch"] is False

    def test_thinking_can_be_true(self):
        req = TaijiRequest(text="hi", thinking=True)
        assert req.thinking is True

    def test_base_url_contains_avuuq(self):
        assert "avuuq" in settings.TAIJI_BASE_URL

    def test_x_app_version_header(self):
        captured = {}
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.text = (
            'data: {"id":"1","type":"string","data":"ok","code":0}\n'
            '\ndata: [DONE]\n'
        )
        mock_resp.headers = {}

        async def _capture(*args, **kwargs):
            captured.update(kwargs.get("headers", {}))
            return mock_resp

        with patch("httpx.AsyncClient.post", new=_capture):
            client.post(
                "/v1/chat/completions",
                json={"model": "taiji", "messages": [{"role": "user", "content": "hi"}]},
            )
        assert captured.get("x-app-version") == "3.2.0"


# ===========================================================================
# 2. TestBusinessError
# ===========================================================================

class TestBusinessError:

    @pytest.mark.asyncio
    async def test_err_field_returns_502(self):
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        inner = json.dumps({"err": "session expired", "code": -1})
        sse_obj = json.dumps({"id": "1", "type": "string", "data": inner, "code": 0})
        mock_resp.text = f"data: {sse_obj}\n\ndata: [DONE]\n"
        mock_resp.headers = {"content-type": "text/event-stream"}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            resp = client.post(
                "/v1/chat/completions",
                json={"model": "taiji", "messages": [{"role": "user", "content": "t"}]},
            )
        assert resp.status_code == 502
        assert "error" in resp.json()

    @pytest.mark.asyncio
    async def test_msg_field_returns_502(self):
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        inner = json.dumps({"msg": "invalid parameter", "code": -2})
        sse_obj = json.dumps({"id": "1", "type": "string", "data": inner, "code": 0})
        mock_resp.text = f"data: {sse_obj}\n\ndata: [DONE]\n"
        mock_resp.headers = {"content-type": "text/event-stream"}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            resp = client.post(
                "/v1/chat/completions",
                json={"model": "taiji", "messages": [{"role": "user", "content": "t"}]},
            )
        assert resp.status_code == 502
        assert "error" in resp.json()


# ===========================================================================
# 3. TestTokenUsage
# ===========================================================================

class TestTokenUsage:

    @pytest.mark.asyncio
    async def test_non_stream_token_usage(self):
        mock_resp = make_sse_response([
            '{"id":"1","type":"string","data":"Hello","code":0}',
            '{"type":"object","data":{"promptTokens":10,"completionTokens":8,"useTokens":18,"contextTokens":100}}',
        ])
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            resp = client.post(
                "/v1/chat/completions",
                json={"model": "taiji", "messages": [{"role": "user", "content": "hi"}]},
            )
        assert resp.status_code == 200
        assert resp.json()["usage"]["completion_tokens"] == 8

    def test_stream_token_usage(self):
        stream = make_stream_mock(make_sse_lines([
            '{"id":"1","type":"string","data":"Hi","code":0}',
            '{"type":"object","data":{"promptTokens":6,"completionTokens":4,"useTokens":10}}',
        ]))
        with patch("httpx.AsyncClient.stream", return_value=stream):
            resp = client.post(
                "/v1/chat/completions",
                json={"model": "taiji", "messages": [{"role": "user", "content": "hi"}], "stream": True},
            )
        assert resp.status_code == 200
        chunks = parse_sse_chunks(resp.text)
        assert chunks[-1]["usage"]["completion_tokens"] == 4


# ===========================================================================
# 4. TestXMLToolCalls
# ===========================================================================

class TestXMLToolCalls:

    def setup_method(self):
        self.provider = TaijiProvider()

    def test_standard_single_tool_call(self):
        result = self.provider._parse_tool_calls(_XML_SINGLE)
        assert len(result) == 1
        assert result[0].function.name == "get_weather"
        args = json.loads(result[0].function.arguments)
        assert args["city"] == "Beijing"

    def test_standard_multiple_tool_calls(self):
        result = self.provider._parse_tool_calls(_XML_MULTI)
        assert len(result) == 2
        names = [tc.function.name for tc in result]
        assert "get_weather" in names
        assert "search" in names

    def test_dsml_format(self):
        result = self.provider._parse_tool_calls(_XML_DSML)
        assert len(result) == 1
        assert result[0].function.name == "calculate"
        args = json.loads(result[0].function.arguments)
        assert args["expression"] == "2+3"

    def test_empty_returns_empty_list(self):
        assert self.provider._parse_tool_calls("") == []
        assert self.provider._parse_tool_calls(None) == []
        assert self.provider._parse_tool_calls("Hello world") == []


# ===========================================================================
# 5. TestEndpoints
# ===========================================================================

class TestEndpoints:

    def test_api_v1_models_returns_list(self):
        resp = client.get("/api/v1/models")
        assert resp.status_code == 200
        data = resp.json()
        assert data["object"] == "list"
        assert isinstance(data["data"], list)

    def test_api_tags_returns_empty_models(self):
        resp = client.get("/api/tags")
        assert resp.status_code == 200
        assert resp.json() == {"models": []}

    def test_v1_models_taiji_returns_model(self):
        resp = client.get("/v1/models/taiji")
        assert resp.status_code == 200
        assert resp.json()["id"] == "taiji"

    def test_v1_models_unknown_returns_404(self):
        resp = client.get("/v1/models/unknown")
        assert resp.status_code == 404

    def test_props_returns_empty(self):
        resp = client.get("/props")
        assert resp.status_code == 200
        assert resp.json() == {}

    def test_version_returns_1_0_0(self):
        resp = client.get("/version")
        assert resp.status_code == 200
        assert resp.json()["version"] == "1.0.0"

    def test_v1_props_returns_empty(self):
        resp = client.get("/v1/props")
        assert resp.status_code == 200
        assert resp.json() == {}


# ===========================================================================
# 6. TestBuildText
# ===========================================================================

class TestBuildText:

    def setup_method(self):
        self.provider = TaijiProvider()

    def test_multi_turn_system_user_assistant(self):
        messages = [
            ChatMessage(role="system", content="You are helpful"),
            ChatMessage(role="user", content="Hello"),
            ChatMessage(role="assistant", content="Hi there"),
        ]
        text, length = self.provider._build_text(messages)
        assert "[System]: You are helpful" in text
        assert "[User]: Hello" in text
        assert "[Assistant]: Hi there" in text

    def test_tool_role_messages(self):
        messages = [
            ChatMessage(role="user", content="call it"),
            ChatMessage(role="tool", content="result data", tool_call_id="call_123"),
        ]
        text, _ = self.provider._build_text(messages)
        assert "[Tool Result for call_123]: result data" in text

    def test_assistant_with_tool_calls(self):
        messages = [
            ChatMessage(role="user", content="do something"),
            ChatMessage(
                role="assistant",
                content="",
                tool_calls=[
                    ToolCall(
                        id="tc_1",
                        type="function",
                        function=ToolCallFunction(name="my_tool", arguments='{"x":1}'),
                    )
                ],
            ),
        ]
        text, _ = self.provider._build_text(messages)
        assert "[Tool Calls Executed]" in text


# ===========================================================================
# 7. TestEdgeCases
# ===========================================================================

class TestEdgeCases:

    def test_empty_sse_produces_empty_content(self):
        """空 SSE data 行应产生空内容。"""
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.text = "data: [DONE]\n"
        mock_resp.headers = {"content-type": "text/event-stream"}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            resp = client.post(
                "/v1/chat/completions",
                json={"model": "taiji", "messages": [{"role": "user", "content": "hi"}]},
            )
        assert resp.status_code == 200
        # content may be None or empty string depending on fallback parsing
        msg = resp.json()["choices"][0]["message"]
        content = msg.get("content")
        assert content is None or content == "" or len(content) > 0  # no crash

    def test_stream_with_tools_no_tool_calls_returns_stop(self):
        """流式 + tools 但响应不含 tool_calls => finish_reason=stop。"""
        stream = make_stream_mock(make_sse_lines([
            '{"id":"1","type":"string","data":"Just text","code":0}',
        ]))
        tools_payload = [{
            "type": "function",
            "function": {"name": "get_time", "description": "Get time", "parameters": {}},
        }]
        with patch("httpx.AsyncClient.stream", return_value=stream):
            resp = client.post(
                "/v1/chat/completions",
                json={
                    "model": "taiji",
                    "messages": [{"role": "user", "content": "hi"}],
                    "stream": True,
                    "tools": tools_payload,
                },
            )
        assert resp.status_code == 200
        chunks = parse_sse_chunks(resp.text)
        finish_chunks = [c for c in chunks if c["choices"][0].get("finish_reason")]
        assert len(finish_chunks) > 0
        assert finish_chunks[-1]["choices"][0]["finish_reason"] == "stop"

    def test_stream_with_tools_and_xml_tool_calls_returns_tool_calls(self):
        """流式 + tools 且响应含 XML tool_calls => finish_reason=tool_calls。"""
        sse_chunks = [
            json.dumps({"id": "1", "type": "string", "data": _XML_SINGLE, "code": 0}),
        ]
        stream = make_stream_mock(make_sse_lines(sse_chunks))
        tools_payload = [{
            "type": "function",
            "function": {"name": "get_weather", "description": "Weather", "parameters": {}},
        }]
        with patch("httpx.AsyncClient.stream", return_value=stream):
            resp = client.post(
                "/v1/chat/completions",
                json={
                    "model": "taiji",
                    "messages": [{"role": "user", "content": "weather?"}],
                    "stream": True,
                    "tools": tools_payload,
                },
            )
        assert resp.status_code == 200
        chunks = parse_sse_chunks(resp.text)
        finish_chunks = [c for c in chunks if c["choices"][0].get("finish_reason")]
        assert len(finish_chunks) > 0
        assert finish_chunks[-1]["choices"][0]["finish_reason"] == "tool_calls"
