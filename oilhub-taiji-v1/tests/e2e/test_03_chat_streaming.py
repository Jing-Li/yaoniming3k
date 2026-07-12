"""
E2E-03: 流式 Chat Completions 真实调用。

验证 SSE 流格式、chunk 结构、finish_reason 时机、[DONE] 标记。
"""
import pytest

from .conftest import parse_sse_chunks


class TestStreamingBasicFlow:

    def test_stream_returns_sse_content_type(self, client, stream_payload):
        """流式响应应返回 text/event-stream。"""
        r = client.post("/v1/chat/completions", json=stream_payload)
        assert r.status_code == 200
        assert "text/event-stream" in r.headers["content-type"]

    def test_stream_has_cache_control_headers(self, client, stream_payload):
        """SSE 响应应包含 no-cache 头。"""
        r = client.post("/v1/chat/completions", json=stream_payload)
        assert r.headers.get("cache-control") == "no-cache"
        # connection header may be 'close' or 'keep-alive' depending on client/server
        assert r.headers.get("connection") in ("keep-alive", "close")

    def test_stream_ends_with_done(self, client, stream_payload):
        """流式响应必须以 data: [DONE] 结尾。"""
        r = client.post("/v1/chat/completions", json=stream_payload)
        assert "data: [DONE]" in r.text

    def test_stream_first_chunk_has_role(self, client, stream_payload):
        """第一个 chunk 必须携带 role=assistant。"""
        r = client.post("/v1/chat/completions", json=stream_payload)
        chunks = parse_sse_chunks(r.text)
        assert len(chunks) > 0
        assert chunks[0]["choices"][0]["delta"]["role"] == "assistant"

    def test_stream_chunks_have_correct_object(self, client, stream_payload):
        """所有 chunk 的 object 应为 chat.completion.chunk。"""
        r = client.post("/v1/chat/completions", json=stream_payload)
        chunks = parse_sse_chunks(r.text)
        for chunk in chunks:
            assert chunk["object"] == "chat.completion.chunk"

    def test_stream_content_concatenation(self, client, stream_payload):
        """拼接所有 content delta 应得到非空有意义文本。"""
        r = client.post("/v1/chat/completions", json=stream_payload)
        chunks = parse_sse_chunks(r.text)
        contents = []
        for chunk in chunks:
            delta = chunk["choices"][0].get("delta", {})
            if "content" in delta and delta["content"]:
                contents.append(delta["content"])
        full = "".join(contents)
        assert len(full) > 0
        assert "<think>" not in full

    def test_stream_consistent_id_across_chunks(self, client, stream_payload):
        """所有 chunk 应共享同一个 completion ID。"""
        r = client.post("/v1/chat/completions", json=stream_payload)
        chunks = parse_sse_chunks(r.text)
        ids = {c["id"] for c in chunks}
        assert len(ids) == 1, f"All chunks should have same ID, got: {ids}"

    def test_stream_consistent_model_across_chunks(self, client, stream_payload):
        """所有 chunk 的 model 字段应一致。"""
        r = client.post("/v1/chat/completions", json=stream_payload)
        chunks = parse_sse_chunks(r.text)
        models = {c["model"] for c in chunks}
        assert models == {"taiji"}


class TestStreamingFinishReason:

    def test_finish_reason_only_in_last_chunk(self, client, stream_payload):
        """finish_reason 应只出现在倒数第二个 chunk（DONE 前）。"""
        r = client.post("/v1/chat/completions", json=stream_payload)
        chunks = parse_sse_chunks(r.text)
        finish_chunks = [c for c in chunks if c["choices"][0].get("finish_reason")]
        assert len(finish_chunks) >= 1
        assert finish_chunks[-1]["choices"][0]["finish_reason"] == "stop"

    def test_non_final_chunks_have_no_finish_reason(self, client, stream_payload):
        """除最后 finish chunk 外，其他 chunk 不应有 finish_reason。"""
        r = client.post("/v1/chat/completions", json=stream_payload)
        chunks = parse_sse_chunks(r.text)
        for chunk in chunks[:-1]:
            fr = chunk["choices"][0].get("finish_reason")
            assert fr is None, f"Non-final chunk should not have finish_reason, got: {fr}"


class TestStreamingWithUsage:

    def test_final_chunk_contains_usage(self, client, stream_payload):
        """最后的 finish chunk 应包含 usage 信息。"""
        r = client.post("/v1/chat/completions", json=stream_payload)
        assert r.status_code == 200
        chunks = parse_sse_chunks(r.text)
        # 过滤掉错误 chunk（限流时可能返回 error）
        valid_chunks = [c for c in chunks if "choices" in c]
        if not valid_chunks:
            pytest.skip("Taiji API returned error chunks (likely rate limiting)")
        finish_chunks = [c for c in valid_chunks if c["choices"][0].get("finish_reason")]
        assert len(finish_chunks) > 0
        usage = finish_chunks[-1].get("usage")
        assert usage is not None
        assert usage["prompt_tokens"] > 0
        assert usage["completion_tokens"] > 0
        assert usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"]


class TestStreamingMultiTurn:

    def test_multi_turn_stream(self, client):
        """多轮对话流式调用应正常工作。"""
        r = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [
                {"role": "system", "content": "你是数学老师"},
                {"role": "user", "content": "2+2=?"},
                {"role": "assistant", "content": "4"},
                {"role": "user", "content": "再乘以3呢？只回答数字"},
            ],
            "stream": True,
        })
        assert r.status_code == 200
        chunks = parse_sse_chunks(r.text)
        assert len(chunks) > 0
        contents = "".join(
            c["choices"][0]["delta"].get("content", "")
            for c in chunks if "content" in c["choices"][0].get("delta", {})
        )
        assert len(contents) > 0


class TestStreamingEmptyContent:

    def test_very_short_prompt(self, client):
        """极短 prompt 应仍能正常流式返回。"""
        r = client.post("/v1/chat/completions", json={
            "model": "taiji",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": True,
        })
        assert r.status_code == 200
        assert "data: [DONE]" in r.text
