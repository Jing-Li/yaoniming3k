"""Position (持仓) 数据类型"""

from dataclasses import dataclass


@dataclass
class Position:
    """持仓"""
    symbol: str
    quantity: float  # > 0 多头，< 0 空头
    avg_cost: float  # 均价

    @property
    def is_long(self) -> bool:
        """是否多头"""
        return self.quantity > 0

    @property
    def is_short(self) -> bool:
        """是否空头"""
        return self.quantity < 0

    @property
    def abs_quantity(self) -> float:
        """绝对数量"""
        return abs(self.quantity)

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "quantity": self.quantity,
            "avg_cost": self.avg_cost,
        }