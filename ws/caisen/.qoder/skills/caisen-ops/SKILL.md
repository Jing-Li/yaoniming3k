---
name: caisen-ops
description: 启动、诊断、监控 caisen 量化回测服务。涵盖一键启动前后端、配置验证与 curl 诊断、日志分析与错误总结、自动排查 bug 并生成运维报告。触发词：caisen-ops, 启动服务, 服务诊断, 日志分析, 服务监控, 运维报告, curl 测试。
---

# Caisen Ops — 服务启动、诊断与运维

## 1. 启动服务

### 前置条件

```bash
# 1. Python 包已安装（提供 caisen CLI）
pip install -e .

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
