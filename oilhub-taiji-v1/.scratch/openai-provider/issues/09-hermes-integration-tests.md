Status: needs-triage

## What to build

Add a comprehensive mock-based integration test suite that simulates Hermes Agent's typical calling patterns against the taiji provider. This includes: streaming with tool calls, multi-turn conversations with tool result round-trips, parallel tool execution scenarios, and edge cases like empty tool results or tool errors. The tests validate that response structure, delta formatting, finish_reason timing, and tool_call ID correlation all match Hermes Agent's expectations.

## Acceptance criteria

- [ ] Test covers streaming + tool_calls scenario with proper delta reconstruction
- [ ] Test covers multi-turn conversation: user -> assistant(tool_calls) -> tool(result) -> assistant(final answer)
- [ ] Test verifies tool_call IDs are consistent between request and response for correlation
- [ ] Test validates SSE format compliance (data: prefix, \n\n separators, [DONE] marker)
- [ ] All tests pass against mocked taiji backend
- [ ] Tests are skipped when TAIJI_API_KEY is not configured (no real API calls)

## Blocked by

- `.scratch/openai-provider/issues/06-streaming-tool-calls-delta.md`
- `.scratch/openai-provider/issues/07-tool-choice-parameter.md`
- `.scratch/openai-provider/issues/08-extra-body-tolerance.md`
