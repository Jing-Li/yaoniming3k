"""PromptBuilder - Prompt 构建器"""

import json
from typing import List, Dict, Any, Optional

from .prompts.default import (
    DEFAULT_TEMPLATE,
    SYSTEM_PROMPT,
    RULES_FRAMEWORK,
    OUTPUT_FORMAT,
    EXAMPLES_TEMPLATE,
)


class PromptBuilder:
    """构建 LLM Prompt

    支持：
    - 规则框架
    - Few-shot 示例
    - K 线数据

    默认使用 prompts/default.py 中的模板，支持自定义覆盖。
    """

    def __init__(
        self,
        system_prompt: str = None,
        rules: str = None,
        examples: List[Dict[str, Any]] = None,
        examples_count: int = 0,
        output_format: str = None,
    ):
        """初始化

        Args:
            system_prompt: 系统提示，默认使用模板中的
            rules: 规则框架字符串，默认使用模板中的
            examples: Few-shot 示例列表（运行时注入）
            examples_count: 示例数量（如果 examples 未提供则生成占位符）
            output_format: 输出格式说明，默认使用模板中的
        """
        self.system_prompt = system_prompt or SYSTEM_PROMPT
        self.rules = rules or RULES_FRAMEWORK
        self.output_format = output_format or OUTPUT_FORMAT
        self.examples = examples or []
        self.examples_count = examples_count

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

        # Few-shot 示例（运行时）
        if self.examples:
            parts.append("\n## 示例\n")
            for i, example in enumerate(self.examples, 1):
                parts.append(f"\n### 示例 {i}")
                # 处理示例中的 bars
                example_bars = example.get('bars', [])
                example_bars_dict = []
                for bar in example_bars:
                    if hasattr(bar, 'to_dict'):
                        example_bars_dict.append(bar.to_dict())
                    elif isinstance(bar, dict):
                        example_bars_dict.append(bar)
                    else:
                        example_bars_dict.append(str(bar))
                parts.append(f"**K线数据**: {json.dumps(example_bars_dict, ensure_ascii=False)}")
                parts.append(f"**输出**:\n```json\n{json.dumps({'signals': example['signals'], 'annotations': example.get('annotations', [])}, ensure_ascii=False)}\n```")
                parts.append("")
        elif self.examples_count > 0:
            parts.append(f"\n[请提供 {self.examples_count} 个交易示例]")

        # 输出格式说明
        parts.append(f"\n{self.output_format}\n")

        # 实际 K 线数据
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
        parts.append("请分析以下 K 线数据，输出交易信号和标注：\n")
        parts.append(f"```json\n{json.dumps(bars_dict, ensure_ascii=False)}\n```")

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