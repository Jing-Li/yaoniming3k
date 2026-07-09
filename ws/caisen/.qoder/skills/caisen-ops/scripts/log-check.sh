#!/usr/bin/env bash
# log-check.sh — 收集 caisen 服务日志并输出结构化摘要
# 用法: bash .qoder/skills/caisen-ops/scripts/log-check.sh [log_file]
#
# 如果不指定 log_file，则尝试从常见位置查找。

set -euo pipefail

# --- 颜色 ---
RED='\033[0;31m'
YELLOW='\033[0;33m'
GREEN='\033[0;32m'
NC='\033[0m'

LOG_FILE="${1:-}"

# 自动查找日志文件
if [ -z "$LOG_FILE" ]; then
    # 尝试常见位置
    for candidate in \
        "logs/caisen.log" \
        "caisen.log" \
        "nohup.out" \
        "/tmp/caisen.log"; do
        if [ -f "$candidate" ]; then
            LOG_FILE="$candidate"
            break
        fi
    done
fi

echo "========================================"
echo " Caisen 日志诊断"
echo " $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"
echo ""

# --- 服务可用性检查 ---
echo "## 服务可用性"

check_port() {
    local port=$1
    local name=$2
    if lsof -i ":$port" -sTCP:LISTEN >/dev/null 2>&1; then
        echo -e "  ${GREEN}✅${NC} $name (port $port) — 运行中"
    else
        echo -e "  ${RED}❌${NC} $name (port $port) — 未运行"
    fi
}

check_port 8001 "FastAPI 后端"
check_port 8000 "Vite 前端"

# 健康检查
if curl -sf --max-time 3 http://localhost:8001/health >/dev/null 2>&1; then
    echo -e "  ${GREEN}✅${NC} /health — 正常"
else
    echo -e "  ${RED}❌${NC} /health — 不可达"
fi

echo ""

# --- API 端点检查 ---
echo "## API 端点"

check_endpoint() {
    local url=$1
    local name=$2
    local code
    code=$(curl -sf --max-time 3 -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
    if [ "$code" = "200" ]; then
        echo -e "  ${GREEN}✅${NC} $name ($code)"
    else
        echo -e "  ${RED}❌${NC} $name ($code)"
    fi
}

check_endpoint "http://localhost:8001/api/strategies" "策略列表"
check_endpoint "http://localhost:8001/api/data-sources" "数据源列表"
check_endpoint "http://localhost:8001/api/runs" "回测列表"

echo ""

# --- 数据目录检查 ---
echo "## 数据目录"

PROJECT_YAML="configs/project.yaml"
if [ -f "$PROJECT_YAML" ]; then
    DATA_DIR=$(grep '^data_dir:' "$PROJECT_YAML" | sed 's/^data_dir: *//')
    if [ -n "$DATA_DIR" ] && [ -d "$DATA_DIR" ]; then
        FILE_COUNT=$(find "$DATA_DIR" -name "*.parquet" 2>/dev/null | wc -l | tr -d ' ')
        echo -e "  ${GREEN}✅${NC} data_dir: $DATA_DIR ($FILE_COUNT 个 parquet 文件)"
    else
        echo -e "  ${RED}❌${NC} data_dir 不存在或为空: $DATA_DIR"
    fi
else
    echo -e "  ${YELLOW}⚠️${NC} configs/project.yaml 未找到"
fi

echo ""

# --- 日志文件分析 ---
if [ -z "$LOG_FILE" ] || [ ! -f "$LOG_FILE" ]; then
    echo "## 日志分析"
    echo -e "  ${YELLOW}⚠️${NC} 未找到日志文件。"
    echo "  提示: 若使用 'caisen web' 启动，日志输出在启动终端中。"
    echo "  可重定向: caisen web 2>&1 | tee logs/caisen.log"
    echo ""
    exit 0
fi

echo "## 日志分析 ($LOG_FILE)"
echo ""

TOTAL_LINES=$(wc -l < "$LOG_FILE" | tr -d ' ')
echo "  总行数: $TOTAL_LINES"

# 统计各级别
ERROR_COUNT=$(grep -c "ERROR\|CRITICAL" "$LOG_FILE" 2>/dev/null || echo "0")
WARN_COUNT=$(grep -c "WARNING\|WARN" "$LOG_FILE" 2>/dev/null || echo "0")
INFO_COUNT=$(grep -c "INFO" "$LOG_FILE" 2>/dev/null || echo "0")

echo -e "  ${RED}ERROR/CRITICAL${NC}: $ERROR_COUNT"
echo -e "  ${YELLOW}WARNING${NC}: $WARN_COUNT"
echo -e "  ${GREEN}INFO${NC}: $INFO_COUNT"
echo ""

# 最近 ERROR
if [ "$ERROR_COUNT" -gt 0 ]; then
    echo "### 最近 ERROR (最多 5 条)"
    grep -E "ERROR|CRITICAL" "$LOG_FILE" | tail -5 | while IFS= read -r line; do
        echo -e "  ${RED}$line${NC}"
    done
    echo ""
fi

# 最近 WARNING
if [ "$WARN_COUNT" -gt 0 ]; then
    echo "### 最近 WARNING (最多 5 条)"
    grep -E "WARNING|WARN" "$LOG_FILE" | tail -5 | while IFS= read -r line; do
        echo -e "  ${YELLOW}$line${NC}"
    done
    echo ""
fi

# 异常堆栈
EXCEPTION_COUNT=$(grep -c "Traceback\|Exception" "$LOG_FILE" 2>/dev/null || echo "0")
if [ "$EXCEPTION_COUNT" -gt 0 ]; then
    echo "### 异常堆栈 ($EXCEPTION_COUNT 处)"
    grep -A 3 "Traceback" "$LOG_FILE" | tail -20
    echo ""
fi

echo "========================================"
echo " 诊断完成"
echo "========================================"
