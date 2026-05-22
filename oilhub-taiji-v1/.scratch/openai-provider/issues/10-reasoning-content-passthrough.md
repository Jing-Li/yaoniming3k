Status: needs-triage

## Problem Statement

Users of the taiji AI provider cannot see the model's thinking/reasoning process. The taiji backend returns reasoning content wrapped in `<think>...</think>` tags within the SSE stream, but this content was being stripped and discarded. Clients like Hermes Agent that support OpenAI o1-style reasoning display receive no reasoning information, making it impossible to show users how the model arrived at its answer.

## Solution

Implement OpenAI-compatible `reasoning_content` field passthrough in both non-streaming and streaming responses. Extract reasoning from taiji's think tags, strip them from the final content, and deliver reasoning separately via the standard `reasoning_content` field. This allows clients to display the model's thinking process alongside or before the final answer.

## User Stories

1. As a chat client user, I want to see the model's reasoning process in real-time during streaming, so that I can understand how it arrives at its conclusion
2. As a developer integrating with the provider, I want `reasoning_content` to appear in non-streaming JSON responses, so that I can display complete reasoning after generation finishes
3. As a client developer, I want `reasoning_content` to be omitted from JSON when empty (not `null`), so that my deserialization logic handles optional fields consistently with OpenAI API behavior
4. As a system operator, I want token usage calculations to include reasoning tokens in `completion_tokens`, so that billing and quota tracking are accurate
5. As a tools user, I want reasoning to be streamed even when tool calls are involved, so that I see the model's decision-making process before it selects a tool
6. As a streaming client, I want reasoning chunks to arrive in real-time as the model thinks, not buffered until the entire reasoning is complete, so that the UX matches OpenAI o1 behavior
7. As an API consumer, I want the response format to be fully OpenAI-compatible, so that existing OpenAI client libraries work without modification

## Implementation Decisions

### Models Modified
- Added `OpenAIModel` base class that overrides `model_dump()` and `model_dump_json()` to default `exclude_none=True`
- All response models (`ChatCompletionMessage`, `ChatCompletionDelta`, etc.) now inherit from `OpenAIModel`
- Added `reasoning_content: Optional[str] = None` field to `ChatCompletionMessage` (non-streaming) and `ChatCompletionDelta` (streaming)

### Provider Logic Changes
- `_strip_think_tags()` now returns `tuple[str, Optional[str]]` — returns `None` instead of empty string when no reasoning exists
- `_parse_sse_body()` returns `(content, reasoning_content)` tuple for non-streaming responses
- `chat_completions()` unpacks reasoning from `_parse_sse_body()` and passes it to `ChatCompletionMessage`
- `stream_chat_completions()` rewritten to detect think tags per-chunk and emit `reasoning_content` deltas in real-time
- Token calculation updated: `completion_tokens` now includes both content and reasoning character counts

### Streaming Behavior
- When `<think>` is detected in a chunk, subsequent chunks are sent as `delta.reasoning_content` until `</think>` is found
- Reasoning and content are sent in separate deltas (not combined), matching OpenAI o1 behavior
- In tool-call scenarios, reasoning is still streamed in real-time before tool_calls delta is emitted
- Finish chunk contains only `finish_reason` with empty delta (no usage info in stream)

### Serialization
- Fields with `None` values are excluded from JSON output (via `exclude_none=True`)
- Empty reasoning results in the field being absent, not `"reasoning_content": null`

## Testing Decisions

### What Makes a Good Test
- Tests verify external API behavior (JSON structure, SSE format), not internal implementation details
- Tests use mocked taiji responses to avoid real API dependencies
- Tests cover both happy paths and edge cases (empty think tags, no think tags, multi-chunk think spans)

### Modules Tested
- `src/openai_provider/models/openai.py`: Model serialization with/without reasoning_content
- `src/openai_provider/providers/taiji.py`: Think tag extraction, streaming logic, token calculation
- End-to-end: Full request/response cycle via FastAPI TestClient

### Prior Art
- Existing tests in `tests/test_chat.py`, `tests/test_hermes_compatibility.py`, `tests/test_openclaw_compatibility.py`, `tests/test_tools.py` follow the same mock-based pattern
- Updated existing tests to accommodate `exclude_none` behavior (assert field absence instead of `is None`)

## Out of Scope

- Adding a separate `reasoning_tokens` field to the `Usage` model (reasoning tokens are included in `completion_tokens` but not separately itemized)
- Sending usage information in streaming finish chunks (current behavior: no usage in stream)
- Supporting multiple independent think blocks in a single response (taiji appears to emit at most one)
- Configurable think tag delimiters (hardcoded to `<think>` and `</think>`)

## Further Notes

- Real API testing confirmed taiji emits think tags as `<think>` (literal text, not Unicode escapes)
- Think content typically spans 40-60 small chunks (1-4 characters each) in streaming mode
- The `exclude_none` change affects all response fields, not just `reasoning_content` — this is intentional for OpenAI compatibility
