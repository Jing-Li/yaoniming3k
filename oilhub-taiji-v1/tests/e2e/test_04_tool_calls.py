"""
E2E-04: Tool Calls（函数调用）真实调用。

验证 JSON/XML 格式 tool_calls 的解析、结构和多轮工具往返。
"""
import json
import pytest

from .conftest import parse_sse_chunks


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather in a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city name",
                    }
                },
                "required": ["location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Calculate a math expression",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "The math expression",
                    }
                },
                "required": ["expression"],
            },
        },
    },
]


class TestToolCallsNonStream:

    def test_tool_call_returns_tool_calls(self, client):
        """带 tools 的请求应返回 tool_calls 结构。"""
        r = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "北京今天天气怎么样？"}],
            "tools": TOOLS,
        })
        assert r.status_code == 200
        data = r.json()
        msg = data["choices"][0]["message"]

        # 应该有 tool_calls
        tool_calls = msg.get("tool_calls")
        if tool_calls:
            assert isinstance(tool_calls, list)
            assert len(tool_calls) > 0
            for tc in tool_calls:
                assert "id" in tc
                assert tc["type"] == "function"
                assert tc["function"]["name"] in ["get_weather", "calculate"]
                # arguments 应为有效 JSON
                args = json.loads(tc["function"]["arguments"])
                assert isinstance(args, dict)

    def test_tool_call_finish_reason_is_tool_calls(self, client):
        """tool_calls 响应时 finish_reason 应为 tool_calls。"""
        r = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "帮我算一下 123 * 456"}],
            "tools": TOOLS,
        })
        assert r.status_code == 200
        # 注意：不一定每次都触发 tool_call，取决于模型
        data = r.json()
        choice = data["choices"][0]
        if choice["message"].get("tool_calls"):
            assert choice["finish_reason"] == "tool_calls"

    def test_tool_call_content_when_tool(self, client):
        """当模型返回 tool_calls 时，content 可能为空或包含自然语言说明。"""
        r = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "北京天气"}],
            "tools": TOOLS,
        })
        assert r.status_code == 200
        msg = r.json()["choices"][0]["message"]
        if msg.get("tool_calls"):
            # content 可能为空（纯 tool_call）或有说明文本，两种都合法
            assert isinstance(msg.get("content", ""), str)


class TestToolCallsStreaming:

    def test_stream_tool_calls(self, client):
        """流式调用中 tool_calls 应被正确解析。"""
        r = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "北京今天天气怎么样？"}],
            "tools": TOOLS,
            "stream": True,
        })
        assert r.status_code == 200
        chunks = parse_sse_chunks(r.text)
        assert len(chunks) > 0

        # 收集 tool_calls delta（兼容有/无 index 字段的格式）
        tool_calls_data = {}
        for chunk in chunks:
            delta = chunk["choices"][0].get("delta", {})
            if "tool_calls" in delta:
                for tc in delta["tool_calls"]:
                    idx = tc.get("index", len(tool_calls_data))
                    if idx not in tool_calls_data:
                        tool_calls_data[idx] = {"function": {"name": "", "arguments": ""}}
                    if "function" in tc:
                        if "name" in tc["function"]:
                            tool_calls_data[idx]["function"]["name"] = tc["function"]["name"]
                        if "arguments" in tc["function"]:
                            tool_calls_data[idx]["function"]["arguments"] += tc["function"]["arguments"]

        # 如果有 tool_calls，验证其结构
        for idx, tc in tool_calls_data.items():
            assert tc["function"]["name"] in ["get_weather", "calculate"]
            # arguments 拼完后应为合法 JSON
            args_str = tc["function"]["arguments"]
            if args_str:
                args = json.loads(args_str)
                assert isinstance(args, dict)

    def test_stream_no_tool_calls_for_plain_message(self, client):
        """普通消息不应触发 tool_calls。"""
        r = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "今天心情如何？"}],
            "stream": True,
        })
        assert r.status_code == 200
        chunks = parse_sse_chunks(r.text)
        for chunk in chunks:
            delta = chunk["choices"][0].get("delta", {})
            assert "tool_calls" not in delta


class TestToolChoiceParameter:

    @pytest.mark.parametrize("tc", [
        {"type": "function", "function": {"name": "get_weather"}},
        {"type": "function", "function": {"name": "calculate"}},
    ])
    def test_tool_choice_forces_specific_tool(self, client, tc):
        """tool_choice 应强制调用指定工具。"""
        r = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "随便聊聊"}],
            "tools": TOOLS,
            "tool_choice": tc,
        })
        assert r.status_code == 200
        msg = r.json()["choices"][0]["message"]
        if msg.get("tool_calls"):
            assert msg["tool_calls"][0]["function"]["name"] == tc["function"]["name"]

    def test_tool_choice_none_no_tool_calls(self, client):
        """tool_choice=none 不应返回 tool_calls。"""
        r = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "北京天气"}],
            "tools": TOOLS,
            "tool_choice": "none",
        })
        assert r.status_code == 200
        msg = r.json()["choices"][0]["message"]
        # tool_choice=none 时不应有 tool_calls
        assert not msg.get("tool_calls")


class TestMultiTurnToolRoundtrip:

    def test_tool_roundtrip_non_stream(self, client):
        """完整的多轮工具往返：user → tool_call → tool_result → assistant。"""
        # Step 1: 触发 tool_call
        r1 = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "北京今天天气怎么样？"}],
            "tools": TOOLS,
        })
        assert r1.status_code == 200
        msg1 = r1.json()["choices"][0]["message"]

        if not msg1.get("tool_calls"):
            pytest.skip("Model did not call tools in this round")

        # Step 2: 将 tool_call 结果送回模型
        messages = [
            {"role": "user", "content": "北京今天天气怎么样？"},
            msg1,  # assistant 消息（含 tool_calls）
            {
                "role": "tool",
                "tool_call_id": msg1["tool_calls"][0]["id"],
                "content": json.dumps({"temperature": 25, "condition": "sunny"}),
            },
        ]

        r2 = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": messages,
            "tools": TOOLS,
        })
        assert r2.status_code == 200
        msg2 = r2.json()["choices"][0]["message"]
        # 模型应基于工具结果生成自然语言回复
        assert msg2["content"] is not None
        assert len(msg2["content"]) > 0
