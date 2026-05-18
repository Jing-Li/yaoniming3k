"""Result (回测结果) 持久化"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from ..core.engine import BacktestResult
from .metrics import calculate_metrics


def _generate_run_id(strategy_name: str, output_dir: str) -> str:
    """生成唯一的 run_id

    格式: {策略名}_{YYYYMMDD}_{序号}
    序号从 1 开始，同日同名策略重复运行递增
    """
    date_str = datetime.now().strftime("%Y%m%d")
    base_name = f"{strategy_name}_{date_str}"

    # 查找已有的 run_id，统计同日同名策略数量
    runs_dir = Path(output_dir)
    max_seq = 0
    if runs_dir.exists():
        for path in runs_dir.iterdir():
            if path.is_dir() and path.name.startswith(base_name):
                # 提取序号
                parts = path.name.split("_")
                if len(parts) >= 3:
                    try:
                        seq = int(parts[-1])
                        max_seq = max(max_seq, seq)
                    except ValueError:
                        pass

    # 新的序号
    new_seq = max_seq + 1
    return f"{base_name}_{new_seq}"


def _get_bars_summary(bars) -> dict:
    """从 bars 列表提取元数据"""
    if not bars:
        return {}

    first = bars[0]
    last = bars[-1]

    return {
        "symbol": first.symbol,
        "freq": first.freq,
        "start": first.timestamp.isoformat(),
        "end": last.timestamp.isoformat(),
        "bar_count": len(bars),
    }


class ResultPersister:
    """结果持久化"""

    @staticmethod
    def save(result: BacktestResult, output_dir: str = "./runs") -> str:
        """保存回测结果，返回 run_id

        保存内容：
        - meta.json: 元数据
        - equity.parquet: 净值曲线
        - trades.parquet: 交易记录
        - annotations.json: 可视化标注
        - metrics.json: 绩效指标
        - bars.parquet: K线数据（用于可视化）
        - data.json: 前端可视化综合文件
        """
        # 生成 run_id
        run_id = _generate_run_id(result.strategy_name, output_dir)
        run_dir = Path(output_dir) / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        # 从 bars 提取元数据
        bars_meta = _get_bars_summary(result.bars)

        # 保存元数据 (JSON)
        meta = {
            "run_id": run_id,
            "strategy_name": result.strategy_name,
            **bars_meta,
            "initial_capital": result.initial_capital,
            "final_equity": result.final_equity,
            "total_return": result.total_return,
            "total_trades": len(result.trades),
            "created_at": datetime.now().isoformat(),
        }
        with open(run_dir / "meta.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

        # 保存净值曲线 (Parquet)
        if result.equity_curve:
            df = pd.DataFrame(result.equity_curve)
            df.to_parquet(run_dir / "equity.parquet", index=False)

        # 保存交易记录 (Parquet)
        if result.trades:
            trades_data = [t.to_dict() for t in result.trades]
            df = pd.DataFrame(trades_data)
            df.to_parquet(run_dir / "trades.parquet", index=False)

        # 保存可视化标注 (JSON)
        if result.annotations:
            annotations_data = [a.to_dict() for a in result.annotations]
            with open(run_dir / "annotations.json", "w", encoding="utf-8") as f:
                json.dump(annotations_data, f, ensure_ascii=False)

        # 计算并保存绩效指标
        metrics = calculate_metrics(result)
        with open(run_dir / "metrics.json", "w", encoding="utf-8") as f:
            json.dump(metrics.__dict__, f, indent=2, ensure_ascii=False)

        # 保存 K 线数据 (Parquet)
        if result.bars:
            bars_data = [b.to_dict() for b in result.bars]
            df = pd.DataFrame(bars_data)
            df.to_parquet(run_dir / "bars.parquet", index=False)

        # 生成前端可视化文件 (data.json)
        ResultPersister.save_visualization(run_id, output_dir)

        return run_id

    @staticmethod
    def save_visualization(run_id: str, output_dir: str = "./runs") -> None:
        """生成前端可视化用的 data.json

        结构参见 ADR-0007
        """
        run_dir = Path(output_dir) / run_id
        if not run_dir.exists():
            return

        # 加载 meta
        meta_path = run_dir / "meta.json"
        if not meta_path.exists():
            return

        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)

        # 构建 data.json
        data = {
            "meta": {
                "strategy_name": meta["strategy_name"],
                "symbol": meta.get("symbol", ""),
                "start": meta.get("start", ""),
                "end": meta.get("end", ""),
                "freq": meta.get("freq", "1d"),
            },
            "metrics": {},
            "bars": [],
            "equity_curve": [],
            "trades": [],
            "annotations": [],
        }

        # 加载绩效指标
        metrics_path = run_dir / "metrics.json"
        if metrics_path.exists():
            with open(metrics_path, encoding="utf-8") as f:
                data["metrics"] = json.load(f)

        # 加载 K 线数据
        bars_path = run_dir / "bars.parquet"
        if bars_path.exists():
            df = pd.read_parquet(bars_path)
            data["bars"] = df.to_dict("records")

        # 加载净值曲线
        equity_path = run_dir / "equity.parquet"
        if equity_path.exists():
            df = pd.read_parquet(equity_path)
            data["equity_curve"] = df.to_dict("records")

        # 加载交易记录
        trades_path = run_dir / "trades.parquet"
        if trades_path.exists():
            df = pd.read_parquet(trades_path)
            data["trades"] = df.to_dict("records")

        # 加载标注
        annotations_path = run_dir / "annotations.json"
        if annotations_path.exists():
            with open(annotations_path, encoding="utf-8") as f:
                data["annotations"] = json.load(f)

        # 写入 data.json
        with open(run_dir / "data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def load(run_id: str, output_dir: str = "./runs") -> Optional[dict]:
        """加载回测结果"""
        run_dir = Path(output_dir) / run_id
        if not run_dir.exists():
            return None

        meta_path = run_dir / "meta.json"
        if not meta_path.exists():
            return None

        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)

        # 加载净值曲线
        equity_path = run_dir / "equity.parquet"
        if equity_path.exists():
            meta["equity_curve"] = pd.read_parquet(equity_path).to_dict("records")

        # 加载交易记录
        trades_path = run_dir / "trades.parquet"
        if trades_path.exists():
            meta["trades"] = pd.read_parquet(trades_path).to_dict("records")

        # 加载标注
        annotations_path = run_dir / "annotations.json"
        if annotations_path.exists():
            with open(annotations_path, encoding="utf-8") as f:
                meta["annotations"] = json.load(f)

        # 加载指标
        metrics_path = run_dir / "metrics.json"
        if metrics_path.exists():
            with open(metrics_path, encoding="utf-8") as f:
                meta["metrics"] = json.load(f)

        # 加载 K 线数据
        bars_path = run_dir / "bars.parquet"
        if bars_path.exists():
            df = pd.read_parquet(bars_path)
            meta["bars"] = df.to_dict("records")

        return meta

    @staticmethod
    def load_visualization(run_id: str, output_dir: str = "./runs") -> Optional[dict]:
        """加载前端可视化数据 (data.json)"""
        run_dir = Path(output_dir) / run_id
        data_path = run_dir / "data.json"

        if not data_path.exists():
            return None

        with open(data_path, encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def list_runs(output_dir: str = "./runs") -> list:
        """列出所有回测结果"""
        runs_dir = Path(output_dir)
        if not runs_dir.exists():
            return []

        runs = []
        for run_path in sorted(runs_dir.iterdir()):
            if run_path.is_dir():
                meta_path = run_path / "meta.json"
                if meta_path.exists():
                    with open(meta_path, encoding="utf-8") as f:
                        runs.append(json.load(f))

        return runs