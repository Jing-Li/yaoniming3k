Status: needs-triage

## What to build

Modify `stream_chat_completions` in `TaijiProvider` to emit incremental `delta.tool_calls` chunks conforming to the OpenAI streaming spec when tools are present and the model returns tool call JSON. Instead of buffering all content then outputting at once, split the tool_calls into indexed delta fragments with proper `index`, `id`, `function.name`, and `function.arguments` fields, ending with `finish_reason="tool_calls"`.

## Acceptance criteria

- [ ] Streaming response emits multiple SSE chunks for tool_calls (not a single buffered chunk)
- [ ] Each delta chunk follows OpenAI format: `{"delta": {"tool_calls": [{"index": 0, "id": "...", "type": "function", "function": {"name": "...", "arguments": "..."}}]}}`
- [ ] Final chunk has `finish_reason: "tool_calls"`
- [ ] Non-tool-call streaming (when model responds with natural language despite tools being present) continues to work correctly
- [ ] All existing tests pass, including new streaming tool_call test

## Blocked by

None - can start immediately
