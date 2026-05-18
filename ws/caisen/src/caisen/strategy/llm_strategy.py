"""LLM Strategy (LLM 驱动的策略)"""

import json
from typing import List, Optional
from datetime import datetime

from ..core.bar import Bar
from ..core.order import Order, Side
from ..core.config import BacktestConfig
from ..strategy.base import Strategy, Annotation, AnnotationType
from ..llm.provider import LLMProvider


class LLMStrategy(Strategy):
    """LLM 驱动的策略"""

    def __init__(
        self,
        prompt_template: str,
        provider: LLMProvider,
        strategy_name: str = "llm_strategy",
        version: str = "1.0",
        cache_enabled: bool = True,
        max_cache_size: int = 10000
    ):
        self.prompt_template = prompt_template
        self.provider = provider
        self.strategy_name = strategy_name
        self.version = version
        self.cache_enabled = cache_enabled
        self.max_cache_size = max_cache_size

        self.all_bars: List[Bar] = []
        self.annotations: List[Annotation] = []
        self.response_cache: dict = {}
        self.bar_index = 0

    def on_init(self, config: BacktestConfig) -> None:
        """初始化"""
        self.all_bars = []
        self.annotations = []
        self.bar_index = 0
        self.response_cache = {}

    def on_bar(self, bar: Bar) -> Optional[Order]:
        """每根 K 线调用 LLM"""
        self.all_bars.append(bar)
        self.bar_index += 1

        # 检查缓存
        cache_key = f"{bar.symbol}_{bar.timestamp.isoformat()}"
        if self.cache_enabled and cache_key in self.response_cache:
            return self._parse_response_to_order(self.response_cache[cache_key])

        # 构造 prompt
        prompt = self._build_prompt(bar)

        # 调用 LLM
        response = self.provider.call(prompt)

        # 解析响应
        result = self.provider.parse_response(response)

        # 缓存
        if self.cache_enabled:
            self.response_cache[cache_key] = result

        # 记录标注
        for annotation in result.get("annotations", []):
            ann_type = annotation.get("type", "marker")
            # 映射到 AnnotationType
            try:
                ann_type_enum = AnnotationType(ann_type)
            except ValueError:
                ann_type_enum = AnnotationType.TEXT_LABEL

            self.annotations.append(Annotation(
                type=ann_type_enum,
                timestamp=bar.timestamp,
                data={
                    "label": annotation.get("label", ""),
                    "color": annotation.get("color", "blue"),
                    "price": annotation.get("price", bar.close),
                    "points": annotation.get("points", []),
                }
            ))

        return self._parse_response_to_order(result)

    def _build_prompt(self, bar: Bar) -> str:
        """构建 prompt"""
        # 格式化历史数据
        bars_text = self._format_bars()

        # 填充模板
        prompt = self.prompt_template.format(
            symbol=bar.symbol,
            timestamp=bar.timestamp.isoformat(),
            bars=bars_text,
            open=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
            volume=bar.volume
        )
        return prompt

    def _format_bars(self) -> str:
        """格式化 K 线数据为文本"""
        if not self.all_bars:
            return ""

        lines = []
        for b in self.all_bars[-20:]:  # 只发送最近 20 根
            lines.append(f"{b.timestamp.date()} O:{b.open:.2f} H:{b.high:.2f} L:{b.low:.2f} C:{b.close:.2f} V:{b.volume:.0f}")

        return "\n".join(lines)

    def _parse_response_to_order(self, result: dict) -> Optional[Order]:
        """解析 LLM 响应为 Order"""
        action = result.get("action", "HOLD").upper()

        if action == "BUY":
            return Order(symbol=self.all_bars[-1].symbol, side=Side.BUY, quantity=0)
        elif action == "SELL":
            return Order(symbol=self.all_bars[-1].symbol, side=Side.SELL, quantity=0)
        else:
            return None

    def on_session_end(self) -> None:
        """会话结束"""
        pass

    def get_annotations(self) -> List[Annotation]:
        """获取可视化标注"""
        return self.annotations

    def reset(self) -> None:
        """重置状态"""
        self.all_bars = []
        self.annotations = []
        self.bar_index = 0
        self.response_cache = {}