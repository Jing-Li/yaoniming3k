"""Local parquet file data loader."""

from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd

from ..core.bar import Bar
from .loader import BaseDataLoader
from .config import DataConfig
from .exceptions import DataNotFoundError, DataValidationError, InvalidDateRangeError


class LocalDataLoader(BaseDataLoader):
    """Load bars from local parquet files.

    Reads data from directory structure:
        {data_dir}/{symbol}/{freq}/{date}.parquet

    Parquet files must contain columns:
        - timestamp: datetime
        - open, high, low, close, volume: float
        - freq (optional): str
    """

    def __init__(self, data_dir: str = "./data"):
        """Initialize local data loader.

        Args:
            data_dir: Base directory for data files
        """
        self.data_dir = Path(data_dir)

    @property
    def name(self) -> str:
        return "local"

    def load(self, config: DataConfig) -> List[Bar]:
        """Load bars from local parquet files.

        Args:
            config: DataConfig with symbol, freq, start, end

        Returns:
            List of Bar objects sorted by timestamp

        Raises:
            DataNotFoundError: No parquet files found
            InvalidDateRangeError: Invalid date range
            DataValidationError: Invalid data format
        """
        data_path = Path(config.data_dir) / config.symbol / config.freq

        if not data_path.exists():
            raise DataNotFoundError(
                config.symbol, config.freq, config.start, config.end
            )

        parquet_files = self._get_files_for_range(data_path, config.start, config.end)

        if not parquet_files:
            raise DataNotFoundError(
                config.symbol, config.freq, config.start, config.end
            )

        bars = []
        for pf in sorted(parquet_files):
            df = pd.read_parquet(pf)
            bars.extend(self._dataframe_to_bars(df, config.symbol, config.freq))

        # Filter by date range if specified
        if config.start:
            start_dt = datetime.fromisoformat(config.start)
            bars = [b for b in bars if b.timestamp >= start_dt]
        if config.end:
            end_dt = datetime.fromisoformat(config.end)
            bars = [b for b in bars if b.timestamp <= end_dt]

        return sorted(bars, key=lambda b: b.timestamp)

    def _get_files_for_range(
        self, data_path: Path, start: Optional[str], end: Optional[str]
    ) -> List[Path]:
        """Get parquet files within date range.

        Args:
            data_path: Path to data directory
            start: Start date (YYYY-MM-DD)
            end: End date (YYYY-MM-DD)

        Returns:
            List of parquet file paths
        """
        all_files = list(data_path.glob("*.parquet"))

        if not start and not end:
            return all_files

        filtered = []
        for pf in all_files:
            # File naming convention: {date}.parquet
            date_str = pf.stem
            if start and date_str < start:
                continue
            if end and date_str > end:
                continue
            filtered.append(pf)

        return filtered

    def _dataframe_to_bars(
        self, df: pd.DataFrame, symbol: str, freq: str
    ) -> List[Bar]:
        """Convert pandas DataFrame to Bar objects.

        Args:
            df: DataFrame with OHLCV data
            symbol: Trading symbol
            freq: Frequency

        Returns:
            List of Bar objects

        Raises:
            DataValidationError: Missing required columns
        """
        required_cols = ["timestamp", "open", "high", "low", "close", "volume"]
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            raise DataValidationError(
                f"Missing required columns: {', '.join(missing)}"
            )

        bars = []
        for _, row in df.iterrows():
            ts = row["timestamp"]
            if not isinstance(ts, datetime):
                ts = datetime.fromisoformat(str(ts))

            bars.append(
                Bar(
                    timestamp=ts,
                    symbol=symbol,
                    freq=row.get("freq", freq),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]),
                )
            )
        return bars