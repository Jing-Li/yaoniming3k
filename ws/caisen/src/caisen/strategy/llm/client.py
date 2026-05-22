"""LLMClient - LLM API 调用封装"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class LLMResult:
    """LLM 返回结果"""
    signals: List[Dict[str, Any]] = None
    annotations: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.signals is None:
            self.signals = []
        if self.annotations is None:
            self.annotations = []


class LLMClient(ABC):
    """LLM 客户端接口

    简化为单一职责：调用 LLM 并返回原始响应
    Prompt 构建和响应解析由独立的 PromptBuilder 和 ResponseParser 负责
    """

    @abstractmethod
    def call(self, prompt: str) -> str:
        """调用 LLM API

        Args:
            prompt: 完整的 Prompt 字符串

        Returns:
            LLM 返回的原始响应字符串
        """
        pass