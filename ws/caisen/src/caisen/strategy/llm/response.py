"""ResponseParser - LLM 响应解析器"""

import json
from typing import List, Dict, Any

from .client import LLMResult


class ResponseParser:
    """解析 LLM 响应为结构化数据

    职责：
    - JSON 解析
    - 格式校验
    - 结果转换
    """

    def parse(self, response: str) -> LLMResult:
        """解析 LLM 响应

        Args:
            response: LLM 返回的原始字符串

        Returns:
            LLMResult: 包含 signals 和 annotations

        Raises:
            ValueError: JSON 格式错误或缺少必需字段
        """
        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {e}")

        signals = data.get("signals", [])
        annotations = data.get("annotations", [])

        # 校验 signals 格式
        for signal in signals:
            if "timestamp" not in signal:
                raise ValueError(f"Signal missing 'timestamp': {signal}")
            if "action" not in signal:
                raise ValueError(f"Signal missing 'action': {signal}")

        return LLMResult(signals=signals, annotations=annotations)

    def parse_raw(self, response: str) -> Dict[str, Any]:
        """解析原始 JSON（不校验业务逻辑）

        Args:
            response: LLM 返回的原始字符串

        Returns:
            解析后的字典

        Raises:
            ValueError: JSON 格式错误
        """
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {e}")