from typing import List, Optional
from pydantic import BaseModel


class TaijiRequest(BaseModel):
    model_config = {"extra": "allow"}

    text: str
    sessionId: int = 0
    files: List[dict] = []


class TaijiResponseChunk(BaseModel):
    """用于灵活解析 taiji 返回的 SSE 中的 JSON 对象。"""
    content: Optional[str] = None
    text: Optional[str] = None
    message: Optional[str] = None
    answer: Optional[str] = None
    result: Optional[str] = None
