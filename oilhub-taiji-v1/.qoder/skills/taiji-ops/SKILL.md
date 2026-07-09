---
name: taiji-ops
description: 启动 Taiji OpenAI 兼容网关服务，自动检测并修复凭证问题（从用户提供的 curl 命令中提取 sessionId/cookie/token 配置到 .env），定时监控服务日志并使用调试技能排查修复 bug 生成报告。触发词：启动服务、taiji 运维、服务日志、curl 配置、凭证修复、日志分析。
---

# Taiji 运维助手

## 服务启动

### 1. 检查环境

```bash
# 确认 .env 存在且包含必要配置
test -f .env && echo "OK" || echo "需要创建 .env"
```

必要配置项：
- `TAIJI_BASE_URL` — Taiji 后端地址
- `TAIJI_API_KEY` — JWT 认证 token
- `TAIJI_SESSION_COOKIE` — 会话 cookie
- `TAIJI_SESSION_ID` — 会话 ID（必须为非 0 的真实会话 ID）

### 2. 启动服务

```bash
# 开发模式（热重载，端口 8199）
bash start.sh dev --port 8199

# 后台启动
bash start.sh dev --port 8199 > /dev/null 2>&1 &
```

### 3. 验证健康

```bash
curl -s http://localhost:8199/health
# 期望：{"status":"ok"}
```

---

## 凭证修复（curl 命令解析）

当服务返回 `无效参数的对话请求`、`登录已过期`、`502 Bad Gateway` 时，触发此流程。

### 步骤

1. **提示用户**提供一条从浏览器 DevTools (F12 → Network) 复制的可工作 curl 命令

2. **从 curl 命令中提取参数**：

| curl 参数 | 对应 .env 变量 |
|-----------|---------------|
| `-b 'server_name_session=xxx'` | `TAIJI_SESSION_COOKIE` |
| `-H 'authorization: xxx'` | `TAIJI_API_KEY` |
| `"sessionId":NNN` (在 `--data-raw` 中) | `TAIJI_SESSION_ID` |
| URL 的域名部分 | `TAIJI_BASE_URL` |

3. **更新 .env 文件**：

```bash
# 用 SearchReplace 工具直接编辑 .env，不要使用脚本
```

4. **重启服务**：

```bash
pkill -f "uvicorn openai_provider" 2>/dev/null
sleep 2
bash start.sh dev --port 8199 > /dev/null 2>&1 &
sleep 5
curl -s http://localhost:8199/health
```

5. **验证流式请求**：

```bash
curl -s -X POST http://localhost:8199/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"taiji","messages":[{"role":"user","content":"hi"}],"stream":true}' \
  | head -5
```

预期输出以 `data: {"id":"chatcmpl-...` 开头，以 `data: [DONE]` 结尾。

### 提取示例

用户提供的 curl：
```
curl 'https://ai.avuuq.cn/api/chat/completions' \
  -H 'authorization: eyJhb...' \
  -b 'server_name_session=abc123' \
  --data-raw '{"text":"test","sessionId":658084,...}'
```

提取结果写入 .env：
```
TAIJI_BASE_URL=https://ai.avuuq.cn
TAIJI_API_KEY=eyJhb...
TAIJI_SESSION_COOKIE=abc123
TAIJI_SESSION_ID=658084
```

---

## 日志监控与自动修复

### 定时检查流程

每次检查按以下顺序执行：

#### Step 1: 采集日志

```bash
# 读取最近日志
tail -200 logs/taiji-provider.log

# 过滤错误和警告
grep -i "error\|exception\|timeout\|502\|business error\|失败\|无效\|过期" logs/taiji-provider.log | tail -30
```

#### Step 2: 分类汇总

将日志问题分为以下类别：

| 类别 | 关键词 | 严重度 |
|------|--------|--------|
| 凭证失效 | `登录已过期`、`无效参数`、`401` | P0 |
| API 超时 | `timeout`、`Taiji API timeout` | P1 |
| 业务错误 | `business error`、`code.*1` | P1 |
| 请求验证 | `validation error`、`Field required` | P2 |
| 限流/过载 | `rate limit`、`502`、`503` | P1 |
| 未知错误 | 其他 exception | P2 |

#### Step 3: 自动修复

根据问题类别执行修复：

- **P0 凭证失效** → 触发「凭证修复」流程，提示用户提供新 curl
- **P1 API 超时** → 检查 `config.py` 中 `TAJI_MAX_TEXT_LENGTH` 是否合理，考虑增加超时
- **P1 业务错误** → 检查请求体构造逻辑，使用 `/debugging-wizard` 定位根因
- **P2 验证错误** → 检查请求参数映射，修复 `_prepare_request`
- **P1 限流** → E2E 测试的 `RetryingClient` 已有重试机制，检查是否需调大延迟

对于需要代码修改的问题，使用 `/python-pro` 或 `/debugging-wizard` 技能进行修复。

#### Step 4: 生成报告

报告格式：

```markdown
## Taiji 服务运维报告

**时间**: YYYY-MM-DD HH:MM
**服务状态**: 正常 / 异常
**检查日志条数**: N 条

### 问题汇总

| # | 类别 | 严重度 | 描述 | 状态 |
|---|------|--------|------|------|
| 1 | ... | P0/P1/P2 | ... | 已修复 / 待处理 / 需人工介入 |

### 修复操作

- [操作描述和结果]

### 建议

- [改进建议]
```

---

## 快速命令参考

```bash
# 启动
bash start.sh dev --port 8199

# 停止
pkill -f "uvicorn openai_provider"

# 健康检查
curl -s http://localhost:8199/health

# 模型列表
curl -s http://localhost:8199/v1/models | python3 -m json.tool

# 非流式调用
curl -s -X POST http://localhost:8199/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"taiji","messages":[{"role":"user","content":"hello"}]}'

# 流式调用
curl -s -X POST http://localhost:8199/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"taiji","messages":[{"role":"user","content":"hello"}],"stream":true}'

# 运行 E2E 测试
python3 -m pytest tests/e2e/ -v --tb=short

# 运行单元测试
python3 -m pytest tests/ --ignore=tests/e2e/ --ignore=tests/test_integration.py -v
```
