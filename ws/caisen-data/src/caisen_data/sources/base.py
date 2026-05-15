"""DataSource 数据源基类"""

from abc import ABC, abstractmethod
from datetime import date
from typing import List

try:
    from caisen.core.bar import Bar
except ImportError:
    Bar = None  # 类型标注，不强制依赖


class DataSource(ABC):
    """数据源抽象接口"""

    name: str = "base"
    supports_freq: List[str] = ["1d"]

    @abstractmethod
    def load(
        self,
        symbol: str,
        start: date,
        end: date,
        freq: str = "1d"
    ) -> List["Bar"]:
        """加载 K 线数据

        Args:
            symbol: 股票代码，如 "000001.SZ"
            start: 开始日期
            end: 结束日期
            freq: 频率，如 "1d", "5m"

        Returns:
            List[Bar] - K 线数据列表
        """
        pass

    def list_symbols(self) -> List[str]:
        """列出可用标的"""
        return []