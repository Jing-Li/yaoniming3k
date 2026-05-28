"""DataSourceScanner：扫描本地 Parquet 数据目录结构。

目录约定：{data_dir}/{symbol}/{freq}/*.parquet
文件名约定：{YYYYMMDD}_{YYYYMMDD}.parquet（起始日期_结束日期）
"""

from pathlib import Path


class DataSourceScanner:
    @staticmethod
    def scan(data_dir: str | Path) -> list[dict]:
        """扫描 data_dir，返回可用行情数据列表。

        data_dir 不存在或为空时返回空列表，不报错。
        """
        data_dir = Path(data_dir)
        if not data_dir.exists():
            return []

        results = []
        for symbol_dir in sorted(data_dir.iterdir()):
            if not symbol_dir.is_dir():
                continue
            for freq_dir in sorted(symbol_dir.iterdir()):
                if not freq_dir.is_dir():
                    continue
                date_range = _infer_date_range(freq_dir)
                results.append({
                    "symbol": symbol_dir.name,
                    "freq": freq_dir.name,
                    "date_range": date_range,
                })
        return results


def _infer_date_range(freq_dir: Path) -> dict | None:
    """从 freq_dir 下的 parquet 文件名推断日期范围，不读文件内容。"""
    starts, ends = [], []
    for f in freq_dir.glob("*.parquet"):
        parts = f.stem.split("_")
        if len(parts) == 2 and len(parts[0]) == 8 and len(parts[1]) == 8:
            try:
                s = parts[0]
                e = parts[1]
                starts.append(f"{s[:4]}-{s[4:6]}-{s[6:]}")
                ends.append(f"{e[:4]}-{e[4:6]}-{e[6:]}")
            except (ValueError, IndexError):
                continue
    if not starts:
        return None
    return {"start": min(starts), "end": max(ends)}
