"""测试数据加载"""

import json
from datetime import datetime
from pathlib import Path
import tempfile
import pandas as pd

from caisen.core.bar import Bar


def test_bar_to_dict_and_back():
    """Bar 序列化/反序列化"""
    bar = Bar(
        timestamp=datetime(2024, 1, 1),
        symbol="TEST",
        freq="1d",
        open=100.0,
        high=105.0,
        low=95.0,
        close=102.0,
        volume=1000.0
    )

    # to_dict
    d = bar.to_dict()
    assert d["symbol"] == "TEST"
    assert d["close"] == 102.0

    # from_dict
    bar2 = Bar.from_dict(d)
    assert bar2.symbol == "TEST"
    assert bar2.close == 102.0


def test_parquet_save_and_load():
    """Parquet 保存和加载 K 线数据"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建测试数据
        bars = [
            Bar(timestamp=datetime(2024, 1, i), symbol="TEST", open=100, high=105, low=95, close=102, volume=1000)
            for i in range(1, 11)
        ]

        # 保存为 Parquet
        df = pd.DataFrame([b.to_dict() for b in bars])
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        path = Path(tmpdir) / "TEST.parquet"
        df.to_parquet(path, index=False)

        # 加载
        df_loaded = pd.read_parquet(path)
        assert len(df_loaded) == 10
        assert "TEST" in df_loaded["symbol"].values


def test_multiple_bars_list():
    """多个 Bar 的列表操作"""
    bars = []
    for i in range(100):
        bars.append(Bar(
            timestamp=datetime(2024, 1, 1) + __import__('datetime').timedelta(days=i),
            symbol="TEST",
            open=100 + i,
            high=105 + i,
            low=95 + i,
            close=102 + i,
            volume=1000
        ))

    assert len(bars) == 100
    # 检查时间顺序
    for i in range(1, len(bars)):
        assert bars[i].timestamp > bars[i-1].timestamp