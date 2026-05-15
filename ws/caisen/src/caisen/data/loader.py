"""Protocol and base classes for data loaders."""

from abc import ABC, abstractmethod
from typing import List, Protocol

from ..core.bar import Bar
from .config import DataConfig


class DataLoader(Protocol):
    """Protocol for data loaders.

    Implement this protocol to create custom data loaders.
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


class BaseDataLoader(ABC):
    """Abstract base class for data loaders.

    Provides common functionality for all data loaders.
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