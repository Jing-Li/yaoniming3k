"""
共享 pytest fixtures 和辅助函数。

所有测试文件均可直接使用此处定义的 fixtures，无需重复 import。
"""
import json
from unittest.mock import AsyncMock

import pytest


# ---------------------------------------------------------------------------
# 通用 SSE mock（非流式）
# ---------------------------------------------------------------------------

def make_sse_response(chunks: list[str], *, status_code: int = 200) -> AsyncMock:
    """构造一个非流式 mock 响应，body 为 SSE 格式。

    Args:
        chunks: 每个元素是 JSON data 行的内容部分（已 JSON-encode 的字符串）。
                最后会自动追加 'data: [DONE]'。
        status_code: HTTP 状态码。
    """
    lines = [f'data: {c}' for c in chunks] + ["data: [DONE]", ""]
    mock = AsyncMock()
    mock.status_code = status_code
    mock.text = "\n".join(lines)
    mock.headers = {"content-type": "text/event-stream"}
    return mock


def make_error_response(status_code: int = 500, body: str = "Internal Server Error") -> AsyncMock:
    """构造一个错误 mock 响应。"""
    mock = AsyncMock()
    mock.status_code = status_code
    mock.text = body
    mock.headers = {"content-type": "text/plain"}
    return mock


# ---------------------------------------------------------------------------
# 通用 SSE mock（流式）
# ---------------------------------------------------------------------------

class MockStreamContext:
    """模拟 httpx 流式响应上下文。"""

    def __init__(self, lines: list[str], *, status_code: int = 200):
        self._lines = lines
        self.status_code = status_code

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def aiter_lines(self):
        for line in self._lines:
            yield line

    async def aread(self):
        return b""


def make_stream_mock(lines: list[str], *, status_code: int = 200) -> MockStreamContext:
    """构造流式 mock。lines 是完整的 SSE 行（含 'data:' 前缀）。"""
    return MockStreamContext(lines, status_code=status_code)


def make_sse_lines(chunks: list[str]) -> list[str]:
    """将 JSON 字符串列表转换为标准 SSE 行列表（含 data: 前缀和 [DONE]）。"""
    return [f'data: {c}' for c in chunks] + ["data: [DONE]"]


# ---------------------------------------------------------------------------
# SSE 解析辅助
# ---------------------------------------------------------------------------

def parse_sse_chunks(response_text: str) -> list[dict]:
    """从 SSE 响应文本中解析出 chunk 字典列表（不含 [DONE]）。"""
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
# 常用 fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sse_ok_response():
    """标准成功响应（单条 SSE）。"""
    return make_sse_response(['{"id":"1","type":"string","data":"Hello","code":0}'])


@pytest.fixture
def sse_multi_chunk():
    """多段 SSE 响应。"""
    return make_sse_response([
        '{"id":"1","type":"string","data":"Hello","code":0}',
        '{"id":"1","type":"string","data":" world","code":0}',
    ])


@pytest.fixture
def sse_with_think():
    """包含 <think> 标签的响应。"""
    return make_sse_response([
        '{"id":"1","type":"string","data":"<think>推理过程</think>最终答案","code":0}',
    ])


@pytest.fixture
def sse_with_token_info():
    """包含 token 用量信息的响应。"""
    return make_sse_response([
        '{"id":"1","type":"string","data":"Hello","code":0}',
        '{"type":"object","data":{"promptTokens":10,"completionTokens":5,"useTokens":15,"contextTokens":100}}',
    ])


@pytest.fixture
def sse_business_error():
    """taiji 业务错误（HTTP 200 但 code != 0）。"""
    return make_sse_response([
        '{"id":"1","type":"string","data":"{\\"err\\":\\"session expired\\",\\"code\\":-1}","code":0}',
    ])


@pytest.fixture
def error_429():
    """429 Rate limit 错误。"""
    return make_error_response(429, "Rate limit exceeded")


@pytest.fixture
def stream_ok():
    """标准流式成功响应。"""
    return make_stream_mock(make_sse_lines([
        '{"id":"1","type":"string","data":"Hello","code":0}',
        '{"id":"1","type":"string","data":"!","code":0}',
    ]))


@pytest.fixture
def stream_with_token_info():
    """包含 token 用量的流式响应。"""
    return make_stream_mock(make_sse_lines([
        '{"id":"1","type":"string","data":"Hello","code":0}',
        '{"type":"object","data":{"promptTokens":8,"completionTokens":3,"useTokens":11}}',
    ]))
