"""Result 模块"""

from .persistence import ResultPersister
from .calculator import PerformanceMetrics, MetricsCalculator
from .types import BacktestResult

__all__ = ["ResultPersister", "PerformanceMetrics", "MetricsCalculator", "BacktestResult"]