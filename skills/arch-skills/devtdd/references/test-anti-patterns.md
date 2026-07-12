# Test Anti-Patterns Catalog

Common test anti-patterns with detection methods and fixes. Use during `/devtdd` REFACTOR phase (Step 4, v1.7.0+).

## Anti-Pattern 1: Testing Implementation, Not Behavior

**Detection:** Test names contain `calls_`, `invokes_`, `sets_`, `creates_`.

**Example (BAD):**
```go
func TestUpsert_callsStoreUpsert(t *testing.T) {
    // Asserts that store.Upsert was called — tests implementation
    mockStore.On("Upsert", ...).Return(nil)
    uc.Upsert(ctx, entry)
    mockStore.AssertCalled(t, "Upsert", ...)
}
```

**Fix:** Rewrite to test behavior — what the system does, not how:
```go
func TestUpsert_insertsNewEntry_whenTableEmpty(t *testing.T) {
    // Asserts the observable outcome
    err := uc.Upsert(ctx, entry)
    assert.NoError(t, err)
    got, _ := store.Get(ctx, entry.ID)
    assert.Equal(t, entry, got)
}
```

## Anti-Pattern 2: Excessive Mocking

**Detection:** > 3 mocks per test, or mocking non-boundary dependencies.

**Fix:** Use real implementations for non-boundary dependencies. Mock ONLY at system boundaries (DB, external APIs, time, randomness).

## Anti-Pattern 3: Brittle Assertions

**Detection:** Assertions on exact strings, timestamps, line numbers, or formatted output.

**Fix:**
- Strings → assert on domain sentinels, not error messages
- Timestamps → use `WithinDuration` with tolerance
- IDs → assert non-empty + format, not exact values
- Ordered collections → sort before comparison or use `ElementsMatch`

## Anti-Pattern 4: Test-After Coding

**Detection:** Tests mirror implementation 1:1 (same structure, same variable names).

**Fix:** Write test FIRST. Verify it fails. THEN implement. If the test passes without new code, it's testing the wrong thing.

## Anti-Pattern 5: Incomplete Mock Setup

**Detection:** Only happy-path mock responses. No error paths, timeouts, or edge cases.

**Fix:** For each mock, add:
- Error response (what happens when the dependency fails?)
- Timeout (what happens when the dependency is slow?)
- Empty/nil response (what happens when nothing comes back?)

## Anti-Pattern 6: Shared Mutable State

**Detection:** Tests fail when run with `-shuffle=on` or in parallel.

**Fix:**
- Each test creates its own fresh state (no shared fixtures)
- Use `t.Cleanup()` for teardown
- Avoid package-level variables modified by tests
- No `TestMain` that sets global state

## Anti-Pattern 7: Assertion-Free Tests

**Detection:** No `assert.*`, `t.Errorf`, or `require.*` calls in the test body.

**Fix:** Every test MUST have at least one explicit assertion. "It compiles" or "it doesn't panic" is not a test.

---

## Flaky Test Stabilization Protocol

When a test passes sometimes and fails sometimes:

### Step 1: Isolate
Mark with skip annotation (don't delete):
```go
func TestFlaky(t *testing.T) {
    t.Skip("FLAKY: investigating — see issue #NNN")
    ...
}
```

### Step 2: Diagnose
Run 20 times, categorize the failure:
```bash
for i in $(seq 20); do go test -run TestFlaky -count=1 ./... 2>&1 | tail -1; done
```

Categories:
- **Time-dependent** — failures near midnight, on slow CI, or with race conditions
- **Order-dependent** — passes alone but fails when run with other tests
- **Concurrency** — data race, goroutine leak, channel deadlock
- **External** — depends on network, database, file system state
- **Resource** — runs out of memory, file descriptors, ports

### Step 3: Stabilize
Fix root cause:
- Time → inject clock interface, use `time.Now()` from injected source
- Order → eliminate shared state, use unique test data
- Concurrency → add sync primitives, use `sync.WaitGroup`, close channels
- External → replace with fakes or testcontainers
- Resource → add cleanup, increase limits for test environment

### Step 4: Verify
```bash
go test -run TestFlaky -count=10 ./...
go test -race -run TestFlaky ./...
go test -shuffle=on -run TestFlaky ./...
```
All must pass consistently.

### Step 5: Unskip
Remove skip annotation. Run full suite.

### Step 6: Post-Mortem
Document root cause and prevention rule. Add to team's test guidelines.
