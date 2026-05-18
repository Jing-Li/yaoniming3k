"""BacktestEngine (回测引擎)"""

from dataclasses import dataclass
from typing import List, Optional, Dict
from .bar import Bar
from .order import Order, Side
from .trade import Trade
from .portfolio import Portfolio
from .position import Position
from .config import BacktestConfig
from ..strategy.base import Strategy, Annotation


class BacktestEngine:
    """回测引擎核心"""

    def __init__(self, config: BacktestConfig):
        self.config = config
        self.portfolio = Portfolio(
            initial_capital=config.initial_capital,
            cash=config.initial_capital
        )
        self.trades: List[Trade] = []
        self.equity_curve: List[dict] = []
        self.annotations: List[Annotation] = []
        self.strategy: Optional[Strategy] = None

    def run(self, strategy: Strategy, bars: List[Bar]) -> "BacktestResult":
        """运行回测"""
        self.strategy = strategy

        # 初始化策略
        strategy.on_init(self.config)

        # 主循环
        for i, bar in enumerate(bars[:-1]):
            # 策略决策
            order = strategy.on_bar(bar)

            # 执行订单
            if order:
                trade = self._execute_order(order, bar, bars[i + 1])
                if trade:
                    self.trades.append(trade)

            # 更新净值
            self._update_equity(bar)

            # 收集标注
            self.annotations.extend(strategy.get_annotations())

        # 最终更新
        self._update_equity(bars[-1])

        # 结束策略
        strategy.on_session_end()

        # 返回结果
        last_bar = bars[-1]
        final_equity = self.portfolio.get_equity_with_prices({last_bar.symbol: last_bar.close})
        return BacktestResult(
            strategy_name=type(strategy).__name__,
            bars=bars,
            trades=self.trades,
            equity_curve=self.equity_curve,
            annotations=self.annotations,
            initial_capital=self.config.initial_capital,
            final_equity=final_equity,
        )

    def _execute_order(self, order: Order, bar: Bar, next_bar: Bar) -> Optional[Trade]:
        """执行订单"""
        # 计算成交价
        execution_price = next_bar.open
        if order.side == Side.BUY:
            execution_price *= (1 + self.config.slippage)
        else:
            execution_price *= (1 - self.config.slippage)

        # 计算数量
        quantity = self._calculate_quantity(order, execution_price)
        if quantity <= 0:
            return None

        # 手续费
        commission = execution_price * quantity * self.config.commission_rate

        # 更新持仓
        self._update_position(order.symbol, order.side, quantity, execution_price)

        # 更新现金
        if order.side == Side.BUY:
            self.portfolio.cash -= (execution_price * quantity + commission)
        else:
            self.portfolio.cash += (execution_price * quantity - commission)

        return Trade(
            timestamp=next_bar.timestamp,
            symbol=order.symbol,
            side=order.side,
            quantity=quantity,
            price=execution_price,
            commission=commission,
            slippage=abs(execution_price - bar.open),
            order_id=order.order_id,
        )

    def _calculate_quantity(self, order: Order, execution_price: float) -> float:
        """计算实际成交数量"""
        if order.quantity > 0:
            return order.quantity

        prices = {order.symbol: execution_price}
        available = self.portfolio.get_available_cash(prices)

        if order.side == Side.BUY:
            # 计算可买入的最大数量
            max_quantity = available / (execution_price * (1 + self.config.commission_rate))

            # 按仓位比例下单
            if order.position_pct > 0:
                return max_quantity * order.position_pct
            else:
                # 全仓
                return max_quantity
        else:
            # 卖出：按仓位比例或全仓
            pos = self.portfolio.positions.get(order.symbol)
            if pos:
                if order.position_pct > 0:
                    return pos.abs_quantity * order.position_pct
                else:
                    return pos.abs_quantity
            return 0

    def _update_position(self, symbol: str, side: Side, quantity: float, execution_price: float):
        """更新持仓"""
        position = self.portfolio.positions.get(symbol)

        if side == Side.BUY:
            if position is None:
                # 无持仓，直接开多
                self.portfolio.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=quantity,
                    avg_cost=execution_price,
                )
            elif position.is_short:
                # 平空仓
                position.quantity += quantity
                if abs(position.quantity) < 1e-6:
                    del self.portfolio.positions[symbol]
                position.avg_cost = 0
            else:
                # 追加多头
                total_cost = position.avg_cost * position.quantity + execution_price * quantity
                position.quantity += quantity
                position.avg_cost = total_cost / position.quantity
        else:  # SELL
            if position is None:
                # 无持仓，开空头
                self.portfolio.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=-quantity,
                    avg_cost=execution_price,
                )
            elif position.is_long:
                # 平多仓
                position.quantity -= quantity
                if abs(position.quantity) < 1e-6:
                    del self.portfolio.positions[symbol]
                # 平多不更新avg_cost
            else:
                # 追加空头
                total_cost = position.avg_cost * abs(position.quantity) + execution_price * quantity
                position.quantity -= quantity
                position.avg_cost = total_cost / abs(position.quantity)

    def _update_equity(self, bar: Bar):
        """更新净值曲线"""
        equity = self.portfolio.get_equity_with_prices({bar.symbol: bar.close})
        self.equity_curve.append({
            "timestamp": bar.timestamp.isoformat(),
            "equity": equity,
            "cash": self.portfolio.cash,
            "positions": {k: v.quantity for k, v in self.portfolio.positions.items()},
        })


@dataclass
class BacktestResult:
    """回测结果"""
    strategy_name: str
    bars: List[Bar]
    trades: List[Trade]
    equity_curve: List[dict]
    annotations: List[Annotation]
    initial_capital: float
    final_equity: float

    @property
    def total_return(self) -> float:
        """总收益率"""
        return (self.final_equity - self.initial_capital) / self.initial_capital

    @property
    def max_drawdown(self) -> float:
        """最大回撤 (从峰值到谷底的最大跌幅)"""
        if not self.equity_curve:
            return 0.0

        peak = 0.0
        max_dd = 0.0

        for entry in self.equity_curve:
            equity = entry.get("equity", 0)
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd

        return max_dd

    @property
    def sharpe_ratio(self) -> float:
        """夏普比率 (假设无风险利率为0，年化)"""
        if len(self.equity_curve) < 2:
            return 0.0

        # 计算每日收益率
        returns = []
        for i in range(1, len(self.equity_curve)):
            prev_equity = self.equity_curve[i - 1].get("equity", 0)
            curr_equity = self.equity_curve[i].get("equity", 0)
            if prev_equity > 0:
                returns.append((curr_equity - prev_equity) / prev_equity)

        if not returns or len(returns) < 2:
            return 0.0

        # 平均收益率
        avg_return = sum(returns) / len(returns)

        # 标准差
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        std = variance ** 0.5

        if std == 0:
            return 0.0

        # 年化 (假设252交易日)
        return (avg_return / std) * (252 ** 0.5)

    @property
    def win_rate(self) -> float:
        """胜率 (盈利交易数 / 总交易数)"""
        if not self.trades:
            return 0.0

        # 配对交易：按时间顺序匹配 BUY/SELL
        position = None
        profits = []

        for trade in sorted(self.trades, key=lambda t: t.timestamp):
            if trade.side == Side.BUY:
                position = {"price": trade.price, "qty": trade.quantity}
            elif trade.side == Side.SELL and position:
                profit = (trade.price - position["price"]) * position["qty"]
                profits.append(profit)
                position = None

        if not profits:
            return 0.0

        wins = sum(1 for p in profits if p > 0)
        return wins / len(profits)

    @property
    def profit_factor(self) -> float:
        """盈亏比 (总盈利 / 总亏损)"""
        if not self.trades:
            return 0.0

        # 配对交易
        position = None
        gross_profit = 0.0
        gross_loss = 0.0

        for trade in sorted(self.trades, key=lambda t: t.timestamp):
            if trade.side == Side.BUY:
                position = {"price": trade.price, "qty": trade.quantity}
            elif trade.side == Side.SELL and position:
                profit = (trade.price - position["price"]) * position["qty"]
                if profit > 0:
                    gross_profit += profit
                else:
                    gross_loss += abs(profit)
                position = None

        if gross_loss == 0:
            return 0.0 if gross_profit == 0 else float('inf')

        return gross_profit / gross_loss