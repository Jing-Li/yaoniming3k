"""Result 模块"""

from .persistence import ResultPersister
from .metrics import PerformanceMetrics, calculate_metrics
from .types import BacktestResult

__all__ = ["ResultPersister", "PerformanceMetrics", "calculate_metrics", "BacktestResult"]