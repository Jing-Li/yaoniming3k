"""Strategy (策略) 基类"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.config import BacktestConfig
    from ..core.bar import Bar
    from ..core.order import Order


@dataclass
class Annotation:
    """可视化标注"""
    bar_index: int
    type: str  # line, marker, label
    points: List[tuple] = field(default_factory=list)  # [(x, y), ...]
    label: str = ""
    color: str = "blue"


class Strategy(ABC):
    """策略基类"""

    def on_init(self, config: "BacktestConfig") -> None:
        """回测开始前调用，可用于初始化"""
        pass

    @abstractmethod
    def on_bar(self, bar: "Bar") -> Optional["Order"]:
        """每根K线调用，返回订单或None"""
        pass

    def on_session_end(self) -> None:
        """回测结束后调用，可用于清理"""
        pass

    def get_annotations(self) -> List[Annotation]:
        """获取可视化标注"""
        return []

    def reset(self) -> None:
        """重置策略状态"""
        pass