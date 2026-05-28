"""BacktestRunner：封装完整回测流程，与 HTTP/WebSocket 层解耦。

流程：加载数据 → 实例化策略 → 运行引擎（带进度回调）→ 持久化结果 → 返回 run_id
"""

from __future__ import annotations

import importlib
import inspect
from pathlib import Path
from typing import Callable, List, Optional

from caisen.config.project_config import ProjectConfig
from caisen.core.bar import Bar
from caisen.core.config import BacktestConfig
from caisen.core.engine import BacktestEngine
from caisen.result.persistence import ResultPersister
from caisen.strategy.base import Strategy
from caisen.strategy.registry import StrategyRegistry


class BacktestError(Exception):
    """回测执行失败"""


class BacktestRunner:
    @staticmethod
    def run_backtest(
        strategy_name: str,
        symbol: str,
        freq: str,
        start: str,
        end: str,
        params: dict | None = None,
        config_name: Optional[str] = None,
        on_progress: Optional[Callable[[int, int, str], None]] = None,
        output_dir: Optional[str] = None,
        bars: Optional[List[Bar]] = None,  # 注入 bars（测试用）；None 时从磁盘加载
    ) -> str:
        """执行完整回测，返回 run_id。

        Args:
            strategy_name: 注册的策略类名
            symbol: 品种代码
            freq: K 线频率
            start: 开始日期（YYYY-MM-DD）
            end: 结束日期（YYYY-MM-DD）
            params: 策略参数字典（直接注入，优先级最高；测试用）
            config_name: 配置预设文件名（不含 .yaml），如 "caisen_default"；
                         指定时从 configs/strategies/{config_name}.yaml 读取参数；
                         params 和 config_name 均为 None 时使用策略 __init__ 默认值
            on_progress: 可选进度回调，每 100 根调用一次
            output_dir: 输出目录（None 时从 ProjectConfig 读取）
            bars: 直接注入 K 线数据（测试专用，跳过磁盘加载）

        Returns:
            run_id 字符串

        Raises:
            BacktestError: 策略不存在、数据为空等明确错误
        """
        cfg = ProjectConfig.load()
        if output_dir is None:
            output_dir = cfg.output_dir

        # 解析参数：params > config_name > 默认值
        if params is None:
            params = _load_params_from_config(config_name) if config_name else {}

        # 1. 实例化策略
        strategy = _instantiate_strategy(strategy_name, params)

        # 2. 加载数据
        if bars is None:
            bars = _load_bars(cfg.data_dir, symbol, freq, start, end)

        if len(bars) == 0:
            raise BacktestError(f"数据为空：{symbol} {freq} {start}~{end}")

        # 3. 运行引擎（带进度回调）
        engine = BacktestEngine(BacktestConfig())
        total = len(bars)
        _counter = [0]

        def _on_bar(idx: int, bar: Bar) -> None:
            _counter[0] += 1
            if on_progress and (_counter[0] % 100 == 0 or _counter[0] == total - 1):
                on_progress(_counter[0], total, bar.timestamp.strftime("%Y-%m-%d"))

        result = engine.run(strategy, bars, on_bar=_on_bar)

        # 4. 持久化，返回 run_id
        run_id = ResultPersister.save(result, output_dir=output_dir)
        return run_id


def _load_params_from_config(config_name: str) -> dict:
    """从 configs/strategies/{config_name}.yaml 加载策略参数。

    文件不存在时返回空字典（策略使用 __init__ 默认值）。
    只提取 strategy/risk/weights/enabled_patterns 等顶层键下的参数，
    展平为单层 dict 传给策略 __init__。
    """
    configs_dir = Path(__file__).parent.parent.parent.parent / "configs" / "strategies"
    yaml_path = configs_dir / f"{config_name}.yaml"
    if not yaml_path.exists():
        return {}

    try:
        import yaml  # pyyaml
        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        return {}

    # 展平：合并所有顶层 dict 值中的参数
    params: dict = {}
    for v in data.values():
        if isinstance(v, dict):
            params.update(v)
    return params


def _instantiate_strategy(strategy_name: str, params: dict) -> Strategy:
    """从注册表找到策略类并实例化。"""
    registry = {s["name"]: s for s in StrategyRegistry.list_strategies()}
    if strategy_name not in registry:
        raise BacktestError(f"策略不存在：{strategy_name}")

    # 根据类型找到对应模块
    _MODULE_MAP = {
        "CaiSenStrategy": "caisen.strategy.algorithm.cai_sen",
        "MACrossStrategy": "caisen.strategy.algorithm.ma_cross",
        "LLMStrategy": "caisen.strategy.llm.strategy",
    }
    module_path = _MODULE_MAP.get(strategy_name)
    if module_path is None:
        raise BacktestError(f"策略模块未注册：{strategy_name}")

    try:
        mod = importlib.import_module(module_path)
        cls = getattr(mod, strategy_name)
    except Exception as e:
        raise BacktestError(f"策略加载失败：{strategy_name}，原因：{e}") from e

    # 过滤 params，只传 __init__ 接受的参数
    sig = inspect.signature(cls.__init__)
    accepted = {
        k for k, p in sig.parameters.items()
        if k != "self" and p.default is not inspect.Parameter.empty
    }
    filtered = {k: v for k, v in params.items() if k in accepted}
    return cls(**filtered)


def _load_bars(data_dir: str, symbol: str, freq: str, start: str, end: str) -> list:
    """从磁盘加载行情数据。"""
    from caisen.data.config import DataConfig
    from caisen.data import load_bars
    from caisen.data.exceptions import DataNotFoundError

    data_cfg = DataConfig(
        symbol=symbol,
        freq=freq,
        start=start,
        end=end,
        data_dir=data_dir,
    )
    try:
        return load_bars(data_cfg)
    except DataNotFoundError:
        return []
