"""可视化报告 Web 服务"""

import sys
from pathlib import Path
from typing import Optional

# 添加 src 路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse

from ..result.persistence import ResultPersister

# 配置
output_dir: str = "./runs"


def set_output_dir(path: str):
    """设置 output_dir"""
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

    # 路由定义（使用闭包捕获 output_dir）
    @app.get("/")
    async def root():
        """返回前端入口页面"""
        html_path = Path(__file__).parent.parent / "visualization" / "index.html"
        if html_path.exists():
            return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
        raise HTTPException(status_code=404, detail="前端文件未找到")

    @app.get("/api/runs")
    async def list_runs():
        """列出所有回测结果"""
        runs = ResultPersister.list_runs(output_dir)
        return {
            "count": len(runs),
            "runs": [
                {
                    "run_id": r["run_id"],
                    "strategy_name": r["strategy_name"],
                    "created_at": r.get("created_at", ""),
                }
                for r in runs
            ],
        }

    @app.get("/api/runs/{run_id}")
    async def get_run(run_id: str):
        """获取回测结果详情"""
        result = ResultPersister.load(run_id, output_dir)
        if not result:
            raise HTTPException(status_code=404, detail=f"Run '{run_id}' 未找到")
        return result

    @app.get("/api/runs/{run_id}/visualization")
    async def get_visualization(run_id: str):
        """获取可视化数据 (data.json)"""
        data = ResultPersister.load_visualization(run_id, output_dir)
        if not data:
            raise HTTPException(status_code=404, detail=f"可视化数据未找到: {run_id}")
        return data

    @app.get("/api/runs/{run_id}/data.json")
    async def get_data_json(run_id: str):
        """直接获取 data.json 文件"""
        run_dir = Path(output_dir) / run_id
        data_path = run_dir / "data.json"
        if not data_path.exists():
            raise HTTPException(status_code=404, detail="data.json 未找到")
        return FileResponse(
            data_path,
            media_type="application/json",
            headers={"Content-Disposition": f"inline; filename={run_id}.json"},
        )

    @app.get("/health")
    async def health():
        """健康检查"""
        return {"status": "ok"}

    return app


# 创建默认 app 实例（兼容旧代码）
app = create_app()


def serve(run_id: Optional[str] = None, port: int = 8000, host: str = "0.0.0.0"):
    """启动服务"""
    import uvicorn

    uvicorn.run(app, host=host, port=port, log_level="info")