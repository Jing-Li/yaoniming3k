"""DetectorFactory - 检测器工厂

根据配置创建检测器实例。
"""

from typing import List, Dict, Any, TYPE_CHECKING

from ..detector import PatternDetector
from ..patterns import (
    WBottomDetector, MTopDetector,
    HeadAndShouldersBottomDetector, HeadAndShouldersTopDetector,
    TriangleDetector,
    FlagDetector, RectangleDetector, RoundingBottomDetector,
    CupHandleDetector, BreakoutPullbackDetector,
)

if TYPE_CHECKING:
    from ....core.bar import Bar


# 检测器类映射
DETECTOR_CLASSES = {
    "w_bottom": WBottomDetector,
    "m_top": MTopDetector,
    "head_and_shoulders_bottom": HeadAndShouldersBottomDetector,
    "head_and_shoulders_top": HeadAndShouldersTopDetector,
    "triangle": TriangleDetector,
    "flag": FlagDetector,
    "rectangle": RectangleDetector,
    "rounding_bottom": RoundingBottomDetector,
    "cup_handle": CupHandleDetector,
    "breakout_pullback": BreakoutPullbackDetector,
}

# 检测器默认配置
DEFAULT_DETECTOR_CONFIG = {
    "w_bottom": {"tolerance": 0.05, "stop_loss_factor": 0.93, "min_profit_pct": 0.03},
    "m_top": {"tolerance": 0.05, "stop_loss_factor": 1.02, "min_profit_pct": 0.03},
    "head_and_shoulders": {"shoulder_tolerance": 0.05, "stop_loss_factor": 0.93, "min_profit_pct": 0.03},
    "triangle": {"min_bars": 11, "min_highs": 3, "min_lows": 3, "stop_loss_factor": 0.93, "min_profit_pct": 0.03},
    "flag": {"min_bars": 8, "max_bars": 20, "stop_loss_factor": 0.93, "min_profit_pct": 0.03},
    "rectangle": {"min_bars": 10, "max_amplitude": 0.05, "stop_loss_factor": 0.93, "min_profit_pct": 0.03},
    "rounding_bottom": {"min_bars": 15, "stop_loss_factor": 0.93, "min_profit_pct": 0.03},
    "cup_handle": {"min_bars": 20, "stop_loss_factor": 0.93, "min_profit_pct": 0.03},
    "breakout_pullback": {"lookback_period": 30, "stop_loss_factor": 0.93, "min_profit_pct": 0.03},
}


class DetectorFactory:
    """检测器工厂

    根据配置创建检测器实例。

    Example:
        factory = DetectorFactory()
        detectors = factory.create(
            enabled_patterns=["w_bottom", "m_top"],
            config={"stop_loss_factor": 0.95}
        )
    """

    def __init__(
        self,
        default_stop_loss: float = 0.93,
        default_profit_pct: float = 0.03,
    ):
        """初始化工厂

        Args:
            default_stop_loss: 默认止损系数
            default_profit_pct: 默认最小盈利目标
        """
        self.default_stop_loss = default_stop_loss
        self.default_profit_pct = default_profit_pct

    def create(
        self,
        enabled_patterns: List[str],
        detector_config: Dict[str, Any] = None,
    ) -> List[PatternDetector]:
        """创建检测器列表

        Args:
            enabled_patterns: 启用的形态列表，如 ["w_bottom", "m_top"]
            detector_config: 检测器专用配置

        Returns:
            检测器实例列表
        """
        detector_config = detector_config or {}
        detectors = []

        for pattern_name in enabled_patterns:
            detector_class = DETECTOR_CLASSES.get(pattern_name)
            if detector_class is None:
                continue

            # 合并配置
            cfg = self._merge_config(pattern_name, detector_config)

            # 创建实例
            detector = self._create_detector(detector_class, pattern_name, cfg)
            if detector:
                detectors.append(detector)

        return detectors

    def _merge_config(
        self,
        pattern_name: str,
        detector_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """合并配置

        Args:
            pattern_name: 形态名称
            detector_config: 检测器配置

        Returns:
            合并后的配置
        """
        # 获取默认配置
        if pattern_name in DEFAULT_DETECTOR_CONFIG:
            cfg = dict(DEFAULT_DETECTOR_CONFIG[pattern_name])
        else:
            cfg = {}

        # 应用传入的配置
        specific_cfg = detector_config.get(pattern_name, {})
        cfg.update(specific_cfg)

        return cfg

    def _create_detector(
        self,
        detector_class: type,
        pattern_name: str,
        config: Dict[str, Any],
    ) -> PatternDetector:
        """创建单个检测器

        Args:
            detector_class: 检测器类
            pattern_name: 形态名称
            config: 配置字典

        Returns:
            检测器实例
        """
        # 根据形态名称选择构造参数
        if pattern_name == "w_bottom":
            return detector_class(
                tolerance=config.get("tolerance", 0.05),
                stop_loss_factor=config.get("stop_loss_factor", self.default_stop_loss),
                min_profit_pct=config.get("min_profit_pct", self.default_profit_pct),
            )
        elif pattern_name == "m_top":
            return detector_class(
                tolerance=config.get("tolerance", 0.05),
                stop_loss_factor=config.get("stop_loss_factor", 1.02),
                min_profit_pct=config.get("min_profit_pct", self.default_profit_pct),
            )
        elif pattern_name in ("head_and_shoulders_bottom", "head_and_shoulders_top"):
            return detector_class(
                shoulder_tolerance=config.get("shoulder_tolerance", 0.05),
                stop_loss_factor=config.get("stop_loss_factor", self.default_stop_loss),
                min_profit_pct=config.get("min_profit_pct", self.default_profit_pct),
            )
        elif pattern_name == "triangle":
            return detector_class(
                min_bars=config.get("min_bars", 11),
                min_highs=config.get("min_highs", 3),
                min_lows=config.get("min_lows", 3),
                stop_loss_factor=config.get("stop_loss_factor", self.default_stop_loss),
                min_profit_pct=config.get("min_profit_pct", self.default_profit_pct),
            )
        elif pattern_name == "flag":
            return detector_class(
                min_bars=config.get("min_bars", 8),
                max_bars=config.get("max_bars", 20),
                stop_loss_factor=config.get("stop_loss_factor", self.default_stop_loss),
                min_profit_pct=config.get("min_profit_pct", self.default_profit_pct),
            )
        elif pattern_name == "rectangle":
            return detector_class(
                min_bars=config.get("min_bars", 10),
                max_amplitude=config.get("max_amplitude", 0.05),
                stop_loss_factor=config.get("stop_loss_factor", self.default_stop_loss),
                min_profit_pct=config.get("min_profit_pct", self.default_profit_pct),
            )
        elif pattern_name == "rounding_bottom":
            return detector_class(
                min_bars=config.get("min_bars", 15),
                stop_loss_factor=config.get("stop_loss_factor", self.default_stop_loss),
                min_profit_pct=config.get("min_profit_pct", self.default_profit_pct),
            )
        elif pattern_name == "cup_handle":
            return detector_class(
                min_bars=config.get("min_bars", 20),
                stop_loss_factor=config.get("stop_loss_factor", self.default_stop_loss),
                min_profit_pct=config.get("min_profit_pct", self.default_profit_pct),
            )
        elif pattern_name == "breakout_pullback":
            return detector_class(
                lookback_period=config.get("lookback_period", 30),
                stop_loss_factor=config.get("stop_loss_factor", self.default_stop_loss),
                min_profit_pct=config.get("min_profit_pct", self.default_profit_pct),
            )
        else:
            return detector_class()