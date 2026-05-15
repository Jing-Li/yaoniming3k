"""Registry for data source plugins."""

from typing import Dict, Optional, Type

from .loader import BaseDataLoader, DataLoader
from .local import LocalDataLoader
from .exceptions import DataSourceNotAvailableError

# Global registry for datasources
_datasources: Dict[str, Type[DataLoader]] = {
    "local": LocalDataLoader,
}

# Currently active datasource
_active_datasource: Optional[str] = None


def register_datasource(name: str, loader_class: Type[DataLoader]) -> None:
    """Register a datasource.

    Args:
        name: Unique name for the datasource
        loader_class: Class implementing DataLoader protocol
    """
    _datasources[name] = loader_class


def set_active_datasource(name: str) -> None:
    """Set the active datasource.

    Args:
        name: Name of the datasource to use

    Raises:
        ValueError: Unknown datasource name
    """
    if name not in _datasources:
        raise ValueError(f"Unknown datasource: {name}. Available: {list(_datasources.keys())}")
    global _active_datasource
    _active_datasource = name


def get_datasource(name: str) -> DataLoader:
    """Get a datasource instance.

    Args:
        name: Name of the datasource

    Returns:
        DataLoader instance

    Raises:
        DataSourceNotAvailableError: Unknown datasource
    """
    if name not in _datasources:
        raise DataSourceNotAvailableError(f"Unknown datasource: {name}")
    return _datasources[name]()


def load_datasource(name: Optional[str] = None) -> DataLoader:
    """Load the active or specified datasource.

    Args:
        name: Optional datasource name. If None, uses active datasource.

    Returns:
        DataLoader instance

    Raises:
        DataSourceNotAvailableError: No suitable datasource found
    """
    # Use specified name or active datasource or fallback to local
    target = name or _active_datasource or "local"

    if target not in _datasources:
        raise DataSourceNotAvailableError(
            f"Datasource '{target}' not found. Available: {list(_datasources.keys())}"
        )

    return _datasources[target]()


def list_datasources() -> list:
    """List all registered datasources.

    Returns:
        List of datasource names
    """
    return list(_datasources.keys())


def get_active_datasource() -> Optional[str]:
    """Get the name of the active datasource.

    Returns:
        Name of active datasource or None
    """
    return _active_datasource