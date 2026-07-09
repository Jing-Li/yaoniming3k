"""OpenAI 兼容 Taiji 网关主入口。

提供 /v1/chat/completions、/v1/models 等 OpenAI 兼容端点，
将请求转发至 Taiji LLM 后端并返回标准格式响应。
"""
from __future__ import annotations

import json
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, AsyncGenerator

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import settings
from .exceptions import ProviderError
from .models.openai import ChatCompletionRequest, ChatCompletionResponse
from .providers import TaijiProvider

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

class JSONFormatter(logging.Formatter):
    """将日志记录格式化为 JSON 字符串。"""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id  # type: ignore[attr-defined]
        if hasattr(record, "extra") and isinstance(record.extra, dict):  # type: ignore[attr-defined]
            log_obj.update(record.extra)  # type: ignore[attr-defined]
        return json.dumps(log_obj, ensure_ascii=False)


def setup_logging() -> None:
    """配置 JSON 结构化日志，输出到 logs/ 目录（10MB 轮转）。"""
    logs_dir = Path(__file__).resolve().parent.parent.parent / "logs"
    logs_dir.mkdir(exist_ok=True)

    log_file = logs_dir / "taiji-provider.log"
    file_handler = RotatingFileHandler(
        str(log_file),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(JSONFormatter())

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers = [file_handler]

    for name in ("raw_request", "raw_response", "provider_request", "provider_response"):
        logging.getLogger(name).setLevel(logging.DEBUG)


logger_raw_req = logging.getLogger("raw_request")
logger_raw_resp = logging.getLogger("raw_response")

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

taiji_provider = TaijiProvider()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期：初始化日志，关闭时清理 Provider 资源。"""
    setup_logging()
    yield
    await taiji_provider.close()


app = FastAPI(title="OpenAI Compatible Provider", lifespan=lifespan)

# CORS: 通过环境变量 CORS_ORIGINS 配置（逗号分隔），默认 "*"
_cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Auth middleware (optional, controlled by API_KEY env var)
# ---------------------------------------------------------------------------

security = HTTPBearer(auto_error=False)


def verify_api_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> HTTPAuthorizationCredentials | None:
    """验证 Bearer token。若未配置 API_KEY 则跳过认证。"""
    if not settings.API_KEY:
        return None  # 未配置，不启用认证
    if credentials is None or credentials.credentials != settings.API_KEY:
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "message": "Invalid or missing API key",
                    "type": "authentication_error",
                    "code": "invalid_api_key",
                }
            },
        )
    return credentials


@app.get("/health")
async def health() -> dict[str, str]:
    """健康检查端点。"""
    return {"status": "ok"}


@app.post("/v1/chat/completions")
async def chat_completions(
    request: Request, _auth=Depends(verify_api_key),
) -> Response:
    """OpenAI 兼容的 Chat Completions 端点（支持流式和非流式）。"""
    request_id = str(uuid.uuid4())

    # 读取原始请求体
    body_bytes = await request.body()
    try:
        body_text = body_bytes.decode("utf-8")
    except UnicodeDecodeError:
        body_text = "<binary body>"

    # 日志：接受的原始请求
    logger_raw_req.debug(
        "Incoming request",
        extra={
            "request_id": request_id,
            "extra": {
                "method": request.method,
                "path": str(request.url),
                "headers": dict(request.headers),
                "body": body_text[:5000],
            },
        },
    )

    # 解析请求
    try:
        req = ChatCompletionRequest.model_validate_json(body_text)
    except Exception as exc:
        error_body = {
            "error": {
                "message": f"Invalid request: {exc}",
                "type": "invalid_request_error",
                "code": None,
            }
        }
        logger_raw_resp.debug(
            "Outgoing response (validation error)",
            extra={
                "request_id": request_id,
                "extra": {
                    "status_code": 400,
                    "body": error_body,
                },
            },
        )
        return JSONResponse(status_code=400, content=error_body)

    if req.stream:
        async def stream_generator():
            all_chunks = []
            try:
                async for chunk in taiji_provider.stream_chat_completions(req, request_id):
                    all_chunks.append(chunk)
                    yield f"data: {chunk}\n\n"
                yield "data: [DONE]\n\n"
                
                # Log the full streaming response for debugging
                logger_raw_resp.debug(
                    "Outgoing response (streaming)",
                    extra={
                        "request_id": request_id,
                        "extra": {
                            "total_chunks": len(all_chunks),
                            "chunks_preview": all_chunks[:5] if len(all_chunks) > 5 else all_chunks,
                        },
                    },
                )
            except Exception as exc:
                error_chunk = json.dumps(
                    {"error": {"message": str(exc), "type": "provider_error", "code": None}}
                )
                yield f"data: {error_chunk}\n\n"

        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    # 调用 provider
    try:
        resp: ChatCompletionResponse = await taiji_provider.chat_completions(req, request_id)
    except ProviderError as exc:
        error_body: dict[str, Any] = {
            "error": {
                "message": str(exc),
                "type": "provider_error",
                "code": None,
            }
        }
        logger_raw_resp.debug(
            "Outgoing response (provider error)",
            extra={
                "request_id": request_id,
                "extra": {
                    "status_code": 502,
                    "body": error_body,
                },
            },
        )
        return JSONResponse(status_code=502, content=error_body)

    resp_dict = resp.model_dump()

    # 日志：返回给客户端的响应
    logger_raw_resp.debug(
        "Outgoing response",
        extra={
            "request_id": request_id,
            "extra": {
                "status_code": 200,
                "body": resp_dict,
            },
        },
    )

    return JSONResponse(content=resp_dict)


def _model_info(model_id: str) -> dict[str, Any]:
    """构建单个模型的元信息。"""
    return {
        "id": model_id,
        "object": "model",
        "created": 0,
        "owned_by": model_id,
        "context_length": settings.MODEL_CONTEXT_LENGTH,
        "max_completion_tokens": settings.MODEL_MAX_COMPLETION_TOKENS,
    }


@app.get("/v1/models")
async def list_models(_auth=Depends(verify_api_key)) -> dict[str, Any]:
    """列出所有可用模型。"""
    return {
        "object": "list",
        "data": [_model_info("taiji")],
    }


@app.get("/v1/models/{model_id}")
async def get_model(model_id: str, _auth=Depends(verify_api_key)) -> dict[str, Any]:
    """Get a specific model by ID. Required by some OpenAI-compatible clients."""
    if model_id == "taiji":
        return _model_info("taiji")
    raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")


@app.get("/api/v1/models")
async def api_list_models(_auth=Depends(verify_api_key)) -> dict[str, Any]:
    """Alias for /v1/models - used by some clients for model discovery."""
    return await list_models()


@app.get("/api/tags")
async def api_tags() -> dict[str, list[Any]]:
    """Empty tags endpoint for Ollama-compatible clients."""
    return {"models": []}


@app.get("/v1/props")
async def v1_props() -> dict[str, Any]:
    """Empty props endpoint for client feature detection."""
    return {}


@app.get("/props")
async def props() -> dict[str, Any]:
    """Empty props endpoint for client feature detection."""
    return {}


@app.get("/version")
async def version() -> dict[str, str]:
    """Version endpoint for client compatibility check."""
    return {"version": "1.0.0", "provider": "taiji"}


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """将所有 HTTPException（含 FastAPI 子类）转换为 OpenAI 风格错误体。"""
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    error_type = (
        "invalid_request_error" if exc.status_code in (404, 405) else "server_error"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"message": str(exc.detail), "type": error_type, "code": None}},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "openai_provider.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=False,
    )
