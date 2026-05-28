"""PromptBuilder - Prompt 构建器"""

import json
from typing import List, Dict, Any, Optional

from .prompts.caisen_pattern import (
    SYSTEM_PROMPT,
    RULES_FRAMEWORK,
    OUTPUT_FORMAT,
    EXAMPLES_TEMPLATE,
)
from .prompts.default import DEFAULT_TEMPLATE


class PromptBuilder:
    """构建 LLM Prompt

    支持：
    - 蔡森形态规则框架（默认）
    - Few-shot 示例（默认使用模板内置 4 个精简示例）
    - K 线数据（纯 JSON，不用 markdown 代码块）

    默认使用 prompts/caisen_pattern.py 中的蔡森专用模板，支持自定义覆盖。
    """

    def __init__(
        self,
        system_prompt: str = None,
        rules: str = None,
        examples: List[Dict[str, Any]] = None,
        examples_count: int = 0,
        output_format: str = None,
        include_examples: bool = False,
    ):
        """初始化

        Args:
            system_prompt: 系统提示，默认使用蔡森专用模板
            rules: 规则框架字符串，默认使用蔡森专用模板
            examples: Few-shot 示例列表（运行时注入，优先级最高）
            examples_count: 保留参数，兼容旧接口
            output_format: 输出格式说明，默认使用蔡森专用模板
            include_examples: 是否注入内置精简示例（默认 False，
                              推理模型会因示例消耗大量 thinking token
                              导致响应截断，建议仅在非推理模型时开启）
        """
        self.system_prompt = system_prompt or SYSTEM_PROMPT
        self.rules = rules or RULES_FRAMEWORK
        self.output_format = output_format or OUTPUT_FORMAT
        self.examples = examples or []
        self.examples_count = examples_count
        self.include_examples = include_examples

    def build(self, bars: List[Dict[str, Any]]) -> str:
        """构建完整的 Prompt

        Args:
            bars: K 线数据列表

        Returns:
            完整的 Prompt 字符串
        """
        parts = []

        # 系统提示
        parts.append(self.system_prompt)

        # 规则框架
        parts.append(f"\n{self.rules}\n")

        # Few-shot 示例：优先用运行时注入的示例，否则用模板默认示例
        if self.examples:
            parts.append("\n## 示例\n")
            for i, example in enumerate(self.examples, 1):
                parts.append(f"\n### 示例 {i}")
                example_bars = example.get('bars', [])
                example_bars_dict = []
                for bar in example_bars:
                    if hasattr(bar, 'to_dict'):
                        example_bars_dict.append(bar.to_dict())
                    elif isinstance(bar, dict):
                        example_bars_dict.append(bar)
                    else:
                        example_bars_dict.append(str(bar))
                parts.append(f"K线数据: {json.dumps(example_bars_dict, ensure_ascii=False)}")
                parts.append(f"输出: {json.dumps({'signals': example['signals'], 'annotations': example.get('annotations', [])}, ensure_ascii=False)}")
                parts.append("")
        elif self.include_examples:
            # 仅在非推理模型或明确开启时注入内置示例
            parts.append(f"\n{EXAMPLES_TEMPLATE}\n")

        # 输出格式说明
        parts.append(f"\n{self.output_format}\n")

        # 实际 K 线数据（纯 JSON，不用 markdown 代码块，避免诱导 LLM 用代码块输出）
        bars_dict = []
        for bar in bars:
            if hasattr(bar, 'to_dict'):
                bars_dict.append(bar.to_dict())
            elif isinstance(bar, dict):
                bars_dict.append(bar)
            else:
                bars_dict.append({
                    "timestamp": str(bar.timestamp) if hasattr(bar, 'timestamp') else str(bar),
                    "open": getattr(bar, 'open', 0),
                    "high": getattr(bar, 'high', 0),
                    "low": getattr(bar, 'low', 0),
                    "close": getattr(bar, 'close', 0),
                    "volume": getattr(bar, 'volume', 0),
                })

        parts.append("\n## 分析任务\n")
        parts.append(f"请分析以下 {len(bars_dict)} 根 K 线数据，为每根 K 线输出一条 signal，直接输出合法 JSON：\n")
        parts.append(json.dumps(bars_dict, ensure_ascii=False))

        return "\n".join(parts)

    def add_example(self, bars: List[Dict], signals: List[Dict], annotations: List[Dict] = None) -> None:
        """添加一个示例

        Args:
            bars: 示例 K 线数据
            signals: 示例信号
            annotations: 示例标注
        """
        self.examples.append({
            "bars": bars,
            "signals": signals,
            "annotations": annotations or []
        })

    def clear_examples(self) -> None:
        """清空所有示例"""
        self.examples = []

    @classmethod
    def from_template(cls, template: dict = None, **kwargs) -> "PromptBuilder":
        """从模板创建 PromptBuilder

        Args:
            template: 模板字典，包含 system_prompt, rules, output_format, examples
            **kwargs: 其他参数
        """
        if template:
            return cls(
                system_prompt=template.get("system_prompt"),
                rules=template.get("rules"),
                output_format=template.get("output_format"),
                examples=template.get("examples"),
                examples_count=template.get("examples_count", 0),
                **kwargs,
            )
        return cls(**kwargs)