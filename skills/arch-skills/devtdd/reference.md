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
| **Design doc references** | DESIGN.md, ARCHITECTURE.md, LANGUAGE.md, CONTEXT.md, SYSTEM.md, design/modules/*/module.md, design/modules/*/interfaces/*.md — all adapter name references should match code | Doc says `RocketMQIntentAdapter` but code says `RocketMQEventAdapter` |
| **Cross-BC doc mirrors** | When a term is renamed in one BC, check sibling BCs' LANGUAGE.md Banned Terms / glossary for stale mirrors | Platform BC renamed `Event` → `Intent`, but AYuan LANGUAGE.md Banned Terms still lists `Event` as replacement |

**When to run**: After any REFACTOR cycle that changes a type name, interface name, or file name. Run BOTH identifier-level grep AND full-text `(?i)\b{old}\b` scan across the entire module **and all documentation files**. If any stale reference is found, fix it in the same cycle.

### Test Placement

- [ ] Test files live alongside source (same package, test suffix convention)
- [ ] Integration tests separated by build tag or directory
- [ ] No test imports production code from adapter packages into app-layer tests

---

## 5. State Synchronization Protocol

### Atomic Update Sequence

When a task passes all DoD items:

1. Update `DESIGN.md` §5 row:
   ```
   Before: | 1 | Domain + Census Upsert Path | ... | ☐ |
   After:  | 1 | Domain + Census Upsert Path | ... | ✅ |
   ```

2. Update `design/modules/<module>/module.md` §7 task DoD:
   ```
   Before: - [ ] Unit test for CanTransition predicate passes.
   After:  - [x] Unit test for CanTransition predicate passes.
   ```

3. Update `docs/arch/PHASES.md` `Last updated` date.

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
