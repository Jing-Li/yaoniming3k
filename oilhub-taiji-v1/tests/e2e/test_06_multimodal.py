"""E2E 测试：多模态图片附件透传。

验证 OpenAI vision 格式 (image_url) 能正确透传为 Taiji files 字段。
"""

import base64
import struct
import zlib

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_png(r: int = 255, g: int = 0, b: int = 0) -> bytes:
    """创建最小有效 PNG (1x1 像素)。"""
    signature = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    ihdr_crc = zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF
    ihdr = struct.pack(">I", 13) + b"IHDR" + ihdr_data + struct.pack(">I", ihdr_crc)
    raw = zlib.compress(bytes([0, r, g, b]))
    idat_crc = zlib.crc32(b"IDAT" + raw) & 0xFFFFFFFF
    idat = struct.pack(">I", len(raw)) + b"IDAT" + raw + struct.pack(">I", idat_crc)
    iend_crc = zlib.crc32(b"IEND") & 0xFFFFFFFF
    iend = struct.pack(">I", 0) + b"IEND" + struct.pack(">I", iend_crc)
    return signature + ihdr + idat + iend


def _data_uri(png_bytes: bytes) -> str:
    return f"data:image/png;base64,{base64.b64encode(png_bytes).decode()}"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def single_image_payload():
    """单图非流式请求体。"""
    return {
        "model": "taiji",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "这张图片是什么颜色？用一个字回答"},
                    {"type": "image_url", "image_url": {"url": _data_uri(_create_png(255, 0, 0))}},
                ],
            }
        ],
        "stream": False,
    }


@pytest.fixture(scope="module")
def multi_image_stream_payload():
    """多图流式请求体。"""
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
    parts = [{"type": "text", "text": "我上传了几张图？用数字回答"}]
    for r, g, b in colors:
        parts.append({"type": "image_url", "image_url": {"url": _data_uri(_create_png(r, g, b))}})
    return {
        "model": "taiji",
        "messages": [{"role": "user", "content": parts}],
        "stream": True,
    }


# ---------------------------------------------------------------------------
# Tests: Non-streaming with image
# ---------------------------------------------------------------------------

class TestSingleImageNonStream:
    """单图非流式请求透传验证。"""

    def test_image_request_returns_200(self, client, single_image_payload):
        """带图片的请求应返回 200。"""
        r = client.post("/v1/chat/completions", json=single_image_payload)
        assert r.status_code == 200

    def test_image_response_has_content(self, client, single_image_payload):
        """带图片请求的响应应包含有意义的 content。"""
        r = client.post("/v1/chat/completions", json=single_image_payload)
        data = r.json()
        content = data["choices"][0]["message"]["content"]
        assert isinstance(content, str)
        assert len(content) > 0

    def test_image_response_has_usage(self, client, single_image_payload):
        """带图片请求的响应应包含 usage 统计。"""
        r = client.post("/v1/chat/completions", json=single_image_payload)
        data = r.json()
        assert "usage" in data
        assert data["usage"]["total_tokens"] > 0


# ---------------------------------------------------------------------------
# Tests: Streaming with multiple images
# ---------------------------------------------------------------------------

class TestMultiImageStreaming:
    """多图流式请求透传验证。"""

    def test_multi_image_stream_returns_200(self, client, multi_image_stream_payload):
        """多图流式请求应返回 200。"""
        r = client.post("/v1/chat/completions", json=multi_image_stream_payload)
        assert r.status_code == 200

    def test_multi_image_stream_has_content(self, client, multi_image_stream_payload):
        """多图流式响应应包含有意义的内容。"""
        r = client.post("/v1/chat/completions", json=multi_image_stream_payload)
        assert "data: [DONE]" in r.text
        # Check that we got at least some content chunks
        content_chunks = [
            line for line in r.text.split("\n")
            if line.startswith("data: ") and line != "data: [DONE]"
        ]
        assert len(content_chunks) > 0

    def test_multi_image_stream_ends_with_done(self, client, multi_image_stream_payload):
        """多图流式响应必须以 [DONE] 结束。"""
        r = client.post("/v1/chat/completions", json=multi_image_stream_payload)
        assert "data: [DONE]" in r.text


# ---------------------------------------------------------------------------
# Tests: Text-only messages still work (backward compatibility)
# ---------------------------------------------------------------------------

class TestBackwardCompatibility:
    """确保纯文本消息在多模态改造后仍然正常工作。"""

    def test_plain_text_still_works(self, client):
        """普通纯文本请求不受影响。"""
        payload = {
            "model": "taiji",
            "messages": [{"role": "user", "content": "说hi"}],
            "stream": False,
        }
        r = client.post("/v1/chat/completions", json=payload)
        assert r.status_code == 200
        assert r.json()["choices"][0]["message"]["content"]

    def test_mixed_content_messages(self, client):
        """混合消息：有的有图片，有的纯文本。"""
        payload = {
            "model": "taiji",
            "messages": [
                {"role": "system", "content": "简洁回答"},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "这张图是什么？"},
                        {"type": "image_url", "image_url": {"url": _data_uri(_create_png())}},
                    ],
                },
                {"role": "assistant", "content": "一个红色方块"},
                {"role": "user", "content": "好的谢谢"},
            ],
            "stream": False,
        }
        r = client.post("/v1/chat/completions", json=payload)
        assert r.status_code == 200
        content = r.json()["choices"][0]["message"]["content"]
        assert isinstance(content, str)
        assert len(content) > 0
