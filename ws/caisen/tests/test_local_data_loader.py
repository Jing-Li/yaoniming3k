"""Tests for LocalDataLoader"""

import pytest
from pathlib import Path
from datetime import datetime
import pandas as pd
import tempfile
import shutil

from caisen.data.local import LocalDataLoader
from caisen.data.config import DataConfig
from caisen.data.exceptions import DataNotFoundError


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory with test files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_bars():
    """Create sample bar data."""
    return pd.DataFrame({
        "timestamp": ["2024-01-01", "2024-01-02", "2024-01-03"],
        "open": [100.0, 101.0, 102.0],
        "high": [105.0, 106.0, 107.0],
        "low": [99.0, 100.0, 101.0],
        "close": [103.0, 104.0, 105.0],
        "volume": [1000.0, 1100.0, 1200.0],
    })


class TestGetFilesForRange:
    """Tests for _get_files_for_range method."""

    def test_single_date_files(self, temp_data_dir):
        """Test matching single date files."""
        # Create test files
        (Path(temp_data_dir) / "AAPL" / "1d").mkdir(parents=True)
        (Path(temp_data_dir) / "AAPL" / "1d" / "20240101.parquet").touch()
        (Path(temp_data_dir) / "AAPL" / "1d" / "20240102.parquet").touch()
        (Path(temp_data_dir) / "AAPL" / "1d" / "20240103.parquet").touch()

        loader = LocalDataLoader(temp_data_dir)
        files = loader._get_files_for_range(
            Path(temp_data_dir) / "AAPL" / "1d",
            "2024-01-01",
            "2024-01-02"
        )

        assert len(files) == 2
        assert sorted([f.name for f in files]) == ["20240101.parquet", "20240102.parquet"]

    def test_range_files(self, temp_data_dir):
        """Test matching range format files (YYYYMMDD_YYYYMMDD)."""
        (Path(temp_data_dir) / "AAPL" / "1d").mkdir(parents=True)
        (Path(temp_data_dir) / "AAPL" / "1d" / "20240101_20240131.parquet").touch()
        (Path(temp_data_dir) / "AAPL" / "1d" / "20240201_20240229.parquet").touch()

        loader = LocalDataLoader(temp_data_dir)
        files = loader._get_files_for_range(
            Path(temp_data_dir) / "AAPL" / "1d",
            "2024-01-15",
            "2024-02-15"
        )

        assert len(files) == 2

    def test_no_filter(self, temp_data_dir):
        """Test without date filter returns all files."""
        (Path(temp_data_dir) / "AAPL" / "1d").mkdir(parents=True)
        (Path(temp_data_dir) / "AAPL" / "1d" / "20240101.parquet").touch()
        (Path(temp_data_dir) / "AAPL" / "1d" / "20240201.parquet").touch()

        loader = LocalDataLoader(temp_data_dir)
        files = loader._get_files_for_range(
            Path(temp_data_dir) / "AAPL" / "1d",
            None,
            None
        )

        assert len(files) == 2

    def test_out_of_range(self, temp_data_dir):
        """Test files outside date range are excluded."""
        (Path(temp_data_dir) / "AAPL" / "1d").mkdir(parents=True)
        (Path(temp_data_dir) / "AAPL" / "1d" / "20231201.parquet").touch()
        (Path(temp_data_dir) / "AAPL" / "1d" / "20240101.parquet").touch()
        (Path(temp_data_dir) / "AAPL" / "1d" / "20240201.parquet").touch()

        loader = LocalDataLoader(temp_data_dir)
        files = loader._get_files_for_range(
            Path(temp_data_dir) / "AAPL" / "1d",
            "2024-01-01",
            "2024-01-31"
        )

        assert len(files) == 1
        assert files[0].name == "20240101.parquet"


class TestLoad:
    """Tests for load method."""

    def test_load_success(self, temp_data_dir, sample_bars):
        """Test successful data loading."""
        data_path = Path(temp_data_dir) / "TEST" / "1d"
        data_path.mkdir(parents=True)
        sample_bars.to_parquet(data_path / "20240101_20240103.parquet", index=False)

        config = DataConfig(symbol="TEST", freq="1d", start="2024-01-01", end="2024-01-03", data_dir=temp_data_dir)
        loader = LocalDataLoader(temp_data_dir)
        bars = loader.load(config)

        assert len(bars) == 3
        assert bars[0].symbol == "TEST"
        assert bars[0].close == 103.0

    def test_load_not_found(self, temp_data_dir):
        """Test DataNotFoundError when path doesn't exist."""
        config = DataConfig(symbol="NOTEXIST", freq="1d", start="2024-01-01", end="2024-01-03", data_dir=temp_data_dir)
        loader = LocalDataLoader(temp_data_dir)

        with pytest.raises(DataNotFoundError):
            loader.load(config)

    def test_load_date_filter(self, temp_data_dir, sample_bars):
        """Test date range filtering."""
        data_path = Path(temp_data_dir) / "TEST" / "1d"
        data_path.mkdir(parents=True)
        sample_bars.to_parquet(data_path / "20240101_20240103.parquet", index=False)

        config = DataConfig(symbol="TEST", freq="1d", start="2024-01-02", end="2024-01-03", data_dir=temp_data_dir)
        loader = LocalDataLoader(temp_data_dir)
        bars = loader.load(config)

        assert len(bars) == 2


class TestDataFrameToBars:
    """Tests for _dataframe_to_bars method."""

    def test_chinese_columns(self):
        """Test conversion with Chinese column names."""
        df = pd.DataFrame({
            "日期": ["2024-01-01", "2024-01-02"],
            "开盘价": [100.0, 101.0],
            "最高价": [105.0, 106.0],
            "最低价": [99.0, 100.0],
            "收盘价": [103.0, 104.0],
            "成交量": [1000.0, 1100.0],
        })

        loader = LocalDataLoader()
        bars = loader._dataframe_to_bars(df, "TEST", "1d")

        assert len(bars) == 2
        assert bars[0].open == 100.0
        assert bars[0].close == 103.0

    def test_english_columns(self):
        """Test conversion with English column names."""
        df = pd.DataFrame({
            "timestamp": ["2024-01-01", "2024-01-02"],
            "open": [100.0, 101.0],
            "high": [105.0, 106.0],
            "low": [99.0, 100.0],
            "close": [103.0, 104.0],
            "volume": [1000.0, 1100.0],
        })

        loader = LocalDataLoader()
        bars = loader._dataframe_to_bars(df, "TEST", "1d")

        assert len(bars) == 2
        assert bars[0].freq == "1d"