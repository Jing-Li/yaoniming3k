"""
E2E-05: 错误处理与边界场景真实验证。

验证真实服务对异常请求的处理方式。
"""
import pytest


class TestRequestValidationErrors:

    def test_empty_body(self, client):
        """空请求体应返回 400/422。"""
        r = client.post(
            "/v1/chat/completions",
            content=b"{}",
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code in (400, 422)
        assert "error" in r.json()

    def test_empty_messages_array(self, client):
        """空 messages 数组应返回错误。"""
        r = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [],
        })
        # 可能返回 400/422 或 502（取决于实现）
        assert r.status_code in (400, 422, 502)

    def test_malformed_json(self, client):
        """非 JSON 请求体应返回 400。"""
        r = client.post(
            "/v1/chat/completions",
            content=b"{invalid json}}}",
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 400

    def test_invalid_role_in_message(self, client):
        """非法 role 应返回验证错误。"""
        r = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "invalid_role", "content": "hi"}],
        })
        assert r.status_code in (400, 422)

    def test_very_long_prompt(self, client):
        """超长 prompt 应被接受或返回合理错误。"""
        r = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "A" * 50000}],
        })
        # 应能处理（200）或返回 413/400
        assert r.status_code in (200, 400, 413)


class TestStreamingErrorHandling:

    def test_stream_with_invalid_body(self, client):
        """流式请求 + 无效体应返回 400。"""
        r = client.post(
            "/v1/chat/completions",
            content=b'{"stream": true}',
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code in (400, 422)

    def test_stream_content_type(self, client):
        """流式响应必须是 SSE。"""
        r = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": True,
        })
        assert r.status_code == 200
        assert "text/event-stream" in r.headers["content-type"]


class TestConcurrentRequests:

    def test_concurrent_health_checks(self, client):
        """并发健康检查应全部成功。"""
        import concurrent.futures

        def check_health():
            return client.get("/health").status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(check_health) for _ in range(10)]
            results = [f.result() for f in futures]

        assert all(code == 200 for code in results)

    def test_concurrent_chat_requests(self, client, chat_payload):
        """并发非流式 chat 请求应全部返回不同 ID。"""
        import concurrent.futures

        def chat():
            return client.post("/v1/chat/completions", json=chat_payload).json()

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(chat) for _ in range(3)]
            results = [f.result() for f in futures]

        ids = {r["id"] for r in results}
        assert len(ids) == 3


class TestAuthentication:

    def test_request_without_api_key(self, client):
        """无 API Key 请求应成功（未配置 API_KEY 时）或返回 401。"""
        r = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "hi"}],
        })
        # 取决于是否配置了 API_KEY
        assert r.status_code in (200, 401)

    def test_request_with_wrong_bearer_token(self, client):
        """错误的 Bearer Token 应返回 401（如果服务配置了 API_KEY）。"""
        r = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "hi"}],
        }, headers={"Authorization": "Bearer wrong_token_12345"})
        # 如果未配置 API_KEY，则任何 token 都应成功
        assert r.status_code in (200, 401)


class TestLargePayloadHandling:

    def test_large_system_message(self, client):
        """大 system message 应被正常处理。"""
        r = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [
                {"role": "system", "content": "你是一个助手。" * 100},
                {"role": "user", "content": "hi"},
            ],
        })
        assert r.status_code == 200

    def test_many_messages(self, client):
        """大量 messages 应被正常处理。"""
        messages = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"msg {i}"}
            for i in range(20)
        ]
        messages.append({"role": "user", "content": "总结一下"})
        r = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": messages,
        })
        assert r.status_code == 200
