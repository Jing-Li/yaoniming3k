"""双策略回测对比脚本

对比 CaiSenStrategy（多种配置）、LLMStrategy 在 sc 日线上的表现。
"""

import json
import sys
import time
from pathlib import Path
from datetime import datetime

# 确保 caisen 包可导入
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from caisen.backtest.runner import BacktestRunner


def run_backtest_safe(strategy_name, symbol, freq, start, end, config_name=None, label=""):
    """安全执行回测，返回 run_id 或错误信息"""
    tag = label or f"{strategy_name}({config_name or 'default'})"
    print(f"\n{'='*60}")
    print(f"  回测: {tag}")
    print(f"  标的: {symbol} | 频率: {freq} | 区间: {start} ~ {end}")
    if config_name:
        print(f"  配置: {config_name}")
    print(f"{'='*60}")

    t0 = time.time()
    try:
        run_id = BacktestRunner.run_backtest(
            strategy_name=strategy_name,
            symbol=symbol,
            freq=freq,
            start=start,
            end=end,
            config_name=config_name,
        )
        elapsed = time.time() - t0
        print(f"  ✓ 完成 run_id={run_id}  耗时 {elapsed:.1f}s")
        return run_id
    except Exception as e:
        elapsed = time.time() - t0
        print(f"  ✗ 失败 ({elapsed:.1f}s): {e}")
        return None


def load_metrics(run_id, output_dir="./runs"):
    """加载回测指标"""
    path = Path(output_dir) / run_id / "metrics.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def print_comparison(results):
    """打印对比表格"""
    print(f"\n\n{'='*80}")
    print("  策 略 回 测 对 比 报 告")
    print(f"{'='*80}")

    # 表头
    headers = ["策略", "总收益", "年化收益", "最大回撤", "夏普比率", "胜率", "盈亏比", "交易次数"]
    col_w = [24, 10, 10, 10, 10, 8, 8, 10]
    sep = "─" * (sum(col_w) + len(col_w) * 3)
    print(f"\n{sep}")
    print("  ".join(h.ljust(w) for h, w in zip(headers, col_w)))
    print(sep)

    best_sharpe = -999
    best_name = ""

    for r in results:
        if r["metrics"] is None:
            print(f"  {r['label'].ljust(col_w[0])}  {'— 回测失败 —'}")
            continue

        m = r["metrics"]
        total_ret = m.get("total_return", 0)
        ann_ret = m.get("annualized_return", 0)
        max_dd = m.get("max_drawdown", 0)
        sharpe = m.get("sharpe_ratio", 0)
        win_rate = m.get("win_rate", 0)
        pf = m.get("profit_factor", 0)
        trades = m.get("total_trades", 0)

        # 颜色标注
        ret_sign = "+" if total_ret >= 0 else ""
        dd_sign = "" if max_dd <= 0 else "+"

        row = [
            r["label"].ljust(col_w[0]),
            f"{ret_sign}{total_ret:.2%}".rjust(col_w[1]),
            f"{ann_ret:.2%}".rjust(col_w[2]),
            f"{max_dd:.2%}".rjust(col_w[3]),
            f"{sharpe:.2f}".rjust(col_w[4]),
            f"{win_rate:.1%}".rjust(col_w[5]),
            f"{pf:.2f}".rjust(col_w[6]),
            str(trades).rjust(col_w[7]),
        ]
        print("  ".join(row))

        if sharpe > best_sharpe and trades > 0:
            best_sharpe = sharpe
            best_name = r["label"]

    print(sep)

    # 综合评价
    print(f"\n{'='*80}")
    print("  综 合 评 价")
    print(f"{'='*80}")

    valid = [r for r in results if r["metrics"] and r["metrics"].get("total_trades", 0) > 0]

    if not valid:
        print("  没有有效的回测结果")
        return

    # 按夏普比率排序
    ranked = sorted(valid, key=lambda r: r["metrics"].get("sharpe_ratio", 0), reverse=True)

    print(f"\n  🏆 最靠谱策略: {ranked[0]['label']}")
    m = ranked[0]["metrics"]
    print(f"     总收益 {m.get('total_return',0):+.2%} | 最大回撤 {m.get('max_drawdown',0):.2%} | "
          f"夏普 {m.get('sharpe_ratio',0):.2f} | 胜率 {m.get('win_rate',0):.1%} | "
          f"交易 {m.get('total_trades',0)} 笔")

    if len(ranked) > 1:
        print(f"\n  📊 排名:")
        for i, r in enumerate(ranked, 1):
            m = r["metrics"]
            print(f"     {i}. {r['label']}: 夏普={m.get('sharpe_ratio',0):.2f}, "
                  f"收益={m.get('total_return',0):+.2%}, 回撤={m.get('max_drawdown',0):.2%}")

    print()


def main():
    # 回测参数
    symbol = "sc"
    freq = "1d"
    start = "2024-01-01"
    end = "2025-06-30"

    results = []

    # 1. CaiSenStrategy - 多种配置
    caisen_configs = [
        ("caisen_default", "CaiSen(默认)"),
        ("caisen_v2", "CaiSen(V2)"),
        ("caisen_high_winrate", "CaiSen(高胜率)"),
        ("caisen_ag_60m_optimized", "CaiSen(AG优化)"),
    ]

    for cfg, label in caisen_configs:
        run_id = run_backtest_safe("CaiSenStrategy", symbol, freq, start, end,
                                   config_name=cfg, label=label)
        metrics = load_metrics(run_id) if run_id else None
        results.append({"label": label, "run_id": run_id, "metrics": metrics})

    # 2. LLMStrategy - 尝试运行
    print(f"\n{'='*60}")
    print("  检查 LLMStrategy 可用性...")
    print(f"{'='*60}")
    try:
        # 快速测试 - 只用很短的时间段
        run_id = run_backtest_safe("LLMStrategy", symbol, freq, "2025-06-01", "2025-06-30",
                                   config_name="config_llm_test", label="LLM(测试)")
        metrics = load_metrics(run_id) if run_id else None
        results.append({"label": "LLM(测试)", "run_id": run_id, "metrics": metrics})
    except Exception as e:
        print(f"  LLMStrategy 不可用: {e}")
        results.append({"label": "LLM(测试)", "run_id": None, "metrics": None})

    # 打印对比
    print_comparison(results)


if __name__ == "__main__":
    main()
