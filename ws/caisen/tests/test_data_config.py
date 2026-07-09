"""DataConfig 单元测试。"""

import pytest
from caisen.data.config import DataConfig, SUPPORTED_FREQS


class TestDataConfig:
    """DataConfig 数据配置测试。"""

    def test_default_values(self):
        cfg = DataConfig()
        assert cfg.symbol == ""
        assert cfg.freq == "1d"
        assert cfg.start is None
        assert cfg.end is None
        assert cfg.data_dir == "./data"

    def test_custom_values(self):
        cfg = DataConfig(symbol="AAPL", freq="5m", start="2024-01-01", end="2024-12-31", data_dir="/data")
        assert cfg.symbol == "AAPL"
        assert cfg.freq == "5m"

    def test_invalid_freq_raises(self):
        with pytest.raises(ValueError, match="Unsupported freq"):
            DataConfig(symbol="AAPL", freq="2d")

    def test_all_supported_freqs(self):
        for freq in SUPPORTED_FREQS:
            cfg = DataConfig(symbol="TEST", freq=freq)
            assert cfg.freq == freq

    def test_data_path(self):
        cfg = DataConfig(symbol="AAPL", freq="1h", data_dir="/data")
        assert str(cfg.data_path) == "/data/AAPL/1h"

    def test_to_dict(self):
        cfg = DataConfig(symbol="AAPL", freq="1d", start="2024-01-01", end="2024-12-31")
        d = cfg.to_dict()
        assert d["symbol"] == "AAPL"
        assert d["freq"] == "1d"
        assert d["start"] == "2024-01-01"
        assert d["end"] == "2024-12-31"
        assert d["data_dir"] == "./data"

    def test_empty_symbol_skips_freq_validation(self):
        """空 symbol 时不验证 freq（允许默认值）。"""
        cfg = DataConfig()  # symbol="" → 不触发 freq 校验
        assert cfg.freq == "1d"
