# Slice 2: Streaming SSE 响应转译

Status: needs-triage

## What to build

在 `/v1/chat/completions` 上支持 `stream: true`。

将 taiji 返回的 SSE 流正确转译为 OpenAI SSE 格式（`data: {...}\n\n`），包括 `[DONE]` 结束标记和正确的 `choices[].delta` 结构。

客户端用 `curl -N` 或 OpenAI SDK 可正常接收流。

## Acceptance criteria

- [ ] `stream: true` 时返回 `text/event-stream` Content-Type
- [ ] 每个 chunk 格式符合 OpenAI streaming spec
- [ ] 流结束时发送 `data: [DONE]\n\n`
- [ ] 连接中断时优雅处理（不崩溃，不泄漏资源）
- [ ] 流式场景也兼容 taiji 字数限制处理逻辑

## Blocked by

- `.scratch/openai-provider/issues/01-min-chat-completions.md`
