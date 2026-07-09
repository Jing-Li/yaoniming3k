# Caisen API curl 命令手册

> 所有命令假定后端运行在 `localhost:8001`。
> 从 `configs/project.yaml` 和 `configs/strategies/*.yaml` 提取最新参数。

## 基础端点

### 健康检查
```bash
curl -sf http://localhost:8001/health
# {"status":"ok"}
```

### 前端页面（由 Vite 8000 提供，后端 8001 也提供静态文件）
```bash
# 首页
curl -sf http://localhost:8000/ -o /dev/null -w "%{http_code}"
# 报告页
curl -sf "http://localhost:8000/report.html?run_id=<RUN_ID>" -o /dev/null -w "%{http_code}"
```

## 数据端点

### 列出可用数据源
```bash
curl -s http://localhost:8001/api/data-sources | python3 -m json.tool
```
**诊断**：返回空 → 检查 `configs/project.yaml` 的 `data_dir`，确认 `{data_dir}/{symbol}/{freq}/*.parquet` 文件存在。

### 列出可用策略
```bash
curl -s http://localhost:8001/api/strategies | python3 -m json.tool
```
**诊断**：返回空 → 检查 `src/caisen/strategy/` 下的策略注册代码。

## 回测端点

### 列出所有回测
```bash
curl -s http://localhost:8001/api/runs | python3 -m json.tool
```

### 获取回测详情
```bash
# 完整数据（meta + metrics + bars + trades）
curl -s http://localhost:8001/api/runs/<RUN_ID> | python3 -m json.tool

# 仅可视化数据（data.json）
curl -s http://localhost:8001/api/runs/<RUN_ID>/visualization | python3 -m json.tool

# 直接下载 data.json
curl -sO http://localhost:8001/api/runs/<RUN_ID>/data.json
```

### 触发回测（REST API）
```bash
curl -s -X POST http://localhost:8001/api/runs \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_name": "CaiSenStrategy",
    "symbol": "ag",
    "freq": "1d",
    "start": "2024-01-01",
    "end": "2024-06-30",
    "config_name": "caisen_default"
  }' | python3 -m json.tool
```
**字段说明**：
- `strategy_name` — 从 `/api/strategies` 获取
- `symbol` / `freq` — 从 `/api/data-sources` 获取
- `config_name` — `configs/strategies/` 下的 YAML 文件名（不含 `.yaml`），可选
- `start` / `end` — 格式 `YYYY-MM-DD`

### 触发回测（WebSocket 进度）
```bash
# 使用 websocat（需安装: brew install websocat）
websocat "ws://localhost:8000/ws/runs/test_run/progress?strategy_name=CaiSenStrategy&symbol=ag&freq=1d&start=2024-01-01&end=2024-06-30"
```

## LLM 端点诊断

### 测试本地 LLM 模型列表
```bash
# 从 config_llm_local.yaml 提取 base_url
BASE_URL="http://localhost:8080/v1"
curl -sf "$BASE_URL/models" | python3 -m json.tool
```

### 测试 LLM Chat Completions
```bash
BASE_URL="http://localhost:8080/v1"
API_KEY="dummy"  # 本地部署用 dummy
MODEL="taiji"    # 从 config_llm_local.yaml 提取

curl -s -X POST "$BASE_URL/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d "{
    \"model\": \"$MODEL\",
    \"messages\": [{\"role\":\"user\",\"content\":\"你好\"}],
    \"max_tokens\": 128,
    \"temperature\": 0.1
  }" | python3 -m json.tool
```

### 诊断 LLM 连接问题
```bash
# 1. 端口是否监听
lsof -i :8080 2>/dev/null || echo "端口 8080 未监听"

# 2. 模型是否可用
curl -sf "$BASE_URL/models" | python3 -c "
import sys, json
data = json.load(sys.stdin)
models = [m['id'] for m in data.get('data', [])]
print('可用模型:', models)
print('taiji 在列表中:', 'taiji' in models)
"

# 3. 简单请求测试（超时 10s）
curl -sf --max-time 10 -X POST "$BASE_URL/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"max_tokens\":16}"
```

## WebSocket 测试

### 回测进度 WebSocket
```bash
# 需要 websocat: brew install websocat
websocat -n1 "ws://localhost:8000/ws/runs/ws_test/progress?strategy_name=CaiSenStrategy&symbol=ag&freq=1d&start=2024-01-01&end=2024-03-31"
```

## 常见错误与对应 curl

| 错误 | 排查命令 |
|------|---------|
| Connection refused | `lsof -i :8001` / `lsof -i :8000` |
| 502 Bad Gateway | 检查 Vite proxy 配置 |
| 404 Not Found | `curl -v http://localhost:8001/api/runs` |
| 422 Validation | 检查 strategy_name 是否在列表中 |
| 数据为空 | 检查 `data_dir` 路径和 parquet 文件 |
