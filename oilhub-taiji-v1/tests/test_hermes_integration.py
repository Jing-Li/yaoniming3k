"""Hermes Agent integration tests.

These tests simulate Hermes Agent's typical calling patterns against the taiji provider,
validating response structure, delta formatting, finish_reason timing, and tool_call ID correlation.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from openai_provider.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

def make_stream_mock(lines):
    """Create a mock stream context with given SSE lines."""
    class MockStreamContext:
        def __init__(self):
            self.status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def aiter_lines(self):
            for line in lines:
                yield line

        async def aread(self):
            return b""

    return MockStreamContext()


def parse_sse_chunks(response_text):
    """Parse SSE response text into list of chunk dicts."""
    chunks = []
    for line in response_text.split("\n"):
        line = line.strip()
        if line.startswith("data:"):
            data = line[5:].strip()
            if data == "[DONE]":
                break
            if data:
                chunks.append(json.loads(data))
    return chunks


# ---------------------------------------------------------------------------
# Test 1: Streaming + tool_calls with proper delta reconstruction
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hermes_streaming_tool_calls_delta():
    """Hermes expects incremental tool_calls deltas that can be reconstructed."""
    stream_lines = [
        'data: {"id":"1","type":"string","data":"{\\"tool_calls\\": [{\\"id\\": \\"call_abc123\\", \\"type\\": \\"function\\", \\"function\\": {\\"name\\": \\"get_weather\\", \\"arguments\\": \\"{\\\\\\"location\\\\\\": \\\\\\\"NYC\\\\\\"}\\"}}]}","code":0}',
        'data: [DONE]',
    ]

    with patch("httpx.AsyncClient.stream", return_value=make_stream_mock(stream_lines)):
        payload = {
            "model": "taiji",
            "messages": [{"role": "user", "content": "What's the weather in NYC?"}],
            "tools": [{
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "parameters": {"type": "object", "properties": {"location": {"type": "string"}}}
                }
            }],
            "stream": True,
        }
        resp = client.post("/v1/chat/completions", json=payload)

    assert resp.status_code == 200
    chunks = parse_sse_chunks(resp.text)

    # Should have at least one chunk with tool_calls and a finish chunk
    tool_call_chunks = [c for c in chunks if "tool_calls" in c["choices"][0].get("delta", {})]
    finish_chunks = [c for c in chunks if c["choices"][0].get("finish_reason") == "tool_calls"]

    assert len(tool_call_chunks) > 0, "Should emit tool_calls delta"
    assert len(finish_chunks) > 0, "Should emit finish_reason=tool_calls"

    # Verify tool_call structure
    tc = tool_call_chunks[0]["choices"][0]["delta"]["tool_calls"][0]
    assert tc["id"] == "call_abc123"
    assert tc["type"] == "function"
    assert tc["function"]["name"] == "get_weather"


# ---------------------------------------------------------------------------
# Test 2: Multi-turn conversation with tool result round-trip
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hermes_multi_turn_tool_roundtrip():
    """Hermes sends: user -> assistant(tool_calls) -> tool(result) -> assistant(final answer)."""

    # First turn: model returns tool_calls
    stream_lines_turn1 = [
        'data: {"id":"1","type":"string","data":"{\\"tool_calls\\": [{\\"id\\": \\"call_xyz\\", \\"type\\": \\"function\\", \\"function\\": {\\"name\\": \\"search\\", \\"arguments\\": \\"{\\\\\\"query\\\\\\": \\\\\\\"test\\\\\\"}\\"}}]}","code":0}',
        'data: [DONE]',
    ]

    with patch("httpx.AsyncClient.stream", return_value=make_stream_mock(stream_lines_turn1)):
        resp1 = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "Search for something"}],
            "tools": [{"type": "function", "function": {"name": "search", "parameters": {}}}],
            "stream": True,
        })

    assert resp1.status_code == 200
    chunks1 = parse_sse_chunks(resp1.text)
    tc_chunks = [c for c in chunks1 if "tool_calls" in c["choices"][0].get("delta", {})]
    assert len(tc_chunks) > 0
    tool_call_id = tc_chunks[0]["choices"][0]["delta"]["tool_calls"][0]["id"]

    # Second turn: send tool result back
    stream_lines_turn2 = [
        'data: {"id":"2","type":"string","data":"Here is the search result.","code":0}',
        'data: [DONE]',
    ]

    with patch("httpx.AsyncClient.stream", return_value=make_stream_mock(stream_lines_turn2)):
        resp2 = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [
                {"role": "user", "content": "Search for something"},
                {"role": "assistant", "tool_calls": [{"id": tool_call_id, "type": "function", "function": {"name": "search", "arguments": "{}"}}]},
                {"role": "tool", "tool_call_id": tool_call_id, "content": "Search results here"},
            ],
            "stream": True,
        })

    assert resp2.status_code == 200
    chunks2 = parse_sse_chunks(resp2.text)
    content_chunks = [c for c in chunks2 if "content" in c["choices"][0].get("delta", {})]
    assert len(content_chunks) > 0, "Final answer should contain content"


# ---------------------------------------------------------------------------
# Test 3: Tool call ID consistency
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hermes_tool_call_id_consistency():
    """Tool call IDs in response must match what Hermes sent in subsequent turns."""
    stream_lines = [
        'data: {"id":"1","type":"string","data":"{\\"tool_calls\\": [{\\"id\\": \\"call_consistent\\", \\"type\\": \\"function\\", \\"function\\": {\\"name\\": \\"fn\\", \\"arguments\\": \\"{}\\"}}]}","code":0}',
        'data: [DONE]',
    ]

    with patch("httpx.AsyncClient.stream", return_value=make_stream_mock(stream_lines)):
        resp = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "test"}],
            "tools": [{"type": "function", "function": {"name": "fn", "parameters": {}}}],
            "stream": True,
        })

    chunks = parse_sse_chunks(resp.text)
    tc_chunks = [c for c in chunks if "tool_calls" in c["choices"][0].get("delta", {})]
    assert len(tc_chunks) > 0

    # The ID should be preserved exactly
    returned_id = tc_chunks[0]["choices"][0]["delta"]["tool_calls"][0]["id"]
    assert returned_id == "call_consistent"


# ---------------------------------------------------------------------------
# Test 4: SSE format compliance
# ---------------------------------------------------------------------------

def test_hermes_sse_format_compliance():
    """SSE format must comply: data: prefix, [DONE] marker."""
    stream_lines = [
        'data: {"id":"1","type":"string","data":"Hello","code":0}',
        'data: [DONE]',
    ]

    with patch("httpx.AsyncClient.stream", return_value=make_stream_mock(stream_lines)):
        resp = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "test"}],
            "stream": True,
        })

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "text/event-stream; charset=utf-8"

    # Verify SSE format: each line starts with "data:" and ends with [DONE]
    lines = resp.text.strip().split("\n")
    data_lines = [l for l in lines if l.strip().startswith("data:")]
    assert len(data_lines) > 0, "Should have data: prefixed lines"
    assert "[DONE]" in resp.text, "Should end with [DONE] marker"


# ---------------------------------------------------------------------------
# Test 5: Empty tool result handling
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hermes_empty_tool_result():
    """Hermes may send empty tool results; provider should handle gracefully."""
    stream_lines = [
        'data: {"id":"1","type":"string","data":"The tool returned no results.","code":0}',
        'data: [DONE]',
    ]

    with patch("httpx.AsyncClient.stream", return_value=make_stream_mock(stream_lines)):
        resp = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [
                {"role": "user", "content": "Search"},
                {"role": "assistant", "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "search", "arguments": "{}"}}]},
                {"role": "tool", "tool_call_id": "call_1", "content": ""},  # Empty tool result
            ],
            "stream": True,
        })

    assert resp.status_code == 200
    chunks = parse_sse_chunks(resp.text)
    assert len(chunks) > 0


# ---------------------------------------------------------------------------
# Test 6: Tool error handling
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hermes_tool_error_in_response():
    """When tool execution fails, model should explain the error to user."""
    stream_lines = [
        'data: {"id":"1","type":"string","data":"The tool encountered an error: connection timeout.","code":0}',
        'data: [DONE]',
    ]

    with patch("httpx.AsyncClient.stream", return_value=make_stream_mock(stream_lines)):
        resp = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [
                {"role": "user", "content": "Fetch data"},
                {"role": "assistant", "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "fetch", "arguments": "{}"}}]},
                {"role": "tool", "tool_call_id": "call_1", "content": "Error: connection timeout"},
            ],
            "stream": True,
        })

    assert resp.status_code == 200
    chunks = parse_sse_chunks(resp.text)
    content_chunks = [c for c in chunks if "content" in c["choices"][0].get("delta", {})]
    assert len(content_chunks) > 0
