"""Configuration for data loading."""

from dataclasses import dataclass, field
from typing import Optional


# 模块级常量
SUPPORTED_FREQS = ("1d", "1h", "30m", "15m", "5m", "1m", "60m")


@dataclass
class DataConfig:
    """Configuration for data loading.

    Attributes:
        symbol: Trading symbol (e.g., "AAPL", "600000.SH")
        freq: Frequency of bars (e.g., "1d", "5m", "1h")
        start: Start date (YYYY-MM-DD format)
        end: End date (YYYY-MM-DD format)
        data_dir: Directory containing parquet files
    """

    symbol: str = ""
    freq: str = "1d"
    start: Optional[str] = None
    end: Optional[str] = None
    data_dir: str = "./data"

    def __post_init__(self):
        """Validate configuration."""
        if self.symbol and self.freq not in SUPPORTED_FREQS:
            raise ValueError(
                f"Unsupported freq '{self.freq}'. "
                f"Supported: {', '.join(SUPPORTED_FREQS)}"
            )

    @property
    def data_path(self) -> str:
        """Get the data path for this symbol and frequency."""
        from pathlib import Path
        return Path(self.data_dir) / self.symbol / self.freq

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "freq": self.freq,
            "start": self.start,
            "end": self.end,
            "data_dir": self.data_dir,
        }