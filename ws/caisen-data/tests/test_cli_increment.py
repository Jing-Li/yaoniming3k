"""Tests for cli.py increment / range helper functions"""

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from caisen_data.cli import (
    find_range_gaps,
    get_existing_range,
    merge_parquet_files,
    normalize_ranges,
    parse_date_range_from_filename,
)


# ---------------------------------------------------------------------------
# parse_date_range_from_filename
# ---------------------------------------------------------------------------


class TestParseDateRangeFromFilename:
    def test_valid_filename(self):
        result = parse_date_range_from_filename(Path("20240101_20240630.parquet"))
        assert result == (date(2024, 1, 1), date(2024, 6, 30))

    def test_invalid_filename_returns_none(self):
        assert parse_date_range_from_filename(Path("invalid.parquet")) is None

    def test_single_part_filename_returns_none(self):
        assert parse_date_range_from_filename(Path("20240101.parquet")) is None

    def test_bad_date_format_returns_none(self):
        assert parse_date_range_from_filename(Path("abcd_efgh.parquet")) is None


# ---------------------------------------------------------------------------
# normalize_ranges
# ---------------------------------------------------------------------------


class TestNormalizeRanges:
    def test_empty_list(self):
        assert normalize_ranges([]) == []

    def test_single_range(self):
        ranges = [(date(2024, 1, 1), date(2024, 6, 30))]
        assert normalize_ranges(ranges) == ranges

    def test_overlapping_ranges(self):
        ranges = [
            (date(2024, 1, 1), date(2024, 6, 30)),
            (date(2024, 4, 1), date(2024, 12, 31)),
        ]
        result = normalize_ranges(ranges)
        assert result == [(date(2024, 1, 1), date(2024, 12, 31))]

    def test_adjacent_ranges(self):
        ranges = [
            (date(2024, 1, 1), date(2024, 6, 30)),
            (date(2024, 7, 1), date(2024, 12, 31)),
        ]
        result = normalize_ranges(ranges)
        assert result == [(date(2024, 1, 1), date(2024, 12, 31))]

    def test_non_overlapping_ranges(self):
        ranges = [
            (date(2024, 1, 1), date(2024, 3, 31)),
            (date(2024, 7, 1), date(2024, 12, 31)),
        ]
        result = normalize_ranges(ranges)
        assert result == ranges

    def test_unsorted_input(self):
        ranges = [
            (date(2024, 7, 1), date(2024, 12, 31)),
            (date(2024, 1, 1), date(2024, 3, 31)),
        ]
        result = normalize_ranges(ranges)
        # Should return sorted, non-overlapping
        assert result == [
            (date(2024, 1, 1), date(2024, 3, 31)),
            (date(2024, 7, 1), date(2024, 12, 31)),
        ]


# ---------------------------------------------------------------------------
# find_range_gaps
# ---------------------------------------------------------------------------


class TestFindRangeGaps:
    def test_no_existing_data(self):
        gaps = find_range_gaps(date(2024, 1, 1), date(2024, 12, 31), [])
        assert gaps == [(date(2024, 1, 1), date(2024, 12, 31))]

    def test_fully_covered(self):
        gaps = find_range_gaps(
            date(2024, 1, 1),
            date(2024, 12, 31),
            [(date(2024, 1, 1), date(2024, 12, 31))],
        )
        assert gaps == []

    def test_gap_at_end(self):
        gaps = find_range_gaps(
            date(2024, 1, 1),
            date(2024, 12, 31),
            [(date(2024, 1, 1), date(2024, 6, 30))],
        )
        assert gaps == [(date(2024, 7, 1), date(2024, 12, 31))]

    def test_gap_at_start(self):
        gaps = find_range_gaps(
            date(2024, 1, 1),
            date(2024, 12, 31),
            [(date(2024, 6, 1), date(2024, 12, 31))],
        )
        assert gaps == [(date(2024, 1, 1), date(2024, 5, 31))]

    def test_gap_in_middle(self):
        gaps = find_range_gaps(
            date(2024, 1, 1),
            date(2024, 12, 31),
            [
                (date(2024, 1, 1), date(2024, 3, 31)),
                (date(2024, 7, 1), date(2024, 12, 31)),
            ],
        )
        assert gaps == [(date(2024, 4, 1), date(2024, 6, 30))]

    def test_existing_outside_requested_range(self):
        # Existing data fully before requested range
        gaps = find_range_gaps(
            date(2024, 7, 1),
            date(2024, 12, 31),
            [(date(2024, 1, 1), date(2024, 6, 30))],
        )
        assert gaps == [(date(2024, 7, 1), date(2024, 12, 31))]

    def test_existing_fully_covers_beyond_requested(self):
        gaps = find_range_gaps(
            date(2024, 3, 1),
            date(2024, 10, 31),
            [(date(2024, 1, 1), date(2024, 12, 31))],
        )
        assert gaps == []


# ---------------------------------------------------------------------------
# get_existing_range (filesystem-based)
# ---------------------------------------------------------------------------


class TestGetExistingRange:
    def test_nonexistent_dir(self, tmp_path):
        assert get_existing_range(tmp_path / "nonexistent") == (None, None)

    def test_empty_dir(self, tmp_path):
        assert get_existing_range(tmp_path) == (None, None)

    def test_with_parquet_files(self, tmp_path):
        (tmp_path / "20240101_20240630.parquet").touch()
        (tmp_path / "20240701_20241231.parquet").touch()
        start, end = get_existing_range(tmp_path)
        assert start == date(2024, 1, 1)
        assert end == date(2024, 12, 31)

    def test_skips_invalid_filenames(self, tmp_path):
        (tmp_path / "invalid.parquet").touch()
        (tmp_path / "20240101_20240630.parquet").touch()
        start, end = get_existing_range(tmp_path)
        assert start == date(2024, 1, 1)
        assert end == date(2024, 6, 30)


# ---------------------------------------------------------------------------
# merge_parquet_files (filesystem-based)
# ---------------------------------------------------------------------------


class TestMergeParquetFiles:
    def test_empty_dir(self, tmp_path):
        result = merge_parquet_files(tmp_path)
        assert result.empty

    def test_single_file(self, tmp_path):
        df = pd.DataFrame(
            {
                "timestamp": pd.to_datetime(["2024-01-01", "2024-01-02"]),
                "close": [100.0, 101.0],
            }
        )
        df.to_parquet(tmp_path / "20240101_20240102.parquet", index=False)
        result = merge_parquet_files(tmp_path)
        assert len(result) == 2

    def test_merges_and_deduplicates(self, tmp_path):
        df1 = pd.DataFrame(
            {
                "timestamp": pd.to_datetime(["2024-01-01", "2024-01-02"]),
                "close": [100.0, 101.0],
            }
        )
        df2 = pd.DataFrame(
            {
                "timestamp": pd.to_datetime(["2024-01-02", "2024-01-03"]),
                "close": [101.0, 102.0],
            }
        )
        df1.to_parquet(tmp_path / "file1.parquet", index=False)
        df2.to_parquet(tmp_path / "file2.parquet", index=False)
        result = merge_parquet_files(tmp_path)
        assert len(result) == 3  # 2024-01-02 deduplicated
        assert list(result["close"]) == [100.0, 101.0, 102.0]


# ---------------------------------------------------------------------------
# DEFAULT_DATA_DIR sanity check
# ---------------------------------------------------------------------------


class TestDefaultDataDir:
    def test_default_dir_is_under_home(self):
        from caisen_data.cli import DEFAULT_DATA_DIR

        # Must not be the hardcoded /home/user/data anymore
        assert "/home/user" not in DEFAULT_DATA_DIR
        assert str(Path.home()) in DEFAULT_DATA_DIR
