"""SignalAggregator - 信号聚合器

收集检测器信号，计算综合评分。
无状态，纯函数接口。
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, TYPE_CHECKING

from ..detector import PatternSignal

if TYPE_CHECKING:
    from ....core.bar import Bar


@dataclass
class AggregatedResult:
    """聚合结果

    Attributes:
        total_score: 综合评分（加权求和）
        best_signal: 置信度最高的信号
        signals: 所有信号列表
        signal_count: 有效信号数量
    """
    total_score: float
    best_signal: Optional[PatternSignal]
    signals: List[PatternSignal]
    signal_count: int

    @property
    def has_signal(self) -> bool:
        """是否有有效信号"""
        return self.best_signal is not None

    @property
    def best_confidence(self) -> float:
        """最佳置信度"""
        return self.best_signal.confidence if self.best_signal else 0.0


class SignalAggregator:
    """信号聚合器

    收集检测器信号，应用权重，计算综合评分。

    无状态（纯函数），每次调用独立。

    Example:
        aggregator = SignalAggregator()
        result = aggregator.aggregate(
            signals=[signal1, signal2],
            weights={"w_bottom": 0.5, "m_top": 0.5}
        )
        if result.has_signal:
            print(f"Total: {result.total_score}, Best: {result.best_signal.pattern}")
    """

    def aggregate(
        self,
        signals: List[Optional[PatternSignal]],
        weights: Dict[str, float],
        threshold: float = 0.0,
    ) -> AggregatedResult:
        """聚合信号

        Args:
            signals: 检测器返回的信号列表（可能包含 None）
            weights: 各检测器权重，如 {"w_bottom": 0.5}
            threshold: 最小置信度阈值（过滤低质量信号）

        Returns:
            AggregatedResult 聚合结果
        """
        # 过滤无效信号
        valid_signals = [s for s in signals if s is not None]

        if not valid_signals:
            return AggregatedResult(
                total_score=0.0,
                best_signal=None,
                signals=[],
                signal_count=0,
            )

        # 计算加权评分
        total_score = 0.0
        best_signal: Optional[PatternSignal] = None

        for signal in valid_signals:
            # 跳过低于阈值的信号
            if signal.confidence < threshold:
                continue

            # 获取权重（默认 1.0）
            weight = weights.get(signal.pattern, 1.0)

            # 累加评分
            total_score += signal.confidence * weight

            # 更新最佳信号
            if best_signal is None or signal.confidence > best_signal.confidence:
                best_signal = signal

        return AggregatedResult(
            total_score=total_score,
            best_signal=best_signal,
            signals=valid_signals,
            signal_count=len(valid_signals),
        )

    def aggregate_with_detection(
        self,
        detectors: List,
        bars: List["Bar"],
        weights: Dict[str, float],
        threshold: float = 0.0,
    ) -> AggregatedResult:
        """一步完成检测+聚合

        便捷方法，避免外部手动调用 detect。

        Args:
            detectors: 检测器列表
            bars: K线列表
            weights: 各检测器权重
            threshold: 最小置信度阈值

        Returns:
            AggregatedResult 聚合结果
        """
        # 检测信号
        signals = [detector.detect(bars) for detector in detectors]

        # 聚合
        return self.aggregate(signals, weights, threshold)


def calculate_weighted_score(
    signals: List[PatternSignal],
    weights: Dict[str, float],
) -> float:
    """计算加权评分（纯函数）

    静态方法，方便直接调用。

    Args:
        signals: 信号列表
        weights: 权重字典

    Returns:
        加权评分
    """
    if not signals:
        return 0.0

    total = sum(s.confidence * weights.get(s.pattern, 1.0) for s in signals)
    return total


def select_best_signal(
    signals: List[PatternSignal],
) -> Optional[PatternSignal]:
    """选择最佳信号

    静态方法，置信度最高的信号。

    Args:
        signals: 信号列表

    Returns:
        最佳信号或 None
    """
    if not signals:
        return None

    return max(signals, key=lambda s: s.confidence)