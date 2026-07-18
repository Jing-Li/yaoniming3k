# Arch-Detail — Reference

Detailed templates, language-specific golden rules, and protocols for the `arch-detail` skill. Loaded only when needed (progressive disclosure from [SKILL.md](SKILL.md)).

---

## 0A. Core Theoretical Foundations

When performing detailed class design, design pattern application, and persistence design, you MUST strictly follow these canonical references:

1. **"Design Patterns: Elements of Reusable Object-Oriented Software" — Erich Gamma et al. ("GoF Gang of Four")**
   - *Status*: One of the greatest classics in software development history.
   - *Core Value*: Introduced 23 design patterns (Factory, Singleton, Strategy, Observer, etc.) — the universal lingua franca for detailed system design and model structuring.
   - *Execution*: You MUST evaluate variability in core domain and application scenarios, applying patterns judiciously (e.g., Factory to isolate entity construction, Strategy to decouple retry/pricing algorithms, Observer to decouple domain event streams).

2. **"Patterns of Enterprise Application Architecture" — Martin Fowler**
   - *Core Value*: Describes how to fully decouple the object model from relational databases via the Data Mapper pattern.
   - *Execution*: Domain models MUST NOT serve as database entities directly. You MUST use the Data Mapper pattern in the Infrastructure layer to map persistence entities to pure domain entities, achieving complete decoupling of business logic from data modeling.

---

## 0. DESIGN.md Index Template

`docs/bc/<bc-slug>/DESIGN.md` is the **Phase 3 index file**. It contains global decisions (DDL, GoF, package layout) and links to modular design files under `detail/modules/`. It must not be appended to `ARCHITECTURE.md`. Use this exact structure:

```markdown
# Detailed Design Specification --- <Project Name> <BC Name>

> Phase 3 output. Translates Phase 2 boundaries into <target language> code structures, DDL, GoF patterns, and vertical-slice tasks.
> Aligned with: [ARCHITECTURE.md](./ARCHITECTURE.md) (Phase 2 boundaries), [LANGUAGE.md](./LANGUAGE.md), [BRD.md](./BRD.md)
> Target language: **<language + version>**
> Last updated: <YYYY-MM-DD>

---

## 1. Database Schema (DDL)
### 1.1 <Database> DDL
### 1.2 Domain-to-Table Mapping (Data Mapper)
### 1.3 Soft-Delete Policy

## 2. GoF Design Patterns (Global Decisions)
### 2.1 Pattern Decisions Table

## 3. <Language> Package Layout (Final)

> When 2+ BCs are registered in AGENTS.md, include a Cross-BC Package Mapping sub-table:
>
> | Package Path | Owner BC | Shared? | Notes |
> |-------------|---------|---------|-------|
> | internal/domain/ | <BC or Shared> | Yes/No | <notes> |
> | internal/port/<bc>/<module>/ | <BC> | No | <port name> |
> | internal/app/<bc>/ | <BC> | No | <use cases> |
> | internal/infra/<tech>/ | <BC or Shared> | Yes/No | <adapter> |

## 4. Module Index

| Module | Port Interface | Design | Methods |
|--------|---------------|--------|---------|
| <module-a> | <PortA> | [module.md](./detail/modules/<module-a>/module.md) | [method1](./detail/modules/<module-a>/interfaces/method1.md), [method2](...) |
| <module-b> | <PortB> | [module.md](./detail/modules/<module-b>/module.md) | [method1](./detail/modules/<module-b>/interfaces/method1.md), ... |

## 5. Vertical-Slice Task Summary

| # | Task | Module | Interface Contracts | Definition of Done |
|---|------|--------|--------------------|--------------------|
| 1 | <task title> | [<module>](./detail/modules/<module>/module.md#vertical-slice-tasks) | [method1](./detail/modules/<module>/interfaces/method1.md) | <one-line summary> |

(Full task details live in each module.md — this table is an index only)

## 6. Dependency Injection Wiring (Composition Root)

## 7. <Language> Diagnosis Checklist (Global)

## 8. Operational Entry Design

Every BC MUST include an operational entry design section covering deployment and runtime management. This prevents the common gap where design documents specify domain logic but leave no path for operators to start, stop, or configure the process.

### 8.1 Environment Variable Schema

Define a table of all environment variables consumed by the Composition Root:

```markdown
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `<BC>_<VAR>` | ✅/❌ | `<default>` | <what it controls> |
```

Rules:
- Every variable referenced in the Composition Root code MUST appear in this table.
- Required variables MUST have explicit validation logic in the config module.
- Default values MUST be documented.

### 8.2 Config Module

Define a dedicated `internal/config/` package:
- `Load() (*Config, error)` — reads env vars, validates required fields, fills defaults.
- Validation failures return domain error sentinels (not raw `os.LookupEnv` errors).
- Composition Root calls `config.Load()` before creating any adapter.

### 8.3 Startup / Shutdown Scripts

When a sibling BC already has `scripts/` (e.g., `platform/scripts/{start,stop,status}.sh`), the new BC MUST design equivalent scripts:

| Script | Responsibility |
|--------|----------------|
| `start.sh` | Compile `cmd/<bc>/main.go` → start process (support `--infra` / `--app` flags) |
| `stop.sh` | Send SIGINT → wait for graceful shutdown |
| `status.sh` | Check process liveness + port reachability |

### 8.4 Vertical-Slice Task

Add a dedicated task in DESIGN.md §5 Task Summary for operational entry:

| # | Task | Module | Definition of Done |
|---|------|--------|--------------------|
| N | Config + Scripts | config, scripts | Config loads and validates; scripts start/stop process cleanly |

---

## 9. <Language> Diagnosis Checklist (Global)
```

**Header requirements**:
- Cross-reference link to `ARCHITECTURE.md` in the same BC directory (Phase 2 boundaries)
- Target language declaration (e.g., **Go 1.22+**, **Java 21+**)
- `Last updated` date
- Aligned-with links to `LANGUAGE.md` and `BRD.md`

**Module Index table**: every module in ARCHITECTURE.md's port table must have a row with relative links to its `module.md` and all `interfaces/<method>.md` files.

---

## 0A. Module Design Template (module.md)

`docs/bc/<bc-slug>/detail/modules/<module>/module.md` contains the per-module design. Use this structure:

```markdown
# Module Design --- <Module Name>

> Part of Phase 3 detailed design for <BC Name>.
> Index: [DESIGN.md](../../DESIGN.md)
> Architecture: [ARCHITECTURE.md](../../ARCHITECTURE.md)
> Last updated: <YYYY-MM-DD>

---

## 1. Domain Layer

(Domain entities, value objects, error sentinels, predicates specific to this module.
Include code blocks for the target language.)

## 2. Port Interface

(Go/Java/Python interface definition with all method signatures.
Include the full interface code block.)

## 3. Application Layer

(Transaction scripts / use case orchestrators that consume this port.
Include code blocks.)

## 4. Infrastructure Adapter Skeleton

(Adapter implementation with Data Mapper, error translation at the boundary.
Include code blocks.)

## 5. GoF Patterns Applied

| Pattern | Variability Axis | Concrete Types | Anti-pattern Avoided |
|---------|-----------------|----------------|---------------------|
| ... | ... | ... | ... |

## 6. Interface Contracts Index

| Method | Contract File | Description |
|--------|--------------|-------------|
| <Method1> | [method1.md](./interfaces/method1.md) | <one-line description> |
| <Method2> | [method2.md](./interfaces/method2.md) | <one-line description> |

## 7. Vertical-Slice Tasks

(Tracer bullets for this module. Each task is one end-to-end slice.)

### Task N — <Imperative title>

**Dependencies/Prerequisites**: <list prerequisite task numbers or "None — independent task">

**Tracer slice**: <UC name> end-to-end (API → UseCase → Port → Adapter → DB)

**Layers touched**: ...

**Interface contracts**: [method1.md](./interfaces/method1.md)

**Acceptance test (TDD red first)**: ...

**Definition of Done**: ...

## 8. Test Strategy

### 8.1 Mock Boundary Decision

| Dependency | Mock? | Rationale |
|------------|-------|-----------|
| Port (driven adapter) | **Mock** — use fake implementation | Domain logic tested in isolation |
| External API / third-party SDK | **Mock** — never call in unit/integration tests | Non-deterministic, slow, rate-limited |
| Database (integration test) | **Real** — ephemeral container (Testcontainers) | Verify Data Mapper + DDL correctness |
| Message broker (if applicable) | **Mock** for unit; **Real** for integration | Verify publish/subscribe contract |

### 8.2 Test Type Breakdown

| Test Type | Scope | Where | Count Guideline |
|-----------|-------|-------|------------------|
| Unit | Use case + domain logic | `_test.go` / `Test.java` / `test_*.py` | One per interface contract method × scenarios |
| Integration | Adapter + real infra | `integration_test.go` / `*IT.java` | One per adapter (CRUD round-trip) |
| Contract | Port interface compliance | Custom or Pact-style | One per port, verify pre/postconditions |
| Architecture guard | Dependency direction | ArchUnit / import-linter / Go script | One per BC |

### 8.3 Test Fixture Strategy

| Fixture | Scope | Construction | Lifetime |
|---------|-------|-------------|----------|
| Domain entity factory | Unit tests | Builder or factory method | Per test |
| DB seed data | Integration tests | SQL migration + seed script or factory | Per test (transaction rollback) |
| External API stub | Unit + integration | WireMock / httptest server | Per test suite |

### 8.4 Contract-to-Test Mapping

Each interface contract (`interfaces/<method>.md`) maps to tests as follows:

| Contract Section | Test Derivation |
|-----------------|----------------|
| Input Contract (preconditions) | → Invalid input test cases |
| Output Contract (postconditions) | → Happy-path assertion targets |
| Error Mapping (sentinels) | → One test per sentinel trigger condition |
| Edge Cases | → One test per edge case |
| Acceptance Test Scenarios | → Direct Given/When/Then test cases |

> **Rule**: Every `interfaces/<method>.md` MUST have ≥ 1 happy-path test + 1 error test + 1 edge-case test. If a contract section is empty, note "no test needed because ...".
```

**Rules**:
- Every port interface from ARCHITECTURE.md must have a corresponding module.
- The Interface Contracts Index must list **every** method in the port — no omissions.
- Domain code in module.md must not import infrastructure, proto, or framework types.
- Vertical-Slice Tasks for this module go here. Cross-module tasks go in the primary module with a cross-reference to the other module.
- **§3 Upstream Consistency (AD Generation)**: If §3 describes runtime behavior (method flows, responsibility assignments, data paths) that refines or changes what ARCHITECTURE.md §2.x says about the same component, you MUST generate an **Architecture Debt (AD)** routed to `/arch-design`. Do NOT directly modify ARCHITECTURE.md or LANGUAGE.md — they are owned by `/arch-design` and `/arch-align` respectively. The AD must include: component name, ARCHITECTURE.md current description, module.md refined description, and suggested resolution.

---

## 0B. Interface Contract Template (method.md)

`docs/bc/<bc-slug>/detail/modules/<module>/interfaces/<method>.md` contains the per-method contract. Use this structure:

```markdown
# Interface Contract --- <Module>.<Method>

> Module: [module.md](../module.md)
> Port: `<PortInterface>.<Method>`
> Last updated: <YYYY-MM-DD>

---

## Signature

(Code block with the method signature in target language)

## Input Contract

| Parameter | Type | Required | Preconditions |
|-----------|------|----------|---------------|
| ctx | context.Context | yes | Non-nil |
| ... | ... | ... | ... |

## Output Contract

| Return | Type | Postconditions |
|--------|------|---------------|
| result | <type> | <description> |
| err | error | nil on success; domain sentinel on failure |

## Error Mapping

| Domain Sentinel | When |
|----------------|------|
| ErrXxx | <condition> |

## Edge Cases

- <edge case 1 -> expected behavior>
- <edge case 2 -> expected behavior>

## Acceptance Test Scenarios

### Scenario 1: Happy path
- Given ...
- When ...
- Then ...

### Scenario 2: <error/edge case name>
- Given ...
- When ...
- Then returns <ErrXxx>

## Cross-References

- Vertical-Slice Task: Task N --- <task title>
- Adapter implementation: [module.md](../module.md) § 4
```

**Trivial methods** (e.g., `Close()`, `Ping()`): still require a method.md file to keep links intact, but may be as short as 10-15 lines — just signature, "no preconditions", return type, and one happy-path scenario.

---

## 1. Per-Language Best Practices

Language-specific golden rules, skeleton code (Go/Java/Python), and diagnosis checklists. See [references/per-language-rules.md](references/per-language-rules.md) for full content.

---

## 2. GoF Pattern Quick Map

| Pattern | When in Clean Arch | Example Use |
|---------|--------------------|-------------|
| **Strategy** | Swappable algorithm injected as a port | Retry policy, pricing, path resolution |
| **Factory** | Constructing aggregates with invariants | `OrderFactory.fromCart(cart, customer)` |
| **Builder** | Optional/many-arg construction | `ManifestBuilder` for Agent manifest |
| **Adapter** | Wrapping third-party SDK behind a port | `RocketMQPublisherAdapter implements EventPublisher` |
| **Decorator** | Cross-cutting around a port | Tracing/Auth/Retry decorator wrapping `OrderRepository` |
| **Observer / Pub-Sub** | Domain events leaving the bounded context | `DomainEventBus.publish(orderCreated)` |
| **Template Method** | Use case skeleton with hooks | Abstract `BatchImportUseCase.execute` with `parseRow` hook |
| **Composite** | Tree-shaped domain (org chart, menu) | `Department.contains(List<Department>)` |
| **State** | Entity with discrete states + transitions | `Order.confirm() / ship() / cancel()` |
| **Specification** | Reusable predicate over domain | `ActiveAgentSpec.isSatisfiedBy(agent)` |

When proposing a pattern, always state:
1. **Variability axis** — what is expected to change?
2. **Pattern chosen** + concrete classes/types.
3. **Anti-pattern avoided** (e.g., "without Strategy, retry policy would leak into use case").

---

## 3. DDL Conventions

### 3.0 Data Mapper Applicability

| Condition | Data Mapper Required? | Rationale |
|-----------|----------------------|-----------|
| Entity has ≥ 8 persistent fields or nested value objects | **Yes** — separate row ↔ domain mapper | Complex mapping justifies the abstraction cost |
| ORM/JPA entity with lifecycle annotations (`@Entity`, `Mapped[...]`) | **Yes** — must decouple | Framework metadata pollutes domain |
| Simple struct (≤ 6 fields, no ORM, no nested types) | **Optional** — may use identity mapping | PoEAA Data Mapper pattern is a guideline, not a mandate; for trivial structs the mapping overhead exceeds the benefit |
| Aggregate root with invariant enforcement | **Yes** — mapper constructs via factory/constructor | Aggregate invariants must survive round-trip |

> **Rule of thumb**: If the domain entity and the persistence row are structurally identical (same field names, same types, same count), an identity mapping (direct scan into domain struct) is acceptable. The section header "Data Mapper" in DESIGN.md §1.2 must explicitly state which entities use full Data Mapper and which use identity mapping, with justification.

### 3.1 Naming

| Element | Convention | Example |
|---------|------------|---------|
| Table | `snake_case`, plural | `agents`, `manifest_records` |
| Column | `snake_case` | `agent_id`, `last_heartbeat_at` |
| PK | `id` (UUID) or `<entity>_id` | `agent_id UUID PK` |
| FK | `<ref>_id` | `tenant_id UUID REFERENCES tenants(id)` |
| Index | `ix_<table>_<col>` | `ix_agents_status` |
| Unique | `ux_<table>_<col>` | `ux_agents_natural_id` |

### 3.2 Audit columns (recommended)

```sql
created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
deleted_at TIMESTAMPTZ NULL  -- soft delete; NULL = live row
```

### 3.3 Domain ↔ Table mapping table (always include)

| Domain Field | Table Column | Type | Notes |
|--------------|--------------|------|-------|
| `AgentEntry.id` | `agents.id` | UUID | natural ID hashed if needed |
| `AgentEntry.status` | `agents.status` | TEXT CHECK IN (...) | enum |
| `AgentEntry.lastBeat` | `agents.last_heartbeat_at` | TIMESTAMPTZ | timezone explicit |

### 3.4 DDL skeleton

```sql
CREATE TABLE agents (
    id              UUID PRIMARY KEY,
    status          TEXT NOT NULL CHECK (status IN ('online','offline','dangling')),
    last_heartbeat_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_agents_status ON agents(status);
```

### 3.5 Index Design Strategy

For each table, derive indexes from the Use Case query patterns in ARCHITECTURE.md. Do not add indexes speculatively.

#### Index Type Decision

| Query Pattern | Index Type | PostgreSQL Syntax | When to Use |
|---------------|-----------|-------------------|-------------|
| Equality filter (`WHERE status = ?`) | **B-tree** (default) | `CREATE INDEX ix ON t(col)` | Most common; works for equality and range |
| Full-text search | **GIN (tsvector)** | `CREATE INDEX ix ON t USING gin(to_tsvector('english', col))` | LIKE / ILIKE on text columns |
| JSONB queries | **GIN** | `CREATE INDEX ix ON t USING gin(metadata)` | JSONB containment (`@>`, `?`) |
| Time-series range queries | **BRIN** | `CREATE INDEX ix ON t USING brin(created_at)` | Large tables, naturally ordered timestamps |
| Geospatial queries | **GiST** | `CREATE INDEX ix ON t USING gist(location)` | PostGIS / geometric types |
| Uniqueness constraint | **Unique B-tree** | `CREATE UNIQUE INDEX ux ON t(col)` | Enforce business rules (e.g., natural ID) |

#### Composite Index Ordering Rules

1. **Leftmost prefix rule**: Put the most selective (highest cardinality) column first
2. **Equality before range**: Columns used in `=` come before columns used in `>`, `<`, `BETWEEN`
3. **Cover frequently**: If a query only needs columns already in the index, no table lookup needed

```sql
-- Example: Use Case "list orders by customer within date range"
-- Query: SELECT ... FROM orders WHERE customer_id = ? AND created_at BETWEEN ? AND ?
-- Index: customer_id (equality) first, created_at (range) second
CREATE INDEX ix_orders_customer_date ON orders(customer_id, created_at);
```

#### Index Design Template

For each table in DDL, add an index design sub-table:

```markdown
#### Index Design — <table_name>

| Index Name | Columns | Type | Use Case | Rationale |
|------------|---------|------|----------|-----------|
| `ix_orders_customer_date` | `(customer_id, created_at)` | B-tree | ListOrdersByCustomer | Equality + range, leftmost prefix |
| `ux_orders_external_id` | `(external_id)` | Unique B-tree | GetOrderByExternalId | Business uniqueness |
| `ix_orders_created_brin` | `(created_at)` | BRIN | AuditReports | Large table, time-range scans |
```

> **Rule**: Every index must trace to a specific Use Case from ARCHITECTURE.md. No speculative indexes. If a Use Case is added later, the index is added with it (generate AD if needed).

---

## 4. Vertical-Slice Task Template

Each task is one **tracer bullet** through the architecture. Tasks are written inside `detail/modules/<module>/module.md` §7, not in DESIGN.md. Use this exact shape:

```markdown
### Task N — <Imperative title>

**Dependencies/Prerequisites**: <list prerequisite task numbers or "None — independent task">
> _Example: `Task 6 (Composition Root)` is a prerequisite for all adapter/wiring tasks._

**Tracer slice**: <UC name> end-to-end (API → UseCase → Port → Adapter → DB)

**Layers touched**:
- domain: `AgentEntry`, `ErrAgentNotFound`
- usecase: `ListAgentsUseCase`, port `CensusReader`
- infrastructure: `PostgresCensusReader` (Data Mapper)
- delivery: `GRPCCensusHandler.List`

**GoF patterns applied**: Strategy (filter), Adapter (gRPC ↔ domain).

**Interface contracts**: [list.md](./interfaces/list.md)

**Acceptance test (TDD red first)**:
- Given 3 agents (2 online, 1 offline) in DB
- When client calls `ListAgents(status=online)`
- Then 2 entries returned, ordered by `last_heartbeat_at desc`

**Definition of Done**:
- [ ] Unit test for `ListAgentsUseCase` with fake `CensusReader` passes.
- [ ] Integration test against ephemeral Postgres passes.
- [ ] gRPC handler test with in-memory bufconn passes.
- [ ] No domain import of `proto/` or `infrastructure/`.
- [ ] CI architecture guard (ArchUnit / import-linter / custom Go script) passes.
```

Keep tasks **small and shippable** — each one ends with a green test. Avoid horizontal tasks like "implement all repositories".

---

## 5. Pre-Output Self-Audit

Before delivering, silently verify:

- [ ] Every class / table / field name appears in `LANGUAGE.md` or is a documented mapping (Section 3.3).
- [ ] DDL uses Data Mapper conventions — no domain class is a JPA/ORM entity.
- [ ] At least one GoF pattern justified per Use Case with explicit rationale.
- [ ] Tasks are **vertical** slices, each touching all relevant layers, and placed in the correct `module.md` §7.
- [ ] Each task has a runnable acceptance test (TDD-friendly) and references its module's interface contracts.
- [ ] Language-specific checklist (Section 1.x) passes for the target language.
- [ ] No port interface lives in an adapter package.
- [ ] No domain code imports framework / driver / proto types.
- [ ] `DESIGN.md` is a standalone index file at `docs/bc/<bc-slug>/detail/DESIGN.md` (not appended to `ARCHITECTURE.md`).
- [ ] `DESIGN.md` header cross-references `ARCHITECTURE.md` and declares target language.
- [ ] `kanban/BOARD.md has been updated with T{N} detail → done.
- [ ] Every module in ARCHITECTURE.md's port table has a corresponding `detail/modules/<module>/module.md`.
- [ ] If source code already exists (redo scenario), Redo Protocol (Step 6) was executed: code↔design delta assessed, delta tasks generated, user confirmed before Phase 3 marked complete.
- [ ] Every method in every port interface has a corresponding `detail/modules/<module>/interfaces/<method>.md`.
- [ ] DESIGN.md Module Index table links to all module.md files with correct relative paths.
- [ ] Every vertical-slice task references at least one specific interface contract file.
- [ ] Every vertical-slice task includes a **Dependencies/Prerequisites** field (even if "None").
- [ ] Every Upsert / mutating use case orchestrates the domain predicate before persisting (not delegated to adapter).
- [ ] Every module.md includes §8 Test Strategy with mock boundary decisions, test type breakdown, and contract-to-test mapping.
- [ ] Every DDL table has an Index Design sub-table (§3.5) with indexes traced to specific Use Cases.
- [ ] STRIDE threat analysis (§0) completed for each module with Component/Threat/Severity/Mitigation table.
- [ ] Security design patterns (Circuit Breaker, Rate Limiter, etc.) documented where applicable.
- [ ] When 2+ BCs registered, DESIGN.md §3 Cross-BC Package Mapping table is present and consistent with sibling BC ARCHITECTURE.md §4 and §6.
- [ ] DESIGN.md §1.2 explicitly states which entities use full Data Mapper vs identity mapping, with justification.
- [ ] DESIGN.md Task Summary table lists all tasks with links to their module.md.
- [ ] DESIGN.md includes an Operational Entry Design section (env var schema, config module, startup/shutdown scripts) when a sibling BC has equivalent facilities.
- [ ] Every environment variable referenced in the Composition Root appears in the env var schema table.
- [ ] A vertical-slice task exists for config module + scripts implementation.
- [ ] All cross-reference links (DESIGN.md <-> module.md <-> method.md) are valid relative paths.
- [ ] **Post-Write: DESIGN.md line count** is within expected range (not truncated, not appended with stale duplicate content).
- [ ] **Post-Write: Old terminology grep** — `grep -rn "<banned-term>" design/ DESIGN.md` for every LANGUAGE.md banned synonym returns zero matches.
- [ ] **Post-Write: File end sanity** — DESIGN.md last 5 lines end cleanly (no truncation mid-sentence, no orphaned table rows).
- [ ] **Redo: ARCHITECTURE.md Mermaid participant aliases** — every `participant X as <Name>` in ARCHITECTURE.md sequence diagrams uses the current port name (not a banned/old name). Compare against LANGUAGE.md banned list and ARCHITECTURE.md §1.2 port table.
- [ ] **Redo: Upstream Consistency AD Generation** — for each module whose `module.md §3` describes runtime behavior (responsibilities, data flows, method sequences), grep both `ARCHITECTURE.md` and `module.md` for the same component name and verify behavioral descriptions are semantically aligned. Also check `LANGUAGE.md` responsibility tables (§E, §F, etc.) for the same components. Any behavioral mismatch is a **blocker** — generate an AD routed to `/arch-design`.
- [ ] **Scope boundary**: arch-detail produces design documents only (DESIGN.md, module.md, interface contracts). It does NOT write source code. Code development is `/devtdd`'s responsibility.

If any check fails, fix the design **before** writing files or proposing tasks.

---

## 6. Clarification Protocol

If `ARCHITECTURE.md` or `DESIGN.md` is ambiguous on a detail (e.g., column nullability, GoF choice, async/sync), **ask exactly one question** at a time and wait. Do not invent answers.

Example:
> "`ARCHITECTURE.md` lists `CensusSweeper` as a port but does not specify whether sweep is triggered by cron or by API. Which one? — Pick one."

---

## Prevention Cases (from AD history)

### Case P1: Implementation Tracking in Design Documents (AD-Dt1, 2026-07-18)

**Trigger**: arch-review found AYuan DESIGN.md §7 mixed design constraints with implementation status (`[x] Engine interface has 4 methods — **Task 10** ✅`). §8 "Code↔Design Alignment Status" and §10 "Adapter Implementation Status" were pure implementation tracking tables.

**Root Cause**: During devtdd cycles, implementers naturally added status tracking to DESIGN.md as a convenient place to mark progress. The skill didn't have an explicit rule separating design constraints from implementation status.

**Fix Applied**: §7 rewritten to pure design constraints only (no Task references, all `[ ]` for verification). §8 and §10 deleted entirely.

**Lesson**: DESIGN.md Diagnosis Checklist (§7) is a design-time verification list — "what MUST be true about the architecture." Implementation progress ("what has been done") belongs in kanban T{N}.md. These are fundamentally different concerns and must never mix.

### Case P2: Task Description Architecture Mismatch (AD-Dt2, 2026-07-18)

**Trigger**: arch-review found DESIGN.md §5 Task 7 described as "TaiyiCLI Watch (gRPC Streaming Client)" — implying a standalone CLI binary, when the actual implementation is a driving adapter within the platform daemon (`infra/cli/watch.go`).

**Root Cause**: The task description was written during initial design, before implementation revealed the actual architecture. It was never updated to reflect the realized design.

**Lesson**: Task descriptions in §5 must accurately reflect the implementation approach. After devtdd completes a task, verify the DESIGN.md description still matches. If the implementation approach changed, update the description to match reality.
