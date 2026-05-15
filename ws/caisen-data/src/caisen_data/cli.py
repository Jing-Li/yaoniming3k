"""caisen-data CLI"""

import click
from pathlib import Path
from datetime import datetime
import pandas as pd

from .sources.akshare import AKShareDataSource


@click.group()
def cli():
    """caisen-data 数据抓取工具"""
    pass


@cli.command()
@click.option("--symbol", "-s", required=True, help="股票代码")
@click.option("--start", required=True, help="开始日期 YYYY-MM-DD")
@click.option("--end", required=True, help="结束日期 YYYY-MM-DD")
@click.option("--freq", default="1d", help="频率: 1d, 5m, 15m, 30m, 60m")
@click.option("--output-dir", default="./data", help="输出目录")
@click.option("--source", default="akshare", help="数据源")
def fetch(symbol: str, start: str, end: str, freq: str, output_dir: str, source: str):
    """下载 K 线数据"""

    start_date = datetime.strptime(start, "%Y-%m-%d").date()
    end_date = datetime.strptime(end, "%Y-%m-%d").date()

    click.echo(f"Fetching {symbol} from {start} to {end} ({freq})...")

    # 加载数据
    if source == "akshare":
        ds = AKShareDataSource()
    else:
        click.echo(f"Unknown source: {source}")
        return

    bars = ds.load(symbol, start_date, end_date, freq)
    click.echo(f"Loaded {len(bars)} bars")

    # 保存为 Parquet
    output_path = Path(output_dir) / symbol / freq
    output_path.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame([{
        "timestamp": b.timestamp.isoformat(),
        "symbol": b.symbol,
        "freq": b.freq,
        "open": b.open,
        "high": b.high,
        "low": b.low,
        "close": b.close,
        "volume": b.volume,
    } for b in bars])

    file_path = output_path / f"{start.replace('-', '')}_{end.replace('-', '')}.parquet"
    df.to_parquet(file_path, index=False)

    click.echo(f"Saved to {file_path}")


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
    click.echo("  akshare - A股免费数据源")


def main():
    cli(prog_name="caisen-data")


if __name__ == "__main__":
    main()