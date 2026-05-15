"""LLM Provider 抽象接口"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class LLMProvider(ABC):
    """LLM API 封装接口"""

    @abstractmethod
    def call(self, prompt: str) -> str:
        """调用 LLM，返回原始响应"""
        pass

    @abstractmethod
    def parse_response(self, response: str) -> Dict[str, Any]:
        """解析 LLM 响应，返回结构化数据"""
        pass