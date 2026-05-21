"""
蔡森策略配置文件加载器
"""

import yaml
from dataclasses import dataclass, field
from typing import Dict, Optional, Any
from pathlib import Path


@dataclass
class CaiSenConfig:
    """蔡森策略配置"""

    # ========== 平台检测参数 ==========
    platform_min_bars: int = 10
    platform_max_amplitude: float = 0.05
    platform_volume_decline: bool = True

    # ========== 破底翻参数 ==========
    breakdown_max_pct: float = 0.02
    breakdown_max_bars: int = 2
    pullback_max_bars: int = 3
    volume_confirm: bool = True

    # ========== 仓位管理 ==========
    first_position_pct: float = 0.30
    second_position_pct: float = 0.50

    # ========== 风险控制（可迭代优化） ==========
    stop_loss_factor: float = 0.96       # 止损系数（破底低点 × factor）
    min_profit_pct: float = 0.03         # 最小盈利目标
    trailing_stop_pct: float = 0.05      # 移动止损回撤百分比
    trailing_stop_enabled: bool = False  # 是否启用移动止损
    volume_threshold: float = 1.5       # 放量倍数阈值
    w_bottom_tolerance: float = 0.05    # W底双底容差
    min_neckline_height: float = 0.02    # 颈线最小高度要求

    # ========== 胜率增强参数 ==========
    long_only_mode: bool = False        # 只做多头
    max_loss_pct: float = 0.0           # 最大亏损容忍比例

    # ========== 形态开关 ==========
    w_bottom_enabled: bool = True
    m_top_enabled: bool = True
    head_and_shoulders_bottom_enabled: bool = True
    head_and_shoulders_top_enabled: bool = True
    triangle_enabled: bool = True
    flag_enabled: bool = True
    rectangle_enabled: bool = True
    rounding_bottom_enabled: bool = True
    cup_handle_enabled: bool = True
    breakout_pullback_enabled: bool = True

    # ========== 形态权重（用于形态质量评分） ==========
    pattern_weights: Dict[str, float] = field(default_factory=lambda: {
        "W_BOTTOM": 1.0,
        "HEAD_AND_SHOULDERS_BOTTOM": 1.0,
        "CUP_HANDLE": 0.8,
        "ROUNDING_BOTTOM": 0.6,
        "TRIANGLE": 0.5,
        "FLAG": 0.5,
        "RECTANGLE": 0.5,
        "BREAKOUT_PULLBACK": 0.7,
        # 空头形态
        "M_TOP": 0.8,
        "HEAD_AND_SHOULDERS_TOP": 0.8,
    })

    @classmethod
    def from_yaml(cls, path: str | Path) -> "CaiSenConfig":
        """从 YAML 文件加载配置"""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data:
            raise ValueError(f"Empty config file: {path}")

        params = data.get("params", {})
        patterns = data.get("patterns", {})

        # 构建配置
        config = cls()

        # 从 YAML 覆盖参数
        for key, value in params.items():
            if hasattr(config, key):
                setattr(config, key, value)

        # 处理形态开关
        if patterns:
            # YAML 名称到属性的映射
            name_map = {
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
            }
            for pattern_name, enabled in patterns.items():
                attr_name = name_map.get(pattern_name)
                if attr_name and hasattr(config, attr_name):
                    setattr(config, attr_name, enabled)

        return config

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "platform_min_bars": self.platform_min_bars,
            "platform_max_amplitude": self.platform_max_amplitude,
            "platform_volume_decline": self.platform_volume_decline,
            "breakdown_max_pct": self.breakdown_max_pct,
            "breakdown_max_bars": self.breakdown_max_bars,
            "pullback_max_bars": self.pullback_max_bars,
            "volume_confirm": self.volume_confirm,
            "first_position_pct": self.first_position_pct,
            "second_position_pct": self.second_position_pct,
            "stop_loss_factor": self.stop_loss_factor,
            "min_profit_pct": self.min_profit_pct,
            "trailing_stop_pct": self.trailing_stop_pct,
            "trailing_stop_enabled": self.trailing_stop_enabled,
            "w_bottom_enabled": self.w_bottom_enabled,
            "m_top_enabled": self.m_top_enabled,
            "head_and_shoulders_bottom_enabled": self.head_and_shoulders_bottom_enabled,
            "head_and_shoulders_top_enabled": self.head_and_shoulders_top_enabled,
            "triangle_enabled": self.triangle_enabled,
            "flag_enabled": self.flag_enabled,
            "rectangle_enabled": self.rectangle_enabled,
            "rounding_bottom_enabled": self.rounding_bottom_enabled,
            "cup_handle_enabled": self.cup_handle_enabled,
            "breakout_pullback_enabled": self.breakout_pullback_enabled,
            "pattern_weights": self.pattern_weights,
            "long_only_mode": self.long_only_mode,
            "max_loss_pct": self.max_loss_pct,
        }