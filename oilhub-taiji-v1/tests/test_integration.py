"""
集成测试：真实调用 taiji API，验证端到端链路。

默认使用 config.py 中的配置值；也可通过环境变量覆盖：
    export TAIJI_API_KEY="your-jwt-token"
    export TAIJI_SESSION_COOKIE="your-cookie"

注意：这些测试会消耗真实的 API 额度，且响应时间可能较长（单次 3~60s）。
"""
import json
import pytest
from fastapi.testclient import TestClient

from openai_provider.main import app
from openai_provider.config import settings

client = TestClient(app)

# 跳过条件：config 中未配置 API key 时跳过集成测试
pytestmark = pytest.mark.skipif(
    not settings.TAIJI_API_KEY,
    reason="TAIJI_API_KEY not configured, skipping integration tests",
)


def test_integration_short_chat():
    """短文本对话端到端验证。"""
    payload = {
        "model": "taiji",
        "messages": [{"role": "user", "content": "你好，请简单自我介绍一下"}],
    }
    resp = client.post("/v1/chat/completions", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    assert data["object"] == "chat.completion"
    assert data["model"] == "taiji"
    assert len(data["choices"]) == 1
    assert data["choices"][0]["message"]["role"] == "assistant"
    content = data["choices"][0]["message"]["content"]
    assert len(content) > 0
    # 不应包含 think 标签（如果模型返回了思考过程）
    assert "<think>" not in content
    assert data["usage"]["prompt_tokens"] > 0
    assert data["usage"]["completion_tokens"] > 0
    print(f"\n[Integration] Short chat response: {content[:100]}...")


def test_integration_with_system_message():
    """带 system 消息的多轮对话。"""
    payload = {
        "model": "taiji",
        "messages": [
            {"role": "system", "content": "你是一个专业的 Python 工程师"},
            {"role": "user", "content": "list 和 tuple 有什么区别？用一句话回答"},
        ],
    }
    resp = client.post("/v1/chat/completions", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    assert len(content) > 0
    assert "<think>" not in content
    print(f"\n[Integration] System msg response: {content[:100]}...")


def test_integration_long_text_truncation():
    """超长文本应被截断到 800000 字符以内，且仍能成功返回。"""
    # Note: Testing with actual 800K+ text against real API would timeout.
    # We verify truncation logic in unit tests; here we just ensure the
    # endpoint handles a reasonable payload without errors.
    payload = {
        "model": "taiji",
        "messages": [{"role": "user", "content": "Hello" * 100}],
    }
    resp = client.post("/v1/chat/completions", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    assert len(content) > 0
    assert "<think>" not in content
    print(f"\n[Integration] Long text response: {content[:100]}...")


def test_integration_response_format_compliance():
    """验证返回格式严格符合 OpenAI Chat Completion 规范。"""
    payload = {
        "model": "taiji",
        "messages": [{"role": "user", "content": "1+1等于几？"}],
    }
    resp = client.post("/v1/chat/completions", json=payload)

    assert resp.status_code == 200
    data = resp.json()

    # 必填字段检查
    required_fields = {"id", "object", "created", "model", "choices", "usage"}
    assert required_fields.issubset(data.keys())

    choice = data["choices"][0]
    assert "index" in choice
    assert "message" in choice
    assert "finish_reason" in choice
    assert choice["message"]["role"] == "assistant"
    assert "content" in choice["message"]

    usage = data["usage"]
    assert "prompt_tokens" in usage
    assert "completion_tokens" in usage
    assert "total_tokens" in usage
    assert usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"]

    print(f"\n[Integration] Format compliance OK. Response: {data['choices'][0]['message']['content'][:80]}...")


def test_integration_streaming():
    """流式响应端到端验证。"""
    payload = {
        "model": "taiji",
        "messages": [{"role": "user", "content": "你好"}],
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

    assert len(chunks) >= 2
    assert chunks[0]["object"] == "chat.completion.chunk"
    assert chunks[0]["choices"][0]["delta"]["role"] == "assistant"
    assert chunks[-2]["choices"][0]["finish_reason"] == "stop"
    assert chunks[-1] == "[DONE]"

    # 拼接所有 content 应得到非空有意义的回答
    contents = []
    for chunk in chunks[:-2]:
        content = chunk["choices"][0]["delta"].get("content")
        if content:
            contents.append(content)
    full_content = "".join(contents)
    assert len(full_content) > 0
    assert "<think>" not in full_content
    print(f"\n[Integration] Streaming response: {full_content[:100]}...")
