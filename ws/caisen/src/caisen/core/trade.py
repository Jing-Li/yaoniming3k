"""Trade (交易记录) 数据类型"""

from dataclasses import dataclass
from datetime import datetime
from .order import Side


@dataclass
class Trade:
    """一次成交记录"""
    timestamp: datetime
    symbol: str
    side: Side
    quantity: float
    price: float
    commission: float  # 手续费
    slippage: float  # 滑点成本
    order_id: str

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": self.quantity,
            "price": self.price,
            "commission": self.commission,
            "slippage": self.slippage,
            "order_id": self.order_id,
        }