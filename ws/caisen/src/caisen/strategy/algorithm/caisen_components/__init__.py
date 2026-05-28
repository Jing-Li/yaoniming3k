"""CaiSenStrategy 组件模块

包含：
- DetectorFactory: 检测器创建
- SignalAggregator: 信号聚合评分
- PositionManager: 仓位管理
- VolumeAnalyzer: 量能分析器
"""

from .factory import DetectorFactory
from .aggregator import SignalAggregator, AggregatedResult
from .position_manager import PositionManager
from .volume_analyzer import VolumeAnalyzer

__all__ = [
    "DetectorFactory",
    "SignalAggregator",
    "AggregatedResult",
    "PositionManager",
    "VolumeAnalyzer",
]