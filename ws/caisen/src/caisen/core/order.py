"""Order (订单) 数据类型"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class Side(Enum):
    """订单方向"""
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class Order:
    """订单

    quantity 和 position_pct 二选一：
    - quantity > 0: 指定具体数量
    - quantity = 0 且 position_pct > 0: 按仓位比例下单
    - quantity = 0 且 position_pct = 0: 全仓
    """
    symbol: str
    side: Side
    quantity: float = 0  # 具体数量，0表示使用仓位比例或全仓
    position_pct: float = 0  # 仓位比例（0-1），0表示全仓
    order_type: str = "MARKET"  # 市价单
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: Optional[datetime] = None
    # 止盈止损
    stop_loss: float = 0  # 止损价
    target: float = 0  # 目标价

    def to_dict(self) -> dict:
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": self.quantity,
            "order_type": self.order_type,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }