"""PromptBuilder - Prompt 构建器"""

import json
from typing import List, Dict, Any, Optional


class PromptBuilder:
    """构建 LLM Prompt

    支持：
    - 规则框架
    - Few-shot 示例
    - K 线数据
    """

    DEFAULT_SYSTEM_PROMPT = """你是一个量化交易策略分析师。根据 K 线数据分析并输出交易信号和标注。

规则框架：
- 支撑位买入（价格触及支撑后反弹）
- 阻力位卖出（价格触及阻力后回落）
- 趋势确认后跟进

输出格式要求：
- 只输出 JSON，不要其他内容
- signals 数组包含每个时间点的交易信号
- annotations 数组包含可视化标注

"""

    def __init__(
        self,
        system_prompt: str = None,
        rules: str = None,
        examples: List[Dict[str, Any]] = None,
        examples_count: int = 0
    ):
        """初始化

        Args:
            system_prompt: 系统提示，自定义指令
            rules: 规则框架字符串
            examples: Few-shot 示例列表
            examples_count: 示例数量（如果 examples 未提供则生成占位符）
        """
        self.system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT
        self.rules = rules
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
        if self.rules:
            parts.append(f"\n交易规则：\n{self.rules}\n")

        # Few-shot 示例
        if self.examples:
            parts.append("\n示例：\n")
            for i, example in enumerate(self.examples, 1):
                parts.append(f"示例 {i}：")
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
                parts.append(f"K线数据：{json.dumps(example_bars_dict, ensure_ascii=False)}")
                parts.append(f"输出：{json.dumps({'signals': example['signals'], 'annotations': example.get('annotations', [])}, ensure_ascii=False)}")
                parts.append("")
        elif self.examples_count > 0:
            parts.append(f"\n[请提供 {self.examples_count} 个交易示例]")

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

        parts.append("\n请分析以下 K 线数据：\n")
        parts.append(json.dumps(bars_dict, ensure_ascii=False))

        # 输出格式说明
        parts.append("\n\n输出 JSON 格式：")
        parts.append("""
{
  "signals": [
    {"timestamp": "YYYY-MM-DD", "action": "buy|sell|hold", "confidence": 0.0-1.0, "reason": "..."}
  ],
  "annotations": [
    {"timestamp": "YYYY-MM-DD", "type": "buy_signal|sell_signal|pattern_mark|horizontal_line|...", "data": {...}}
  ]
}
""")

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