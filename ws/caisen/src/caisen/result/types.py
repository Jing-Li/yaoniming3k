"""Result types for backtesting."""

from dataclasses import dataclass
from typing import List

from ..core.annotation import Annotation


@dataclass
class BacktestResult:
    """回测结果

    一次 Run 的输出，包含交易记录、净值曲线、绩效指标、可视化标注等结构化数据。

    纯数据容器，不含计算逻辑。

    Attributes:
        strategy_name: 策略名称
        bars: K线数据列表
        trades: 交易记录列表
        equity_curve: 净值曲线数据
        annotations: 可视化标注列表
        initial_capital: 初始资金
        final_equity: 最终净值
    """
    strategy_name: str
    bars: List
    trades: List
    equity_curve: List[dict]
    annotations: List[Annotation]
    initial_capital: float
    final_equity: float