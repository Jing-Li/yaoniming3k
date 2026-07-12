---
name: caisen-ops
description: 启动、诊断、监控 caisen 量化回测服务。涵盖一键启动前后端、配置验证与 curl 诊断、日志分析与错误总结、自动排查 bug 并生成运维报告。触发词：caisen-ops, 启动服务, 服务诊断, 日志分析, 服务监控, 运维报告, curl 测试。
---

# Caisen Ops — 服务启动、诊断与运维

## 端口约定（固定，勿混用）

| 组件 | 端口 | 说明 |
|------|------|------|
| **FastAPI 后端** | **8001** | API 服务，`/api/*` 和 `/ws/*` 端点 |
| **Vite 前端** | **8000** | 开发服务器，`/api` 请求自动代理到 8001 |

> **记忆口诀**：前端 8000，后端 8001。浏览器访问 8000，Vite 自动转发 API 到 8001。

## 1. 启动服务

### 前置条件

```bash
# 1. Python 包已安装（项目使用 uv，非 pip）
uv pip install -e . --quiet

# 2. 前端依赖已安装
cd src/caisen/frontend && npm install && cd -

# 3. 数据目录已配置（configs/project.yaml）
#    data_dir: <你的 parquet 数据根目录>
```

### 一键启动

```bash
caisen web
```

- 后端 FastAPI → `http://localhost:8001`
- 前端 Vite  → `http://localhost:8000`（`/api` 请求自动代理到 8001）

可选参数：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--port` / `-p` | 8000 | 前端端口 |
| `--backend-port` | 8001 | 后端端口 |
| `--host` | 0.0.0.0 | 监听地址 |
| `--output-dir` | ./runs | 回测结果目录 |
| `--run-id` / `-r` | — | 直接打开指定回测 |

### 分步启动（调试模式）

```bash
# Terminal 1 — 后端
cd src/caisen && python -m uvicorn web.main:app --host 0.0.0.0 --port 8001 --reload

# Terminal 2 — 前端
cd src/caisen/frontend && npx vite --port 8000
```

## 2. 配置验证与 curl 诊断

启动后依次验证服务可用性。从 `configs/project.yaml` 和 `configs/strategies/*.yaml` 提取最新参数。

### 健康检查

```bash
curl -s http://localhost:8001/health
# 预期: {"status":"ok"}
```

### 列出可用策略

```bash
curl -s http://localhost:8001/api/strategies | python3 -m json.tool
```

### 列出数据源

```bash
curl -s http://localhost:8001/api/data-sources | python3 -m json.tool
```

### 列出回测记录

```bash
curl -s http://localhost:8001/api/runs | python3 -m json.tool
```

### 触发回测（POST）

从 `configs/project.yaml` 提取 `data_dir`，从策略列表确认 `strategy_name`，从数据源确认 `symbol`/`freq`：

```bash
curl -s -X POST http://localhost:8001/api/runs \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_name": "CaiSenStrategy",
    "symbol": "ag",
    "freq": "1d",
    "start": "2024-01-01",
    "end": "2024-06-30"
  }'
```

### 获取回测详情

```bash
curl -s http://localhost:8001/api/runs/<RUN_ID> | python3 -m json.tool
curl -s http://localhost:8001/api/runs/<RUN_ID>/visualization | python3 -m json.tool | head -50
```

### LLM 配置验证

若使用 LLM 策略，读取 `configs/strategies/config_llm_*.yaml` 中的 `llm` 配置段：

```bash
# 测试 LLM 端点可达性（从 config_llm_local.yaml 提取 base_url 和 model）
curl -s <base_url>/models | python3 -m json.tool

# 测试 LLM chat completions（替换实际 api_key / model）
curl -s -X POST <base_url>/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <api_key>" \
  -d '{
    "model": "<model>",
    "messages": [{"role":"user","content":"hello"}],
    "max_tokens": 64
  }'
```

**诊断规则：**
- `/health` 无响应 → 后端未启动或端口错误
- `/api/strategies` 返回空 → 检查策略注册代码
- `/api/data-sources` 返回空 → 检查 `configs/project.yaml` 的 `data_dir` 路径和数据文件结构
- LLM 401/403 → `api_key` 无效，从配置文件提取正确值并提示用户
- LLM timeout → `base_url` 不可达，检查本地模型服务状态

完整 curl 命令参考见 [curl-recipes.md](curl-recipes.md)。

## 3. 日志监控与分析

### 运行 log-check.sh 收集日志

```bash
bash .qoder/skills/caisen-ops/scripts/log-check.sh
```

脚本输出结构化摘要：
- 错误数量与最近 5 条 ERROR
- 警告数量与最近 5 条 WARNING
- 关键异常堆栈（如有）

### 手动日志检查

```bash
# 后端日志（uvicorn stdout/stderr）
# 若用 caisen web 启动，日志混合输出在终端

# 按级别过滤
tail -100 <log_file> | grep -E "(ERROR|CRITICAL|Exception)"
```

### 分析流程

1. **分类统计** — ERROR / WARNING / INFO 各自计数
2. **错误聚类** — 相同异常类型归类，识别高频问题
3. **时间线** — 错误发生时间点，是否与特定操作关联
4. **根因推测** — 根据错误信息推断可能原因

### 3.1 前端结构化日志（浏览器 Console）

前端使用 `logger.js` 模块输出结构化日志，格式如下：

```
[LEVEL] HH:MM:SS.mmm [Module] message {context}
```

| 缩写 | 级别 | 说明 |
|------|------|------|
| `[DBG]` | DEBUG | 详细调试信息（默认不显示） |
| `[INF]` | INFO | 常规操作日志 |
| `[WRN]` | WARN | 非致命警告 |
| `[ERR]` | ERROR | 错误信息 |

**模块标签**（`[Module]`）：

| 标签 | 模块文件 | 职责 |
|------|---------|------|
| `[Main]` | `main.js` | 应用入口、全局错误捕获 |
| `[RunsList]` | `runs-list.js` | 列表加载、搜索过滤、版本标签 |
| `[BacktestPanel]` | `backtest-panel.js` | 回测表单、WebSocket 进度、表单持久化 |
| `[DataLoader]` | `data-loader.js` | 报告页数据加载、缓存 |

**动态调整日志级别**：在浏览器地址栏添加 URL 参数：

```
http://localhost:8000/?log=debug    # 显示全部日志
http://localhost:8000/?log=warn     # 仅显示 WARN 及以上
http://localhost:8000/?log=error    # 仅显示 ERROR
```

**计时器日志**：`log.time()` / `log.timeEnd()` 配对使用，输出含耗时：

```
[INF] 14:23:01.123 [RunsList] ⏱ GET /api/runs
[INF] 14:23:01.456 [RunsList] ⏱ GET /api/runs: 333ms
```

**Toast 通知**：前端操作结果通过右上角 Toast 通知反馈，分四种类型：
- ✅ success（绿色）— 操作成功，4 秒消失
- ❌ error（红色）— 操作失败，8 秒消失
- ⚠️ warn（橙色）— 警告，5 秒消失
- ℹ️ info（蓝色）— 提示，4 秒消失

### 3.2 后端请求日志

后端 FastAPI 中间件自动记录每个 HTTP 请求：

```
INFO:root:GET /api/runs → 200 (45ms)
INFO:root:POST /api/runs → 200 (12350ms)
WARNING:root:GET /api/runs/nonexist → 404 (3ms)
```

格式：`METHOD /path → STATUS_CODE (DURATIONms)`

- 状态码 >= 400 自动升级为 WARNING 级别
- 静态资源请求（`/js/`、`/src/`、`/node_modules/`）不记录
- POST `/api/runs` 额外记录请求参数（策略名、标的、频率、日期范围、配置预设）

### 3.3 日志排查速查表

| 现象 | 查看日志位置 | 关键词/过滤 |
|------|-------------|------------|
| 回测按钮点击无反应 | 浏览器 Console `[BacktestPanel]` | `POST /api/runs` |
| 回测进度条不动 | 浏览器 Console `[BacktestPanel]` | `WebSocket`、`progress` |
| 列表页空白 | 浏览器 Console `[RunsList]` | `GET /api/runs`、`error` |
| 报告页加载失败 | 浏览器 Console `[DataLoader]` | `数据加载`、`error` |
| API 返回 500 | 终端后端日志 | `500`、`ERROR`、`Exception` |
| API 响应慢 | 终端后端日志 | 关注 `(XXXms)` 中耗时 > 1000ms |
| 表单数据丢失 | 浏览器 Console `[BacktestPanel]` | `localStorage`、`form` |
| 搜索无结果 | 浏览器 Console `[RunsList]` | `search`、`filter` |

## 4. 问题排查与修复

发现日志问题后，按以下流程排查：

### 4.1 识别问题模块

| 日志关键词 | 模块 | 排查文件 |
|-----------|------|---------|
| `BacktestRunner` / `run_backtest` | 回测引擎 | `src/caisen/backtest/runner.py` |
| `BacktestEngine` / `execute` | 撮合引擎 | `src/caisen/core/engine.py` |
| `DataSourceScanner` / `scan` | 数据扫描 | `src/caisen/data/scanner.py` |
| `load_bars` / `DataNotFoundError` | 数据加载 | `src/caisen/data/local_source.py` |
| `ResultPersister` / `save` / `load` | 结果持久化 | `src/caisen/result/persistence.py` |
| `StrategyRegistry` / `list_strategies` | 策略注册 | `src/caisen/strategy/registry.py` |
| `LLMStrategy` / `openai_provider` | LLM 策略 | `src/caisen/strategy/llm/` |
| `WebSocket` / `progress` | 进度推送 | `src/caisen/web/main.py` (ws端点) |
| `chart-builder` / `chart-renderer` | 前端图表 | `src/caisen/frontend/src/js/chart-*.js` |
| `[BacktestPanel]` / `localStorage` | 前端回测面板 | `src/caisen/frontend/src/js/backtest-panel.js` |
| `[RunsList]` / `search` / `filter` | 前端列表 | `src/caisen/frontend/src/js/runs-list.js` |
| `[DataLoader]` / `数据加载` | 前端数据加载 | `src/caisen/frontend/src/js/data-loader.js` |
| `[Main]` / `unhandledrejection` | 前端全局错误 | `src/caisen/frontend/src/js/main.js` |

### 4.2 修复步骤

1. **定位** — 从日志堆栈确认出错文件和行号
2. **读码** — 阅读出错上下文，理解数据流
3. **修复** — 最小化改动，遵循项目现有模式
4. **验证** — 使用对应 curl 命令验证 API 响应
5. **测试** — 运行相关单元测试：`python -m pytest tests/test_<module>.py -v`

## 5. 运维报告模板

每次诊断完成后，按此格式生成报告：

```markdown
# Caisen 运维报告

**日期**: YYYY-MM-DD HH:MM
**服务状态**: ✅ 正常 / ⚠️ 部分异常 / ❌ 不可用

## 服务启动

| 组件 | 端口 | 状态 |
|------|------|------|
| FastAPI 后端 | 8001 | ✅/❌ |
| Vite 前端 | 8000 | ✅/❌ |
| 数据目录 | — | ✅/❌ |

## 配置验证

| 检查项 | 结果 | 备注 |
|--------|------|------|
| /health | ✅/❌ | |
| /api/strategies | N 个策略 | |
| /api/data-sources | N 个数据源 | |
| LLM 端点 (如适用) | ✅/❌ | base_url: ... |

## 日志摘要

- **ERROR**: N 条
- **WARNING**: N 条
- **关键异常**: <描述或"无">

## 发现的问题

### [P0/P1/P2] 问题标题
- **现象**: ...
- **根因**: ...
- **修复**: ...
- **验证**: ...

## 建议

1. ...
2. ...
```
