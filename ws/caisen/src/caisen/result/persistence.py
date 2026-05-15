"""Result (回测结果) 持久化"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
import pandas as pd

from ..core.engine import BacktestResult
from ..core.bar import Bar
from ..core.trade import Trade
from .metrics import PerformanceMetrics, calculate_metrics


class ResultPersister:
    """结果持久化"""

    @staticmethod
    def save(result: BacktestResult, output_dir: str = "./runs") -> str:
        """保存回测结果，返回 run_id"""
        # 生成 run_id
        run_id = f"{result.strategy_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        run_dir = Path(output_dir) / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        # 保存元数据 (JSON)
        meta = {
            "run_id": run_id,
            "strategy_name": result.strategy_name,
            "initial_capital": result.initial_capital,
            "final_equity": result.final_equity,
            "total_return": result.total_return,
            "total_trades": len(result.trades),
            "created_at": datetime.now().isoformat(),
        }
        with open(run_dir / "meta.json", "w") as f:
            json.dump(meta, f, indent=2)

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
            annotations_data = [a.__dict__ for a in result.annotations]
            with open(run_dir / "annotations.json", "w") as f:
                json.dump(annotations_data, f)

        # 计算并保存绩效指标
        metrics = calculate_metrics(result)
        with open(run_dir / "metrics.json", "w") as f:
            json.dump(metrics.__dict__, f, indent=2)

        return run_id

    @staticmethod
    def load(run_id: str, output_dir: str = "./runs") -> Optional[dict]:
        """加载回测结果"""
        run_dir = Path(output_dir) / run_id
        if not run_dir.exists():
            return None

        meta_path = run_dir / "meta.json"
        if not meta_path.exists():
            return None

        with open(meta_path) as f:
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
            with open(annotations_path) as f:
                meta["annotations"] = json.load(f)

        # 加载指标
        metrics_path = run_dir / "metrics.json"
        if metrics_path.exists():
            with open(metrics_path) as f:
                meta["metrics"] = json.load(f)

        return meta

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
                    with open(meta_path) as f:
                        runs.append(json.load(f))

        return runs