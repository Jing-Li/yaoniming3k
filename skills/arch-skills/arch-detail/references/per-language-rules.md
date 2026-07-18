# Per-Language Best Practices

Language-specific golden rules, skeleton code, and diagnosis checklists for `arch-detail`. Loaded when generating language-specific module designs and interface contracts.

---

## 1.1 Go — Golden Rules

| Rule | Do | Don't |
|------|-----|-------|
| Interface ownership | Define interface in **consumer** package (usecase) | Define in adapter package |
| Return types | Accept interfaces, **return structs** | Return `interface{}` from constructors |
| Context propagation | First param `ctx context.Context` on every port method | Store ctx in struct fields |
| Error types | Sentinel `var ErrXxx = errors.New(...)` in `domain/errors.go` | Return raw `pgx.ErrNoRows` to upper layers |
| Package layout | `domain/`, `internal/usecase/<ctx>/`, `internal/infrastructure/<tech>/` or `domain/`, `internal/port/<ctx>/`, `internal/app/`, `internal/infra/<tech>/` | `internal/<feature>/` mixing layers |
| Error translation | Adapter wraps with `errors.Is`-friendly conversions | Pass driver errors upward verbatim |

### Go skeleton

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

### Go skeleton — Transaction Script variant (port/ umbrella + app/ scripts)

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

### Go diagnosis checklist

- [ ] No `domain/*.go` imports any third-party package (only stdlib).
- [ ] No `domain/*.go` imports generated `proto/*`.
- [ ] Every port method's first parameter is `ctx context.Context`.
- [ ] All errors crossing the adapter→usecase boundary are domain sentinels.
- [ ] No `interface{}` return types in public APIs.
- [ ] Every Upsert / mutating use case **orchestrates** the relevant domain predicate (e.g., `entry.CanTransition(newStatus)`) **before** persisting — the predicate is a domain-layer concern, not an adapter concern.

---

## 1.2 Java — Golden Rules

| Rule | Do | Don't |
|------|-----|-------|
| Domain purity | Plain POJOs / records, only `java.*` imports | `@Entity`, `@Table`, `@Component` in domain |
| Persistence mapping | Separate `XxxJpaEntity` in infra + MapStruct mapper | Reuse domain class as JPA `@Entity` |
| Validation | Pure Java in domain (e.g., constructor guards) | `@NotNull` / `@Valid` in domain |
| Spring | Inject ports (interfaces) into use cases | Inject `JpaRepository` directly into business logic |
| Architecture guard | ArchUnit test enforcing dep direction | Trust developer discipline alone |
| Module layout | Multi-module: `domain`, `application`, `infrastructure`, `bootstrap` | Single Spring Boot module with packages |

### Java skeleton

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

### Java ArchUnit guard (snippet)

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

### Java diagnosis checklist

- [ ] `domain` module has zero Spring/JPA/Jackson imports.
- [ ] Every persistent entity has a separate `XxxJpaEntity` + Mapper.
- [ ] Use cases depend only on domain ports, never `JpaRepository`.
- [ ] ArchUnit rule enforced in CI.

---

## 1.3 Python — Golden Rules

| Rule | Do | Don't |
|------|-----|-------|
| Domain types | `@dataclass(frozen=True)` or `pydantic.BaseModel` (with `model_config={"frozen": True}`) | Inherit from `Base = declarative_base()` |
| Ports | `typing.Protocol` (structural typing) | `abc.ABC` with imports from infra |
| ORM | SQLAlchemy lives in `infrastructure/`; Mapper translates Row → Domain | Use `Mapped[...]` columns directly as domain |
| Async | Decide once: all-async ports or all-sync, no mixing within a context | Half-async / half-sync use cases |
| Validation | Pydantic at boundaries (HTTP / message edges) only | Pydantic in domain entities (couples to v1/v2 quirks) |
| Errors | Custom domain exceptions in `domain/errors.py` | Raise `sqlalchemy.exc.NoResultFound` to use cases |

### Python skeleton

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

### Python diagnosis checklist

- [ ] `domain/` imports only stdlib + `typing` (no `sqlalchemy`, no `pydantic` if avoidable).
- [ ] All ports are `Protocol` subclasses.
- [ ] No domain class inherits from an ORM base.
- [ ] Async/sync choice is consistent within a bounded context.
