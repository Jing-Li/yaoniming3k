"""Order (订单) 数据类型"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class Side(Enum):
    """订单方向"""
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class Order:
    """订单"""
    symbol: str
    side: Side
    quantity: float = 0  # 0 = 全仓
    order_type: str = "MARKET"  # 市价单
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = None

    def to_dict(self) -> dict:
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": self.quantity,
            "order_type": self.order_type,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }