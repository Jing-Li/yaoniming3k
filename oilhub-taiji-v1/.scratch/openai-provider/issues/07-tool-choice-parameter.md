Status: needs-triage

## What to build

Add support for the `tool_choice` parameter in `ChatCompletionRequest` and propagate it through to the prompt construction logic. Support values: `"auto"`, `"none"`, `"required"`, and forced function `{"type": "function", "function": {"name": "..."}}`. The `_build_tools_prompt` method should adjust its behavioral instructions based on the `tool_choice` value (e.g., mandatory tool use for `"required"`, prohibition for `"none"`).

## Acceptance criteria

- [ ] `ChatCompletionRequest` model accepts `tool_choice` field with correct types
- [ ] `tool_choice` value is passed to `_build_tools_prompt` and affects the generated system prompt
- [ ] `"required"` mode adds explicit instruction that model MUST call at least one tool
- [ ] `"none"` mode adds explicit instruction that model MUST NOT call any tools
- [ ] Forced function mode (`{"type": "function", ...}`) instructs model to call the specific named tool
- [ ] Tests verify prompt content changes based on `tool_choice` value

## Blocked by

None - can start immediately
