from abc import ABC, abstractmethod
from typing import AsyncGenerator

from ..models.openai import ChatCompletionRequest, ChatCompletionResponse


class BaseProvider(ABC):
    """Provider 抽象基类。

    所有后端 Provider（如 TaijiProvider）必须实现此接口，
    以支持非流式和流式两种 Chat Completions 调用模式。
    """

    @abstractmethod
    async def chat_completions(
        self, req: ChatCompletionRequest, request_id: str
    ) -> ChatCompletionResponse:
        """非流式 Chat Completions。"""
        ...

    @abstractmethod
    async def stream_chat_completions(
        self, req: ChatCompletionRequest, request_id: str
    ) -> AsyncGenerator[str, None]:
        """流式 Chat Completions，yield SSE data 行（不含 data: 前缀）。"""
        ...
