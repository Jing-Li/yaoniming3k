"""caisen-data CLI"""

import click
from pathlib import Path
from datetime import datetime, date, timedelta
import pandas as pd
import os

from .sources.akshare import AKShareDataSource

# 默认数据目录
DEFAULT_DATA_DIR = "/home/user/data"


@click.group()
def cli():
    """caisen-data 数据抓取工具"""
    pass


def get_existing_range(data_dir: Path) -> tuple[date | None, date | None]:
    """获取已有数据的时间范围"""
    if not data_dir.exists():
        return None, None

    parquet_files = list(data_dir.glob("*.parquet"))
    if not parquet_files:
        return None, None

    min_date = None
    max_date = None

    for pf in parquet_files:
        try:
            df = pd.read_parquet(pf)
            if "timestamp" in df.columns:
                df["ts"] = pd.to_datetime(df["timestamp"])
                file_min = df["ts"].min().date()
                file_max = df["ts"].max().date()

                if min_date is None or file_min < min_date:
                    min_date = file_min
                if max_date is None or file_max > max_date:
                    max_date = file_max
        except Exception:
            continue

    return min_date, max_date


def merge_parquet_files(data_dir: Path) -> pd.DataFrame:
    """合并目录下的所有 parquet 文件"""
    parquet_files = list(data_dir.glob("*.parquet"))
    if not parquet_files:
        return pd.DataFrame()

    dfs = []
    for pf in parquet_files:
        df = pd.read_parquet(pf)
        dfs.append(df)

    combined = pd.concat(dfs, ignore_index=True)
    # 去重，按 timestamp
    combined = combined.drop_duplicates(subset=["timestamp"])
    combined = combined.sort_values("timestamp").reset_index(drop=True)
    return combined


@cli.command()
@click.option("--symbol", "-s", required=True, help="标的代码")
@click.option("--start", required=True, help="开始日期 YYYY-MM-DD")
@click.option("--end", required=True, help="结束日期 YYYY-MM-DD")
@click.option("--freq", default="1d", help="频率: 1d, 5m, 15m, 30m, 60m")
@click.option("--output-dir", default=DEFAULT_DATA_DIR, help="输出目录")
@click.option("--source", default="akshare", help="数据源")
@click.option("--force", is_flag=True, help="强制重新下载，覆盖已有文件")
def fetch(symbol: str, start: str, end: str, freq: str, output_dir: str, source: str, force: bool):
    """下载 K 线数据（自动保存 + 增量更新）"""

    start_date = datetime.strptime(start, "%Y-%m-%d").date()
    end_date = datetime.strptime(end, "%Y-%m-%d").date()

    # 确保输出目录存在
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 检查已有数据
    data_dir = output_path / symbol / freq

    # --force 模式：直接删除旧文件，重新下载
    if force and data_dir.exists():
        click.echo("Force mode: removing existing files...")
        for f in data_dir.glob("*.parquet"):
            f.unlink()

    existing_start, existing_end = get_existing_range(data_dir)

    if existing_start and existing_end:
        # 有已有数据，检查是否需要更新
        if start_date >= existing_start and end_date <= existing_end:
            click.echo(f"Found existing data: {existing_start} to {existing_end}")
            # 获取实际数据范围（可能更宽）
            actual_df = merge_parquet_files(data_dir)
            if not actual_df.empty:
                actual_start = pd.to_datetime(actual_df["timestamp"]).min().date()
                actual_end = pd.to_datetime(actual_df["timestamp"]).max().date()
                if start_date >= actual_start and end_date <= actual_end:
                    click.echo(f"Data is up to date ({len(actual_df)} bars).")
                    return

        # 计算实际需要下载的范围
        new_start = start_date
        if existing_start and start_date <= existing_start:
            # 已有数据比请求的更早，跳过已存在的部分
            click.echo(f"Found existing data: {existing_start} to {existing_end}")
            # 仍然下载，因为 akshare 可能需要完整历史
            new_start = start_date

    click.echo(f"Fetching {symbol} from {start} to {end} ({freq})...")

    # 加载数据
    if source == "akshare":
        ds = AKShareDataSource()
    else:
        click.echo(f"Unknown source: {source}")
        return

    bars = ds.load(symbol, start_date, end_date, freq)
    click.echo(f"Loaded {len(bars)} bars")

    if not bars:
        click.echo("No data loaded.")
        return

    # 转换为 DataFrame
    new_df = pd.DataFrame([{
        "timestamp": b.timestamp.isoformat(),
        "symbol": b.symbol,
        "freq": b.freq,
        "open": b.open,
        "high": b.high,
        "low": b.low,
        "close": b.close,
        "volume": b.volume,
    } for b in bars])

    # 合并已有数据（如果存在）
    if data_dir.exists():
        existing_files = list(data_dir.glob("*.parquet"))
        existing_df = merge_parquet_files(data_dir)
        if not existing_df.empty:
            combined = pd.concat([existing_df, new_df], ignore_index=True)
            combined = combined.drop_duplicates(subset=["timestamp"])
            combined = combined.sort_values("timestamp").reset_index(drop=True)
            click.echo(f"Merged: {len(existing_df)} existing + {len(new_df)} new = {len(combined)} total")

            # 删除旧的分段文件（ADR-0001: 多文件合并为单个文件）
            for f in existing_files:
                f.unlink()
                click.echo(f"  Removed: {f.name}")
        else:
            combined = new_df
    else:
        data_dir.mkdir(parents=True, exist_ok=True)
        combined = new_df

    # 确定实际数据范围
    if len(combined) > 0:
        actual_start = pd.to_datetime(combined["timestamp"]).min().strftime("%Y%m%d")
        actual_end = pd.to_datetime(combined["timestamp"]).max().strftime("%Y%m%d")
    else:
        actual_start = start.replace("-", "")
        actual_end = end.replace("-", "")

    # 保存为单个文件（文件名使用实际数据时间范围）
    file_path = data_dir / f"{actual_start}_{actual_end}.parquet"
    combined.to_parquet(file_path, index=False)

    # 输出实际数据范围
    click.echo(f"Saved to {file_path} ({len(combined)} bars)")
    click.echo(f"Data range: {actual_start[:4]}-{actual_start[4:6]}-{actual_start[6:]} to {actual_end[:4]}-{actual_end[4:6]}-{actual_end[6:]}")


@cli.command()
@click.option("--source", default="akshare", help="数据源")
def list_symbols(source: str):
    """列出可用标的"""

    if source == "akshare":
        ds = AKShareDataSource()
        symbols = ds.list_symbols()
        click.echo(f"Found {len(symbols)} symbols:")
        for s in symbols[:20]:
            click.echo(f"  {s}")
        if len(symbols) > 20:
            click.echo(f"  ... and {len(symbols) - 20} more")
    else:
        click.echo(f"Unknown source: {source}")


@cli.command()
def list_sources():
    """列出可用数据源"""
    click.echo("Available datasources:")
    click.echo("  akshare - A股、期货免费数据源")


def main():
    cli(prog_name="caisen-data")


if __name__ == "__main__":
    main()