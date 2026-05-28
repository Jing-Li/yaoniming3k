"""OpenAI LLM Provider"""

from typing import Optional, Dict, Any

from .client import LLMClient, LLMResult


class OpenAIProvider(LLMClient):
    """OpenAI API 实现

    支持自定义端点（如 vLLM、本地部署模型）
    """

    def __init__(
        self,
        api_key: str = "dummy",
        model: str = "gpt-4o",
        temperature: float = 0.3,
        base_url: str = "https://api.openai.com/v1",
        disable_thinking: bool = True,
        extra_body: Optional[Dict[str, Any]] = None,
        max_tokens: Optional[int] = 2048,
    ):
        """初始化

        Args:
            api_key: API Key，默认 "dummy" 用于本地部署
            model: 模型名称，默认 gpt-4o
            temperature: 温度参数，控制随机性
            base_url: API 端点，默认 OpenAI，可自定义（如 http://localhost:8080/v1）
            disable_thinking: 是否禁用推理模型的 <think> 输出（默认 True）。
                              对不支持此参数的模型无副作用（服务端会忽略未知字段）。
            extra_body: 透传给 API 的额外参数（优先级高于 disable_thinking）
            max_tokens: 最大输出 token 数，默认 2048。本地推理模型默认值往往过小
                        导致 JSON 被截断，需显式指定。设为 None 则依赖服务端默认值。
        """
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.base_url = base_url
        self.disable_thinking = disable_thinking
        self.extra_body = extra_body
        self.max_tokens = max_tokens

    def call(self, prompt: str) -> str:
        """调用 OpenAI API（或兼容 API）"""
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

        client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

        # 构建 extra_body：用户显式传入的优先，否则按 disable_thinking 自动生成
        body = self.extra_body
        if body is None and self.disable_thinking:
            body = {"thinking": {"type": "disabled"}}

        kwargs = dict(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            extra_body=body,
        )
        if self.max_tokens is not None:
            kwargs["max_tokens"] = self.max_tokens

        response = client.chat.completions.create(**kwargs)

        content = response.choices[0].message.content
        return content
