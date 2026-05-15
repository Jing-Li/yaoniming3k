"""蔡森策略真实数据回测

使用 caisen-data 的本地数据运行回测
"""

from datetime import datetime
from pathlib import Path

from caisen.core.engine import BacktestEngine
from caisen.core.config import BacktestConfig
from caisen.data.local import LocalDataLoader
from caisen.data.config import DataConfig
from caisen.strategy.cai_sen import CaiSenStrategy


def run_backtest():
    """运行真实数据回测"""
    print("=" * 60)
    print("蔡森策略回测 - 白银(ag) 2023-2024")
    print("=" * 60)

    # 使用 LocalDataLoader 加载数据
    data_dir = Path("../caisen-data/data")
    if not data_dir.exists():
        data_dir = Path("./data")

    loader = LocalDataLoader(data_dir=str(data_dir))

    config = DataConfig(
        symbol="ag",
        freq="1d",
        start="2023-01-01",
        end="2024-12-31",
        data_dir=str(data_dir)
    )

    try:
        bars = loader.load(config)
    except Exception as e:
        print(f"加载数据失败: {e}")
        return

    print(f"\n加载 {len(bars)} 根K线")
    print(f"时间范围: {bars[0].timestamp.date()} ~ {bars[-1].timestamp.date()}")
    print(f"价格范围: {min(b.low for b in bars):.0f} ~ {max(b.high for b in bars):.0f}")

    # 创建策略（放宽参数以适应真实数据）
    strategy = CaiSenStrategy(
        platform_min_bars=4,      # 最少4根K线形成平台
        platform_max_amplitude=0.05,  # 最大5%振幅
        breakdown_max_pct=0.03,  # 破底最大3%
        pullback_max_bars=5,      # 5根K线内必须拉回
        volume_confirm=False,     # 关闭成交量确认（真实数据中可能太严格）
    )

    # 创建回测引擎
    config = BacktestConfig(
        initial_capital=100000,
        commission_rate=0.0003,  # 期货手续费约万分之3
        slippage=0.0001,         # 滑点万分之一
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
        print(f"  {i}. {trade.side.value:4} @ {trade.price:8.2f} "
              f"数量:{trade.quantity:6.0f} "
              f"时间:{trade.timestamp.strftime('%m-%d')}")

    if strategy.signals:
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

    # 计算绩效指标
    from caisen.result.metrics import calculate_metrics
    metrics = calculate_metrics(result)
    print(f"  最大回撤: {metrics.max_drawdown*100:.2f}%")
    print(f"  夏普比率: {metrics.sharpe_ratio:.2f}")
    print(f"  总交易数: {metrics.total_trades}")
    print(f"  胜率: {metrics.win_rate*100:.1f}%")

    # 净值曲线摘要
    if len(result.equity_curve) > 0:
        print(f"\n净值曲线摘要:")
        print(f"  起点: {result.equity_curve[0]['equity']:,.2f}")
        print(f"  终点: {result.equity_curve[-1]['equity']:,.2f}")
        max_equity = max(e['equity'] for e in result.equity_curve)
        min_equity = min(e['equity'] for e in result.equity_curve)
        print(f"  最高: {max_equity:,.2f}")
        print(f"  最低: {min_equity:,.2f}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    run_backtest()
