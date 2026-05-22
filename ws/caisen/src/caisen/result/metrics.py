"""Performance Metrics - 绩效指标

数据容器，不含计算逻辑。
计算逻辑在 MetricsCalculator 中。
"""

# 重新导出，方便导入
from .calculator import PerformanceMetrics, MetricsCalculator

__all__ = ["PerformanceMetrics", "MetricsCalculator"]