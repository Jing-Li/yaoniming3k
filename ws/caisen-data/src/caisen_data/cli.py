"""caisen-data CLI"""

import logging
import click
from pathlib import Path
from datetime import datetime, date, timedelta
import pandas as pd

from .sources.akshare import AKShareDataSource

logger = logging.getLogger("caisen_data.cli")

# 默认数据目录
DEFAULT_DATA_DIR = "/Users/weimiao/Desktop/jing/projects/github/yaoniming3k/ws/data"

_ONE_DAY = timedelta(days=1)


def parse_date_range_from_filename(filename: Path) -> tuple[date, date] | None:
    """从 parquet 文件名解析日期范围，如 20240101_20240630.parquet -> (date, date)"""
    try:
        parts = filename.stem.split("_")
        if len(parts) >= 2:
            start = datetime.strptime(parts[0], "%Y%m%d").date()
            end = datetime.strptime(parts[1], "%Y%m%d").date()
            return start, end
    except ValueError:
        logger.debug("无法解析文件名: %s", filename.name)
    return None


def get_existing_range(data_dir: Path) -> tuple[date | None, date | None]:
    """通过文件名获取已有数据的时间范围（无需读取文件内容）"""
    if not data_dir.exists():
        return None, None

    parquet_files = list(data_dir.glob("*.parquet"))
    if not parquet_files:
        return None, None

    min_date = None
    max_date = None

    for pf in parquet_files:
        result = parse_date_range_from_filename(pf)
        if result:
            file_start, file_end = result
            if min_date is None or file_start < min_date:
                min_date = file_start
            if max_date is None or file_end > max_date:
                max_date = file_end

    return min_date, max_date


def normalize_ranges(ranges: list[tuple[date, date]]) -> list[tuple[date, date]]:
    """合并重叠或相邻的日期范围"""
    if not ranges:
        return []
    sorted_ranges = sorted(ranges, key=lambda x: x[0])
    merged: list[tuple[date, date]] = [sorted_ranges[0]]
    for start, end in sorted_ranges[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end + _ONE_DAY:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def find_range_gaps(
    requested_start: date,
    requested_end: date,
    existing_ranges: list[tuple[date, date]],
) -> list[tuple[date, date]]:
    """计算请求范围中缺失的日期区间

    Args:
        requested_start: 请求的开始日期
        requested_end: 请求的结束日期
        existing_ranges: 已有的日期范围列表

    Returns:
        缺失的日期区间列表（无缺失时返回空列表）
    """
    if not existing_ranges:
        return [(requested_start, requested_end)]

    sorted_ranges = sorted(existing_ranges, key=lambda x: x[0])
    gaps: list[tuple[date, date]] = []
    current = requested_start

    for exist_start, exist_end in sorted_ranges:
        if current < exist_start:
            gap_end = min(exist_start - _ONE_DAY, requested_end)
            if gap_end >= current:
                gaps.append((current, gap_end))
        current = max(current, exist_end + _ONE_DAY)

    if current <= requested_end:
        gaps.append((current, requested_end))

    return gaps


def merge_parquet_files(data_dir: Path) -> pd.DataFrame:
    """合并目录下的所有 parquet 文件"""
    parquet_files = list(data_dir.glob("*.parquet"))
    if not parquet_files:
        return pd.DataFrame()

    dfs = [pd.read_parquet(pf) for pf in parquet_files]
    combined = pd.concat(dfs, ignore_index=True)
    combined = combined.drop_duplicates(subset=["timestamp"])
    combined = combined.sort_values("timestamp").reset_index(drop=True)
    return combined


def _get_datasource(source: str):
    """根据名称获取数据源实例，不支持时返回 None"""
    if source == "akshare":
        return AKShareDataSource()
    return None


@click.group()
def cli():
    """caisen-data 数据抓取工具"""
    pass


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

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    data_dir = output_path / symbol / freq

    # --force 模式：删除旧文件，全量重新下载
    if force and data_dir.exists():
        logger.info("Force 模式，删除已有文件...")
        click.echo("Force mode: removing existing files...")
        for f in data_dir.glob("*.parquet"):
            logger.debug("删除: %s", f.name)
            f.unlink()

    # 计算已有数据范围（基于文件名，无需读取内容）
    existing_start, existing_end = get_existing_range(data_dir)

    if force or (existing_start is None):
        # 全量下载
        missing_ranges = [(start_date, end_date)]
    else:
        # 增量：计算缺失区间
        existing_ranges = [(existing_start, existing_end)]
        missing_ranges = find_range_gaps(start_date, end_date, existing_ranges)

        if not missing_ranges:
            click.echo(
                f"数据已是最新 ({existing_start} ~ {existing_end})，无需更新。"
            )
            logger.info("数据已是最新，跳过下载")
            return

        logger.info("缺失区间: %s", missing_ranges)
        click.echo(f"已有数据: {existing_start} ~ {existing_end}")
        for gap_s, gap_e in missing_ranges:
            click.echo(f"  缺失区间: {gap_s} ~ {gap_e}")

    # 获取数据源
    ds = _get_datasource(source)
    if ds is None:
        click.echo(f"未知数据源: {source}")
        logger.error("未知数据源: %s", source)
        return

    # 下载所有缺失区间
    new_dfs: list[pd.DataFrame] = []
    for gap_start, gap_end in missing_ranges:
        click.echo(f"正在获取 {symbol} {gap_start} ~ {gap_end} ({freq})...")
        logger.info("获取 %s %s ~ %s (%s)", symbol, gap_start, gap_end, freq)
        try:
            # 优先使用 DataFrame 接口（避免 Bar 对象转换开销）
            if hasattr(ds, "load_stock_df") and hasattr(ds, "load_futures_df"):
                from .sources.akshare import FUTURES_MAIN_CONTRACT

                if symbol in FUTURES_MAIN_CONTRACT:
                    df = ds.load_futures_df(symbol, gap_start, gap_end, freq)
                else:
                    df = ds.load_stock_df(symbol, gap_start, gap_end, freq)
            else:
                # 回退：通过 Bar 对象转换
                bars = ds.load(symbol, gap_start, gap_end, freq)
                if not bars:
                    logger.warning("区间 %s ~ %s 无数据", gap_start, gap_end)
                    continue
                df = pd.DataFrame(
                    [
                        {
                            "timestamp": b.timestamp.isoformat(),
                            "symbol": b.symbol,
                            "freq": b.freq,
                            "open": b.open,
                            "high": b.high,
                            "low": b.low,
                            "close": b.close,
                            "volume": b.volume,
                        }
                        for b in bars
                    ]
                )

            if not df.empty:
                new_dfs.append(df)
                click.echo(f"  获取到 {len(df)} 条数据")
        except Exception as e:
            logger.error("获取数据失败 (%s ~ %s): %s", gap_start, gap_end, e)
            click.echo(f"  获取失败: {e}")

    if not new_dfs:
        click.echo("未能获取到任何数据。")
        return

    new_df = pd.concat(new_dfs, ignore_index=True)

    # 合并已有数据
    combined: pd.DataFrame
    if data_dir.exists():
        existing_files = list(data_dir.glob("*.parquet"))
        existing_df = merge_parquet_files(data_dir)
        if not existing_df.empty:
            combined = pd.concat([existing_df, new_df], ignore_index=True)
            combined = combined.drop_duplicates(subset=["timestamp"])
            combined = combined.sort_values("timestamp").reset_index(drop=True)
            click.echo(
                f"合并: {len(existing_df)} 条旧 + {len(new_df)} 条新 = {len(combined)} 条"
            )
            # 删除旧的分段文件（ADR-0001: 合并为单个文件）
            for f in existing_files:
                logger.debug("删除旧文件: %s", f.name)
                f.unlink()
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

    click.echo(f"已保存到 {file_path} ({len(combined)} 条数据)")
    click.echo(
        f"数据范围: {actual_start[:4]}-{actual_start[4:6]}-{actual_start[6:]}"
        f" ~ {actual_end[:4]}-{actual_end[4:6]}-{actual_end[6:]}"
    )
    logger.info("保存完成: %s (%d 条)", file_path, len(combined))


@cli.command()
@click.option("--source", default="akshare", help="数据源")
def list_symbols(source: str):
    """列出可用标的"""
    ds = _get_datasource(source)
    if ds is None:
        click.echo(f"未知数据源: {source}")
        return

    try:
        symbols = ds.list_symbols()
        click.echo(f"共 {len(symbols)} 个标的:")
        for s in symbols[:20]:
            click.echo(f"  {s}")
        if len(symbols) > 20:
            click.echo(f"  ... 还有 {len(symbols) - 20} 个")
    except Exception as e:
        logger.error("列出标的失败: %s", e)
        click.echo(f"获取失败: {e}")


@cli.command()
def list_sources():
    """列出可用数据源"""
    click.echo("可用数据源:")
    click.echo("  akshare - A股、期货免费数据源")


def main():
    cli(prog_name="caisen-data")


if __name__ == "__main__":
    main()

