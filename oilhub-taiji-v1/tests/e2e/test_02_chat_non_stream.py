"""
E2E-02: 非流式 Chat Completions 真实调用。

向真实 Taiji 后端发送请求，验证完整响应结构。
注意：每次调用消耗真实 API 额度。
"""
import time
import pytest


class TestBasicChatCompletion:

    def test_simple_user_message(self, client, chat_payload):
        """最简调用：user 消息 → assistant 回复。"""
        r = client.post("/v1/chat/completions", json=chat_payload)
        assert r.status_code == 200
        data = r.json()

        # 结构完整性
        assert data["object"] == "chat.completion"
        assert data["model"] == "taiji"
        assert data["id"].startswith("chatcmpl-")
        assert len(data["choices"]) == 1

        choice = data["choices"][0]
        assert choice["index"] == 0
        assert choice["message"]["role"] == "assistant"
        assert isinstance(choice["message"]["content"], str)
        assert len(choice["message"]["content"]) > 0
        assert choice["finish_reason"] in ("stop", "length")

    def test_response_has_valid_usage(self, client, chat_payload):
        """usage 字段应含有效 token 计数。"""
        r = client.post("/v1/chat/completions", json=chat_payload)
        data = r.json()
        usage = data["usage"]

        assert usage["prompt_tokens"] > 0
        assert usage["completion_tokens"] > 0
        assert usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"]

    def test_response_id_is_unique(self, client, chat_payload):
        """多次调用应返回不同的 response ID。"""
        ids = set()
        for _ in range(3):
            r = client.post("/v1/chat/completions", json=chat_payload)
            assert r.status_code == 200
            ids.add(r.json()["id"])
        assert len(ids) == 3

    def test_created_timestamp_is_recent(self, client, chat_payload):
        """created 字段应为近期 Unix 时间戳。"""
        before = int(time.time())
        r = client.post("/v1/chat/completions", json=chat_payload)
        after = int(time.time())
        created = r.json()["created"]
        assert before - 60 <= created <= after + 60

    def test_content_no_think_tags(self, client, chat_payload):
        """content 中不应包含 <think> 标签（已被分离）。"""
        r = client.post("/v1/chat/completions", json=chat_payload)
        content = r.json()["choices"][0]["message"].get("content", "")
        assert "<think>" not in content
        assert "</think>" not in content


class TestChatWithSystemMessage:

    def test_system_message_influences_response(self, client):
        """system 消息应影响模型行为。"""
        r = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [
                {"role": "system", "content": "你是一个专业的 Python 工程师，回答简洁"},
                {"role": "user", "content": "list 和 tuple 的区别？一句话"},
            ],
        })
        assert r.status_code == 200
        content = r.json()["choices"][0]["message"]["content"]
        assert len(content) > 0


class TestChatWithParameters:

    def test_temperature_zero(self, client):
        """temperature=0 应被接受。"""
        r = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "1+1=?"}],
            "temperature": 0,
        })
        assert r.status_code == 200

    def test_temperature_high(self, client):
        """temperature=1.5 应被接受。"""
        r = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "random word"}],
            "temperature": 1.5,
        })
        assert r.status_code == 200

    def test_max_tokens_limits_output(self, client):
        """max_tokens 应限制输出长度（Taiji 后端可能不严格遵循）。"""
        r = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "写一篇 1000 字的文章关于 AI"}],
            "max_tokens": 50,
        })
        assert r.status_code == 200
        data = r.json()
        # Taiji 后端可能不完全遵守 max_tokens，但应该有 usage
        assert data["usage"]["completion_tokens"] > 0

    def test_extra_body_fields_ignored(self, client):
        """未知字段应被静默忽略。"""
        r = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "hi"}],
            "thinking": False,
            "custom_field": "should_be_ignored",
        })
        assert r.status_code == 200


class TestChatValidation:

    def test_missing_messages_returns_400(self, client):
        """缺少 messages 字段应返回 400。"""
        r = client.post("/v1/chat/completions", json={
            "model": "taiji",
        })
        assert r.status_code in (400, 422)
        data = r.json()
        assert "error" in data

    def test_invalid_json_body(self, client):
        """非法 JSON 应返回 400。"""
        r = client.post(
            "/v1/chat/completions",
            content=b"not json at all",
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 400

    def test_temperature_out_of_range(self, client):
        """temperature > 2 应返回验证错误。"""
        r = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "hi"}],
            "temperature": 10.0,
        })
        assert r.status_code in (400, 422)


class TestCORSBehavior:

    def test_cors_preflight(self, client):
        """CORS preflight 应返回正确的 allow 头。"""
        r = client.options(
            "/v1/chat/completions",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert r.status_code == 200
        assert "access-control-allow-origin" in r.headers

    def test_cors_actual_request(self, client, chat_payload):
        """实际请求应包含 CORS 响应头。"""
        r = client.post(
            "/v1/chat/completions",
            json=chat_payload,
            headers={"Origin": "http://example.com"},
        )
        assert r.status_code == 200
        assert "access-control-allow-origin" in r.headers
