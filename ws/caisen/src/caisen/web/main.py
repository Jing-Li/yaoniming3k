"""可视化报告 Web 服务"""

import asyncio
import json
import logging
import queue
import re
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Query, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, field_validator

from caisen.backtest.runner import BacktestRunner
from caisen.config.project_config import ProjectConfig
from caisen.data.scanner import DataSourceScanner
from caisen.result.persistence import ResultPersister
from caisen.strategy.registry import StrategyRegistry
from caisen.web.optimizer import submit_optimize, submit_evolve, get_job

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

logger = logging.getLogger(__name__)


def _safe_resolve(base_dir: Path, user_input: str) -> Path:
    """安全解析路径，防止路径遍历攻击。

    Raises:
        HTTPException(400): 路径包含遍历字符或逃逸出 base_dir
    """
    if ".." in user_input or "/" in user_input or "\\" in user_input:
        raise HTTPException(status_code=400, detail="非法路径字符")
    resolved = (base_dir / user_input).resolve()
    if not str(resolved).startswith(str(base_dir.resolve())):
        raise HTTPException(status_code=400, detail="路径逃逸出允许范围")
    return resolved


class RunRequest(BaseModel):
    strategy_name: str
    symbol: str
    freq: str
    start: str
    end: str
    config_name: Optional[str] = None  # 配置预设文件名（不含 .yaml）；None 时使用策略默认值

    @field_validator("start", "end")
    @classmethod
    def validate_date(cls, v: str) -> str:
        if not _DATE_RE.match(v):
            raise ValueError(f"日期格式必须为 YYYY-MM-DD，收到：{v}")
        return v


class OptimizeRequest(BaseModel):
    strategy_name: str = "CaiSenStrategy"
    symbol: str
    freq: str
    start: str
    end: str
    workers: int = 4
    top_n: int = 10
    param_ranges: Optional[Dict[str, list]] = None

    @field_validator("start", "end")
    @classmethod
    def validate_date(cls, v: str) -> str:
        if not _DATE_RE.match(v):
            raise ValueError(f"日期格式必须为 YYYY-MM-DD，收到：{v}")
        return v


class EvolveRequest(BaseModel):
    symbol: str
    freq: str
    start: str
    end: str
    max_generations: int = 5
    base_prompt: Optional[str] = None

    @field_validator("start", "end")
    @classmethod
    def validate_date(cls, v: str) -> str:
        if not _DATE_RE.match(v):
            raise ValueError(f"日期格式必须为 YYYY-MM-DD，收到：{v}")
        return v


# 配置（从 configs/project.yaml 读取，无文件时用内嵌默认）
_project_config = ProjectConfig.load()
output_dir: str = _project_config.output_dir


def set_output_dir(path: str):
    """设置 output_dir（供测试或 CLI 覆盖）"""
    global output_dir
    output_dir = path


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(
        title="Caisen 可视化报告",
        description="量化回测系统可视化报告服务",
        version="0.1.0",
    )

    # CORS 配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 请求日志中间件 — 记录每个请求的方法、路径、状态码和耗时
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration_ms = int((time.time() - start) * 1000)
        # 跳过静态资源和健康检查的详细日志
        path = request.url.path
        if path.startswith(('/js/', '/src/', '/node_modules/')):
            return response
        level = logging.WARNING if response.status_code >= 400 else logging.INFO
        logger.log(level, '%s %s → %d (%dms)',
                   request.method, path, response.status_code, duration_ms)
        return response

    # 路由定义（使用闭包捕获 output_dir）
    @app.get("/")
    async def root():
        """返回前端入口页面"""
        # __file__ = src/caisen/web/main.py
        # parent.parent = src/caisen/
        html_path = Path(__file__).parent.parent / "frontend" / "index.html"
        if html_path.exists():
            return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
        raise HTTPException(status_code=404, detail="前端文件未找到")

    @app.get("/api/data-sources")
    async def list_data_sources():
        """列出本地可用行情数据（供前端下拉菜单使用）"""
        sources = DataSourceScanner.scan(_project_config.data_dir)
        return {"data_sources": sources}

    @app.get("/api/strategies")
    async def list_strategies():
        """列出所有可用策略（供前端下拉菜单使用）"""
        return {"strategies": StrategyRegistry.list_strategies()}

    @app.post("/api/runs", status_code=202)
    async def create_run(req: RunRequest):
        """触发回测：预校验策略名，后台执行，立即返回 run_id。"""
        known = {s["name"] for s in StrategyRegistry.list_strategies()}
        if req.strategy_name not in known:
            logger.warning('回测请求策略不存在: %s', req.strategy_name)
            raise HTTPException(status_code=422, detail=f"策略未注册：{req.strategy_name}")

        import datetime
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        run_id_placeholder = f"{req.strategy_name}_{ts}"

        logger.info('回测请求: strategy=%s symbol=%s freq=%s range=%s~%s config=%s → run_id=%s',
                     req.strategy_name, req.symbol, req.freq, req.start, req.end,
                     req.config_name or '(default)', run_id_placeholder)

        def _bg():
            try:
                BacktestRunner.run_backtest(
                    strategy_name=req.strategy_name,
                    symbol=req.symbol,
                    freq=req.freq,
                    start=req.start,
                    end=req.end,
                    config_name=req.config_name,
                )
            except Exception:
                logger.exception("回测后台执行失败: strategy=%s symbol=%s", req.strategy_name, req.symbol)

        threading.Thread(target=_bg, daemon=True).start()
        return {"run_id": run_id_placeholder}

    @app.get("/api/runs")
    async def list_runs():
        """列出所有回测结果（仅返回数据有效的 run）"""
        runs = ResultPersister.list_runs(output_dir)
        valid_runs = []
        for r in runs:
            run_dir = Path(output_dir) / r["run_id"]

            # 必须存在 meta.json
            meta_path = run_dir / "meta.json"
            if not meta_path.exists():
                continue

            # 必须存在 data.json 或 bars.parquet
            if not (run_dir / "data.json").exists() and not (run_dir / "bars.parquet").exists():
                continue

            # 若 meta.json 中显式声明 bar_count == 0，视为无效
            try:
                with open(meta_path, encoding="utf-8") as f:
                    meta = json.load(f)
            except (OSError, ValueError):
                continue
            if meta.get("bar_count", 1) == 0:
                continue

            # 附带读取 metrics.json（供前端版本对比使用）
            metrics: dict = {}
            metrics_path = run_dir / "metrics.json"
            if metrics_path.exists():
                try:
                    with open(metrics_path, encoding="utf-8") as f:
                        metrics = json.load(f) or {}
                except (OSError, ValueError):
                    metrics = {}

            valid_runs.append({**r, "metrics": metrics})

        return {
            "count": len(valid_runs),
            "runs": [
                {
                    "run_id": r["run_id"],
                    "strategy_name": r["strategy_name"],
                    "created_at": r.get("created_at", ""),
                    "metrics": r.get("metrics", {}),
                }
                for r in valid_runs
            ],
        }

    @app.get("/api/runs/{run_id}")
    async def get_run(run_id: str):
        """获取回测结果详情"""
        _safe_resolve(Path(output_dir), run_id)  # 路径校验
        result = ResultPersister.load(run_id, output_dir)
        if not result:
            raise HTTPException(status_code=404, detail=f"Run '{run_id}' 未找到")
        return result

    @app.get("/api/runs/{run_id}/visualization")
    async def get_visualization(run_id: str):
        """获取可视化数据 (data.json)"""
        _safe_resolve(Path(output_dir), run_id)  # 路径校验
        data = ResultPersister.load_visualization(run_id, output_dir)
        if not data:
            raise HTTPException(status_code=404, detail=f"可视化数据未找到: {run_id}")
        return data

    @app.get("/api/runs/{run_id}/data.json")
    async def get_data_json(run_id: str):
        """直接获取 data.json 文件"""
        run_dir = _safe_resolve(Path(output_dir), run_id)
        data_path = run_dir / "data.json"
        if not data_path.exists():
            raise HTTPException(status_code=404, detail="data.json 未找到")
        return FileResponse(
            data_path,
            media_type="application/json",
            headers={"Content-Disposition": f"inline; filename={run_id}.json"},
        )

    @app.get("/report.html")
    async def report_page():
        """返回回测详情页面"""
        html_path = Path(__file__).parent.parent / "frontend" / "report.html"
        if html_path.exists():
            return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
        raise HTTPException(status_code=404, detail="报告页面未找到")

    @app.get("/health")
    async def health():
        """健康检查"""
        return {"status": "ok"}

    @app.get("/js/{filename}")
    async def get_js_file(filename: str):
        """提供 JS 模块文件"""
        js_dir = Path(__file__).parent.parent / "frontend" / "src" / "js"
        js_path = _safe_resolve(js_dir, filename)
        if not js_path.exists():
            raise HTTPException(status_code=404, detail=f"JS file not found: {filename}")
        return FileResponse(js_path, media_type="application/javascript")

    @app.get("/src/css/{filename}")
    async def get_css_file(filename: str):
        """提供 CSS 文件"""
        css_dir = Path(__file__).parent.parent / "frontend" / "src" / "css"
        css_path = _safe_resolve(css_dir, filename)
        if not css_path.exists():
            raise HTTPException(status_code=404, detail=f"CSS file not found: {filename}")
        return FileResponse(css_path, media_type="text/css")

    @app.websocket("/ws/runs/{run_id}/progress")
    async def ws_run_progress(
        websocket: WebSocket,
        run_id: str,
        strategy_name: str = Query(...),
        symbol: str = Query(...),
        freq: str = Query(...),
        start: str = Query(...),
        end: str = Query(...),
        config_name: Optional[str] = Query(default=None),
    ):
        """WebSocket 进度端点：连接后在后台线程执行回测，实时推送进度消息。

        协议：
          {status: "running", processed, total, current_date}  每 100 根一次
          {status: "done", run_id}                             回测完成
          {status: "error", message}                           回测出错
        """
        await websocket.accept()

        msg_queue: queue.Queue = queue.Queue()

        def on_progress(processed: int, total: int, current_date: str) -> None:
            msg_queue.put({"status": "running", "processed": processed,
                           "total": total, "current_date": current_date})

        def _run():
            try:
                real_run_id = BacktestRunner.run_backtest(
                    strategy_name=strategy_name,
                    symbol=symbol,
                    freq=freq,
                    start=start,
                    end=end,
                    config_name=config_name,
                    on_progress=on_progress,
                )
                msg_queue.put({"status": "done", "run_id": real_run_id})
            except Exception as exc:
                msg_queue.put({"status": "error", "message": str(exc)})

        t = threading.Thread(target=_run, daemon=True)
        t.start()

        # 从队列取消息并推送，直到终态
        while True:
            try:
                msg = msg_queue.get(timeout=300)  # 最长等 5 分钟
            except queue.Empty:
                await websocket.send_json({"status": "error", "message": "回测超时"})
                break
            await websocket.send_json(msg)
            if msg["status"] in ("done", "error"):
                break

        await websocket.close()

    # ── 策略中心页面 ──────────────────────────────────────

    @app.get("/strategy.html")
    async def strategy_page():
        """返回策略管理与优化页面"""
        html_path = Path(__file__).parent.parent / "frontend" / "strategy.html"
        if html_path.exists():
            return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
        raise HTTPException(status_code=404, detail="策略中心页面未找到")

    # ── 策略详情 ──────────────────────────────────────────

    @app.get("/api/strategies/{name}")
    async def get_strategy(name: str):
        """返回单个策略的完整信息：params_schema, config_presets, type, note"""
        strategies = StrategyRegistry.list_strategies()
        for s in strategies:
            if s["name"] == name:
                return s
        raise HTTPException(status_code=404, detail=f"策略未注册：{name}")

    # ── 网格搜索优化 ─────────────────────────────────────

    def _load_bars_for_task(symbol: str, freq: str, start: str, end: str):
        """加载 K 线数据（供优化/进化任务使用）"""
        from caisen.backtest.runner import _load_bars
        return _load_bars(_project_config.data_dir, symbol, freq, start, end)

    @app.post("/api/optimize", status_code=202)
    async def create_optimize(req: OptimizeRequest):
        """提交网格搜索优化任务，返回 job_id"""
        try:
            bars = _load_bars_for_task(req.symbol, req.freq, req.start, req.end)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"数据加载失败：{e}")

        if not bars:
            raise HTTPException(status_code=422, detail="数据为空，请检查品种/频率/日期范围")

        msg_queue: queue.Queue = queue.Queue()

        def on_progress(completed: int, total: int, msg: str):
            msg_queue.put({"status": "running", "progress": completed, "total": total, "message": msg})

        job_id = submit_optimize(
            bars=bars,
            param_ranges=req.param_ranges,
            n_workers=req.workers,
            top_n=req.top_n,
            on_progress=on_progress,
        )

        logger.info('优化任务提交: job_id=%s symbol=%s freq=%s', job_id, req.symbol, req.freq)
        return {"job_id": job_id}

    @app.get("/api/optimize/{job_id}")
    async def get_optimize_result(job_id: str):
        """查询优化任务状态和结果"""
        job = get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"任务未找到：{job_id}")
        return job.to_dict()

    @app.websocket("/ws/optimize/{job_id}/progress")
    async def ws_optimize_progress(websocket: WebSocket, job_id: str):
        """WebSocket 实时推送优化进度"""
        await websocket.accept()

        job = get_job(job_id)
        if not job:
            await websocket.send_json({"status": "error", "message": f"任务未找到：{job_id}"})
            await websocket.close()
            return

        try:
            last_progress = -1
            while True:
                job = get_job(job_id)
                if not job:
                    break

                # 推送进度更新
                if job.progress != last_progress:
                    last_progress = job.progress
                    await websocket.send_json({
                        "status": job.status.value,
                        "progress": job.progress,
                        "total": job.total,
                        "message": job.message,
                    })

                # 终态退出
                if job.status in ("done", "error"):
                    if job.status == "done" and job.results:
                        await websocket.send_json({
                            "status": "done",
                            "progress": job.total,
                            "total": job.total,
                            "message": job.message,
                            "results": job.results,
                        })
                    elif job.status == "error":
                        await websocket.send_json({
                            "status": "error",
                            "message": job.error or "未知错误",
                        })
                    break

                await asyncio.sleep(0.5)

        except Exception:
            pass  # 客户端已断开
        finally:
            try:
                await websocket.close()
            except Exception:
                pass

    # ── Prompt 进化 ───────────────────────────────────────

    @app.post("/api/prompt-evolve", status_code=202)
    async def create_evolve(req: EvolveRequest):
        """提交 Prompt 进化任务，返回 job_id"""
        try:
            bars = _load_bars_for_task(req.symbol, req.freq, req.start, req.end)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"数据加载失败：{e}")

        if not bars:
            raise HTTPException(status_code=422, detail="数据为空，请检查品种/频率/日期范围")

        # 将 Bar 对象转为 dict 列表（LLM 策略使用 dict 格式）
        bars_dict = [
            {
                "timestamp": b.timestamp.isoformat(),
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
            }
            for b in bars
        ]

        msg_queue: queue.Queue = queue.Queue()

        def on_progress(gen: int, total: int, msg: str):
            msg_queue.put({"status": "running", "progress": gen, "total": total, "message": msg})

        job_id = submit_evolve(
            bars=bars_dict,
            symbol=req.symbol,
            freq=req.freq,
            max_generations=req.max_generations,
            base_prompt=req.base_prompt,
            on_progress=on_progress,
        )

        logger.info('进化任务提交: job_id=%s symbol=%s freq=%s', job_id, req.symbol, req.freq)
        return {"job_id": job_id}

    @app.get("/api/prompt-evolve/{job_id}")
    async def get_evolve_result(job_id: str):
        """查询进化任务状态和结果"""
        job = get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"任务未找到：{job_id}")
        return job.to_dict()

    @app.websocket("/ws/prompt-evolve/{job_id}/progress")
    async def ws_evolve_progress(websocket: WebSocket, job_id: str):
        """WebSocket 实时推送进化进度"""
        await websocket.accept()

        job = get_job(job_id)
        if not job:
            await websocket.send_json({"status": "error", "message": f"任务未找到：{job_id}"})
            await websocket.close()
            return

        try:
            last_progress = -1
            while True:
                job = get_job(job_id)
                if not job:
                    break

                if job.progress != last_progress:
                    last_progress = job.progress
                    await websocket.send_json({
                        "status": job.status.value,
                        "progress": job.progress,
                        "total": job.total,
                        "message": job.message,
                    })

                if job.status in ("done", "error"):
                    if job.status == "done" and job.results:
                        await websocket.send_json({
                            "status": "done",
                            "progress": job.total,
                            "total": job.total,
                            "message": job.message,
                            "results": job.results,
                        })
                    elif job.status == "error":
                        await websocket.send_json({
                            "status": "error",
                            "message": job.error or "未知错误",
                        })
                    break

                await asyncio.sleep(0.5)

        except Exception:
            pass  # 客户端已断开
        finally:
            try:
                await websocket.close()
            except Exception:
                pass

    return app


# 创建默认 app 实例（兼容旧代码）
app = create_app()


def serve(run_id: Optional[str] = None, port: int = 8000, host: str = "0.0.0.0"):
    """启动服务"""
    import uvicorn

    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    serve(port=_project_config.api_port)