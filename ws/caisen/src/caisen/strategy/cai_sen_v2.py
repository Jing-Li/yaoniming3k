"""CaiSenStrategy V2 - 组合形态检测器的新实现"""

import os
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from .base import Strategy, Annotation, AnnotationType
from .detector import PatternDetector, PatternSignal
from .patterns import (
    WBottomDetector, MTopDetector,
    HeadAndShouldersBottomDetector, HeadAndShouldersTopDetector,
    TriangleDetector,
    FlagDetector, RectangleDetector, RoundingBottomDetector,
    CupHandleDetector, BreakoutPullbackDetector,
)

if TYPE_CHECKING:
    from ..core.bar import Bar
    from ..core.order import Order
    from ..core.config import BacktestConfig


def load_config_from_yaml(config_path: str) -> Dict[str, Any]:
    """从 YAML 文件加载配置

    Args:
        config_path: 配置文件路径

    Returns:
        配置字典
    """
    try:
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except ImportError:
        raise ImportError("需要安装 pyyaml: pip install pyyaml")
    except FileNotFoundError:
        raise FileNotFoundError(f"配置文件不存在: {config_path}")


class CaiSenStrategy(Strategy):
    """蔡森策略 V2 - 组合形态检测器

    新架构：策略只做决策，检测器只做检测。

    Args:
        detectors: 形态检测器列表
        weights: 各检测器权重 dict，如 {"w_bottom": 0.3}
        threshold: 综合评分阈值 (0~1)
        stop_loss_factor: 止损系数
        min_profit_pct: 最小盈利目标百分比
        enabled_patterns: 启用的形态列表，如 ["w_bottom", "m_top"]
    """

    @classmethod
    def from_config(cls, config_path: str = None, config_dict: Dict = None) -> "CaiSenStrategy":
        """从配置文件创建策略

        Args:
            config_path: YAML 配置文件路径
            config_dict: 配置字典（直接传入）

        Returns:
            CaiSenStrategy 实例
        """
        if config_dict is None:
            if config_path is None:
                # 默认配置文件在项目根目录的 configs/ 下
                # strategy/cai_sen_v2.py -> caisen -> src -> 项目根 -> configs/
                import os
                _base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                config_path = os.path.join(_base, "configs", "cai_sen_v2.yaml")
            config_dict = load_config_from_yaml(config_path)

        # 解析配置
        strategy_cfg = config_dict.get("strategy", {})
        weights = config_dict.get("weights", {})
        risk_cfg = config_dict.get("risk", {})
        enabled = config_dict.get("enabled_patterns", {})
        detector_cfg = config_dict.get("detectors", {})

        # 构建 enabled_patterns 列表
        enabled_patterns = [k for k, v in enabled.items() if v]

        return cls(
            weights=weights,
            threshold=strategy_cfg.get("threshold", 0.6),
            stop_loss_factor=risk_cfg.get("stop_loss_factor", 0.93),
            min_profit_pct=risk_cfg.get("min_profit_pct", 0.03),
            enabled_patterns=enabled_patterns,
            detector_config=detector_cfg,
        )

    def __init__(
        self,
        detectors: List[PatternDetector] = None,
        weights: Dict[str, float] = None,
        threshold: float = 0.6,
        stop_loss_factor: float = 0.93,
        min_profit_pct: float = 0.03,
        enabled_patterns: List[str] = None,
        detector_config: Dict[str, Any] = None,
        # ===== 向下兼容参数 =====
        platform_min_bars: int = 10,
        platform_max_amplitude: float = 0.05,
        w_bottom_enabled: bool = True,
        m_top_enabled: bool = True,
        head_and_shoulders_bottom_enabled: bool = True,
        head_and_shoulders_top_enabled: bool = True,
        triangle_enabled: bool = True,
        flag_enabled: bool = True,
        rectangle_enabled: bool = True,
        rounding_bottom_enabled: bool = True,
        cup_handle_enabled: bool = True,
        breakout_pullback_enabled: bool = True,
        stop_loss_factor_legacy: float = 0.96,
        min_profit_pct_legacy: float = 0.03,
        **kwargs,
    ):
        self.detector_config = detector_config or {}

        # 如果没有传入检测器，使用默认检测器
        if detectors is None:
            # 构建启用的形态列表
            if enabled_patterns is None:
                enabled_patterns = self._get_enabled_patterns(
                    w_bottom_enabled, m_top_enabled,
                    head_and_shoulders_bottom_enabled, head_and_shoulders_top_enabled,
                    triangle_enabled, flag_enabled, rectangle_enabled,
                    rounding_bottom_enabled, cup_handle_enabled, breakout_pullback_enabled,
                )

            detectors = self._create_default_detectors(
                stop_loss_factor=stop_loss_factor_legacy,
                min_profit_pct=min_profit_pct_legacy,
                enabled_patterns=enabled_patterns,
                detector_config=self.detector_config,
            )

        self.detectors = detectors
        self.weights = weights or {d.name: 1.0 / len(detectors) for d in detectors}
        self.threshold = threshold
        self.stop_loss_factor = stop_loss_factor
        self.min_profit_pct = min_profit_pct

        # 状态
        self.bars: List["Bar"] = []
        self.annotations: List[Annotation] = []
        self.position = 0
        self.entry_price = 0.0
        self.current_stop_loss = 0.0

    @staticmethod
    def _get_enabled_patterns(
        w_bottom: bool, m_top: bool,
        hs_bottom: bool, hs_top: bool,
        triangle: bool, flag: bool,
        rectangle: bool, rounding: bool,
        cup_handle: bool, breakout: bool,
    ) -> List[str]:
        """根据开关获取启用的形态列表"""
        patterns = []
        if w_bottom:
            patterns.append("w_bottom")
        if m_top:
            patterns.append("m_top")
        if hs_bottom:
            patterns.append("head_and_shoulders_bottom")
        if hs_top:
            patterns.append("head_and_shoulders_top")
        if triangle:
            patterns.append("triangle")
        if flag:
            patterns.append("flag")
        if rectangle:
            patterns.append("rectangle")
        if rounding:
            patterns.append("rounding_bottom")
        if cup_handle:
            patterns.append("cup_handle")
        if breakout:
            patterns.append("breakout_pullback")
        return patterns

    @staticmethod
    def _create_default_detectors(
        stop_loss_factor: float,
        min_profit_pct: float,
        enabled_patterns: List[str],
        detector_config: Dict[str, Any] = None,
    ) -> List[PatternDetector]:
        """创建默认检测器列表

        Args:
            stop_loss_factor: 默认止损系数
            min_profit_pct: 默认最小盈利目标
            enabled_patterns: 启用的形态列表
            detector_config: 检测器专用配置
        """
        detectors = []
        detector_config = detector_config or {}

        if "w_bottom" in enabled_patterns:
            cfg = detector_config.get("w_bottom", {})
            detectors.append(WBottomDetector(
                tolerance=cfg.get("tolerance", 0.05),
                stop_loss_factor=cfg.get("stop_loss_factor", stop_loss_factor),
                min_profit_pct=cfg.get("min_profit_pct", min_profit_pct),
            ))

        if "m_top" in enabled_patterns:
            cfg = detector_config.get("m_top", {})
            detectors.append(MTopDetector(
                tolerance=cfg.get("tolerance", 0.05),
                stop_loss_factor=cfg.get("stop_loss_factor", 1.02),
                min_profit_pct=cfg.get("min_profit_pct", min_profit_pct),
            ))

        if "head_and_shoulders_bottom" in enabled_patterns:
            cfg = detector_config.get("head_and_shoulders", {})
            detectors.append(HeadAndShouldersBottomDetector(
                shoulder_tolerance=cfg.get("shoulder_tolerance", 0.05),
                stop_loss_factor=cfg.get("stop_loss_factor", stop_loss_factor),
                min_profit_pct=cfg.get("min_profit_pct", min_profit_pct),
            ))

        if "head_and_shoulders_top" in enabled_patterns:
            cfg = detector_config.get("head_and_shoulders", {})
            detectors.append(HeadAndShouldersTopDetector(
                shoulder_tolerance=cfg.get("shoulder_tolerance", 0.05),
                stop_loss_factor=cfg.get("stop_loss_factor", 1.02),
                min_profit_pct=cfg.get("min_profit_pct", min_profit_pct),
            ))

        if "triangle" in enabled_patterns:
            cfg = detector_config.get("triangle", {})
            detectors.append(TriangleDetector(
                min_bars=cfg.get("min_bars", 11),
                min_highs=cfg.get("min_highs", 3),
                min_lows=cfg.get("min_lows", 3),
                stop_loss_factor=cfg.get("stop_loss_factor", stop_loss_factor),
                min_profit_pct=cfg.get("min_profit_pct", min_profit_pct),
            ))

        if "flag" in enabled_patterns:
            cfg = detector_config.get("flag", {})
            detectors.append(FlagDetector(
                min_bars=cfg.get("min_bars", 8),
                max_bars=cfg.get("max_bars", 20),
                stop_loss_factor=cfg.get("stop_loss_factor", stop_loss_factor),
                min_profit_pct=cfg.get("min_profit_pct", min_profit_pct),
            ))

        if "rectangle" in enabled_patterns:
            cfg = detector_config.get("rectangle", {})
            detectors.append(RectangleDetector(
                min_bars=cfg.get("min_bars", 10),
                max_amplitude=cfg.get("max_amplitude", 0.05),
                stop_loss_factor=cfg.get("stop_loss_factor", stop_loss_factor),
                min_profit_pct=cfg.get("min_profit_pct", min_profit_pct),
            ))

        if "rounding_bottom" in enabled_patterns:
            cfg = detector_config.get("rounding_bottom", {})
            detectors.append(RoundingBottomDetector(
                min_bars=cfg.get("min_bars", 15),
                stop_loss_factor=cfg.get("stop_loss_factor", stop_loss_factor),
                min_profit_pct=cfg.get("min_profit_pct", min_profit_pct),
            ))

        if "cup_handle" in enabled_patterns:
            cfg = detector_config.get("cup_handle", {})
            detectors.append(CupHandleDetector(
                min_bars=cfg.get("min_bars", 20),
                stop_loss_factor=cfg.get("stop_loss_factor", stop_loss_factor),
                min_profit_pct=cfg.get("min_profit_pct", min_profit_pct),
            ))

        if "breakout_pullback" in enabled_patterns:
            cfg = detector_config.get("breakout_pullback", {})
            detectors.append(BreakoutPullbackDetector(
                lookback_period=cfg.get("lookback_period", 30),
                stop_loss_factor=cfg.get("stop_loss_factor", stop_loss_factor),
                min_profit_pct=cfg.get("min_profit_pct", min_profit_pct),
            ))

        return detectors

    def on_init(self, config: "BacktestConfig") -> None:
        """回测初始化"""
        pass

    def on_bar(self, bar: "Bar") -> Optional["Order"]:
        """每根K线调用

        流程：
        1. 更新所有检测器
        2. 计算综合评分
        3. 决策是否下单
        """
        from ...core.order import Order, Side

        self.bars.append(bar)

        # 更新所有检测器
        for detector in self.detectors:
            detector.update(bar)

        # 计算综合评分
        total_score = 0.0
        best_signal: Optional[PatternSignal] = None
        signals: List[PatternSignal] = []

        for detector in self.detectors:
            signal = detector.detect()
            if signal:
                weight = self.weights.get(detector.name, 0)
                total_score += signal.confidence * weight
                signals.append(signal)
                if not best_signal or signal.confidence > best_signal.confidence:
                    best_signal = signal

        # 达到阈值，下单
        if total_score >= self.threshold and best_signal and self.position == 0:
            # 添加可视化标注
            self._add_pattern_annotation(best_signal)

            self.position = 1
            self.entry_price = bar.close
            self.current_stop_loss = best_signal.stop_loss

            return Order(
                side=Side.BUY,
                symbol=bar.symbol,
                quantity=0,  # 全仓
                stop_loss=best_signal.stop_loss,
                target=best_signal.target,
            )

        # 止损检查
        if self.position > 0 and bar.low < self.current_stop_loss:
            self.position = 0
            return Order(
                side=Side.SELL,
                symbol=bar.symbol,
                quantity=0,  # 全仓
            )

        # 止盈检查
        if self.position > 0 and best_signal:
            target = best_signal.target
            if bar.high >= target:
                self.position = 0
                return Order(
                    side=Side.SELL,
                    symbol=bar.symbol,
                    quantity=0,
                )

        return None

    def _add_pattern_annotation(self, signal: PatternSignal) -> None:
        """添加形态可视化标注"""
        ann = Annotation(
            type=AnnotationType.PATTERN_MARK,
            timestamp=self.bars[-1].timestamp if self.bars else None,
            data={
                "pattern": signal.pattern,
                "points": signal.points,
                "confidence": signal.confidence,
                "stop_loss": signal.stop_loss,
                "target": signal.target,
                "label": f"{signal.pattern} ({signal.confidence:.0%})",
            },
        )
        self.annotations.append(ann)

    def on_session_end(self) -> None:
        """回测结束"""
        pass

    def get_annotations(self) -> List[Annotation]:
        """获取可视化标注"""
        return self.annotations

    def reset(self) -> None:
        """重置策略状态"""
        self.bars = []
        self.annotations = []
        self.position = 0
        self.entry_price = 0.0
        self.current_stop_loss = 0.0
        for detector in self.detectors:
            detector.reset()