"""Portfolio (组合/账户) 数据类型"""

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class Portfolio:
    """回测账户"""
    initial_capital: float
    cash: float
    positions: Dict[str, "Position"] = field(default_factory=dict)

    @property
    def equity(self) -> float:
        """当前总权益（用 avg_cost 估算）"""
        position_value = sum(p.quantity * p.avg_cost for p in self.positions.values())
        return self.cash + position_value

    def get_equity_with_prices(self, prices: Dict[str, float]) -> float:
        """用指定价格计算权益"""
        position_value = sum(
            p.quantity * prices.get(p.symbol, p.avg_cost)
            for p in self.positions.values()
        )
        return self.cash + position_value

    def get_available_cash(self, prices: Dict[str, float]) -> float:
        """可用资金 = 现金 + 空头释放的资金"""
        cash = self.cash
        for pos in self.positions.values():
            if pos.is_short:
                cash += pos.abs_quantity * prices.get(pos.symbol, pos.avg_cost)
        return cash

    def to_dict(self) -> dict:
        return {
            "initial_capital": self.initial_capital,
            "cash": self.cash,
            "positions": {k: v.to_dict() for k, v in self.positions.items()},
        }