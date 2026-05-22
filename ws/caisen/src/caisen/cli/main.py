"""CLI 主入口"""

import click
import sys
from datetime import datetime
from pathlib import Path

from ..core.config import Config, BacktestConfig
from ..data.config import DataConfig
from ..core.bar import Bar
from ..core.engine import BacktestEngine
from ..strategy.base import Strategy
from ..result.persistence import ResultPersister
from ..result.metrics import PerformanceMetrics
from ..data import DataConfig, load_bars
from ..data.exceptions import DataNotFoundError


def load_strategy_from_file(file_path: str) -> Strategy:
    """从文件加载策略"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("strategy", file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # 找到 Strategy 子类
    for name in dir(module):
        obj = getattr(module, name)
        if isinstance(obj, type) and issubclass(obj, Strategy) and obj != Strategy:
            return obj()
    raise ValueError(f"No Strategy subclass found in {file_path}")


def generate_mock_bars(symbol: str, count: int) -> list:
    """生成模拟 K 线数据（仅用于测试）"""
    import random

    bars = []
    price = 100
    for i in range(count):
        timestamp = datetime(2024, 1, 1) + __import__('datetime').timedelta(days=i)
        change = random.uniform(-0.02, 0.025)
        open_price = price
        close_price = price * (1 + change)
        high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.01))
        low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.01))

        bars.append(Bar(
            timestamp=timestamp,
            symbol=symbol,
            open=round(open_price, 2),
            high=round(high_price, 2),
            low=round(low_price, 2),
            close=round(close_price, 2),
            volume=random.uniform(1000000, 5000000),
        ))
        price = close_price

    return bars


@click.group()
def cli():
    """caisen 量化回测系统"""
    pass


@cli.command()
@click.option("--strategy", "-s", required=True, help="策略名称或文件路径")
@click.option("--strategy-type", "-t", default="code", type=click.Choice(["code", "llm"]), help="策略类型 [code/llm]")
@click.option("--symbol", default="TEST", help="股票代码")
@click.option("--freq", default="1d", help="K线频率 [1d/1h/30m/15m/5m]")
@click.option("--start", default="2024-01-01", help="开始日期")
@click.option("--end", default="2024-12-31", help="结束日期")
@click.option("--config", "-c", help="配置文件路径")
@click.option("--output-dir", default="./runs", help="输出目录")
@click.option("--mock", is_flag=True, help="使用模拟数据运行测试")
@click.option("--strategy-config", help="策略配置文件路径（YAML）")
def run(strategy: str, strategy_type: str, symbol: str, freq: str, start: str, end: str, config: str, output_dir: str, mock: bool, strategy_config: str):
    """运行回测"""

    # 加载配置
    if config:
        cfg = Config.from_yaml(config)
    else:
        cfg = Config(
            backtest=BacktestConfig(),
            data=DataConfig(
                symbol=symbol,
                freq=freq,
                start=start,
                end=end,
                data_dir="/home/user/data",
            ),
            output_dir=output_dir,
        )

    # 加载策略
    if Path(strategy).exists():
        strat = load_strategy_from_file(strategy)
    else:
        # 尝试从内置策略加载
        builtin_strategies = {
            "MACrossStrategy": "caisen.strategy.ma_cross",
            "CaiSenStrategy": "caisen.strategy.cai_sen",
        }

        # 如果指定了策略配置文件，且策略是蔡森策略
        if strategy_config and strategy in ("CaiSenStrategy", "CaiSenStrategyOptimized"):
            try:
                from ..strategy.cai_sen_v2 import CaiSenStrategy
                strat = CaiSenStrategy.from_config(strategy_config)
                click.echo(f"Loaded CaiSenStrategy from config: {strategy_config}")
            except Exception as e:
                click.echo(f"Failed to load strategy config: {e}")
                sys.exit(1)
        elif strategy in builtin_strategies:
            try:
                mod = __import__(builtin_strategies[strategy], fromlist=[""])
                # 找到指定的 Strategy 子类
                target_class = None
                for name in dir(mod):
                    obj = getattr(mod, name)
                    if isinstance(obj, type) and issubclass(obj, Strategy) and obj != Strategy:
                        if name == strategy:
                            target_class = obj
                            break
                        # 如果没有精确匹配，记录第一个找到的
                        if target_class is None:
                            target_class = obj
                if target_class:
                    strat = target_class()
                else:
                    click.echo(f"Strategy '{strategy}' class not found in module")
                    sys.exit(1)
            except ImportError as e:
                click.echo(f"Failed to import {strategy}: {e}")
                sys.exit(1)
        else:
            # 尝试从 examples 加载
            try:
                from examples.ma_cross import MACrossStrategy
                strat = MACrossStrategy()
            except ImportError:
                click.echo(f"Strategy '{strategy}' not found")
                sys.exit(1)

    # 加载数据或使用 mock 数据
    if mock:
        from datetime import date
        start_date = datetime.strptime(start, "%Y-%m-%d").date()
        end_date = datetime.strptime(end, "%Y-%m-%d").date()
        days = (end_date - start_date).days + 1
        bars = generate_mock_bars(symbol, days)
        click.echo(f"Generated {len(bars)} mock bars for {symbol}")
    else:
        data_cfg = DataConfig(
            symbol=cfg.data.symbol,
            freq=cfg.data.freq,
            start=cfg.data.start,
            end=cfg.data.end,
            data_dir=cfg.data.data_dir,
        )
        try:
            bars = load_bars(data_cfg)
        except DataNotFoundError:
            click.echo("No data found. Use --mock flag to generate test data.")
            sys.exit(1)

        if not bars:
            click.echo("No data found")
            sys.exit(1)

        click.echo(f"Loaded {len(bars)} bars for {symbol}")

    click.echo(f"Running backtest with strategy: {type(strat).__name__}")

    # 运行回测
    engine = BacktestEngine(cfg.backtest if isinstance(cfg.backtest, BacktestConfig) else BacktestConfig())
    result = engine.run(strat, bars)

    # 保存结果
    run_id = ResultPersister.save(result, output_dir)
    click.echo(f"\nBacktest Complete!")
    click.echo(f"Run ID: {run_id}")
    click.echo(f"Total Trades: {len(result.trades)}")
    click.echo(f"Final Equity: {result.final_equity:.2f}")
    click.echo(f"Total Return: {result.total_return * 100:.2f}%")


@cli.command()
@click.argument("run_id")
@click.option("--output-dir", default="./runs", help="输出目录")
def show_result(run_id: str, output_dir: str):
    """查看回测结果"""
    result = ResultPersister.load(run_id, output_dir)

    if not result:
        click.echo(f"Run '{run_id}' not found")
        sys.exit(1)

    click.echo(f"\n{'='*60}")
    click.echo(f"Run ID: {result['run_id']}")
    click.echo(f"Strategy: {result['strategy_name']}")
    click.echo(f"{'='*60}")

    if "metrics" in result:
        m = result["metrics"]
        click.echo(f"\nPerformance Metrics:")
        click.echo(f"  Annual Return:  {m['annual_return']*100:.2f}%")
        click.echo(f"  Max Drawdown:   {m['max_drawdown']*100:.2f}%")
        click.echo(f"  Sharpe Ratio:   {m['sharpe_ratio']:.2f}")
        click.echo(f"  Win Rate:       {m['win_rate']*100:.2f}%")
        click.echo(f"  Total Trades:   {m['total_trades']}")


@cli.command()
@click.option("--output-dir", default="./runs", help="输出目录")
def list_runs(output_dir: str):
    """列出所有回测结果"""
    runs = ResultPersister.list_runs(output_dir)

    if not runs:
        click.echo("No runs found")
        return

    click.echo(f"\n{'Run ID':<40} {'Strategy':<20} {'Created':<20}")
    click.echo("-" * 80)
    for run in runs:
        click.echo(f"{run['run_id']:<40} {run['strategy_name']:<20} {run['created_at']:<20}")


@cli.command("web")
@click.option("--run-id", "-r", help="直接打开指定回测结果")
@click.option("--port", "-p", default=8000, help="服务端口")
@click.option("--host", default="0.0.0.0", help="服务地址")
@click.option("--output-dir", default="./runs", help="回测结果目录")
def report(run_id: str, port: int, host: str, output_dir: str):
    """启动可视化报告服务"""
    import uvicorn
    from ..web.main import create_app, set_output_dir

    # 设置 output_dir
    set_output_dir(output_dir)

    click.echo(f"Starting visualization report server at http://{host}:{port}")
    click.echo(f"Output directory: {output_dir}")

    if run_id:
        click.echo(f"Direct open run: {run_id}")
        click.echo(f"URL: http://{host}:{port}/?run_id={run_id}")

    click.echo("\nPress Ctrl+C to stop")

    # 创建 app 并启动
    app = create_app()
    uvicorn.run(app, host=host, port=port, log_level="info")


@cli.command("optimize")
@click.option("--symbol", default="TEST", help="股票代码")
@click.option("--freq", default="1d", help="K线频率")
@click.option("--start", default="2024-01-01", help="开始日期")
@click.option("--end", default="2024-12-31", help="结束日期")
@click.option("--output-dir", default="./runs", help="输出目录")
@click.option("--workers", default=4, help="并行工作线程数")
@click.option("--top-n", default=10, help="返回前N个最优结果")
@click.option("--mock", is_flag=True, help="使用模拟数据")
def optimize(symbol: str, freq: str, start: str, end: str, output_dir: str, workers: int, top_n: int, mock: bool):
    """运行蔡森策略参数优化（网格搜索）"""
    from ..strategy.caisen_optimizer import grid_search, GridSearchConfig, generate_optimized_config
    from ..data import DataConfig, load_bars

    # 加载数据
    if mock:
        bars = generate_mock_bars(symbol, 250)
    else:
        data_cfg = DataConfig(
            symbol=symbol,
            freq=freq,
            start=start,
            end=end,
            data_dir="/home/user/data",
        )
        try:
            bars = load_bars(data_cfg)
        except DataNotFoundError:
            click.echo("No data found. Use --mock flag to generate test data.")
            sys.exit(1)

    if not bars:
        click.echo("No data loaded")
        sys.exit(1)

    click.echo(f"Loaded {len(bars)} bars for {symbol}")

    # 运行优化
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 使用较小的搜索空间（快速模式）
    config = GridSearchConfig()
    # 缩减搜索空间加快速度
    config.stop_loss_factors = [0.95, 0.96, 0.97]
    config.min_profit_pcts = [0.02, 0.03]
    config.trailing_stop_pcts = [0.05]
    config.platform_min_bars_list = [10, 12]
    config.volume_thresholds = [1.5]
    config.pattern_configs = [
        {"w_bottom": True, "head_and_shoulders_bottom": True, "cup_handle": False,
         "rounding_bottom": False, "triangle": False, "flag": False,
         "rectangle": False, "breakout_pullback": False, "m_top": False,
         "head_and_shoulders_top": False},
        {"w_bottom": True, "head_and_shoulders_bottom": True, "cup_handle": True,
         "rounding_bottom": False, "triangle": False, "flag": False,
         "rectangle": False, "breakout_pullback": False, "m_top": False,
         "head_and_shoulders_top": False},
    ]

    results = grid_search(bars, config, output_dir, workers, top_n)

    if results:
        # 生成最优配置的配置文件
        best = results[0]
        config_path = Path(output_dir) / f"caisen_optimized_{timestamp}.yaml"
        generate_optimized_config(best, str(config_path))
        click.echo(f"\n最优配置已保存到: {config_path}")


def main():
    cli(prog_name="caisen")


if __name__ == "__main__":
    main()