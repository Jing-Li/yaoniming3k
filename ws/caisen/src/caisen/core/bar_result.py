"""BarResult：Strategy.on_bar() 的返回类型。

封装一根 K 线上策略产生的所有输出：
- order: 可选订单（None 表示本 bar 不交易）
- annotations: 本 bar 新增的标注列表（空列表表示无标注）

引擎每根 bar 解包 BarResult，立即处理 order 并累积 annotations。
策略不再需要维护内部标注累积列表，也不再需要 get_annotations() 接口。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .order import Order
    from .annotation import Annotation


@dataclass
class BarResult:
    """单根 K 线处理结果。

    Attributes:
        order: 策略决策产生的订单，None 表示不交易
        annotations: 本 bar 产生的可视化标注列表
    """
    order: Optional["Order"] = None
    annotations: List["Annotation"] = field(default_factory=list)

    @classmethod
    def no_action(cls) -> "BarResult":
        """无订单、无标注的快捷构造方法"""
        return cls()

    @classmethod
    def with_order(cls, order: "Order", annotations: Optional[List["Annotation"]] = None) -> "BarResult":
        """带订单的快捷构造方法"""
        return cls(order=order, annotations=annotations or [])
