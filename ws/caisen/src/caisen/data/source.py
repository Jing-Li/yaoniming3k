"""Protocol and base classes for data sources."""

from abc import ABC, abstractmethod
from typing import List, Protocol

from ..core.bar import Bar
from .config import DataConfig


class DataSource(Protocol):
    """Protocol for data sources.

    Implement this protocol to create custom data sources.
    Datasources registered via Entry Points must implement this protocol.
    """

    def load(self, config: DataConfig) -> List[Bar]:
        """Load bars from data source.

        Args:
            config: DataConfig with loading parameters

        Returns:
            List of Bar objects sorted by timestamp

        Raises:
            DataLoadError: If loading fails
        """
        ...

    @property
    def name(self) -> str:
        """Name of the datasource."""
        ...


# Backward compatibility alias
DataLoader = DataSource


class BaseDataSource(ABC):
    """Abstract base class for data sources.

    Provides common functionality for all data sources.
    """

    @abstractmethod
    def load(self, config: DataConfig) -> List[Bar]:
        """Load bars from data source.

        Args:
            config: DataConfig with loading parameters

        Returns:
            List of Bar objects sorted by timestamp
        """
        pass

    @property
    def name(self) -> str:
        """Name of the datasource."""
        return self.__class__.__name__