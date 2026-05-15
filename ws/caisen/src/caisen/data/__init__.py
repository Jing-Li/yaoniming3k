"""Data loading module for caisen backtesting system."""

from .loader import DataLoader
from .local import LocalDataLoader
from .registry import load_datasource, register_datasource
from .exceptions import (
    DataLoadError,
    DataNotFoundError,
    DataSourceNotAvailableError,
    InvalidDateRangeError,
)
from .config import DataConfig

__all__ = [
    # Core interface
    "DataLoader",
    # Implementations
    "LocalDataLoader",
    # Registry
    "load_datasource",
    "register_datasource",
    # Config
    "DataConfig",
    # Exceptions
    "DataLoadError",
    "DataNotFoundError",
    "DataSourceNotAvailableError",
    "InvalidDateRangeError",
]


def load_bars(config: DataConfig) -> list:
    """Load bars using available datasource.

    Args:
        config: DataConfig with symbol, freq, start, end, data_dir

    Returns:
        List of Bar objects

    Raises:
        DataSourceNotAvailableError: No datasource registered
        DataNotFoundError: No data found for the given parameters
        InvalidDateRangeError: Invalid date range specified
    """
    loader = load_datasource()
    return loader.load(config)