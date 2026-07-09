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
        self, req: ChatCompletionRequest, request_id: str,
    ) -> ChatCompletionResponse:
        """非流式 Chat Completions。

        Args:
            req: OpenAI 格式的聊天完成请求。
            request_id: 请求唯一标识，用于日志关联。

        Returns:
            OpenAI 格式的聊天完成响应。
        """
        ...

    @abstractmethod
    async def stream_chat_completions(
        self, req: ChatCompletionRequest, request_id: str,
    ) -> AsyncGenerator[str, None]:
        """流式 Chat Completions，yield SSE data 行（不含 data: 前缀）。

        Args:
            req: OpenAI 格式的聊天完成请求（stream=True）。
            request_id: 请求唯一标识，用于日志关联。

        Yields:
            JSON 字符串，每个代表一个 SSE chunk。
        """
        ...

    async def close(self) -> None:
        """释放 Provider 持有的资源（如 HTTP 连接池）。子类可覆写。"""
