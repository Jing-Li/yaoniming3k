"""OpenAI LLM Provider 实现"""

import json
from typing import Dict, Any, Optional
from .provider import LLMProvider


class OpenAIProvider(LLMProvider):
    """OpenAI API 实现"""

    def __init__(self, model: str = "gpt-4", api_key: str = None):
        self.model = model
        self.api_key = api_key or self._get_api_key()

    def _get_api_key(self) -> str:
        """从环境变量获取 API Key"""
        import os
        return os.environ.get("OPENAI_API_KEY", "")

    def call(self, prompt: str) -> str:
        """调用 OpenAI API"""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个量化交易分析师。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
            )
            return response.choices[0].message.content
        except ImportError:
            # 如果没有 openai 库，返回模拟响应
            return self._mock_response(prompt)
        except Exception as e:
            return f"Error: {e}"

    def _mock_response(self, prompt: str) -> str:
        """模拟响应（用于测试）"""
        if "买入" in prompt or "BUY" in prompt:
            return json.dumps({
                "action": "BUY",
                "reason": "模拟买入信号",
                "confidence": 0.8,
                "annotations": []
            })
        elif "卖出" in prompt or "SELL" in prompt:
            return json.dumps({
                "action": "SELL",
                "reason": "模拟卖出信号",
                "confidence": 0.8,
                "annotations": []
            })
        else:
            return json.dumps({
                "action": "HOLD",
                "reason": "模拟持有信号",
                "confidence": 0.5,
                "annotations": []
            })

    def parse_response(self, response: str) -> Dict[str, Any]:
        """解析 LLM 响应"""
        try:
            data = json.loads(response)
            return {
                "action": data.get("action", "HOLD").upper(),
                "reason": data.get("reason", ""),
                "confidence": data.get("confidence", 0.5),
                "annotations": data.get("annotations", [])
            }
        except json.JSONDecodeError:
            return {
                "action": "HOLD",
                "reason": f"解析失败: {response[:100]}",
                "confidence": 0,
                "annotations": []
            }