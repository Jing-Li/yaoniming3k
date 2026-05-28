"""Patterns module - 形态检测器集合"""

from .w_bottom import WBottomDetector
from .m_top import MTopDetector
from .head_shoulders import HeadAndShouldersBottomDetector, HeadAndShouldersTopDetector
from .triangle import TriangleDetector
from .other import (
    FlagDetector, RectangleDetector, RoundingBottomDetector,
    CupHandleDetector, BreakoutPullbackDetector,
)
from .breakdown_pullback import BreakdownPullbackDetector
from .fake_breakout import FakeBreakoutDetector

__all__ = [
    "WBottomDetector",
    "MTopDetector",
    "HeadAndShouldersBottomDetector",
    "HeadAndShouldersTopDetector",
    "TriangleDetector",
    "FlagDetector",
    "RectangleDetector",
    "RoundingBottomDetector",
    "CupHandleDetector",
    "BreakoutPullbackDetector",
    "BreakdownPullbackDetector",
    "FakeBreakoutDetector",
]