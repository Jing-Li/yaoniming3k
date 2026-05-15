"""Bar (K线) 数据类型"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any


@dataclass
class Bar:
    """一根 K 线数据"""
    timestamp: datetime
    symbol: str
    freq: str = "1d"  # 频率: 1d, 5m, 1h 等
    open: float = 0
    high: float = 0
    low: float = 0
    close: float = 0
    volume: float = 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "freq": self.freq,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Bar":
        """从字典创建"""
        if isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)