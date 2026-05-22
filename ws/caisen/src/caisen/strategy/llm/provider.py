"""OpenAI LLM Provider"""

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
    ):
        """初始化

        Args:
            api_key: API Key，默认 "dummy" 用于本地部署
            model: 模型名称，默认 gpt-4o
            temperature: 温度参数，控制随机性
            base_url: API 端点，默认 OpenAI，可自定义（如 http://localhost:8080/v1）
        """
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.base_url = base_url

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

        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=self.temperature
        )

        content = response.choices[0].message.content
        return content