"""LLMClient - LLM API 调用封装"""

import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


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


class LLMClient:
    """LLM 客户端

    封装 LLM API 调用，包括：
    - Prompt 构建
    - API 调用
    - 响应解析
    - 结果校验
    """

    def __init__(self, provider_name: str = "openai", **config):
        """初始化

        Args:
            provider_name: LLM 提供者名称
            **config: 其他配置（如 api_key, model 等）
        """
        self.provider_name = provider_name
        self.config = config

    def analyze(self, bars: List[Dict]) -> LLMResult:
        """分析 K 线数据，返回信号和标注

        Args:
            bars: K 线数据列表

        Returns:
            LLMResult: 包含 signals 和 annotations
        """
        prompt = self.build_prompt(bars)
        response = self.call_llm(prompt)
        result = self.parse_response(response)
        return result

    def build_prompt(self, bars: List[Dict]) -> str:
        """构建 Prompt

        子类应重写此方法以提供具体的 Prompt 模板
        """
        bars_json = json.dumps(bars, indent=2)
        return f"""你是一个量化交易策略分析师。根据以下 K 线数据分析并输出交易信号和标注。

K 线数据：
{bars_json}

请按以下 JSON 格式输出（只输出 JSON，不要其他内容）：
{{
  "signals": [
    {{"timestamp": "YYYY-MM-DD", "action": "buy|sell|hold", "confidence": 0.0-1.0, "reason": "..."}}
  ],
  "annotations": [
    {{"timestamp": "YYYY-MM-DD", "type": "buy_signal|sell_signal|pattern_mark|...", "data": {{}}}}
  ]
}}
"""

    def call_llm(self, prompt: str) -> str:
        """调用 LLM API

        子类应重写此方法以实现具体的 API 调用
        默认实现返回错误提示
        """
        raise NotImplementedError("Subclass must implement call_llm()")

    def parse_response(self, response: str) -> LLMResult:
        """解析 LLM 响应"""
        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {e}")

        # 校验必需字段
        signals = data.get("signals", [])
        annotations = data.get("annotations", [])

        # 校验 signals 格式
        for signal in signals:
            if "timestamp" not in signal:
                raise ValueError(f"Signal missing 'timestamp': {signal}")
            if "action" not in signal:
                raise ValueError(f"Signal missing 'action': {signal}")

        return LLMResult(signals=signals, annotations=annotations)