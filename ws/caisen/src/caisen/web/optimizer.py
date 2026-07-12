"""
异步优化任务管理器

管理网格搜索和 Prompt 进化任务的生命周期：
- 任务提交 → 后台线程执行 → 进度回调 → 结果查询
- job_id → JobState 字典，线程安全
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from enum import Enum

from caisen.strategy.algorithm.caisen_optimizer import (
    grid_search,
    GridSearchConfig,
    OptimizationResult,
)


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


@dataclass
class JobState:
    """单个优化任务的运行时状态"""

    job_id: str
    status: JobStatus = JobStatus.PENDING
    progress: int = 0
    total: int = 0
    message: str = ""
    results: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "job_id": self.job_id,
            "status": self.status.value,
            "progress": self.progress,
            "total": self.total,
            "message": self.message,
            "created_at": self.created_at,
        }
        if self.results is not None:
            d["results"] = self.results
        if self.error is not None:
            d["error"] = self.error
        return d


_lock = threading.Lock()
_jobs: Dict[str, JobState] = {}


def get_job(job_id: str) -> Optional[JobState]:
    with _lock:
        return _jobs.get(job_id)


def _register_job(job: JobState) -> None:
    with _lock:
        _jobs[job.job_id] = job


def _update_job(job_id: str, **kwargs) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if job:
            for k, v in kwargs.items():
                setattr(job, k, v)


# ── 网格搜索优化 ────────────────────────────────────────


def submit_optimize(
    *,
    bars: List,
    param_ranges: Optional[Dict] = None,
    n_workers: int = 4,
    top_n: int = 5,
    on_progress: Optional[Callable] = None,
) -> str:
    """提交网格搜索优化任务，返回 job_id。

    Args:
        bars: K 线数据
        param_ranges: 用户自定义参数范围（可选）
        n_workers: 并行线程数
        top_n: 返回前 N 个最优结果
        on_progress: 进度回调 (completed, total, message)
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    job = JobState(job_id=f"opt_{ts}")
    _register_job(job)

    def _run():
        try:
            _update_job(job.job_id, status=JobStatus.RUNNING, message="正在生成参数网格...")

            config = GridSearchConfig()
            if param_ranges:
                for attr in ("stop_loss_factors", "min_profit_pcts", "trailing_stop_pcts",
                             "platform_min_bars_list", "volume_thresholds"):
                    if attr in param_ranges:
                        setattr(config, attr, param_ranges[attr])

            total = config.total_combinations()

            def _on_complete(completed: int, total_n: int, msg: str = "done"):
                _update_job(job.job_id, progress=completed, total=total_n, message=msg)

            results = _run_grid_search_with_progress(
                bars, config, n_workers, on_progress or _on_complete
            )

            # 排序取 top_n
            results.sort(key=lambda x: x.score, reverse=True)
            formatted = []
            for i, r in enumerate(results[:top_n]):
                formatted.append({
                    "rank": i + 1,
                    "score": r.score,
                    "annual_return": r.annual_return,
                    "max_drawdown": r.max_drawdown,
                    "sharpe_ratio": r.sharpe_ratio,
                    "win_rate": r.win_rate,
                    "total_trades": r.total_trades,
                    "profit_factor": r.profit_factor,
                    "params": r.params,
                })

            _update_job(
                job.job_id,
                status=JobStatus.DONE,
                results=formatted,
                message=f"优化完成，共 {len(results)} 组结果",
            )

        except Exception as e:
            _update_job(job.job_id, status=JobStatus.ERROR, error=str(e))

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return job.job_id


def _run_grid_search_with_progress(
    bars: List,
    config: GridSearchConfig,
    n_workers: int,
    on_progress: Callable,
) -> List[OptimizationResult]:
    """带进度回调的网格搜索（改造自 caisen_optimizer.grid_search）"""
    from caisen.strategy.algorithm.caisen_optimizer import (
        _generate_param_grid,
        _run_single_backtest,
    )

    param_grids = _generate_param_grid(config)
    results: List[OptimizationResult] = []
    total = len(param_grids)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    with ThreadPoolExecutor(max_workers=n_workers) as executor:
        futures = {}
        for i, params in enumerate(param_grids):
            run_id = f"optimize_{timestamp}_{i}"
            future = executor.submit(_run_single_backtest, params, bars, run_id)
            futures[future] = i

        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)
            completed = len(futures) - sum(1 for f in futures if not f.done())
            on_progress(completed, total, f"进度: {completed}/{total}")

    results.sort(key=lambda x: x.score, reverse=True)
    return results


# ── Prompt 进化 ────────────────────────────────────────


def submit_evolve(
    *,
    bars: List[Dict],
    symbol: str,
    freq: str,
    max_generations: int = 5,
    base_prompt: Optional[str] = None,
    on_progress: Optional[Callable] = None,
) -> str:
    """提交 Prompt 进化任务，返回 job_id。

    Args:
        bars: K 线数据（dict 列表，LLM 策略使用 dict 格式）
        symbol: 品种代码
        freq: K 线频率
        max_generations: 最大进化代数
        base_prompt: 基础 Prompt（可选）
        on_progress: 进度回调 (gen, total, message)
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    job = JobState(job_id=f"evo_{ts}")
    _register_job(job)

    def _run():
        try:
            _update_job(job.job_id, status=JobStatus.RUNNING, message="正在初始化 Prompt 进化器...")

            from caisen.strategy.llm.evolver import PromptEvolver
            from caisen.strategy.llm.client import LLMClient
            from caisen.config.project_config import ProjectConfig

            project_config = ProjectConfig.load()
            llm_config = project_config.get_llm_config()
            llm_client = LLMClient.from_config(llm_config)

            evolver = PromptEvolver(
                llm_client=llm_client,
                bars=bars,
                max_iterations=max_generations,
            )

            generations = []
            current_rules = base_prompt or "支撑位买入，阻力位卖出"

            for gen in range(max_generations):
                _update_job(
                    job.job_id,
                    progress=gen,
                    total=max_generations,
                    message=f"第 {gen + 1}/{max_generations} 代进化中...",
                )

                if on_progress:
                    on_progress(gen, max_generations, f"第 {gen + 1}/{max_generations} 代进化中...")

                gen_result = evolver.evolve(initial_rules=current_rules)
                if gen_result and gen_result.best_result:
                    score = round(gen_result.best_result.score, 4)
                    generations.append({
                        "generation": gen + 1,
                        "score": score,
                        "rules": gen_result.best_result.prompt,
                    })
                    current_rules = gen_result.best_result.prompt

            _update_job(
                job.job_id,
                status=JobStatus.DONE,
                progress=max_generations,
                total=max_generations,
                results=generations,
                message="进化完成",
            )

        except Exception as e:
            _update_job(job.job_id, status=JobStatus.ERROR, error=str(e))

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return job.job_id
