Status: needs-triage

## What to build

Configure `ChatCompletionRequest` Pydantic model to ignore unknown fields in the request body (via `model_config = {"extra": "ignore"}`). This allows Hermes Agent and other clients to send provider-specific parameters in `extra_body` (like `thinking`, `reasoning`, etc.) without causing 400 validation errors. The taiji provider should silently discard unrecognized fields rather than rejecting the entire request.

## Acceptance criteria

- [ ] Requests with unknown top-level fields (e.g., `{"model": "...", "messages": [...], "thinking": false}`) return 200 instead of 400
- [ ] Known fields continue to be validated normally
- [ ] Existing tests remain passing
- [ ] New test verifies extra field tolerance

## Blocked by

None - can start immediately
