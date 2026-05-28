"""测试 DataSourceScanner 本地数据目录扫描"""

from pathlib import Path

from caisen.data.scanner import DataSourceScanner


def test_returns_empty_when_data_dir_missing(tmp_path):
    """data_dir 不存在时返回空列表，不报错"""
    result = DataSourceScanner.scan(tmp_path / "nonexistent")
    assert result == []


def test_scans_single_symbol_freq(tmp_path):
    """标准三级目录 + 单个 parquet 文件 → 正确解析 symbol/freq/日期范围"""
    parquet_dir = tmp_path / "ag" / "60m"
    parquet_dir.mkdir(parents=True)
    (parquet_dir / "20260105_20260526.parquet").touch()

    result = DataSourceScanner.scan(tmp_path)

    assert len(result) == 1
    assert result[0]["symbol"] == "ag"
    assert result[0]["freq"] == "60m"
    assert result[0]["date_range"] == {"start": "2026-01-05", "end": "2026-05-26"}


def test_multiple_parquet_files_union_date_range(tmp_path):
    """同一 freq 下多个 parquet 文件 → 取最小 start 和最大 end"""
    parquet_dir = tmp_path / "rb" / "1d"
    parquet_dir.mkdir(parents=True)
    (parquet_dir / "20200102_20221231.parquet").touch()
    (parquet_dir / "20230101_20260525.parquet").touch()

    result = DataSourceScanner.scan(tmp_path)

    assert len(result) == 1
    assert result[0]["date_range"] == {"start": "2020-01-02", "end": "2026-05-25"}


def test_api_data_sources_endpoint(tmp_path, monkeypatch):
    """GET /api/data-sources 端点返回扫描结果"""
    from fastapi.testclient import TestClient
    import caisen.web.main as web_main

    # 准备测试数据目录
    parquet_dir = tmp_path / "cu" / "30m"
    parquet_dir.mkdir(parents=True)
    (parquet_dir / "20250601_20260101.parquet").touch()

    # 让端点使用测试目录
    monkeypatch.setattr(web_main, "_project_config",
                        type("C", (), {"data_dir": str(tmp_path), "output_dir": "./runs", "api_port": 8001})())

    client = TestClient(web_main.create_app())
    response = client.get("/api/data-sources")

    assert response.status_code == 200
    body = response.json()
    assert "data_sources" in body
    assert len(body["data_sources"]) == 1
    assert body["data_sources"][0]["symbol"] == "cu"
    assert body["data_sources"][0]["freq"] == "30m"
    assert body["data_sources"][0]["date_range"]["start"] == "2025-06-01"
