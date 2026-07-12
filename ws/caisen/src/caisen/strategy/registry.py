"""StrategyRegistry：动态扫描并注册所有可用策略。

扫描范围：
- strategy/algorithm/ 下的 Strategy 子类（type: "code"）
- strategy/llm/ 下的 Strategy 子类（type: "llm"）

导入失败时跳过该策略，不影响整体列表。
"""

import importlib
import inspect
from pathlib import Path
from typing import Any

from caisen.strategy.base import Strategy

# 内置策略清单：(模块路径, 类名, display_name, type, note)
_BUILTIN_STRATEGIES = [
    (
        "caisen.strategy.algorithm.cai_sen",
        "CaiSenStrategy",
        "蔡森策略",
        "code",
        None,
    ),
    (
        "caisen.strategy.llm.strategy",
        "LLMStrategy",
        "LLM 策略",
        "llm",
        "需要服务器端预先配置 API Key",
    ),
]

# 策略名 → configs/strategies/ 下的文件名前缀映射
_STRATEGY_CONFIG_PREFIX = {
    "CaiSenStrategy": "caisen_",
    "LLMStrategy": "llm_",
}

# params_schema 中需要过滤掉的复杂参数（不在 UI 中展示）
_HIDDEN_PARAMS = {
    "detectors", "weights", "enabled_patterns", "detector_config",
    "kwargs",
    # LLMStrategy 内部组件参数
    "llm_client", "config", "prompt_builder", "response_parser", "data_source",
}

# 参数名 → 中文显示名映射
_PARAM_DISPLAY_NAMES = {
    "threshold": "信号阈值",
    "stop_loss_factor": "止损因子",
    "min_profit_pct": "最小止盈比例",
    "stop_loss_factor_legacy": "止损因子(旧)",
    "min_profit_pct_legacy": "最小止盈(旧)",
    "w_bottom_enabled": "W底",
    "m_top_enabled": "M顶",
    "head_and_shoulders_bottom_enabled": "头肩底",
    "head_and_shoulders_top_enabled": "头肩顶",
    "triangle_enabled": "三角形",
    "flag_enabled": "旗形",
    "rectangle_enabled": "矩形",
    "rounding_bottom_enabled": "圆弧底",
    "cup_handle_enabled": "杯柄形",
    "breakout_pullback_enabled": "突破回踩",
    "breakdown_pullback_enabled": "破底回踩",
    "fake_breakout_enabled": "假突破",
}


def _scan_config_presets(strategy_name: str) -> list[str]:
    """扫描 configs/strategies/ 目录，返回该策略可用的配置预设名称列表。

    预设名称为去掉 .yaml 后缀的文件名，按字母序排列。
    找不到对应目录或无匹配文件时返回空列表。
    """
    prefix = _STRATEGY_CONFIG_PREFIX.get(strategy_name, "")
    if not prefix:
        return []

    # configs/ 目录相对于本文件：src/caisen/strategy/ → ../../.. → 项目根
    configs_dir = Path(__file__).parent.parent.parent.parent / "configs" / "strategies"
    if not configs_dir.exists():
        return []

    presets = sorted(
        p.stem for p in configs_dir.glob(f"{prefix}*.yaml")
    )
    return presets


def _extract_params_schema(cls: type) -> list[dict]:
    """从策略类的 __init__ 签名提取参数 schema。

    跳过 self，只处理有默认值的参数。
    过滤掉复杂类型参数（List、Dict 等），只保留可调的标量参数。
    """
    try:
        sig = inspect.signature(cls.__init__)
    except (ValueError, TypeError):
        return []

    schema = []
    for name, param in sig.parameters.items():
        if name == "self" or name in _HIDDEN_PARAMS:
            continue
        if param.default is inspect.Parameter.empty:
            continue  # 必填参数暂不纳入 schema
        default = param.default
        if isinstance(default, bool):
            ptype = "bool"
        elif isinstance(default, int):
            ptype = "int"
        elif isinstance(default, float):
            ptype = "float"
        else:
            ptype = "str"
        # 跳过非 None 的复杂默认值（如 list、dict）
        if default is not None and ptype == "str" and not isinstance(default, (str, type(None))):
            continue
        schema.append({
            "name": name,
            "display_name": _PARAM_DISPLAY_NAMES.get(name, name),
            "type": ptype,
            "default": default,
            "min": None,
            "max": None,
            "options": None,
        })
    return schema


def _get_optimize_config(strategy_name: str) -> dict | None:
    """返回策略的优化配置（供前端渲染参数范围使用）。

    CaiSenStrategy → GridSearchConfig 默认值
    LLMStrategy → 进化配置（代数等）
    """
    if strategy_name == "CaiSenStrategy":
        try:
            from caisen.strategy.algorithm.caisen_optimizer import GridSearchConfig
            cfg = GridSearchConfig()
            return {
                "type": "grid_search",
                "strategy": "CaiSenStrategy",
                "params": {
                    "stop_loss_factor": {
                        "display_name": "止损因子",
                        "values": cfg.stop_loss_factors,
                    },
                    "min_profit_pct": {
                        "display_name": "最小止盈",
                        "values": cfg.min_profit_pcts,
                    },
                    "trailing_stop_pct": {
                        "display_name": "移动止损",
                        "values": cfg.trailing_stop_pcts,
                    },
                    "platform_min_bars": {
                        "display_name": "平台最小K线数",
                        "values": cfg.platform_min_bars_list,
                    },
                    "volume_threshold": {
                        "display_name": "成交量阈值",
                        "values": cfg.volume_thresholds,
                    },
                },
                "pattern_presets": [
                    {"name": "激进", "desc": "仅W底+头肩底",
                     "w_bottom": True, "head_and_shoulders_bottom": True,
                     "cup_handle": False, "rounding_bottom": False,
                     "triangle": False, "flag": False, "rectangle": False,
                     "breakout_pullback": False, "m_top": False,
                     "head_and_shoulders_top": False},
                    {"name": "平衡", "desc": "主要看涨形态",
                     "w_bottom": True, "head_and_shoulders_bottom": True,
                     "cup_handle": True, "rounding_bottom": True,
                     "triangle": False, "flag": False, "rectangle": False,
                     "breakout_pullback": False, "m_top": False,
                     "head_and_shoulders_top": False},
                    {"name": "保守", "desc": "全形态开启",
                     "w_bottom": True, "head_and_shoulders_bottom": True,
                     "cup_handle": True, "rounding_bottom": True,
                     "triangle": True, "flag": True, "rectangle": True,
                     "breakout_pullback": True, "m_top": True,
                     "head_and_shoulders_top": True},
                ],
                "total_combinations": cfg.total_combinations,
            }
        except ImportError:
            return None

    elif strategy_name == "LLMStrategy":
        return {
            "type": "prompt_evolution",
            "strategy": "LLMStrategy",
            "max_generations": 5,
        }

    return None


def _enrich_schema_with_ranges(schema: list[dict], optimize_config: dict | None) -> list[dict]:
    """用 optimize_config 的真实搜索范围填充 params_schema 的 options 字段。"""
    if not optimize_config or optimize_config.get("type") != "grid_search":
        return schema
    opt_params = optimize_config.get("params", {})
    for item in schema:
        if item["name"] in opt_params:
            item["options"] = opt_params[item["name"]]["values"]
            item["display_name"] = opt_params[item["name"]].get("display_name", item["display_name"])
    return schema


def _build_llm_schema() -> list[dict]:
    """为 LLMStrategy 构建 params_schema，包含 prompt 模板信息。"""
    schema = []
    try:
        from caisen.strategy.llm.prompts import RULES_FRAMEWORK
        # 截取前 200 字符作为预览
        rules_preview = RULES_FRAMEWORK[:200].strip()
        if len(RULES_FRAMEWORK) > 200:
            rules_preview += "..."
        schema.append({
            "name": "rules_template",
            "display_name": "交易规则模板",
            "type": "text",
            "default": rules_preview,
            "full_text": RULES_FRAMEWORK,
            "min": None,
            "max": None,
            "options": None,
        })
    except ImportError:
        pass
    schema.append({
        "name": "max_generations",
        "display_name": "进化最大代数",
        "type": "int",
        "default": 5,
        "min": 1,
        "max": 20,
        "options": None,
    })
    return schema


class StrategyRegistry:
    @staticmethod
    def list_strategies() -> list[dict]:
        """返回所有可用策略的描述列表。

        某策略导入失败时跳过该策略，不抛出异常。
        """
        results = []
        for module_path, class_name, display_name, strategy_type, note in _BUILTIN_STRATEGIES:
            try:
                mod = importlib.import_module(module_path)
                cls = getattr(mod, class_name)
                if not (inspect.isclass(cls) and issubclass(cls, Strategy)):
                    continue
                optimize_config = _get_optimize_config(class_name)
                presets = _scan_config_presets(class_name)

                if class_name == "LLMStrategy":
                    schema = _build_llm_schema()
                else:
                    schema = _extract_params_schema(cls)
                    schema = _enrich_schema_with_ranges(schema, optimize_config)

                results.append({
                    "name": class_name,
                    "display_name": display_name,
                    "type": strategy_type,
                    "note": note,
                    "params_schema": schema,
                    "config_presets": presets,
                    "optimize_config": optimize_config,
                })
            except Exception:
                continue  # 跳过导入失败的策略
        return results

    @staticmethod
    def get_module_path(strategy_name: str) -> str | None:
        """根据策略类名返回其模块路径，未注册时返回 None。"""
        for module_path, class_name, *_ in _BUILTIN_STRATEGIES:
            if class_name == strategy_name:
                return module_path
        return None
