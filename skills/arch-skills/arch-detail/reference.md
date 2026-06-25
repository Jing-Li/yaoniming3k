# Arch-Detail — Reference

Detailed templates, language-specific golden rules, and protocols for the `arch-detail` skill. Loaded only when needed (progressive disclosure from [SKILL.md](SKILL.md)).

---

## 0. DESIGN.md Index Template

`docs/bc/<bc-slug>/DESIGN.md` is the **Phase 3 index file**. It contains global decisions (DDL, GoF, package layout) and links to modular design files under `design/modules/`. It must not be appended to `ARCHITECTURE.md`. Use this exact structure:

```markdown
# Detailed Design Specification --- <Project Name> <BC Name>

> Phase 3 output. Translates Phase 2 boundaries into <target language> code structures, DDL, GoF patterns, and vertical-slice tasks.
> Aligned with: [ARCHITECTURE.md](./ARCHITECTURE.md) (Phase 2 boundaries), [LANGUAGE.md](./LANGUAGE.md), [CONTEXT.md](./CONTEXT.md)
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

> When 2+ BCs are registered in PHASES.md, include a Cross-BC Package Mapping sub-table:
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
| <module-a> | <PortA> | [module.md](./design/modules/<module-a>/module.md) | [method1](./design/modules/<module-a>/interfaces/method1.md), [method2](...) |
| <module-b> | <PortB> | [module.md](./design/modules/<module-b>/module.md) | [method1](./design/modules/<module-b>/interfaces/method1.md), ... |

## 5. Vertical-Slice Task Summary

| # | Task | Module | Interface Contracts | Definition of Done |
|---|------|--------|--------------------|--------------------|
| 1 | <task title> | [<module>](./design/modules/<module>/module.md#vertical-slice-tasks) | [method1](./design/modules/<module>/interfaces/method1.md) | <one-line summary> |

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
- Aligned-with links to `LANGUAGE.md` and `CONTEXT.md`

**Module Index table**: every module in ARCHITECTURE.md's port table must have a row with relative links to its `module.md` and all `interfaces/<method>.md` files.

---

## 0A. Module Design Template (module.md)

`docs/bc/<bc-slug>/design/modules/<module>/module.md` contains the per-module design. Use this structure:

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
```

**Rules**:
- Every port interface from ARCHITECTURE.md must have a corresponding module.
- The Interface Contracts Index must list **every** method in the port — no omissions.
- Domain code in module.md must not import infrastructure, proto, or framework types.
- Vertical-Slice Tasks for this module go here. Cross-module tasks go in the primary module with a cross-reference to the other module.

---

## 0B. Interface Contract Template (method.md)

`docs/bc/<bc-slug>/design/modules/<module>/interfaces/<method>.md` contains the per-method contract. Use this structure:

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

### 1.1 Go — Golden Rules

| Rule | Do | Don't |
|------|-----|-------|
| Interface ownership | Define interface in **consumer** package (usecase) | Define in adapter package |
| Return types | Accept interfaces, **return structs** | Return `interface{}` from constructors |
| Context propagation | First param `ctx context.Context` on every port method | Store ctx in struct fields |
| Error types | Sentinel `var ErrXxx = errors.New(...)` in `domain/errors.go` | Return raw `pgx.ErrNoRows` to upper layers |
| Package layout | `domain/`, `internal/usecase/<ctx>/`, `internal/infrastructure/<tech>/` or `domain/`, `internal/port/<ctx>/`, `internal/app/`, `internal/infra/<tech>/` | `internal/<feature>/` mixing layers |
| Error translation | Adapter wraps with `errors.Is`-friendly conversions | Pass driver errors upward verbatim |

#### Go skeleton

```go
// domain/agent.go
package domain

type AgentID string
type AgentStatus string

const (
    StatusOnline  AgentStatus = "online"
    StatusOffline AgentStatus = "offline"
)

type AgentEntry struct {
    ID       AgentID
    Status   AgentStatus
    LastBeat time.Time
}

// domain/errors.go
var (
    ErrAgentNotFound = errors.New("agent not found")
    ErrManifestExists = errors.New("manifest already exists")
)

// internal/usecase/census/list.go
package census

type Reader interface {
    List(ctx context.Context, filter Filter) ([]domain.AgentEntry, error)
}

type ListUseCase struct {
    reader Reader
}

func (uc *ListUseCase) Execute(ctx context.Context, f Filter) ([]domain.AgentEntry, error) { ... }

// internal/infrastructure/postgres/census_store.go
package postgres

type CensusStore struct{ db *sql.DB }

func (s *CensusStore) List(ctx context.Context, f census.Filter) ([]domain.AgentEntry, error) {
    rows, err := s.db.QueryContext(ctx, `SELECT ... FROM agents WHERE ...`)
    if errors.Is(err, sql.ErrNoRows) { return nil, domain.ErrAgentNotFound }
    // map rows → []domain.AgentEntry (Data Mapper)
}
```

#### Go skeleton — Transaction Script variant (port/ umbrella + app/ scripts)

When use cases are thin transaction-script functions (not structs), ports live in a separate `port/` umbrella rather than embedded in the usecase package. All adapters (driven + driving) go under `infra/`.

```go
// <bc-slug>/internal/port/census/store.go
package census

import "github.com/<org>/<project>/<bc-slug>/internal/domain"

type CensusStore interface {
    Upsert(ctx context.Context, entry domain.Entry) error
    Get(ctx context.Context, id string) (domain.Entry, error)
    List(ctx context.Context) ([]domain.Entry, error)
}

// <bc-slug>/internal/app/upsert_census.go
package app

import (
    "github.com/<org>/<project>/<bc-slug>/internal/domain"
    "github.com/<org>/<project>/<bc-slug>/internal/port/census"
)

func UpsertCensus(ctx context.Context, store census.CensusStore, entry domain.Entry) error {
    if !entry.CanTransition(entry.Status) { return domain.ErrInvalidTransition }
    return store.Upsert(ctx, entry)
}

// <bc-slug>/internal/infra/postgres/census_adapter.go — implements census.CensusStore
// <bc-slug>/internal/infra/grpc/server.go         — driving adapter (gRPC)
// <bc-slug>/internal/infra/cli/list.go            — driving adapter (CLI)
```

> **Multi-BC independent modules (MANDATORY when ≥2 BCs with independent processes)**: Each BC is a **completely independent module** with its own `go.mod`, `cmd/`, `internal/`, `docs/`, and `scripts/`. **Zero shared code** — no `pkg/`, no shared `internal/`, no cross-module imports. Ports previously shared between BCs (e.g., IntentClient with Publish + Subscribe) are split by responsibility: each BC defines only the port methods it consumes. DESIGN.md §3 Cross-BC Package Mapping table shows only this BC's module paths.

#### Go diagnosis checklist

- [ ] No `domain/*.go` imports any third-party package (only stdlib).
- [ ] No `domain/*.go` imports generated `proto/*`.
- [ ] Every port method's first parameter is `ctx context.Context`.
- [ ] All errors crossing the adapter→usecase boundary are domain sentinels.
- [ ] No `interface{}` return types in public APIs.
- [ ] Every Upsert / mutating use case **orchestrates** the relevant domain predicate (e.g., `entry.CanTransition(newStatus)`) **before** persisting — the predicate is a domain-layer concern, not an adapter concern.

---

### 1.2 Java — Golden Rules

| Rule | Do | Don't |
|------|-----|-------|
| Domain purity | Plain POJOs / records, only `java.*` imports | `@Entity`, `@Table`, `@Component` in domain |
| Persistence mapping | Separate `XxxJpaEntity` in infra + MapStruct mapper | Reuse domain class as JPA `@Entity` |
| Validation | Pure Java in domain (e.g., constructor guards) | `@NotNull` / `@Valid` in domain |
| Spring | Inject ports (interfaces) into use cases | Inject `JpaRepository` directly into business logic |
| Architecture guard | ArchUnit test enforcing dep direction | Trust developer discipline alone |
| Module layout | Multi-module: `domain`, `application`, `infrastructure`, `bootstrap` | Single Spring Boot module with packages |

#### Java skeleton

```java
// domain/AgentEntry.java   (zero framework imports)
package com.taiyi.domain;

public record AgentEntry(AgentId id, AgentStatus status, Instant lastBeat) {
    public AgentEntry {
        if (id == null) throw new IllegalArgumentException("id required");
    }
}

// application/CensusReader.java   (port owned by use case)
package com.taiyi.application.census;

public interface CensusReader {
    List<AgentEntry> list(ListAgentsQuery query);
}

// application/ListAgentsUseCase.java
@Service
public class ListAgentsUseCase {
    private final CensusReader reader;
    public ListAgentsUseCase(CensusReader reader) { this.reader = reader; }
    public List<AgentEntry> execute(ListAgentsQuery q) { return reader.list(q); }
}

// infrastructure/persistence/AgentJpaEntity.java
@Entity @Table(name = "agents")
public class AgentJpaEntity { ... }

// infrastructure/persistence/AgentMapper.java   (MapStruct)
@Mapper
public interface AgentMapper {
    AgentEntry toDomain(AgentJpaEntity e);
    AgentJpaEntity toJpa(AgentEntry d);
}

// infrastructure/persistence/PostgresCensusReader.java
@Component
public class PostgresCensusReader implements CensusReader {
    private final AgentJpaRepository repo;
    private final AgentMapper mapper;
    @Override public List<AgentEntry> list(ListAgentsQuery q) {
        return repo.findAllByStatus(q.status()).stream().map(mapper::toDomain).toList();
    }
}
```

#### Java ArchUnit guard (snippet)

```java
@AnalyzeClasses(packages = "com.taiyi")
class CleanArchitectureTest {
    @ArchTest
    static final ArchRule domain_should_not_depend_on_anything =
        noClasses().that().resideInAPackage("..domain..")
            .should().dependOnClassesThat().resideInAnyPackage(
                "..application..", "..infrastructure..", "org.springframework..", "javax.persistence..");
}
```

#### Java diagnosis checklist

- [ ] `domain` module has zero Spring/JPA/Jackson imports.
- [ ] Every persistent entity has a separate `XxxJpaEntity` + Mapper.
- [ ] Use cases depend only on domain ports, never `JpaRepository`.
- [ ] ArchUnit rule enforced in CI.

---

### 1.3 Python — Golden Rules

| Rule | Do | Don't |
|------|-----|-------|
| Domain types | `@dataclass(frozen=True)` or `pydantic.BaseModel` (with `model_config={"frozen": True}`) | Inherit from `Base = declarative_base()` |
| Ports | `typing.Protocol` (structural typing) | `abc.ABC` with imports from infra |
| ORM | SQLAlchemy lives in `infrastructure/`; Mapper translates Row → Domain | Use `Mapped[...]` columns directly as domain |
| Async | Decide once: all-async ports or all-sync, no mixing within a context | Half-async / half-sync use cases |
| Validation | Pydantic at boundaries (HTTP / message edges) only | Pydantic in domain entities (couples to v1/v2 quirks) |
| Errors | Custom domain exceptions in `domain/errors.py` | Raise `sqlalchemy.exc.NoResultFound` to use cases |

#### Python skeleton

```python
# domain/agent.py
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class AgentStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"

@dataclass(frozen=True)
class AgentEntry:
    id: str
    status: AgentStatus
    last_beat: datetime

# domain/errors.py
class AgentNotFound(Exception): ...

# domain/census.py   (port via Protocol)
from typing import Protocol, Iterable

class CensusReader(Protocol):
    def list(self, status: AgentStatus | None) -> Iterable[AgentEntry]: ...

# application/list_agents.py
from domain.census import CensusReader
from domain.agent import AgentEntry, AgentStatus

class ListAgentsUseCase:
    def __init__(self, reader: CensusReader) -> None:
        self._reader = reader
    def execute(self, status: AgentStatus | None) -> list[AgentEntry]:
        return list(self._reader.list(status))

# infrastructure/postgres/census_store.py
from sqlalchemy.orm import Session
from .schema import AgentRow   # SQLAlchemy model, infra-only

class PostgresCensusReader:
    def __init__(self, session: Session) -> None: self._s = session
    def list(self, status):
        rows = self._s.query(AgentRow).filter_by(status=status.value).all()
        return [AgentEntry(id=r.id, status=AgentStatus(r.status), last_beat=r.last_beat) for r in rows]
```

#### Python diagnosis checklist

- [ ] `domain/` imports only stdlib + `typing` (no `sqlalchemy`, no `pydantic` if avoidable).
- [ ] All ports are `Protocol` subclasses.
- [ ] No domain class inherits from an ORM base.
- [ ] Async/sync choice is consistent within a bounded context.

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

### 3.0 Data Mapper Applicability (何时需要 / 不需要 Data Mapper)

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

---

## 4. Vertical-Slice Task Template

Each task is one **tracer bullet** through the architecture. Tasks are written inside `design/modules/<module>/module.md` §7, not in DESIGN.md. Use this exact shape:

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

## 5. Pre-Output Self-Audit (在交付前自检)

Before delivering, silently verify:

- [ ] Every class / table / field name appears in `LANGUAGE.md` or is a documented mapping (Section 3.3).
- [ ] DDL uses Data Mapper convention — no domain class is a JPA/ORM entity.
- [ ] At least one GoF pattern justified per Use Case with explicit rationale.
- [ ] Tasks are **vertical** slices, each touching all relevant layers, and placed in the correct `module.md` §7.
- [ ] Each task has a runnable acceptance test (TDD-friendly) and references its module's interface contracts.
- [ ] Language-specific checklist (Section 1.x) passes for the target language.
- [ ] No port interface lives in an adapter package.
- [ ] No domain code imports framework / driver / proto types.
- [ ] `DESIGN.md` is a standalone index file at `docs/bc/<bc-slug>/DESIGN.md` (not appended to `ARCHITECTURE.md`).
- [ ] `DESIGN.md` header cross-references `ARCHITECTURE.md` and declares target language.
- [ ] `docs/arch/PHASES.md` has been updated with Phase 3 ✅ and current date.
- [ ] Every module in ARCHITECTURE.md's port table has a corresponding `design/modules/<module>/module.md`.
- [ ] Every method in every port interface has a corresponding `design/modules/<module>/interfaces/<method>.md`.
- [ ] DESIGN.md Module Index table links to all module.md files with correct relative paths.
- [ ] Every vertical-slice task references at least one specific interface contract file.
- [ ] Every vertical-slice task includes a **Dependencies/Prerequisites** field (even if "None").
- [ ] Every Upsert / mutating use case orchestrates the domain predicate before persisting (not delegated to adapter).
- [ ] When 2+ BCs registered, DESIGN.md §3 Cross-BC Package Mapping table is present and consistent with sibling BC ARCHITECTURE.md §4 and SYSTEM.md §4.
- [ ] DESIGN.md §1.2 explicitly states which entities use full Data Mapper vs identity mapping, with justification.
- [ ] DESIGN.md Task Summary table lists all tasks with links to their module.md.
- [ ] DESIGN.md includes an Operational Entry Design section (env var schema, config module, startup/shutdown scripts) when a sibling BC has equivalent facilities.
- [ ] Every environment variable referenced in the Composition Root appears in the env var schema table.
- [ ] A vertical-slice task exists for config module + scripts implementation.
- [ ] All cross-reference links (DESIGN.md <-> module.md <-> method.md) are valid relative paths.

If any check fails, fix the design **before** writing files or proposing tasks.

---

## 6. Clarification Protocol

If `ARCHITECTURE.md` or `DESIGN.md` is ambiguous on a detail (e.g., column nullability, GoF choice, async/sync), **ask exactly one question** at a time and wait. Do not invent answers.

Example:
> "`ARCHITECTURE.md` lists `CensusSweeper` as a port but does not specify whether sweep is triggered by cron or by API. Which one? — Pick one."
