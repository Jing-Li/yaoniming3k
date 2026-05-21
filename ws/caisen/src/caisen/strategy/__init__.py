"""Strategy 模块"""

from .base import Strategy, Annotation, AnnotationType
from .cai_sen import CaiSenStrategy  # 保持向后兼容
from .detector import PatternDetector, PatternSignal
from .cai_sen_v2 import CaiSenStrategy as CaiSenStrategyV2  # 新架构

__all__ = [
    "Strategy", "Annotation", "AnnotationType",
    "CaiSenStrategy", "CaiSenStrategyV2",
    "PatternDetector", "PatternSignal",
]