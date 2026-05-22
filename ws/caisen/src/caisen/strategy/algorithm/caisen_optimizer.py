"""
蔡森策略参数优化工具

使用网格搜索（Grid Search）遍历参数组合，找到最优参数。
"""

import itertools
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np


@dataclass
class OptimizationResult:
    """单次优化结果"""
    params: Dict[str, Any]
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    total_trades: int
    profit_factor: float
    run_id: str

    def score(self) -> float:
        """
        综合评分

        目标：年化收益高、最大回撤小、夏普比率高、胜率高
        权重可根据偏好调整
        """
        # 基本指标
        annual_return = self.annual_return
        max_drawdown = abs(self.max_drawdown)  # 转正数
        sharpe = self.sharpe_ratio
        win_rate = self.win_rate

        # 避免除零
        if max_drawdown < 0.001:
            max_drawdown = 0.001

        # 综合评分（可调整权重）
        # 偏向高收益、低回撤、高夏普
        score = (
            annual_return * 0.4 +
            max_drawdown * 0.2 +
            sharpe * 0.2 +
            win_rate * 0.2
        )

        return score


@dataclass
class GridSearchConfig:
    """网格搜索配置"""

    # ===== 参数范围定义 =====
    stop_loss_factors: List[float] = field(default_factory=lambda: [0.94, 0.95, 0.96, 0.97, 0.98])
    min_profit_pcts: List[float] = field(default_factory=lambda: [0.02, 0.03, 0.04, 0.05])
    trailing_stop_pcts: List[float] = field(default_factory=lambda: [0.03, 0.05, 0.08])
    platform_min_bars_list: List[int] = field(default_factory=lambda: [8, 10, 12, 15])
    volume_thresholds: List[float] = field(default_factory=lambda: [1.2, 1.5, 2.0])

    # ===== 形态开关组合 =====
    # 格式：(开关名, 默认启用)
    pattern_configs: List[Dict[str, bool]] = field(default_factory=lambda: [
        # 激进：只开最强形态
        {"w_bottom": True, "head_and_shoulders_bottom": True, "cup_handle": False,
         "rounding_bottom": False, "triangle": False, "flag": False,
         "rectangle": False, "breakout_pullback": False, "m_top": False,
         "head_and_shoulders_top": False},
        # 平衡：开主要形态
        {"w_bottom": True, "head_and_shoulders_bottom": True, "cup_handle": True,
         "rounding_bottom": True, "triangle": False, "flag": False,
         "rectangle": False, "breakout_pullback": False, "m_top": False,
         "head_and_shoulders_top": False},
        # 保守：全开
        {"w_bottom": True, "head_and_shoulders_bottom": True, "cup_handle": True,
         "rounding_bottom": True, "triangle": True, "flag": True,
         "rectangle": True, "breakout_pullback": True, "m_top": True,
         "head_and_shoulders_top": True},
    ])

    # ===== 其他参数 =====
    first_position_pct: float = 0.30
    second_position_pct: float = 0.50
    breakdown_max_pct: float = 0.02
    pullback_max_bars: int = 3
    platform_max_amplitude: float = 0.05
    breakdown_max_bars: int = 2
    volume_confirm: bool = True
    platform_volume_decline: bool = True

    @property
    def total_combinations(self) -> int:
        """计算总参数组合数"""
        n = (len(self.stop_loss_factors) *
             len(self.min_profit_pcts) *
             len(self.trailing_stop_pcts) *
             len(self.platform_min_bars_list) *
             len(self.volume_thresholds) *
             len(self.pattern_configs))
        return n


def _generate_param_grid(config: GridSearchConfig) -> List[Dict[str, Any]]:
    """生成参数网格"""
    grids = []

    for (slf, mpp, tsp, pmb, vt, pc) in itertools.product(
        config.stop_loss_factors,
        config.min_profit_pcts,
        config.trailing_stop_pcts,
        config.platform_min_bars_list,
        config.volume_thresholds,
        config.pattern_configs,
    ):
        params = {
            "stop_loss_factor": slf,
            "min_profit_pct": mpp,
            "trailing_stop_pct": tsp,
            "platform_min_bars": pmb,
            "volume_threshold": vt,
            # 形态开关
            "w_bottom_enabled": pc["w_bottom"],
            "head_and_shoulders_bottom_enabled": pc["head_and_shoulders_bottom"],
            "cup_handle_enabled": pc["cup_handle"],
            "rounding_bottom_enabled": pc["rounding_bottom"],
            "triangle_enabled": pc["triangle"],
            "flag_enabled": pc["flag"],
            "rectangle_enabled": pc["rectangle"],
            "breakout_pullback_enabled": pc["breakout_pullback"],
            "m_top_enabled": pc["m_top"],
            "head_and_shoulders_top_enabled": pc["head_and_shoulders_top"],
            # 固定参数
            "platform_max_amplitude": config.platform_max_amplitude,
            "breakdown_max_pct": config.breakdown_max_pct,
            "pullback_max_bars": config.pullback_max_bars,
            "breakdown_max_bars": config.breakdown_max_bars,
            "first_position_pct": config.first_position_pct,
            "second_position_pct": config.second_position_pct,
            "volume_confirm": config.volume_confirm,
            "platform_volume_decline": config.platform_volume_decline,
        }
        grids.append(params)

    return grids


def _run_single_backtest(params: Dict[str, Any], bars: List, run_id: str) -> Optional[OptimizationResult]:
    """运行单次回测（延迟导入避免循环依赖）"""
    try:
        # 延迟导入避免循环依赖
        from .cai_sen_v2 import CaiSenStrategy
        from ..core.engine import BacktestEngine
        from ..core.config import BacktestConfig

        # 创建策略
        strategy = CaiSenStrategy(**params)

        # 运行回测
        engine = BacktestEngine(BacktestConfig())
        result = engine.run(strategy, bars)

        return OptimizationResult(
            params=params,
            annual_return=result.total_return,
            max_drawdown=result.max_drawdown,
            sharpe_ratio=result.sharpe_ratio,
            win_rate=result.win_rate,
            total_trades=len(result.trades),
            profit_factor=result.profit_factor,
            run_id=run_id,
        )
    except Exception as e:
        print(f"  [ERROR] {run_id}: {e}")
        return None


def grid_search(bars,
               config: Optional[GridSearchConfig] = None,
               output_dir: str = "./runs",
               n_workers: int = 4,
               top_n: int = 10) -> List[OptimizationResult]:
    """
    网格搜索参数优化

    Args:
        bars: K线数据
        config: 网格搜索配置（默认配置覆盖常用范围）
        output_dir: 结果输出目录
        n_workers: 并行工作线程数
        top_n: 返回前N个最优结果

    Returns:
        按综合评分排序的最优参数列表
    """
    if config is None:
        config = GridSearchConfig()

    print(f"\n{'='*60}")
    print(f"蔡森策略参数优化 - 网格搜索")
    print(f"{'='*60}")
    print(f"总参数组合数: {config.total_combinations}")
    print(f"并行线程数: {n_workers}")
    print(f"{'='*60}\n")

    # 生成参数网格
    param_grids = _generate_param_grid(config)
    print(f"生成了 {len(param_grids)} 组参数")

    # 生成运行ID前缀
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 并行执行回测
    results: List[OptimizationResult] = []
    total = len(param_grids)

    with ThreadPoolExecutor(max_workers=n_workers) as executor:
        futures = {}
        for i, params in enumerate(param_grids):
            run_id = f"optimize_{timestamp}_{i+1}"
            future = executor.submit(_run_single_backtest, params, bars, run_id)
            futures[future] = run_id

        for completed, future in enumerate(futures, 1):
            result = future.result()
            if result:
                results.append(result)
                # 打印进度
                if completed % 10 == 0 or completed == total:
                    print(f"  进度: {completed}/{total} ({completed*100//total}%)")

    print(f"\n完成! 成功回测 {len(results)}/{total} 组参数")

    # 按评分排序
    results.sort(key=lambda x: x.score(), reverse=True)

    # 输出前N个最优结果
    print(f"\n{'='*60}")
    print(f"最优参数 Top {top_n}")
    print(f"{'='*60}")

    for i, r in enumerate(results[:top_n], 1):
        print(f"\n--- #{i} (评分: {r.score():.4f}) ---")
        print(f"  年化收益: {r.annual_return*100:.2f}%")
        print(f"  最大回撤: {r.max_drawdown*100:.2f}%")
        print(f"  夏普比率: {r.sharpe_ratio:.2f}")
        print(f"  胜率: {r.win_rate*100:.2f}%")
        print(f"  总交易: {r.total_trades}")
        print(f"  盈亏比: {r.profit_factor:.2f}")
        print(f"  关键参数:")
        print(f"    stop_loss_factor: {r.params['stop_loss_factor']}")
        print(f"    min_profit_pct: {r.params['min_profit_pct']}")
        print(f"    trailing_stop_pct: {r.params['trailing_stop_pct']}")
        print(f"    platform_min_bars: {r.params['platform_min_bars']}")
        print(f"    volume_threshold: {r.params['volume_threshold']}")

        # 启用的形态
        enabled = [k.replace("_enabled", "") for k, v in r.params.items()
                   if k.endswith("_enabled") and v]
        print(f"    启用形态: {enabled}")

    # 保存结果到文件
    output_file = Path(output_dir) / f"optimization_results_{timestamp}.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    output_data = {
        "timestamp": timestamp,
        "total_combinations": config.total_combinations,
        "successful_runs": len(results),
        "top_results": [
            {
                "rank": i + 1,
                "score": r.score(),
                "params": r.params,
                "metrics": {
                    "annual_return": r.annual_return,
                    "max_drawdown": r.max_drawdown,
                    "sharpe_ratio": r.sharpe_ratio,
                    "win_rate": r.win_rate,
                    "total_trades": r.total_trades,
                    "profit_factor": r.profit_factor,
                }
            }
            for i, r in enumerate(results[:top_n])
        ]
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\n结果已保存到: {output_file}")

    return results[:top_n]


def generate_optimized_config(result: OptimizationResult, output_path: str) -> str:
    """
    从优化结果生成配置文件

    Args:
        result: 优化结果
        output_path: 输出路径

    Returns:
        生成的配置文件路径
    """
    params = result.params

    config_content = f'''# 蔡森策略优化配置 - 自动生成
# 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
# 评分: {result.score():.4f}

params:
  platform_min_bars: {params["platform_min_bars"]}
  platform_max_amplitude: {params["platform_max_amplitude"]}
  platform_volume_decline: true
  volume_threshold: {params["volume_threshold"]}

  breakdown_max_pct: {params["breakdown_max_pct"]}
  breakdown_max_bars: {params["breakdown_max_bars"]}
  pullback_max_bars: {params["pullback_max_bars"]}
  volume_confirm: true

  first_position_pct: {params["first_position_pct"]}
  second_position_pct: {params["second_position_pct"]}

  stop_loss_factor: {params["stop_loss_factor"]}
  min_profit_pct: {params["min_profit_pct"]}
  trailing_stop_pct: {params["trailing_stop_pct"]}
  trailing_stop_enabled: false

patterns:
  W_BOTTOM: {str(params["w_bottom_enabled"]).lower()}
  M_TOP: {str(params["m_top_enabled"]).lower()}
  HEAD_AND_SHOULDERS_BOTTOM: {str(params["head_and_shoulders_bottom_enabled"]).lower()}
  HEAD_AND_SHOULDERS_TOP: {str(params["head_and_shoulders_top_enabled"]).lower()}
  TRIANGLE: {str(params["triangle_enabled"]).lower()}
  FLAG: {str(params["flag_enabled"]).lower()}
  RECTANGLE: {str(params["rectangle_enabled"]).lower()}
  ROUNDING_BOTTOM: {str(params["rounding_bottom_enabled"]).lower()}
  CUP_HANDLE: {str(params["cup_handle_enabled"]).lower()}
  BREAKOUT_PULLBACK: {str(params["breakout_pullback_enabled"]).lower()}
'''

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(config_content)

    return output_path