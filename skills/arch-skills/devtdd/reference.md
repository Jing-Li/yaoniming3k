# DevTDD Reference

Detailed protocols, templates, and checklists for the `devtdd` skill.
Loaded progressively from [SKILL.md](SKILL.md).

---

## 1. Contract-to-Test Translation Protocol

Each interface contract file (`interfaces/<method>.md`) has 7 sections. Here is how devtdd consumes each section:

| Contract Section | devtdd Usage |
|-----------------|--------------|
| §1 Signature | Determines the function/method under test; defines the test's call site |
| §2 Input Contract (preconditions) | Generates **invalid input** tests (one per precondition violation) |
| §3 Output Contract (postconditions) | Generates **assertion clauses** in every test's Then-block |
| §4 Error Mapping | Generates **error assertion** tests (one per domain sentinel) |
| §5 Edge Cases | Generates **edge case** tests (one per bullet) |
| §6 Acceptance Test Scenarios | **PRIMARY** test source — each Given/When/Then becomes one test function |
| §7 Cross-References | Links back to Task and module for traceability |

### Translation Algorithm

For each Scenario in §6:

1. **Given** → Test SETUP phase:
   - "Given an empty store" → instantiate fake with no seed data
   - "Given entry X exists" → pre-populate fake with seed data
   - "Given context is cancelled" → create cancelled context

2. **When** → Test ACTION phase:
   - Extract the method call from the scenario description
   - Use the §1 Signature to construct the correct call with §2 parameters

3. **Then** → Test ASSERTION phase:
   - Map each Then-clause to a specific assertion
   - Use §3 postconditions to determine expected state
   - Use §4 error mapping to determine expected error type

### Test Naming Convention

Pattern: `Test<Method>_<behavior_description>`

Examples derived from contracts:
- `upsert.md` Scenario 1 → `TestUpsert_insertsNewEntry_whenTableEmpty`
- `upsert.md` Scenario 3 → `TestUpsert_rejectsInvalidTransition_whenSourceIsDead`
- `list.md` Scenario 2 → `TestList_returnsEmptySlice_whenNoEntries`

### Supplementary Test Generation

After all §6 scenarios are covered, check for gaps:

| Source | Supplemental Test Type |
|--------|----------------------|
| §2 precondition not covered in §6 | One test per uncovered precondition violation |
| §4 error sentinel not covered in §6 | One test per uncovered error type |
| §5 edge case not covered in §6 | One test per uncovered edge case |

### Error Chain Testing (v1.8.0+)

Beyond individual error sentinels, verify the **full error propagation chain** from adapter → use case → delivery:

| Layer Transition | What to Test | Test Strategy |
|-----------------|-------------|---------------|
| Adapter → Use Case | Driver error (e.g., `pgx.ErrNoRows`) → domain sentinel (`ErrNotFound`) | Adapter integration test: trigger real driver error, assert domain sentinel returned |
| Use Case → Delivery | Domain sentinel → HTTP/gRPC error response | Delivery handler test: invoke with fake that returns sentinel, assert RFC 7807 / gRPC status code |
| Panic → Recovery | Unexpected panic in use case → graceful error response | Delivery handler test: invoke with fake that panics, assert 500 / INTERNAL (no stack trace leaked) |

#### Error Chain Test Template

```
For each port method that returns domain sentinels:
1. Adapter test: force driver-level error → verify translation to sentinel
2. Use case test: fake returns sentinel → verify use case propagates (not swallows)
3. Delivery test: fake use case returns sentinel → verify mapped to RFC 7807 / gRPC status
```

---

## 2. Micro-Cycle Planning Templates

### Template: Single-Port Task

A task that implements one port's full lifecycle (e.g., Census Upsert Path):

| Cycle | Source | Test | RED Target | GREEN Target | Mock |
|-------|--------|------|-----------|-------------|------|
| 1 | method_a.md S1 | TestMethodA_happyPath | domain types + port interface + use case | fakePort.MethodA + .MethodB | fakePort |
| 2 | method_a.md S2 | TestMethodA_updateExisting | (extends cycle 1) | fakePort overwrite logic | fakePort |
| 3 | method_a.md S3 | TestMethodA_errorCase | predicate/error in app layer | validation before store call | none |
| 4 | method_b.md S1 | TestMethodB_existingEntry | (extends cycle 1) | fakePort.MethodB | fakePort |
| 5 | method_b.md S2 | TestMethodB_notFound | (extends cycle 4) | ErrNotFound sentinel | fakePort |

### Template: Adapter Skeleton Task

A task that defines a port + adapter skeleton (e.g., IntentClient + RocketMQ Adapter):

| Cycle | Source | Test | RED Target | GREEN Target | Mock |
|-------|--------|------|-----------|-------------|------|
| 1 | (compile check) | TestAdapter_ImplementsPort | port interface definition | adapter struct + method stubs | none |
| 2 | method.md S1 | TestMethod_happyPath | method skeleton | return nil/empty (TODO) | none |

### Template: Multi-Layer Task

A task that spans port + delivery layer (e.g., gRPC ListCensusEntries):

| Cycle | Source | Test | RED Target | GREEN Target | Mock |
|-------|--------|------|-----------|-------------|------|
| 1 | method.md S1 | TestDelivery_returnsResult | delivery handler + proto mapping | handler calls use case with fake | bufconn + fakePort |
| 2 | method.md S2 | TestDelivery_emptyResult | (extends cycle 1) | empty result handling | bufconn + fakePort |

### Ordering Principle

1. **Tracer bullet** scenario first (proves architecture end-to-end)
2. **Happy path** scenarios next (core business logic)
3. **Error cases** (domain sentinels, preconditions)
4. **Edge cases** (boundaries, empty states)

### Template: Adapter Performance Cycle (v1.8.0+)

After all functional cycles for an adapter task pass, add performance validation cycles:

| Cycle | Focus | Test | Assertion |
|-------|-------|------|----------|
| P1 | N+1 detection | `TestList_noNPlusOne` | Count SQL queries: should be 1 (JOIN) not N+1 (loop) |
| P2 | Batch efficiency | `TestBatchInsert_usesBulk` | Verify SQL uses `INSERT ... VALUES (...),(...)` not N individual inserts |
| P3 | Index usage | `TestQuery_usesIndex` | `EXPLAIN` output shows Index Scan, not Seq Scan |
| P4 | Large dataset | `TestList_1000Rows_performance` | Response time < threshold (e.g., 100ms for 1000 rows) |

#### N+1 Detection Pattern

```
1. Seed test DB with N records (e.g., 50 orders with 5 items each)
2. Execute the List operation
3. Count SQL queries executed (query logger or pgx tracer)
4. Assert: query_count <= expected (1 for JOIN, or 2 for separate parent+children)
5. If query_count > expected → N+1 detected → refactor adapter to use JOIN or batch query
```

#### Index Usage Verification

```
1. Run EXPLAIN on the adapter's key queries
2. Compare against indexes defined in DESIGN.md §1.1 DDL (Index Design table from arch-detail §3.5)
3. Assert: expected index appears in EXPLAIN output
4. If Seq Scan where Index Scan expected → check WHERE clause matches index columns
```

---

## 3. Mock Boundary Decision Matrix

**Decision rule**: Mock ONLY at system boundaries. Everything else uses real code.

### Layer-Based Mock Decisions

| Layer Being Tested | What to Mock | What to Use Real | Rationale |
|-------------------|-------------|-----------------|-----------|
| Domain (pure functions) | Nothing | All predicates, value objects | Domain has zero dependencies |
| Port interface (definition) | Nothing | Interface compiles | Compile-time check only |
| Use Case (transaction script) | Port implementations (fake) | Domain types, port interfaces | Use cases receive ports via DI |
| Adapter (infrastructure) | External driver (if expensive) | Domain types, port interface | Use testcontainers for DB if available |
| Delivery (gRPC/CLI/HTTP) | Use case dependencies (fake) | Proto/handler definitions | In-process test server + fake store |

### Fake Implementation Pattern

For each port interface, create an in-memory test double:
- Implements the port interface exactly
- Records all calls (for assertion)
- Supports seeding (for Given-clause setup)
- Lives in test helper files in the same package as the consumer

### When to Use Real Infrastructure vs Fakes

| Scenario | Use | Rationale |
|----------|-----|-----------|
| Use case tests (app layer) | Fakes | Fast, isolated, no infrastructure |
| Adapter integration tests | Real (testcontainers) | Validates SQL, schema, error translation |
| Delivery handler tests | In-process server + Fakes | Tests proto/HTTP mapping without network |
| End-to-end smoke test | Real + real server | Only for final Task verification |

### Test Data Management (v1.8.0+)

#### Lifecycle Strategy Decision

| Test Type | Data Strategy | Isolation | Performance |
|-----------|--------------|-----------|-------------|
| Unit (domain/app) | **In-memory fakes** | Per-test fresh instance | Fast (<1ms/test) |
| Integration (adapter) | **Testcontainers** + per-test transaction rollback | Schema per suite, data per test | Medium (50-200ms/test) |
| E2E smoke | **Docker Compose** full stack | Shared container set | Slow (seconds) |

#### Fixture Patterns

| Pattern | When to Use | Example |
|---------|------------|--------|
| **Builder** | Entity with many optional fields | `NewOrderBuilder().WithItems(...).WithDiscount(...).Build()` |
| **Object Mother** | Shared canonical test entities | `testdata.ValidOrder()`, `testdata.CancelledOrder()` |
| **Inline Factory** | Simple entity (≤4 fields) | `Order{ID: "o1", Status: Pending}` |

#### Time & Randomness Control

| Concern | Solution | Where |
|---------|----------|-------|
| Time-dependent logic | Inject `Clock` interface (fake returns fixed time) | Use case tests |
| ID generation | Inject `IDGenerator` interface (fake returns sequential IDs) | Domain tests |
| Random selection | Inject `Random` interface (fake returns deterministic sequence) | Use case tests |

> **Rule**: No test should depend on `time.Now()`, `uuid.New()`, or `rand.Int()` directly. Always inject via port or constructor parameter.

---

## 4. Architecture Compliance Checklist (Per-Cycle)

Run these checks after every GREEN phase. If ANY check fails, enter REFACTOR immediately.

### Dependency Direction (from ARCHITECTURE.md DIP Enforcement)

- [ ] Domain layer imports ONLY standard library
- [ ] Domain layer does NOT import proto, infrastructure, or database driver packages
- [ ] Application layer does NOT import any infrastructure/adapter package
- [ ] Every port method accepts a context parameter (language-appropriate)
- [ ] Port interfaces defined in consumer-adjacent packages, NOT in adapter packages

### Type Purity

- [ ] No serialization/framework types in domain layer
- [ ] No driver-specific types in application layer
- [ ] All errors crossing adapter boundary are domain sentinels (typed errors)
- [ ] No generic/untyped return types in any public API

### Naming Alignment (from LANGUAGE.md)

- [ ] Domain types use LANGUAGE.md canonical terms (not synonyms)
- [ ] Package names match ARCHITECTURE.md package layout
- [ ] Error sentinels follow naming convention: `Err<Concept><Condition>`

### Naming Consistency Scan (Post-Rename Refactoring)

When a refactoring cycle involves renaming a port interface, adapter type, or field (e.g., `IntentClient` → `EventSubscriber`), run this additional scan to catch stale references:

| Check | What to Scan | Example Violation |
|-------|-------------|-------------------|
| **Field names match port type** | Struct fields typed by a port interface should use the port's concept name | `intentClient event.EventSubscriber` — field says "intent" but type says "event" |
| **Adapter class/file names match port** | Adapter type name and file name should reflect the port they implement | `IntentAdapter` implementing `EventSubscriber` — class says "Intent" but port says "Event" |
| **Host file names match renamed types** | Physical `.go` file names should follow type renames (e.g., `event_adapter.go` → `intent_adapter.go` after `EventAdapter` → `IntentAdapter`) | Type renamed to `IntentAdapter` but file still named `event_adapter.go` |
| **Constructor names match adapter** | `New<Adapter>()` functions should use the current adapter name | `NewIntentAdapter()` when type is `EventAdapter` |
| **Variable names in composition root** | `cmd/` variable names should use current adapter terminology | `intentAdapter := rocketmq.NewEventAdapter(...)` — var name stale |
| **Full-text scan (not just identifiers)** | Run `(?i)\b{old_name}\b` across the entire module — catches stale references in comments, string literals, test messages, and doc prose that identifier-only grep misses | Comment says `// dispatches an event` after `Event` → `Intent` rename |
| **Design doc references** | DESIGN.md, ARCHITECTURE.md, LANGUAGE.md, BRD.md, SYSTEM.md, detail/modules/*/module.md, detail/modules/*/interfaces/*.md — all adapter name references should match code | Doc says `RocketMQIntentAdapter` but code says `RocketMQEventAdapter` |
| **Cross-BC doc mirrors** | When a term is renamed in one BC, check sibling BCs' LANGUAGE.md Banned Terms / glossary for stale mirrors | Platform BC renamed `Event` → `Intent`, but AYuan LANGUAGE.md Banned Terms still lists `Event` as replacement |
| **Test fake types match current ports** | `*_test.go` fake type names and variable names must use current port terminology, not banned/old names. Scan against LANGUAGE.md Part II Banned Terms. | `fakeManifestStore` when port is `ManifestLoader/ManifestSaver` — "Store" is banned |
| **Test fake types vs LANGUAGE.md banned terms** | grep `*_test.go` for every term in LANGUAGE.md Part II Banned Terms list (e.g., `Store`, `Kernel`, `ScopePrivate`). Any match in type names, variable names, or function names is a violation | `fakeAOSStore` when banned terms list includes `AOSStore` |

**When to run**: After any REFACTOR cycle that changes a type name, interface name, or file name. Run BOTH identifier-level grep AND full-text `(?i)\b{old}\b` scan across the entire module **and all documentation files**. If any stale reference is found, fix it in the same cycle.

### Security Implementation Checks (v1.8.0+)

Run these checks after implementing adapter and delivery layer code. Complement the architecture boundary checks above.

#### Input Validation at Boundary

- [ ] All user inputs validated at adapter boundary (string length, numeric range, format regex)
- [ ] Validation errors return structured RFC 7807 ProblemDetail, not raw framework errors
- [ ] No raw user input passed to domain layer without validation

#### SQL Injection Prevention

- [ ] All SQL queries use parameterized statements (`$1`, `$2`, not string concatenation)
- [ ] No `fmt.Sprintf` or string interpolation in SQL query construction
- [ ] Dynamic column/table names (if any) validated against allowlist

#### Secret Hygiene

- [ ] No hardcoded credentials, API keys, or tokens in source code
- [ ] Secrets loaded from env vars or secrets manager (per DESIGN.md §8 env var schema)
- [ ] Sensitive fields excluded from log output (grep for `password`, `secret`, `token`, `key` in log statements)

#### Error Response Safety

- [ ] No stack traces in HTTP/gRPC error responses
- [ ] No internal paths, SQL fragments, or driver errors exposed to clients
- [ ] Panic recovery middleware active on all delivery layer entry points

### Test Placement

- [ ] Test files live alongside source (same package, test suffix convention)
- [ ] Integration tests separated by build tag or directory
- [ ] No test imports production code from adapter packages into app-layer tests

### Code Craftsmanship (Hard Constraint #11)

- [ ] No magic strings/numbers — every domain concept literal is a named `const` (see §9.1 decision tree)
- [ ] No DRY violations — structurally identical code blocks extracted to helpers (see §9.3)
- [ ] No dead code — unused fields, functions, imports, unreachable branches deleted (see §9.5)
- [ ] Standard library preferred — no custom utility duplicating stdlib functionality (see §9.6)
- [ ] Test code uses same constants as production code — no hardcoded assertion strings
- [ ] Every extracted helper has single responsibility — no "god helpers"
- [ ] File permission bits (`0755`, `0644`) defined as named constants, not inline octals
- [ ] Timer intervals and timeout values defined as named constants, not inline expressions
- [ ] Configuration defaults and env var names defined as named constants in config package

---

## 5. State Synchronization Protocol

### Atomic Update Sequence

When a task passes all DoD items:

1. Update `DESIGN.md` §5 row:
   ```
   Before: | 1 | Domain + Census Upsert Path | ... | ☐ |
   After:  | 1 | Domain + Census Upsert Path | ... | ✅ |
   ```

2. Update `detail/modules/<module>/module.md` §7 task DoD:
   ```
   Before: - [ ] Unit test for CanTransition predicate passes.
   After:  - [x] Unit test for CanTransition predicate passes.
   ```

3. Update `kanban/BOARD.md Last updated date.

4. **Stub Adapter Tracking Sync** (if applicable): If the completed task involved implementing or upgrading an adapter listed in `DESIGN.md` §10 Stub Adapter Tracking:
   ```
   Before: | `RocketMQIntentAdapter` | Stub (returns errors) | producer.Send, ... | 待引入 SDK |
   After:  | `RocketMQIntentAdapter` | Implemented (full pub/sub/close) | — | v3-v5 devtdd 周期完成实现 |
   ```
   This step is conditional — only apply when the task touched an adapter listed in §10.

**All three updates must happen atomically.** If any file operation fails, report the error and do not leave partial state.

### Failure Recovery

If a task is partially complete (some DoD items pass, some fail):
- Do NOT update DESIGN.md Status column (remains ☐)
- Check ONLY the passing DoD items to `[x]`
- On next `/devtdd` invocation, resume from first unchecked DoD item

### Batch Completion Detection

After updating a task to ✅, scan DESIGN.md §5:
- If remaining ☐ tasks exist → report count and suggest next task
- If zero ☐ tasks remain → proceed to Post-Implementation Verification

### Post-Implementation Verification

When **all** tasks in DESIGN.md §5 are marked ✅, before outputting the completion message:

1. **Locate the global diagnosis/enforcement checklist** in DESIGN.md (e.g., §8 Go Diagnosis Checklist or any section with unchecked `[ ]` items).
2. **Verify each item** against the current codebase (grep, build, test).
3. **Tick satisfied items** `[ ]` → `[x]`. For items intentionally deferred (e.g., MVP simplifications), update the text to reflect current state and mark `[x]`.
4. **Full-scan naming consistency**: grep all `*.md` files under `docs/` and all `*_test.go` files for stale type/port names that were renamed during implementation (e.g., `IntentPublisher` → `Publisher`, `port/intent/` → `domain/`). Update module.md files, interface contract .md files, and test comments.
5. **Update SYSTEM.md**: if the BC has been fully implemented (all tasks ✅), update `docs/arch/SYSTEM.md` §2 Process Inventory and §4 BC Code Ownership to reflect the current state (remove "planned" markers, add actual package paths).
6. **Report**: list any items that could not be verified (potential Architecture Debt).
7. Only then output the completion message and suggest `/arch-review`.

This step prevents the common gap where per-task DoD checklists are verified but cross-cutting architecture guardrails are left unticked.

---

## 6. Cross-Module Task Handling

Some tasks touch multiple modules (e.g., WatchEvents touches Intent + gRPC delivery).

### Strategy: Primary Module First, Secondary Module Integration After

1. Identify the PRIMARY module (the one listed in DESIGN.md §5 Module column)
2. Implement the primary module's port + adapter first (in isolation)
3. Then implement the integration layer (gRPC handler / CLI command)

### Three-Phase Execution

| Phase | Focus | Tests | Layers |
|-------|-------|-------|--------|
| A | Primary module port + use case | TestUseCase_behavior | app + primary port |
| B | Delivery layer (gRPC/CLI) | TestHandler_endToEnd | delivery handler + fake primary port |
| C | Integration verification | TestIntegration_fullPath | delivery + use case + primary port |

### Cross-Module Contract Linking

When a task references interface contracts from multiple modules:
- Read ALL linked contracts during Step 2 (Task Analysis)
- Plan micro-cycles that respect the dependency order (port before delivery)
- Run architecture compliance checks for ALL touched layers

---

## 7. Idempotency & Resumption Protocol

### Scenario: Task Already Complete

1. Check DESIGN.md §5 Status column for the requested task
2. If Status is ✅:
   - Output: *"Task N is already complete (✅). DoD items all checked."*
   - Ask: *"Re-implement from scratch? This will DELETE existing implementation files."*
   - Default: NO (do nothing)
   - If user confirms: reset DoD to `[ ]`, reset Status to `☐`, proceed normally

### Scenario: Interrupted Mid-Task

1. Check module.md §7 DoD for the target task
2. If some items are `[x]` and some are `[ ]`:
   - Report: *"Task N is partially complete. Items done: X/Y."*
   - Run existing tests first to verify current state
   - Resume from first unchecked DoD item
   - Continue micro-cycles for remaining acceptance scenarios

### Scenario: DESIGN.md and module.md Out of Sync

| State | Truth Source | Action |
|-------|-------------|--------|
| DESIGN.md `✅` + module.md has `[ ]` | module.md (more granular) | Warn user, resume from first `[ ]` |
| DESIGN.md `☐` + module.md all `[x]` | module.md | Auto-fix DESIGN.md to `✅`, report fix |

---

## 8. Test Quality Heuristics

### Good Tests (Behavior-Focused)

- Test through public interfaces, not mocks of internal parts
- Describe WHAT the system does, not HOW it does it
- Survive internal refactors (renaming private methods doesn't break them)
- One logical assertion per test (may have multiple asserts for one behavior)
- Integration-style: exercise real code paths

### Bad Tests (Implementation-Coupled) — Red Flags

- Mocking internal collaborators (not system boundaries)
- Testing private methods directly
- Asserting on call counts or call order
- Test breaks when refactoring without behavior change
- Test name describes HOW not WHAT
- Verifying through external means (querying DB directly) instead of public interface

### Deep Modules in Testing

From "A Philosophy of Software Design":

```
Deep module = small interface + deep implementation
```

When testing deep modules:
- Test the SMALL INTERFACE (few methods, simple params)
- Don't test the deep implementation details
- If the implementation changes but the interface stays the same, tests should still pass

### Refactor Signals (After All GREEN)

After the TDD cycle completes, look for:
- **Duplication** → Extract shared setup helpers
- **Long methods** → Break into private helpers (keep tests on public interface)
- **Shallow modules** → Combine or deepen
- **Feature envy** → Move logic to where data lives
- **Primitive obsession** → Introduce value objects
- **Existing code** the new code reveals as problematic

---

## 9. Code Craftsmanship Iron Rules (代码工艺铁律)

Concrete patterns and decision trees for Hard Constraint #11. These rules apply during EVERY GREEN and REFACTOR cycle.

### 9.1 Constant Extraction Decision Tree

For every literal in production code, ask:

```
Is this literal a domain concept?
├─ YES → ALWAYS name it as const (even if used once)
│   Examples: "online", "offline", "reply", "broadcast"
│   → const PayloadOnline = "online"
│
├─ NO — Is it used ≥2 times?
│   ├─ YES → ALWAYS extract to const
│   │   Examples: "ayuan.*", 0755, 30*time.Second
│   │   → const SubjectAll = "ayuan.*"
│   │   → const DefaultDirPerm = 0755
│   │
│   └─ NO — Would a reader ask "why this value?"
│       ├─ YES → Name it
│       │   Examples: "127.0.0.1:9876" (default MQ addr)
│       │   → const DefaultMQAddr = "127.0.0.1:9876"
│       │
│       └─ NO → OK as inline literal
│           Examples: 0 (zero index), "" (empty string), nil
```

### 9.2 Constant Naming Convention (Go)

```go
// Group by semantic category, not by location
domain/
  const (
      // Lifecycle payloads
      PayloadOnline          = "online"
      PayloadOffline         = "offline"
      PayloadRetireAnnounced = "retire.announced"
      PayloadManifestChanged = "manifest.changed"

      // Subject patterns
      SubjectAll    = "ayuan.*"
      SubjectPrefix = "ayuan."

      // Timing
      MeditationCheckInterval = 30 * time.Second
  )

infra/localfs/
  const (
      DefaultDirPerm  os.FileMode = 0755
      DefaultFilePerm os.FileMode = 0644
  )

config/
  const (
      DefaultMQAddr   = "127.0.0.1:9876"
      DefaultLogLevel = "info"
      EnvAYuanID      = "AYUAN_ID"
      EnvBaseDir      = "AYUAN_BASE_DIR"
  )
```

### 9.3 DRY Extraction Decision Tree

```
Do 2+ code blocks share identical structure (differing only in parameters)?
├─ YES, same function → Extract inner loop into private helper
│   Example: 4x broadcast Intent construction in ABody
│   → func (b *ABody) broadcast(payload string) error { ... }
│
├─ YES, different functions in same package → Extract package-level helper
│   Example: 8x os.IsNotExist → ErrNotFound pattern in localfs
│   → func notExistToNotFound(err error) error { ... }
│
├─ YES, across packages → Extract to shared internal package
│   Example: home directory lookup in both domain and config
│   → Keep in config only, domain should not need filesystem paths
│
└─ NO → Check Rule of Three (3 similar → extract on 3rd occurrence)
```

### 9.4 Common Extraction Patterns (Go)

#### Pattern: Broadcast Helper

```go
// BEFORE: 4 nearly-identical blocks
func (b *ABody) goOnline() error {
    return b.sensorium.Publisher.Publish(Intent{
        ID: generateID(), TraceID: generateTraceID(),
        From: b.ID, Type: IntentBroadcast, Payload: []byte("online"),
    })
}

// AFTER: One helper, 4 call sites
func (b *ABody) broadcast(payload string) error {
    return b.sensorium.Publisher.Publish(Intent{
        ID: generateID(), TraceID: generateTraceID(),
        From: b.ID, Type: IntentBroadcast, Payload: []byte(payload),
    })
}

func (b *ABody) goOnline() error  { return b.broadcast(PayloadOnline) }
func (b *ABody) goOffline() error { return b.broadcast(PayloadOffline) }
```

#### Pattern: Error Translation Helper

```go
// BEFORE: 6x the same pattern in localfs adapters
if os.IsNotExist(err) {
    return AManifest{}, domain.ErrNotFound
}

// AFTER: One helper per return shape
func wrapNotFound(err error, zero interface{}) (interface{}, error) {
    if os.IsNotExist(err) { return zero, domain.ErrNotFound }
    return zero, err
}
// Or simpler: type-specific helpers
func loadOrNotFound[T any](load func() (T, error)) (T, error) {
    v, err := load()
    if os.IsNotExist(err) { return v, domain.ErrNotFound }
    return v, err
}
```

#### Pattern: Workspace Directory Constants

```go
// BEFORE: Directory list duplicated in engine.go and engine_test.go
dirs := []string{
    filepath.Join(workspaceDir, "inbox"),
    filepath.Join(workspaceDir, "outbox"),
    // ... 6 more
}

// AFTER: Single source of truth
var workspaceSubdirs = []string{
    "inbox", "outbox", ".claude", ".claude/rules",
    "private", "private/aos", "shared",
}

func workspaceDirs(base string) []string {
    dirs := make([]string, len(workspaceSubdirs))
    for i, sub := range workspaceSubdirs {
        dirs[i] = filepath.Join(base, sub)
    }
    return dirs
}
```

### 9.5 Dead Code Detection Checklist

After every GREEN cycle, scan for:

| Signal | Detection | Action |
|--------|-----------|--------|
| Unused struct field | Field declared but never read in any method | Delete field + constructor param |
| Unused function/method | `grep -c "funcName" module/` returns only the declaration | Delete function |
| Unused import | `go vet` or IDE warning | Remove import |
| Unreachable branch | Code after unconditional `return` | Delete unreachable block |
| Commented-out code | `//` lines that look like code | Delete — git history preserves it |
| Redundant helper | Helper exists in two packages doing the same thing | Keep in the more appropriate package, delete the other |

### 9.6 Standard Library Preference Matrix

Before writing a utility function, check this matrix:

| Need | Standard Library | Custom Alternative (FORBIDDEN) |
|------|-----------------|-------------------------------|
| String contains | `strings.Contains(s, sub)` | Hand-written `containsStr()` |
| String join/split | `strings.Join()` / `strings.Split()` | Manual loop + concat |
| Path manipulation | `filepath.Join()`, `filepath.Base()` | Manual string concatenation |
| Time comparison | `time.Since()`, `time.Before()` | Manual `time.Now().Sub()` |
| Error wrapping | `fmt.Errorf("...%w...", err)` | Manual error string construction |
| Slice operations | `slices.Contains()`, `slices.Index()` (Go 1.21+) | Manual loop search |
| Maps operations | `maps.Keys()`, `maps.Values()` (Go 1.21+) | Manual loop collection |

### 9.7 Test Code Craftsmanship

Test code follows the SAME craftsmanship rules as production code:

```go
// BAD: Magic strings in test assertions
if string(intent.Payload) != "online" { ... }
if intent.Type != "broadcast" { ... }

// GOOD: Use the same constants as production
if string(intent.Payload) != domain.PayloadOnline { ... }
if intent.Type != domain.IntentBroadcast { ... }
```

```go
// BAD: Duplicated test setup
func TestFoo(t *testing.T) {
    ms := &fakeManifestLoaderSaver{manifests: make(map[string]domain.AManifest)}
    aosStore := &fakeAOSLoaderSaverChecker{files: make(map[string][]domain.AOSFile)}
    // ... 10 more lines of setup
}

// GOOD: Use the existing test factory
func TestFoo(t *testing.T) {
    ta := newTestABody("echo", true)
    // customize as needed: ta.manifest.manifests["echo"] = ...
}
```

```go
// BAD: Duplicated manifest creation across tests
ta.manifest.manifests["echo"] = domain.AManifest{ID: "echo", Name: "Echo Agent", Raw: map[string]interface{}{"id": "echo"}}

// GOOD: Test helper with descriptive name
func withManifest(ta *testABody, id, name string) {
    ta.manifest.manifests[id] = domain.AManifest{
        ID: id, Name: name, Raw: map[string]interface{}{"id": id},
    }
}
```

---

## 10. E2E Smoke Test Protocol (v1.8.0+)

Run this protocol after ALL tasks in DESIGN.md §5 are ✅. This validates the entire BC boots and serves correctly.

**Precondition**: `DESIGN.md` §8 Operational Entry Design MUST exist. If missing → HALT and write AD to arch-detail:

```
AD-{ID}: DESIGN.md §8 Operational Entry Design missing
  Required: env var schema, config module, startup/shutdown scripts
  Impact: E2E smoke test cannot determine configuration baseline
  (by devtdd, <date>)
```

Do NOT proceed with smoke test until detail provides §8.

### 10.1 Composition Root Boot Test

```
1. Build the BC binary: go build ./cmd/<bc-slug>/
2. Start with minimal config (env vars from DESIGN.md §8)
3. Verify:
   - Process starts without panic
   - All dependency injections succeed (no nil ports)
   - All adapters connect (DB pool, message broker, etc.)
4. Graceful shutdown: send SIGINT → process exits cleanly (exit code 0)
```

### 10.2 Health Check

```
1. Start the BC process
2. GET /health (HTTP) or equivalent health check
3. Assert: 200 OK, response body includes:
   - Status: "healthy"
   - Version: from build metadata
   - Dependencies: all "connected"
4. Kill DB connection → health check should return 503 "degraded"
```

### 10.3 One Happy-Path Request

```
1. Seed the database with minimal test data (one entity)
2. Send a real request through the delivery layer:
   - REST: POST /api/v1/{resource} + GET /api/v1/{resource}/{id}
   - gRPC: Create RPC + Get RPC
   - CLI: create command + list command
3. Assert:
   - Create returns 201 / OK with resource ID
   - Get returns the created resource with correct fields
   - All layers exercised (check logs or traces)
4. Tear down: delete test data, stop process
```

### 10.4 Graceful Shutdown Under Load

```
1. Start the BC process
2. Send N in-flight requests (e.g., 10 concurrent)
3. Send SIGINT mid-flight
4. Assert:
   - In-flight requests complete (no connection reset)
   - New requests rejected (connection refused)
   - Process exits within shutdown timeout (default 30s)
   - No goroutine leaks (runtime.NumGoroutine() before == after)
```

### 10.5 Smoke Test Report

After completing the protocol, output:

```
E2E Smoke Test Results:
  [PASS] Composition Root Boot — all 5 adapters connected
  [PASS] Health Check — 200 OK (healthy) / 503 (degraded on DB kill)
  [PASS] Happy Path — POST + GET round-trip successful
  [PASS] Graceful Shutdown — 10 in-flight requests completed, clean exit
  
  Duration: 12.3s | Binary size: 18MB
```

If any check fails, report the failure and suggest returning to the specific task that needs fixing.
