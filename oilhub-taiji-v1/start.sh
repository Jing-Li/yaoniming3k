#!/usr/bin/env bash
# OpenAI Provider 启动脚本
# 用法: ./start.sh [dev|prod] [--port PORT]

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHONPATH="${PROJECT_ROOT}/src:${PYTHONPATH:-}"
export PYTHONPATH

PORT="${APP_PORT:-8080}"
HOST="${APP_HOST:-0.0.0.0}"
WORKERS="${UVICORN_WORKERS:-1}"

# 检测模式（第一个参数如果是 dev/prod，则消费它）
MODE="prod"
if [[ $# -gt 0 ]] && [[ "$1" == "dev" || "$1" == "development" ]]; then
    MODE="dev"
    shift
elif [[ $# -gt 0 ]] && [[ "$1" == "prod" || "$1" == "production" ]]; then
    MODE="prod"
    shift
fi

# 解析剩余选项
while [[ $# -gt 0 ]]; do
    case "$1" in
        --port)
            PORT="$2"
            shift 2
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        --workers)
            WORKERS="$2"
            shift 2
            ;;
        -h|--help)
            cat <<'EOF'
用法: ./start.sh [MODE] [选项]

模式:
  dev   开发模式（启用热重载，单进程）
  prod  生产模式（多 worker，默认）

选项:
  --port PORT       监听端口（默认 8080，可由 APP_PORT 环境变量覆盖）
  --host HOST       监听地址（默认 0.0.0.0）
  --workers N       worker 数量（仅生产模式，默认 1）
  -h, --help        显示此帮助信息

环境变量:
  APP_PORT          监听端口
  APP_HOST          监听地址
  API_KEY           Bearer Token 认证密钥（可选）
  TAIJI_API_KEY     taiji API 密钥
  TAIJI_SESSION_COOKIE  taiji Session Cookie
EOF
            exit 0
            ;;
        *)
            echo "未知参数: $1" >&2
            echo "使用 -h 查看帮助" >&2
            exit 1
            ;;
    esac
done

cd "${PROJECT_ROOT}"

echo "======================================"
echo "  OpenAI Compatible Provider"
echo "======================================"
echo "  Mode:    ${MODE}"
echo "  Host:    ${HOST}"
echo "  Port:    ${PORT}"
echo "  PYTHONPATH: ${PYTHONPATH}"
echo "======================================"

# 检查 Python
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "错误: 未找到 python3 或 python" >&2
    exit 1
fi

# 检查依赖
if ! ${PYTHON} -c "import fastapi" 2>/dev/null; then
    echo "错误: 依赖未安装，请先运行: pip install -r requirements.txt" >&2
    exit 1
fi

MODULE="openai_provider.main:app"

if [[ "${MODE}" == "dev" ]]; then
    echo "[dev] 启动热重载开发服务器..."
    exec ${PYTHON} -m uvicorn "${MODULE}" \
        --host "${HOST}" \
        --port "${PORT}" \
        --reload \
        --log-level info
else
    if [[ "${WORKERS}" -gt 1 ]]; then
        echo "[prod] 启动生产服务器 (${WORKERS} workers)..."
        exec ${PYTHON} -m uvicorn "${MODULE}" \
            --host "${HOST}" \
            --port "${PORT}" \
            --workers "${WORKERS}" \
            --log-level info
    else
        echo "[prod] 启动单进程服务器..."
        exec ${PYTHON} -m uvicorn "${MODULE}" \
            --host "${HOST}" \
            --port "${PORT}" \
            --log-level info
    fi
fi
