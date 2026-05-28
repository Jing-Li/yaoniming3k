"""CaiSenStrategy - 组合形态检测器（组件化版本）

基于 ADR-0011 的组件拆分：
- DetectorFactory: 检测器创建
- SignalAggregator: 信号聚合评分
- PositionManager: 仓位管理

策略只做决策，组件各司其职。
"""

import os
from typing import List, Optional, Dict, Any, TYPE_CHECKING

from ..base import Strategy, Annotation, AnnotationType, BarResult
from .detector import PatternDetector, PatternSignal
from .caisen_components import DetectorFactory, SignalAggregator, PositionManager

if TYPE_CHECKING:
    from caisen.core.bar import Bar
    from caisen.core.order import Order
    from caisen.core.config import BacktestConfig


def load_config_from_yaml(config_path: str) -> Dict[str, Any]:
    """从 YAML 文件加载配置"""
    try:
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except ImportError:
        raise ImportError("需要安装 pyyaml: pip install pyyaml")
    except FileNotFoundError:
        raise FileNotFoundError(f"配置文件不存在: {config_path}")


class CaiSenStrategy(Strategy):
    """蔡森策略 V2 - 组件化架构

    组件职责：
    - DetectorFactory: 创建检测器
    - SignalAggregator: 聚合信号计算评分
    - PositionManager: 管理持仓和风控

    策略只负责流程编排和决策。

    Args:
        detectors: 形态检测器列表
        weights: 各检测器权重，如 {"w_bottom": 0.3}
        threshold: 综合评分阈值 (0~1)
        stop_loss_factor: 止损系数
        min_profit_pct: 最小盈利目标
        enabled_patterns: 启用的形态列表
    """

    @classmethod
    def from_config(cls, config_path: str = None, config_dict: Dict = None) -> "CaiSenStrategy":
        """从配置文件创建策略"""
        if config_dict is None:
            if config_path is None:
                _base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                config_path = os.path.join(_base, "configs", "cai_sen_v2.yaml")
            config_dict = load_config_from_yaml(config_path)

        strategy_cfg = config_dict.get("strategy", {})
        weights = config_dict.get("weights", {})
        risk_cfg = config_dict.get("risk", {})
        enabled = config_dict.get("enabled_patterns", {})
        detector_cfg = config_dict.get("detectors", {})

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
        breakdown_pullback_enabled: bool = True,
        fake_breakout_enabled: bool = True,
        stop_loss_factor_legacy: float = 0.96,
        min_profit_pct_legacy: float = 0.03,
        **kwargs,
    ):
        # 如果没有传入检测器，使用 DetectorFactory 创建
        if detectors is None:
            if enabled_patterns is None:
                enabled_patterns = self._get_enabled_patterns(
                    w_bottom_enabled, m_top_enabled,
                    head_and_shoulders_bottom_enabled, head_and_shoulders_top_enabled,
                    triangle_enabled, flag_enabled, rectangle_enabled,
                    rounding_bottom_enabled, cup_handle_enabled, breakout_pullback_enabled,
                    breakdown_pullback_enabled, fake_breakout_enabled,
                )

            factory = DetectorFactory(
                default_stop_loss=stop_loss_factor_legacy,
                default_profit_pct=min_profit_pct_legacy,
            )
            detectors = factory.create(enabled_patterns, detector_config or {})

        self.detectors = detectors
        self.weights = weights or {d.name: 1.0 / len(detectors) for d in detectors}
        self.threshold = threshold
        self.stop_loss_factor = stop_loss_factor
        self.min_profit_pct = min_profit_pct

        # 组件
        self._aggregator = SignalAggregator()
        self._position_mgr = PositionManager()

        # 状态
        self.bars: List["Bar"] = []

    @staticmethod
    def _get_enabled_patterns(
        w_bottom: bool, m_top: bool,
        hs_bottom: bool, hs_top: bool,
        triangle: bool, flag: bool,
        rectangle: bool, rounding: bool,
        cup_handle: bool, breakout: bool,
        breakdown_pullback: bool, fake_breakout: bool,
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
        if breakdown_pullback:
            patterns.append("breakdown_pullback")
        if fake_breakout:
            patterns.append("fake_breakout")
        return patterns

    def on_init(self, config: "BacktestConfig") -> None:
        """回测初始化"""
        pass

    def on_bar(self, bar: "Bar") -> "BarResult":
        """每根K线调用，返回 BarResult

        流程（ADR-0011）：
        1. 更新 K 线列表
        2. 检测器检测形态
        3. SignalAggregator 聚合评分
        4. 决策：入场 / 止损 / 止盈
        """
        from caisen.core.order import Order, Side

        self.bars.append(bar)

        # 1. 检测信号
        signals = [detector.detect(self.bars) for detector in self.detectors]

        # 2. 聚合评分
        result = self._aggregator.aggregate(signals, self.weights)

        # 3. 决策
        # 入场 - 使用最佳信号的 confidence 而非 total_score
        if result.best_signal and result.best_signal.confidence >= self.threshold and not self._position_mgr.has_position:
            ann = self._make_pattern_annotation(result.best_signal)
            self._position_mgr.open(result.best_signal, bar)
            order = Order(
                side=Side.BUY,
                symbol=bar.symbol,
                quantity=0,
                stop_loss=result.best_signal.stop_loss,
                target=result.best_signal.target,
            )
            return BarResult(order=order, annotations=[ann])

        # 止损检查
        if self._position_mgr.check_stop_loss(bar):
            self._position_mgr.close()
            return BarResult(order=Order(side=Side.SELL, symbol=bar.symbol, quantity=0))

        # 止盈检查
        if self._position_mgr.check_take_profit(bar):
            self._position_mgr.close()
            return BarResult(order=Order(side=Side.SELL, symbol=bar.symbol, quantity=0))

        return BarResult()

    def _make_pattern_annotation(self, signal: PatternSignal) -> Annotation:
        """构造形态可视化标注（不再维护内部 list）"""
        return Annotation(
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

    def on_session_end(self) -> None:
        """回测结束"""
        pass

    def reset(self) -> None:
        """重置策略状态"""
        self.bars = []
        self._position_mgr.reset()