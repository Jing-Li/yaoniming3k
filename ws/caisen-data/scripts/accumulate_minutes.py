#!/usr/bin/env python3
"""分钟线数据自动累积脚本

定时运行（建议每天收盘后），从新浪 API 获取最新分钟线数据，
与本地已有数据合并去重，逐步积累历史深度。

用法:
    python scripts/accumulate_minutes.py --symbol sc --freq 5m
    python scripts/accumulate_minutes.py --symbol sc --freq 30m
    python scripts/accumulate_minutes.py --symbol sc --all-freqs

定时任务 (crontab):
    # 每天 16:00 累积原油期货 5 分钟线
    0 16 * * 1-5 cd /path/to/caisen-data && .venv/bin/python scripts/accumulate_minutes.py --symbol sc --all-freqs
"""

import argparse
import logging
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

# 项目路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from caisen_data.sources.akshare import AKShareDataSource

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("accumulate")

DATA_DIR = Path("/Users/weimiao/Desktop/jing/projects/github/yaoniming3k/ws/data")


def get_existing_data(data_dir: Path, symbol: str, freq: str) -> pd.DataFrame | None:
    """加载本地已有的分钟线数据"""
    freq_dir = data_dir / symbol / freq
    if not freq_dir.exists():
        return None

    dfs = []
    for f in freq_dir.glob("*.parquet"):
        df = pd.read_parquet(f)
        if len(df) > 0:
            dfs.append(df)

    if not dfs:
        return None

    combined = pd.concat(dfs, ignore_index=True)
    combined["timestamp"] = pd.to_datetime(combined["timestamp"])
    combined = combined.sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)
    return combined


def accumulate(data_dir: Path, symbol: str, freq: str, ds: AKShareDataSource) -> int:
    """累积指定品种的分钟线数据，返回新增行数"""
    logger.info(f"开始累积 {symbol}/{freq} ...")

    # 加载已有数据
    existing = get_existing_data(data_dir, symbol, freq)
    if existing is not None:
        logger.info(f"  已有: {len(existing)} 条, 范围: {existing['timestamp'].iloc[0]} ~ {existing['timestamp'].iloc[-1]}")
    else:
        logger.info(f"  无已有数据")

    # 计算请求日期范围（尽量往前请求）
    if existing is not None:
        # 从已有数据最早时间往前推，尽量获取更多历史
        earliest = existing["timestamp"].min().date()
        request_start = earliest - timedelta(days=90)  # 往前多推 90 天
    else:
        request_start = date.today() - timedelta(days=90)

    request_end = date.today() + timedelta(days=1)

    # 下载新数据
    try:
        new_df = ds.load_futures_df(symbol, request_start, request_end, freq=freq)
    except Exception as e:
        logger.error(f"  下载失败: {e}")
        return 0

    if new_df is None or len(new_df) == 0:
        logger.warning(f"  未获取到新数据")
        return 0

    logger.info(f"  API返回: {len(new_df)} 条")

    # 合并去重
    new_df["timestamp"] = pd.to_datetime(new_df["timestamp"])
    if existing is not None:
        merged = pd.concat([existing, new_df], ignore_index=True)
    else:
        merged = new_df.copy()

    merged = merged.sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)

    new_count = len(merged) - (len(existing) if existing is not None else 0)

    # 保存
    freq_dir = data_dir / symbol / freq
    freq_dir.mkdir(parents=True, exist_ok=True)

    # 删除旧文件
    for f in freq_dir.glob("*.parquet"):
        f.unlink()

    ts_min = merged["timestamp"].min().strftime("%Y%m%d")
    ts_max = merged["timestamp"].max().strftime("%Y%m%d")
    out_path = freq_dir / f"{ts_min}_{ts_max}.parquet"
    merged.to_parquet(out_path, index=False)

    logger.info(f"  合并后: {len(merged)} 条, 新增: {new_count} 条")
    logger.info(f"  保存: {out_path}")
    logger.info(f"  范围: {merged['timestamp'].iloc[0]} ~ {merged['timestamp'].iloc[-1]}")

    return new_count


def main():
    parser = argparse.ArgumentParser(description="分钟线数据自动累积")
    parser.add_argument("--symbol", default="sc", help="品种代码")
    parser.add_argument("--freq", choices=["5m", "15m", "30m", "60m"], help="K线频率")
    parser.add_argument("--all-freqs", action="store_true", help="累积所有分钟频率 (5m, 15m, 30m, 60m)")
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR, help="数据目录")
    args = parser.parse_args()

    ds = AKShareDataSource()

    if args.all_freqs:
        freqs = ["5m", "15m", "30m", "60m"]
    elif args.freq:
        freqs = [args.freq]
    else:
        parser.error("必须指定 --freq 或 --all-freqs")
        return

    total_new = 0
    for freq in freqs:
        try:
            new_count = accumulate(args.data_dir, args.symbol, freq, ds)
            total_new += new_count
        except Exception as e:
            logger.error(f"累积 {args.symbol}/{freq} 失败: {e}")

    logger.info(f"全部完成, 共新增 {total_new} 条数据")


if __name__ == "__main__":
    main()
