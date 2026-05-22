import json
import logging
import os
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import settings
from .models.openai import ChatCompletionRequest, ChatCompletionResponse
from .providers import BaseProvider, TaijiProvider

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            log_obj.update(record.extra)
        return json.dumps(log_obj, ensure_ascii=False)


def setup_logging():
    # Ensure logs directory exists
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    logs_dir = os.path.join(project_root, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    # File handler with rotation (10MB max, 5 backup files)
    log_file = os.path.join(logs_dir, "taiji-provider.log")
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(JSONFormatter())

    # Root logger: only file output, no stdout
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers = [file_handler]

    # Set specific loggers to DEBUG level
    for name in ["raw_request", "raw_response", "provider_request", "provider_response"]:
        logging.getLogger(name).setLevel(logging.DEBUG)


setup_logging()

logger_raw_req = logging.getLogger("raw_request")
logger_raw_resp = logging.getLogger("raw_response")

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

taiji_provider = TaijiProvider()


app = FastAPI(title="OpenAI Compatible Provider")

# ---------------------------------------------------------------------------
# Auth middleware (optional, controlled by API_KEY env var)
# ---------------------------------------------------------------------------

security = HTTPBearer(auto_error=False)


def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
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
async def health():
    return {"status": "ok"}


@app.post("/v1/chat/completions")
async def chat_completions(request: Request, _auth=Depends(verify_api_key)):
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
    except Exception as exc:
        error_body = {
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


@app.get("/v1/models")
async def list_models(_auth=Depends(verify_api_key)):
    # taiji uses modern LLM models (GT-5/GPT-5.5) with large context windows.
    # The actual single-request limit is 800,000 characters (~200,000 tokens).
    # Set context_length to 200K tokens to match the real capacity.
    # This ensures hermes-agent correctly triggers compact when approaching the limit.
    # Note: The provider enforces TAIJI_MAX_TEXT_LENGTH (800,000 chars)
    # via smart truncation in _build_text to avoid API errors.
    CONTEXT_LENGTH = 200000
    
    return {
        "object": "list",
        "data": [
            {
                "id": "taiji",
                "object": "model",
                "created": 0,
                "owned_by": "taiji",
                "context_length": CONTEXT_LENGTH,
                "max_completion_tokens": 4096,
            }
        ],
    }


@app.get("/v1/models/{model_id}")
async def get_model(model_id: str, _auth=Depends(verify_api_key)):
    """Get a specific model by ID. Required by some OpenAI-compatible clients."""
    CONTEXT_LENGTH = 200000
    
    if model_id == "taiji":
        return {
            "id": "taiji",
            "object": "model",
            "created": 0,
            "owned_by": "taiji",
            "context_length": CONTEXT_LENGTH,
            "max_completion_tokens": 4096,
        }
    raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")


@app.get("/api/v1/models")
async def api_list_models(_auth=Depends(verify_api_key)):
    """Alias for /v1/models - used by some clients for model discovery."""
    return await list_models()


@app.get("/api/tags")
async def api_tags():
    """Empty tags endpoint for Ollama-compatible clients."""
    return {"models": []}


@app.get("/v1/props")
async def v1_props():
    """Empty props endpoint for client feature detection."""
    return {}


@app.get("/props")
async def props():
    """Empty props endpoint for client feature detection."""
    return {}


@app.get("/version")
async def version():
    """Version endpoint for client compatibility check."""
    return {"version": "1.0.0", "provider": "taiji"}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """将 FastAPI HTTPException 转换为 OpenAI 风格错误体。"""
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"message": str(exc.detail), "type": "server_error", "code": None}},
    )


@app.exception_handler(StarletteHTTPException)
async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """将 Starlette HTTPException（如 404 路由未找到）转换为 OpenAI 风格错误体。"""
    error_type = (
        "invalid_request_error" if exc.status_code in (404, 405) else "server_error"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": str(exc.detail),
                "type": error_type,
                "code": None,
            }
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "openai_provider.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=False,
    )
