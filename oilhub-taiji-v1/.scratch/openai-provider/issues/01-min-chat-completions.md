# Slice 1: 最小可运行的 OpenAI-compatible Chat Completions（非 streaming，仅 taiji）

Status: needs-triage

## What to build

搭建项目骨架（Python + FastAPI + httpx），暴露 `POST /v1/chat/completions` 端点。

将标准 OpenAI 请求格式（`messages` 数组）转换为 taiji 格式（`text` + `sessionId`），将 taiji 的 JSON 响应转译为标准 OpenAI response（含 `id`, `object`, `created`, `model`, `choices[]`, `usage`）。

**关键约束**：taiji 接口有最大字数限制，需要根据实测进行优化（如分段发送、截断策略或错误处理）。

端到端可用 `curl` 验证。

## Acceptance criteria

- [ ] 项目可启动，监听某个端口
- [ ] `curl -X POST /v1/chat/completions -d '{"model":"taiji","messages":[{"role":"user","content":"你好"}]}'` 返回标准 OpenAI 格式
- [ ] 内部成功调用 taiji 后端并返回有意义的内容
- [ ] 处理 taiji 字数超限场景（返回合适错误或自动截断/分段策略）
- [ ] 包含基础单元测试

## Blocked by

None - can start immediately
