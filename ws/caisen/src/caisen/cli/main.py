"""CLI 主入口"""

import os
import click
import sys
from datetime import datetime, timedelta
from pathlib import Path

from ..config.project_config import ProjectConfig
from ..core.config import Config, BacktestConfig
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
        timestamp = datetime(2024, 1, 1) + timedelta(days=i)
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
                data_dir=ProjectConfig.load().data_dir,
            ),
            output_dir=output_dir,
        )

    # 加载策略
    if Path(strategy).exists():
        strat = load_strategy_from_file(strategy)
    else:
        # 尝试从内置策略加载（通过 StrategyRegistry）
        from caisen.strategy.registry import StrategyRegistry
        module_path = StrategyRegistry.get_module_path(strategy)

        if strategy_config and strategy == "CaiSenStrategy":
            try:
                from caisen.strategy.algorithm.cai_sen import CaiSenStrategy
                strat = CaiSenStrategy.from_config(strategy_config)
                click.echo(f"Loaded CaiSenStrategy from config: {strategy_config}")
            except Exception as e:
                click.echo(f"Failed to load strategy config: {e}")
                sys.exit(1)
        elif module_path:
            try:
                mod = __import__(module_path, fromlist=[""])
                # 找到指定的 Strategy 子类
                target_class = None
                for name in dir(mod):
                    obj = getattr(mod, name)
                    if isinstance(obj, type) and issubclass(obj, Strategy) and obj != Strategy:
                        if name == strategy:
                            target_class = obj
                            break
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
            click.echo(f"Strategy '{strategy}' not found. "
                       f"Available: {[s['name'] for s in StrategyRegistry.list_strategies()]}")
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
    total_return = (result.final_equity - result.initial_capital) / result.initial_capital if result.initial_capital > 0 else 0
    click.echo(f"Total Return: {total_return * 100:.2f}%")


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
@click.option("--port", "-p", default=8000, help="前端端口（Vite）")
@click.option("--host", default="0.0.0.0", help="服务地址")
@click.option("--output-dir", default="./runs", help="回测结果目录")
@click.option("--backend-port", default=8001, help="后端 API 端口")
def report(run_id: str, port: int, host: str, output_dir: str, backend_port: int):
    """启动可视化报告服务（前端 + 后端）"""
    import threading
    import uvicorn
    import subprocess
    import time
    import sys
    from ..web.main import create_app, set_output_dir

    # 设置 output_dir
    set_output_dir(output_dir)

    click.echo(f"Starting visualization report server...")
    click.echo(f"  Frontend:    http://{host}:{port}")
    click.echo(f"  Backend API:  http://{host}:{backend_port}")
    click.echo(f"  Output dir:  {output_dir}")

    if run_id:
        click.echo(f"  Direct open: http://localhost:{port}/?run_id={run_id}")

    # 启动后端 (先启动，避免前端找不到 API)
    def run_backend():
        app = create_app()
        uvicorn.run(app, host=host, port=backend_port, log_level="info")

    backend_thread = threading.Thread(target=run_backend, daemon=True)
    backend_thread.start()

    # 等待后端启动
    time.sleep(1)

    # 启动前端 (Vite dev server)
    frontend_dir = Path(__file__).parent.parent / "frontend"
    vite_env = {
        **os.environ,
        'VITE_API_PROXY': f'http://localhost:{backend_port}',
    }
    import shutil
    npx_cmd = shutil.which("npx") or "npx"
    vite_process = subprocess.Popen(
        [npx_cmd, "vite", "--port", str(port), "--host", host],
        cwd=str(frontend_dir),
        env=vite_env,
    )

    click.echo("\nPress Ctrl+C to stop")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        click.echo("\nStopping servers...")
        vite_process.terminate()
        sys.exit(0)


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
            data_dir=ProjectConfig.load().data_dir,
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

        # 自动注册为配置预设（保存到 configs/strategies/）
        preset_path = Path(__file__).parent.parent.parent.parent / "configs" / "strategies" / "caisen_optimized.yaml"
        preset_path.parent.mkdir(parents=True, exist_ok=True)
        generate_optimized_config(best, str(preset_path))
        click.echo(f"已自动注册为配置预设: {preset_path}")
        click.echo(f"可直接使用: caisen run -s CaiSenStrategy -c caisen_optimized")


@cli.command("evolve-prompt")
@click.option("--config", "-c", required=True, help="LLM 策略配置文件（YAML）")
@click.option("--iterations", default=5, help="进化迭代次数")
@click.option("--output", default="configs/strategies/llm_evolved_rules.txt", help="进化规则输出路径")
@click.option("--mock", is_flag=True, help="使用模拟数据")
def evolve_prompt(config: str, iterations: int, output: str, mock: bool):
    """运行 LLM Prompt 进化，产出最优规则文件"""
    import yaml as _yaml
    from ..strategy.llm.provider import OpenAIProvider
    from ..strategy.llm.evolver import PromptEvolver

    # 加载 LLM 配置
    config_path = Path(config)
    if not config_path.exists():
        click.echo(f"配置文件不存在: {config_path}")
        sys.exit(1)

    with open(config_path, encoding="utf-8") as f:
        raw = _yaml.safe_load(f)

    llm_data = raw.get("llm", {})
    api_key = llm_data.get("api_key", "dummy")
    base_url = llm_data.get("base_url", "http://localhost:8199/v1")
    model = llm_data.get("model", "gpt-4o")
    temperature = llm_data.get("temperature", 0.3)

    # 创建 LLM 客户端
    provider_kwargs = {}
    for key in ("disable_thinking", "max_tokens"):
        if key in llm_data:
            provider_kwargs[key] = llm_data[key]

    client = OpenAIProvider(
        api_key=api_key,
        model=model,
        temperature=temperature,
        base_url=base_url,
        **provider_kwargs,
    )

    # 加载数据
    data_cfg_raw = raw.get("data", {})
    symbol = data_cfg_raw.get("symbol", "TEST")
    freq = data_cfg_raw.get("freq", "1d")
    start = data_cfg_raw.get("start", "2024-01-01")
    end = data_cfg_raw.get("end", "2024-12-31")

    if mock:
        bars = [
            {"timestamp": f"2024-01-{i+1:02d}", "open": 100 + i, "high": 102 + i,
             "low": 99 + i, "close": 101 + i, "volume": 1000000 + i * 10000}
            for i in range(30)
        ]
    else:
        data_cfg = DataConfig(
            symbol=symbol, freq=freq, start=start, end=end,
            data_dir=ProjectConfig.load().data_dir,
        )
        try:
            raw_bars = load_bars(data_cfg)
        except DataNotFoundError:
            click.echo("No data found. Use --mock flag to generate test data.")
            sys.exit(1)
        # 转换为 dict 列表供 evolver 使用
        bars = []
        for bar in raw_bars:
            if hasattr(bar, "to_dict"):
                bars.append(bar.to_dict())
            else:
                bars.append({
                    "timestamp": str(bar.timestamp),
                    "open": bar.open, "high": bar.high,
                    "low": bar.low, "close": bar.close,
                    "volume": bar.volume,
                })

    click.echo(f"Loaded {len(bars)} bars for {symbol} ({freq})")
    click.echo(f"开始 Prompt 进化（{iterations} 次迭代）...")

    # 运行进化
    evolver = PromptEvolver(
        llm_client=client,
        bars=bars,
        max_iterations=iterations,
    )

    from ..strategy.llm.prompts.caisen_pattern import RULES_FRAMEWORK
    result = evolver.evolve(initial_rules=RULES_FRAMEWORK)

    # 保存最优规则
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result.prompt, encoding="utf-8")

    click.echo(f"\n进化完成!")
    click.echo(f"  最佳评分: {result.score:.4f}")
    click.echo(f"  迭代次数: {len(evolver.history)}")
    click.echo(f"  最优规则已保存到: {output_path}")
    click.echo(f"  下次回测将自动加载此规则（需在 YAML 配置中设置 evolved_rules_path）")


def main():
    cli(prog_name="caisen")


if __name__ == "__main__":
    main()