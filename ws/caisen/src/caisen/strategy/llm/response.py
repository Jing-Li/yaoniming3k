"""ResponseParser - LLM 响应解析器"""

import json
import re
from typing import List, Dict, Any

from .client import LLMResult


def _strip_thinking(text: str) -> str:
    """剥离推理模型输出的 <think>...</think> 块。

    部分推理模型（如 DeepSeek-R1、QwQ）会在回答前输出思考过程，
    真正的 JSON 答案在 </think> 之后。
    """
    end_tag = "</think>"
    idx = text.find(end_tag)
    if idx != -1:
        return text[idx + len(end_tag):].strip()
    # 没有闭合标签时，如果以 <think> 开头说明响应被截断在思考阶段
    if text.strip().startswith("<think>"):
        raise ValueError("LLM 响应在 <think> 推理阶段被截断，未产生实际输出。"
                         "请检查模型 max_tokens 设置或减少 K 线数量。")
    return text


def _extract_json(text: str) -> str:
    """从 LLM 原始响应中提取 JSON 字符串。

    按优先级尝试以下策略：
    1. 直接解析（纯 JSON 响应）
    2. 从 markdown 代码块中提取（```json ... ``` 或 ``` ... ```）
    3. 找第一个 { 到最后一个 } 之间的内容（响应被截断时的降级）
    """
    stripped = text.strip()

    # 策略 1：直接可用
    try:
        json.loads(stripped)
        return stripped
    except json.JSONDecodeError:
        pass

    # 策略 2：markdown 代码块
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, re.DOTALL)
    if match:
        candidate = match.group(1).strip()
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            pass

    # 策略 3：截断降级——取最外层 { ... } 并尝试修复尾部
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = stripped[start:end + 1]
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            pass

    # 策略 4：截断但没有闭合的 }——尝试找 signals 数组并补全
    if start != -1:
        partial = stripped[start:]
        # 补全常见截断：末尾缺少 }] 或 }]}
        for suffix in ("]}}", "]}", "}"):
            try:
                json.loads(partial + suffix)
                return partial + suffix
            except json.JSONDecodeError:
                continue

    raise ValueError(f"无法从响应中提取合法 JSON，原始响应（前200字符）: {stripped[:200]}")


class ResponseParser:
    """解析 LLM 响应为结构化数据

    职责：
    - JSON 提取（支持 markdown 代码块、截断响应降级）
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
            ValueError: 无法提取合法 JSON 或缺少必需字段
        """
        json_str = _extract_json(_strip_thinking(response))
        data = json.loads(json_str)

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
            ValueError: 无法提取合法 JSON
        """
        json_str = _extract_json(_strip_thinking(response))
        return json.loads(json_str)