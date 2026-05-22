"""Pattern Detector (形态检测器) 基类"""

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
    """形态检测器基类

    检测器负责在每根 K 线更新时检测特定形态，
    只负责"看"，不做交易决策。

    接口设计：
    - update(bar): 接收新 K 线，更新内部状态
    - detect(): 检测形态，返回信号或 None
    - reset(): 重置状态
    """

    def __init__(self, name: str = None):
        """初始化检测器

        Args:
            name: 检测器名称，用于配置和日志
        """
        self.name = name or self.__class__.__name__
        self._bars: List["Bar"] = []
        self._last_signal: Optional[PatternSignal] = None

    @property
    def bars(self) -> List["Bar"]:
        """获取已接收的 K 线"""
        return self._bars

    def update(self, bar: "Bar") -> None:
        """接收新 K 线

        Args:
            bar: 新的 K 线数据
        """
        self._bars.append(bar)
        self._on_update(bar)

    def _on_update(self, bar: "Bar") -> None:
        """K 线更新时的钩子方法

        子类可重写此方法执行额外的状态更新。

        Args:
            bar: 新的 K 线数据
        """
        pass

    @abstractmethod
    def detect(self) -> Optional[PatternSignal]:
        """检测形态

        Returns:
            如果检测到形态，返回 PatternSignal
            否则返回 None
        """
        pass

    def reset(self) -> None:
        """重置检测器状态

        清空历史 K 线数据和中间状态。
        """
        self._bars = []
        self._last_signal = None
        self._on_reset()

    def _on_reset(self) -> None:
        """重置时的钩子方法

        子类可重写此方法执行额外的清理工作。
        """
        pass

    @property
    def last_signal(self) -> Optional[PatternSignal]:
        """获取上一次检测到的信号"""
        return self._last_signal

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
        signal = PatternSignal(
            pattern=pattern,
            confidence=confidence,
            stop_loss=stop_loss,
            target=target,
            points=points or [],
            data=kwargs,
        )
        self._last_signal = signal
        return signal

    def _get_recent_bars(self, count: int) -> List["Bar"]:
        """获取最近的 K 线

        Args:
            count: 获取数量

        Returns:
            最近的 K 线列表
        """
        return self._bars[-count:] if len(self._bars) >= count else self._bars

    def _is_trend_up(self, period: int = 20) -> bool:
        """判断当前趋势是否向上

        Args:
            period: 判断周期

        Returns:
            True if trend is up
        """
        bars = self._get_recent_bars(period)
        if len(bars) < 2:
            return False
        return bars[-1].close > bars[0].close

    def _is_trend_down(self, period: int = 20) -> bool:
        """判断当前趋势是否向下

        Args:
            period: 判断周期

        Returns:
            True if trend is down
        """
        bars = self._get_recent_bars(period)
        if len(bars) < 2:
            return False
        return bars[-1].close < bars[0].close

    def _volume_ratio(self, period: int = 20) -> float:
        """计算成交量放大倍数

        Args:
            period: 对比周期

        Returns:
            成交量倍数 (>1 表示放量)
        """
        bars = self._get_recent_bars(period)
        if len(bars) < period:
            return 1.0

        recent_avg = sum(b.volume for b in bars[-5:]) / 5
        historical_avg = sum(b.volume for b in bars[:-5]) / max(1, len(bars) - 5)

        if historical_avg == 0:
            return 1.0
        return recent_avg / historical_avg