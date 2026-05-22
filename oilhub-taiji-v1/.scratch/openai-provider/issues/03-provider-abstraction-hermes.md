# Slice 3: Provider 抽象层 + 客户端兼容性验证

Status: in-progress

## 架构澄清

**hermes 和 openclaw 是客户端，不是后端。**

调用链：用户（通过 hermes/openclaw 等 OpenAI-compatible 客户端）→ **本 provider**（OpenAI-compatible API）→ **taiji 后端**

因此本 provider 只对接 **taiji 一个后端**。hermes/openclaw 的"集成"是指验证这些客户端能正确通过标准 OpenAI API 调用本 provider。

## What to build

设计 Provider 抽象接口（`BaseProvider`），将 Slice 1 的 taiji 代码重构为 `TaijiProvider`。

为未来可能扩展的其他后端（如本地 Ollama、其他自定义 API）预留抽象层。

## Acceptance criteria

- [x] 存在清晰的 Provider 接口/抽象基类（`BaseProvider`）
- [x] `TaijiProvider` 继承 `BaseProvider` 并通过全部测试
- [ ] 验证 hermes 客户端可正确连接（标准 OpenAI API 兼容性）
- [ ] 验证 openclaw 客户端可正确连接（标准 OpenAI API 兼容性）
- [ ] 路由失败时返回标准 OpenAI 风格 404 错误

## Blocked by

- `.scratch/openai-provider/issues/01-min-chat-completions.md`
- `.scratch/openai-provider/issues/02-streaming-sse.md`
