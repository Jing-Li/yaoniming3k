"""Annotation (可视化标注) - 核心类型

策略返回语义化标注，可视化层根据 type 决定渲染方式。
作为策略、结果、前端之间的共享契约。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime


class AnnotationType(Enum):
    """标注类型枚举"""
    # 点位标注
    BUY_SIGNAL = "buy_signal"      # 买入信号
    SELL_SIGNAL = "sell_signal"     # 卖出信号
    NEUTRAL_SIGNAL = "neutral_signal"  # 中性信号

    # 线条标注
    HORIZONTAL_LINE = "horizontal_line"  # 水平线 (支撑/阻力)
    TREND_LINE = "trend_line"            # 趋势线
    FIB_LINE = "fib_line"                 # 斐波那契回撤线

    # 区域标注
    SUPPORT_ZONE = "support_zone"         # 支撑区间
    RESISTANCE_ZONE = "resistance_zone"   # 阻力区间
    VOLUME_SPIKE = "volume_spike"         # 成交量异常

    # 文本标注
    TEXT_LABEL = "text_label"             # 文本标签
    PATTERN_MARK = "pattern_mark"         # 形态标记

    # 图形标注
    RECTANGLE = "rectangle"               # 矩形
    POLYGON = "polygon"                   # 多边形


@dataclass
class Annotation:
    """可视化标注

    策略返回语义化标注，可视化层根据 type 决定渲染方式。
    """
    type: AnnotationType
    timestamp: datetime
    data: Dict[str, Any] = field(default_factory=dict)

    @property
    def label(self) -> str:
        """获取标签文本"""
        return self.data.get("label", "")

    @property
    def color(self) -> str:
        """获取颜色"""
        return self.data.get("color", "blue")

    @property
    def price(self) -> Optional[float]:
        """获取价格（如果适用）"""
        return self.data.get("price")

    @staticmethod
    def _serialize_value(value):
        """递归序列化值，处理 datetime 对象"""
        if isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, dict):
            return {k: Annotation._serialize_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [Annotation._serialize_value(item) for item in value]
        return value

    def to_dict(self) -> dict:
        """转换为字典（用于序列化）"""
        return {
            "type": self.type.value,
            "timestamp": self.timestamp.isoformat(),
            "data": self._serialize_value(self.data),
        }

    @classmethod
    def buy_signal(cls, timestamp: datetime, price: float, label: str = "", **kwargs):
        """创建买入信号标注"""
        return cls(
            type=AnnotationType.BUY_SIGNAL,
            timestamp=timestamp,
            data={"price": price, "label": label, "color": "green", **kwargs}
        )

    @classmethod
    def sell_signal(cls, timestamp: datetime, price: float, label: str = "", **kwargs):
        """创建卖出信号标注"""
        return cls(
            type=AnnotationType.SELL_SIGNAL,
            timestamp=timestamp,
            data={"price": price, "label": label, "color": "red", **kwargs}
        )

    @classmethod
    def horizontal_line(cls, timestamp: datetime, price: float, label: str = "", **kwargs):
        """创建水平线标注"""
        return cls(
            type=AnnotationType.HORIZONTAL_LINE,
            timestamp=timestamp,
            data={"price": price, "label": label, "color": "blue", **kwargs}
        )

    @classmethod
    def pattern_mark(cls, timestamp: datetime, pattern: str, points: List[Dict], label: str = "", **kwargs):
        """创建形态标记标注

        Args:
            timestamp: 主时间点
            pattern: 形态类型 (w_bottom, m_top, head_and_shoulders_bottom 等)
            points: 形态关键点列表 [{"timestamp": ..., "price": ..., "label": ...}, ...]
            label: 标签文本
            **kwargs: 其他参数 (color, neckline 等)
        """
        return cls(
            type=AnnotationType.PATTERN_MARK,
            timestamp=timestamp,
            data={
                "pattern": pattern,
                "points": points,
                "label": label,
                **kwargs
            }
        )

    @classmethod
    def text_label(cls, timestamp: datetime, text: str, price: float = None, **kwargs):
        """创建文本标签标注"""
        return cls(
            type=AnnotationType.TEXT_LABEL,
            timestamp=timestamp,
            data={"text": text, "price": price, **kwargs}
        )