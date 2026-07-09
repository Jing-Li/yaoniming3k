from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class TaijiRequest(BaseModel):
    """Taiji API 请求体模型。

    使用 extra="allow" 以透传 temperature、max_tokens 等可选参数。
    """

    model_config = {"extra": "allow"}

    text: str
    sessionId: int = 0
    files: list[dict[str, Any]] = []
    thinking: bool = False
    webSearch: bool = False


class TaijiResponseChunk(BaseModel):
    """用于灵活解析 taiji 返回的 SSE 中的 JSON 对象。"""

    content: str | None = None
    text: str | None = None
    message: str | None = None
    answer: str | None = None
    result: str | None = None
