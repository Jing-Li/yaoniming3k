"""
E2E 测试共享 fixtures。

所有 E2E 测试对运行中真实服务（默认 localhost:8199）发起 HTTP 请求。
通过环境变量 E2E_BASE_URL 可覆盖地址。

前置条件：
  1. 服务已通过 start.sh dev --port 8199 启动
  2. .env 中配置了 TAIJI_API_KEY 和 TAIJI_SESSION_COOKIE
  3. pip install httpx pytest pytest-asyncio
"""
import os
import json
import time
from typing import Any

import httpx
import pytest

BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:8199")

# 重试配置：真实 API 可能因限流/超时返回 502
MAX_RETRIES = 2
RETRY_DELAY = 3.0  # seconds


def _is_service_alive() -> bool:
    """检测服务是否在线。"""
    try:
        r = httpx.get(f"{BASE_URL}/health", timeout=3.0)
        return r.status_code == 200
    except Exception:
        return False


# 跳过条件：服务未启动或无法连通
pytestmark = pytest.mark.skipif(
    not os.getenv("E2E_FORCE", "") and not _is_service_alive(),
    reason=f"Service not reachable at {BASE_URL}. Start with: bash start.sh dev --port 8199",
)


# ---------------------------------------------------------------------------
# Retrying HTTP Client
# ---------------------------------------------------------------------------

class RetryingClient:
    """包装 httpx.Client，对 502 响应自动重试。"""

    def __init__(self, base_url: str, timeout: float = 120.0):
        self._client = httpx.Client(base_url=base_url, timeout=timeout)

    def _retry(self, method: str, *args: Any, **kwargs: Any) -> httpx.Response:
        for attempt in range(MAX_RETRIES + 1):
            resp = getattr(self._client, method)(*args, **kwargs)
            if resp.status_code != 502 or attempt == MAX_RETRIES:
                return resp
            time.sleep(RETRY_DELAY)
        return resp  # type: ignore

    def get(self, *args: Any, **kwargs: Any) -> httpx.Response:
        return self._retry("get", *args, **kwargs)

    def post(self, *args: Any, **kwargs: Any) -> httpx.Response:
        return self._retry("post", *args, **kwargs)

    def options(self, *args: Any, **kwargs: Any) -> httpx.Response:
        return self._retry("options", *args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> httpx.Response:
        return self._retry("delete", *args, **kwargs)

    def close(self) -> None:
        self._client.close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def base_url() -> str:
    """返回 E2E 服务地址。"""
    return BASE_URL


@pytest.fixture(scope="session")
def client() -> RetryingClient:
    """带重试的同步 HTTP 客户端（session 级复用）。"""
    return RetryingClient(base_url=BASE_URL, timeout=120.0)


@pytest.fixture
def chat_payload() -> dict:
    """最小化 chat completion 请求体。"""
    return {
        "model": "taiji",
        "messages": [{"role": "user", "content": "你好，用一句话回复我"}],
    }


@pytest.fixture
def stream_payload(chat_payload) -> dict:
    """流式 chat completion 请求体。"""
    return {**chat_payload, "stream": True}


def parse_sse_chunks(text: str) -> list[dict]:
    """从 SSE 响应文本中解析 chunk 字典列表（不含 [DONE]）。"""
    chunks = []
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("data:"):
            data = line[5:].strip()
            if data == "[DONE]":
                break
            if data:
                try:
                    chunks.append(json.loads(data))
                except json.JSONDecodeError:
                    continue
    return chunks
