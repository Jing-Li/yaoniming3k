"""蔡森策略回测示例

使用模拟数据演示破底翻策略的回测流程
"""

from datetime import datetime, timedelta
from typing import List

from caisen.core.bar import Bar
from caisen.core.engine import BacktestEngine
from caisen.core.config import BacktestConfig
from caisen.strategy.cai_sen import CaiSenStrategy


def generate_platform_bars(start_idx: int, n: int, base_price: float, amplitude: float = 0.03) -> List[Bar]:
    """生成整理平台K线"""
    bars = []
    for i in range(n):
        # 价格在 base_price ± amplitude/2 范围内波动
        noise = (i % 3 - 1) * amplitude * base_price / 3
        close = base_price + noise
        high = close + amplitude * base_price / 4
        low = close - amplitude * base_price / 4
        open_p = close - (i % 2 - 0.5) * amplitude * base_price / 6
        
        bars.append(Bar(
            timestamp=datetime(2024, 1, 1) + timedelta(days=start_idx + i),
            symbol="TEST",
            open=round(open_p, 2),
            high=round(high, 2),
            low=round(low, 2),
            close=round(close, 2),
            volume=1000 + i * 10
        ))
    return bars


def generate_breakdown_scenario() -> List[Bar]:
    """
    生成破底翻场景数据
    
    场景:
    1. 10根K线形成整理平台 (价格100±1.5)
    2. 1根K线破底 (跌破98.5)
    3. 1根K线拉回 (站回99以上)
    4. 1根K线突破平台上沿 (突破101.5)
    """
    bars = []
    
    # 1. 整理平台 (10根K线，价格100±1.5)
    platform_bars = generate_platform_bars(0, 10, 100.0, 0.03)
    bars.extend(platform_bars)
    
    # 平台上沿约101.5，下沿约98.5
    platform_upper = 101.5
    platform_lower = 98.5
    
    # 2. 破底 (跌破平台下沿约1%)
    breakdown_price = platform_lower * 0.99  # 约97.5
    bars.append(Bar(
        timestamp=datetime(2024, 1, 11),
        symbol="TEST",
        open=99.0,
        high=99.5,
        low=breakdown_price * 0.998,
        close=breakdown_price,
        volume=2500  # 破底放量
    ))
    
    # 3. 拉回 (站回平台下沿之上)
    pullback_price = platform_lower * 1.01  # 约99.5
    bars.append(Bar(
        timestamp=datetime(2024, 1, 12),
        symbol="TEST",
        open=breakdown_price,
        high=pullback_price * 1.02,
        low=breakdown_price * 0.995,
        close=pullback_price,
        volume=3000  # 拉回放量，主力吸筹
    ))
    
    # 4. 突破平台上沿 (第二买点)
    breakout_price = platform_upper * 1.02  # 约103.5
    bars.append(Bar(
        timestamp=datetime(2024, 1, 13),
        symbol="TEST",
        open=pullback_price,
        high=breakout_price * 1.01,
        low=platform_upper * 0.995,
        close=breakout_price,
        volume=3500  # 突破放量
    ))
    
    # 5. 继续上涨到目标价附近
    for i in range(5):
        bars.append(Bar(
            timestamp=datetime(2024, 1, 14 + i),
            symbol="TEST",
            open=breakout_price + i * 0.5,
            high=breakout_price + i * 0.5 + 0.5,
            low=breakout_price + i * 0.5 - 0.3,
            close=breakout_price + (i + 1) * 0.5,
            volume=2000
        ))
    
    return bars


def run_backtest():
    """运行回测"""
    print("=" * 60)
    print("蔡森策略回测示例 - 破底翻形态")
    print("=" * 60)
    
    # 生成测试数据
    bars = generate_breakdown_scenario()
    print(f"\n生成 {len(bars)} 根测试K线")
    print(f"整理平台: K线0-9 (价格约100±1.5)")
    print(f"破底: K线10 (跌破98.5)")
    print(f"拉回: K线11 (站回99.5) -> 第一买点")
    print(f"突破: K线12 (突破101.5) -> 第二买点")
    
    # 创建策略
    strategy = CaiSenStrategy(
        platform_min_bars=10,
        platform_max_amplitude=0.05,
        breakdown_max_pct=0.02,
        pullback_max_bars=3
    )
    
    # 创建回测引擎
    config = BacktestConfig(
        initial_capital=100000,
        commission_rate=0.001,
        slippage=0.001
    )
    engine = BacktestEngine(config)
    
    # 运行回测
    print("\n" + "-" * 60)
    print("开始回测...")
    print("-" * 60)
    
    result = engine.run(strategy, bars)
    
    # 输出结果
    print("\n" + "=" * 60)
    print("回测结果")
    print("=" * 60)
    
    print(f"\n交易记录 ({len(result.trades)} 笔):")
    for i, trade in enumerate(result.trades, 1):
        print(f"  {i}. {trade.side.value} @ {trade.price:.2f} "
              f"数量:{trade.quantity:.0f} "
              f"时间:{trade.timestamp.strftime('%m-%d')}")
    
    print(f"\n信号记录 ({len(strategy.signals)} 个):")
    for sig in strategy.signals:
        print(f"  - {sig.action}: {sig.reason}")
        print(f"    价格:{sig.price:.2f} 止损:{sig.stop_loss:.2f} 目标:{sig.target:.2f}")
    
    print(f"\n绩效指标:")
    print(f"  初始资金: {config.initial_capital:,.0f}")
    
    if result.equity_curve:
        final_equity = result.equity_curve[-1].get('equity', config.initial_capital)
        print(f"  最终净值: {final_equity:,.2f}")
        print(f"  收益率: {(final_equity/config.initial_capital - 1)*100:.2f}%")
    
    # 计算并显示绩效指标
    from caisen.result.calculator import MetricsCalculator
    calculator = MetricsCalculator()
    metrics = calculator.calculate(result)
    print(f"  最大回撤: {metrics.max_drawdown*100:.2f}%")
    print(f"  夏普比率: {metrics.sharpe_ratio:.2f}")
    print(f"  总交易数: {metrics.total_trades}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    run_backtest()
