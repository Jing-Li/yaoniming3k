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
        "caisen.strategy.algorithm.ma_cross",
        "MACrossStrategy",
        "均线交叉策略",
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
    "MACrossStrategy": "ma_cross_",
    "LLMStrategy": "llm_",
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
    类型映射：int → "int"，float → "float"，bool → "bool"，其他 → "str"
    """
    try:
        sig = inspect.signature(cls.__init__)
    except (ValueError, TypeError):
        return []

    schema = []
    for name, param in sig.parameters.items():
        if name == "self":
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
        schema.append({
            "name": name,
            "type": ptype,
            "default": default,
            "min": None,
            "max": None,
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
                schema = _extract_params_schema(cls)
                presets = _scan_config_presets(class_name)
                results.append({
                    "name": class_name,
                    "display_name": display_name,
                    "type": strategy_type,
                    "note": note,
                    "params_schema": schema,
                    "config_presets": presets,
                })
            except Exception:
                continue  # 跳过导入失败的策略
        return results
