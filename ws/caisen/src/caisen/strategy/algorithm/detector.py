"""Pattern Detector (形态检测器) - Pure Function Interface

Issue #5: PatternDetector 改造为纯函数接口
- 移除内部状态管理
- detect(bars) 接收完整 K 线列表，返回信号
- 简化接口，提升可测试性
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ...core.bar import Bar


@dataclass
class PatternSignal:
    """形态信号

    检测器检测到形态后返回的信号，包含置信度和风控参数。

    Attributes:
        pattern: 形态名称
        confidence: 置信度 (0~1)
        stop_loss: 止损价
        target: 目标价
        points: 形态关键点列表 (可视化用)
        data: 额外数据
    """
    pattern: str
    confidence: float
    stop_loss: float = 0.0
    target: float = 0.0
    points: List[Dict[str, Any]] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        """信号是否有效"""
        return self.confidence > 0 and self.stop_loss > 0


@dataclass
class ConfidenceFactors:
    """置信度因子

    用于计算形态置信度的多维度因子。
    """
    completion: float = 0.0   # 形态完成度 0~1
    volume: float = 0.0        # 成交量因子 0~1
    trend: float = 0.0         # 趋势共振 0~1
    momentum: float = 0.0       # 动量因子 0~1

    def weighted_sum(self, weights: Dict[str, float] = None) -> float:
        """加权求和

        Args:
            weights: 因子权重，默认为等权重

        Returns:
            加权置信度 0~1
        """
        if weights is None:
            weights = {
                "completion": 0.4,
                "volume": 0.3,
                "trend": 0.2,
                "momentum": 0.1,
            }
        return (
            self.completion * weights.get("completion", 0.4) +
            self.volume * weights.get("volume", 0.3) +
            self.trend * weights.get("trend", 0.2) +
            self.momentum * weights.get("momentum", 0.1)
        )


class PatternDetector(ABC):
    """形态检测器基类 (纯函数接口)

    检测器负责检测特定形态，只负责"看"，不做交易决策。

    纯函数接口设计：
    - detect(bars): 接收完整 K 线列表，返回信号或 None
    - 无内部状态，无副作用，可重复调用
    - 便于并行测试和策略回测

    Example:
        detector = WBottomDetector(tolerance=0.05)
        signal = detector.detect(bars)
        if signal:
            print(f"Detected: {signal.pattern}, confidence: {signal.confidence}")
    """

    def __init__(self, name: str = None, volume_config: Dict[str, Any] = None):
        """初始化检测器

        Args:
            name: 检测器名称，用于配置和日志
            volume_config: VolumeAnalyzer 配置参数，支持 base_period 和 breakout_multiplier
        """
        from .caisen_components.volume_analyzer import VolumeAnalyzer
        self.name = name or self.__class__.__name__
        vol_cfg = volume_config or {}
        self.volume_analyzer = VolumeAnalyzer(
            base_period=vol_cfg.get('base_period', 20),
            breakout_multiplier=vol_cfg.get('breakout_multiplier', 1.5),
        )

    @abstractmethod
    def detect(self, bars: List["Bar"]) -> Optional[PatternSignal]:
        """检测形态

        Args:
            bars: 完整 K 线列表，至少包含检测所需的最小数量

        Returns:
            如果检测到形态，返回 PatternSignal
            否则返回 None
        """
        pass

    def _calculate_confidence(
        self,
        completion: float,
        volume: float = 0.5,
        trend: float = 0.5,
        momentum: float = 0.5,
    ) -> float:
        """计算综合置信度

        Args:
            completion: 形态完成度
            volume: 成交量因子
            trend: 趋势共振
            momentum: 动量因子

        Returns:
            加权置信度 0~1
        """
        factors = ConfidenceFactors(
            completion=completion,
            volume=volume,
            trend=trend,
            momentum=momentum,
        )
        return min(1.0, max(0.0, factors.weighted_sum()))

    def _create_signal(
        self,
        pattern: str,
        confidence: float,
        stop_loss: float = 0.0,
        target: float = 0.0,
        points: List[Dict] = None,
        **kwargs,
    ) -> PatternSignal:
        """创建形态信号

        Args:
            pattern: 形态名称
            confidence: 置信度
            stop_loss: 止损价
            target: 目标价
            points: 形态关键点
            **kwargs: 额外数据

        Returns:
            PatternSignal 实例
        """
        return PatternSignal(
            pattern=pattern,
            confidence=confidence,
            stop_loss=stop_loss,
            target=target,
            points=points or [],
            data=kwargs,
        )

    def _get_recent_bars(self, bars: List["Bar"], count: int) -> List["Bar"]:
        """获取最近的 K 线

        Args:
            bars: K 线列表
            count: 获取数量

        Returns:
            最近的 K 线列表
        """
        return bars[-count:] if len(bars) >= count else bars

    def _is_trend_up(self, bars: List["Bar"], period: int = 20) -> bool:
        """判断当前趋势是否向上

        Args:
            bars: K 线列表
            period: 判断周期

        Returns:
            True if trend is up
        """
        recent = self._get_recent_bars(bars, period)
        if len(recent) < 2:
            return False
        return recent[-1].close > recent[0].close

    def _is_trend_down(self, bars: List["Bar"], period: int = 20) -> bool:
        """判断当前趋势是否向下

        Args:
            bars: K 线列表
            period: 判断周期

        Returns:
            True if trend is down
        """
        recent = self._get_recent_bars(bars, period)
        if len(recent) < 2:
            return False
        return recent[-1].close < recent[0].close

    def _volume_ratio(self, bars: List["Bar"], period: int = 20) -> float:
        """计算成交量放大倍数

        Args:
            bars: K 线列表
            period: 对比周期

        Returns:
            成交量倍数 (>1 表示放量)
        """
        recent = self._get_recent_bars(bars, period)
        if len(recent) < period:
            return 1.0

        recent_avg = sum(b.volume for b in recent[-5:]) / 5
        historical_avg = sum(b.volume for b in recent[:-5]) / max(1, len(recent) - 5)

        if historical_avg == 0:
            return 1.0
        return recent_avg / historical_avg
