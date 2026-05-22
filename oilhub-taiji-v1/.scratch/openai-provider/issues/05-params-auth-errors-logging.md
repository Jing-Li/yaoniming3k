# Slice 5: 完整参数映射、认证与错误处理标准化

Status: needs-triage

## What to build

将 OpenAI 标准参数（`temperature`, `max_tokens`, `top_p`, `presence_penalty`, `frequency_penalty`, `tools`/`functions` 等）正确映射到各后端支持的子集。

添加 Bearer token 认证中间件（可配置是否开启）。统一错误响应格式为 OpenAI 风格（`error: {message, type, code}`）。

**日志规范**：
- 接受的原始请求（HTTP method, path, headers, body）单独打印
- 返回给客户端的响应内容单独打印
- 调用 taiji（及各 provider）的 request（URL, headers, body）单独打印
- 调用 taiji（及各 provider）的 response（status, headers, body）单独打印
- 所有日志带 request_id、timestamp、latency，用于错误排查和代码优化

## Acceptance criteria

- [ ] `temperature`, `max_tokens` 等参数被正确透传或转换到后端
- [ ] 未认证的请求返回 401 + OpenAI 风格错误体
- [ ] 后端超时/错误时返回 502/503 + 有意义的 OpenAI 风格错误体
- [ ] 每条请求有结构化日志（request_id, timestamp, model, provider, latency, status）
- [ ] 原始请求、原始响应、taiji request、taiji response 四组日志可独立过滤查看
- [ ] 支持可配置的日志级别（DEBUG/INFO/ERROR）

## Blocked by

- `.scratch/openai-provider/issues/04-openclaw-models-config.md`
