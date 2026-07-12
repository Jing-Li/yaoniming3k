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
        raw_yaml = {}
        if params is None:
            if config_name:
                params, raw_yaml = _load_params_from_config(config_name)
            else:
                params = {}

        # 判断是否为 LLM 策略
        is_llm = raw_yaml.get("mode") == "llm" or "llm" in raw_yaml

        # 1. 实例化策略
        strategy = _instantiate_strategy(strategy_name, params, raw_yaml=raw_yaml if is_llm else None)

        # 2. 加载数据
        if bars is None:
            bars = _load_bars(cfg.data_dir, symbol, freq, start, end)

        if len(bars) == 0:
            raise BacktestError(f"数据为空：{symbol} {freq} {start}~{end}")

        # 3. 运行引擎（带进度回调）
        #    丰富 BacktestConfig，附带数据信息供 LLM 策略 on_init 使用
        bt_config = BacktestConfig()
        bt_config.symbol = symbol
        bt_config.freq = freq
        bt_config.start = start
        bt_config.end = end
        bt_config.data_dir = cfg.data_dir
        engine = BacktestEngine(bt_config)

        # LLM 策略：预先注入 bars，避免 on_init 重复加载
        if is_llm and hasattr(strategy, '_bars'):
            strategy._bars = bars
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


def _load_params_from_config(config_name: str) -> tuple:
    """从 configs/strategies/{config_name}.yaml 加载策略参数。

    文件不存在时返回 ({}, {})。
    兼容两套 YAML schema：
    - Schema A (V2): strategy/weights/risk/enabled_patterns/detectors
    - Schema B (legacy): params/patterns/pattern_weights
    展平并转换为 CaiSenStrategy.__init__ 可接受的单层 dict。

    Returns:
        (params_dict, raw_yaml_dict) 元组
    """
    configs_dir = Path(__file__).parent.parent.parent.parent / "configs" / "strategies"
    yaml_path = configs_dir / f"{config_name}.yaml"
    if not yaml_path.exists():
        return {}, {}

    try:
        import yaml  # pyyaml
        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        return {}, {}

    # 先做基础展平
    params: dict = {}
    for v in data.values():
        if isinstance(v, dict):
            params.update(v)

    # ===== Schema 归一化 =====

    # 1) enabled_patterns (Schema A): dict → list of enabled pattern names
    #    只在 YAML 显式包含 enabled_patterns 节时才设置，否则留给 *_enabled 参数控制
    enabled = data.get("enabled_patterns")
    if isinstance(enabled, dict):
        params["enabled_patterns"] = [k for k, v in enabled.items() if v]
    elif isinstance(enabled, list):
        params["enabled_patterns"] = enabled

    # 2) weights (Schema A): 直接传递 weights dict
    if "weights" in data and isinstance(data["weights"], dict):
        params["weights"] = data["weights"]

    # 3) strategy.threshold (Schema A)
    strategy_cfg = data.get("strategy", {})
    if isinstance(strategy_cfg, dict) and "threshold" in strategy_cfg:
        params["threshold"] = strategy_cfg["threshold"]

    # 4) risk (Schema A): 展开 risk 节
    risk_cfg = data.get("risk", {})
    if isinstance(risk_cfg, dict):
        for key in ("stop_loss_factor", "min_profit_pct",
                     "trailing_stop_enabled", "trailing_stop_pct"):
            if key in risk_cfg:
                params[key] = risk_cfg[key]

    # 5) patterns (Schema B): UPPERCASE → lowercase_enabled
    _UPPER_PATTERN_MAP = {
        "W_BOTTOM": "w_bottom_enabled",
        "M_TOP": "m_top_enabled",
        "HEAD_AND_SHOULDERS_BOTTOM": "head_and_shoulders_bottom_enabled",
        "HEAD_AND_SHOULDERS_TOP": "head_and_shoulders_top_enabled",
        "TRIANGLE": "triangle_enabled",
        "FLAG": "flag_enabled",
        "RECTANGLE": "rectangle_enabled",
        "ROUNDING_BOTTOM": "rounding_bottom_enabled",
        "CUP_HANDLE": "cup_handle_enabled",
        "BREAKOUT_PULLBACK": "breakout_pullback_enabled",
        "BREAKDOWN_PULLBACK": "breakdown_pullback_enabled",
        "FAKE_BREAKOUT": "fake_breakout_enabled",
    }
    patterns_cfg = data.get("patterns", {})
    if isinstance(patterns_cfg, dict):
        for upper_key, lower_key in _UPPER_PATTERN_MAP.items():
            if upper_key in patterns_cfg:
                params[lower_key] = patterns_cfg[upper_key]

    # 6) 清理 params 中残留的大写形态 key（展平时混入的，不会被 __init__ 接受）
    for upper_key in _UPPER_PATTERN_MAP:
        params.pop(upper_key, None)

    # 7) detectors (Schema A): nested dict → detector_config
    if "detectors" in data and isinstance(data["detectors"], dict):
        params["detector_config"] = data["detectors"]

    # 8) pattern_weights (Schema B) → 也作为 detector_config 传入
    pw = data.get("pattern_weights", {})
    if isinstance(pw, dict) and "detector_config" not in params:
        params["detector_config"] = {"pattern_weights": pw}

    return params, data


def _instantiate_strategy(strategy_name: str, params: dict,
                          raw_yaml: dict = None) -> Strategy:
    """从注册表找到策略类并实例化。

    Args:
        strategy_name: 注册的策略类名
        params: 策略参数字典
        raw_yaml: 原始 YAML 数据（LLM 策略专用，用于构建 LLMStrategyConfig）
    """
    module_path = StrategyRegistry.get_module_path(strategy_name)
    if module_path is None:
        raise BacktestError(f"策略模块未注册：{strategy_name}")

    try:
        mod = importlib.import_module(module_path)
        cls = getattr(mod, strategy_name)
    except Exception as e:
        raise BacktestError(f"策略加载失败：{strategy_name}，原因：{e}") from e

    # LLM 策略专用处理：从 raw_yaml 构建 LLMStrategyConfig
    if raw_yaml and "llm" in raw_yaml:
        from caisen.core.config import LLMStrategyConfig
        llm_data = raw_yaml["llm"]
        llm_config = LLMStrategyConfig(
            provider=llm_data.get("provider", "openai"),
            api_key=llm_data.get("api_key", "dummy"),
            base_url=llm_data.get("base_url", ""),
            model=llm_data.get("model", "gpt-4o"),
            temperature=llm_data.get("temperature", 0.3),
            rules=llm_data.get("rules", ""),
            examples=llm_data.get("examples", 0),
            evolved_rules_path=llm_data.get("evolved_rules_path", ""),
            cache_enabled=llm_data.get("cache_enabled", True),
            cache_dir=llm_data.get("cache_dir", "./cache"),
            walk_forward=llm_data.get("walk_forward", True),
        )
        # 构建额外参数
        kwargs = {"config": llm_config}

        # 传入 disable_thinking / max_tokens（OpenAIProvider 支持）
        provider_kwargs = {}
        for key in ("disable_thinking", "max_tokens"):
            if key in llm_data:
                provider_kwargs[key] = llm_data[key]
        if provider_kwargs:
            llm_config._provider_kwargs = provider_kwargs

        return cls(**kwargs)

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
