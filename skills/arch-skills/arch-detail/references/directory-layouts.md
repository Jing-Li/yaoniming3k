# Canonical Directory Layouts — 5-Layer Clean Architecture

Single source of truth for project directory structure. Referenced by:
- `arch-detail` when generating DESIGN.md §3 Package Layout
- `devtdd` when creating source files (HC#3 boundary enforcement)
- `arch-ops` when writing scripts (binary paths, build commands)
- `arch-review` when auditing dependency direction

---

## 1. Layer Semantic Definitions (语言无关)

| # | Layer | Responsibility | Dependency Rule | Contains | NEVER Contains |
|---|-------|---------------|-----------------|----------|----------------|
| 1 | **Domain** | Business entities, value objects, domain events, domain errors, invariant predicates | Zero external imports (only language stdlib) | Entity structs/records, VO, `ErrXxx`, `CanTransition()` | ORM annotations, HTTP types, framework imports, I/O |
| 2 | **Port** | Interface contracts between layers (SPI) | May import Domain only | Interface / Protocol / Trait / abstract class definitions | Implementations, concrete types, framework types |
| 3 | **Application** | Use case orchestration (transaction scripts or command handlers) | May import Domain + Port | UseCase structs/classes, DTOs (request/response), transaction boundaries | Direct DB access, HTTP parsing, file I/O, message publishing |
| 4 | **Infrastructure** | Adapter implementations (driven side) | May import Domain + Port (+ external libs) | DB adapters, HTTP clients, MQ producers/consumers, file storage, cache | Business rules, domain validation logic |
| 5 | **Delivery** | Entry points (driving side) + composition root | May import ALL layers (wires everything) | HTTP handlers, gRPC servers, CLI commands, MQ listeners, DI wiring, `main()` | Business logic beyond param parsing + response formatting |

### Dependency Direction (MANDATORY)

```
Delivery → Application → Domain
    ↓           ↑
Infrastructure → Port → Domain
```

- Arrows point TOWARD Domain (innermost).
- Domain imports NOTHING outside itself.
- Port imports only Domain.
- Application imports Domain + Port.
- Infrastructure imports Domain + Port (+ third-party drivers).
- Delivery imports everything (it is the composition root).

### Layer ↔ Directory Naming Convention

Each language maps the 5 semantic layers to its idiomatic directory names below. The **semantic layer** is what matters for dependency rules; the **directory name** is the physical manifestation.

---

## 2. Go

### Single-BC Layout

```
<bc-slug>/
├── cmd/
│   └── <service-name>/
│       └── main.go              # [Delivery] composition root + server start
├── internal/
│   ├── domain/                  # [Domain]
│   │   ├── <aggregate>.go      #   entities, value objects
│   │   ├── events.go           #   domain events
│   │   └── errors.go           #   sentinel errors (var ErrXxx)
│   ├── port/                    # [Port]
│   │   └── <context>/          #   one sub-package per bounded context
│   │       └── store.go        #   interface definitions
│   ├── app/                     # [Application]
│   │   └── <usecase>.go        #   transaction script functions or UseCase structs
│   └── infra/                   # [Infrastructure]
│       ├── postgres/            #   database adapters
│       ├── redis/               #   cache adapters
│       ├── httpclient/          #   outbound HTTP adapters
│       ├── mq/                  #   message queue adapters
│       └── http/                #   [Delivery] HTTP handlers + router
│           ├── handler/         #     request handlers
│           ├── middleware/      #     auth, logging, recovery
│           └── openapi/         #     OpenAPI declarations (HC#11)
├── go.mod
├── go.sum
└── Makefile
```

### Variant A (usecase-embedded ports, for smaller projects)

```
internal/
├── domain/
├── usecase/
│   └── <context>/              # [Port + Application] interface defined HERE + use case
└── infrastructure/
    └── <tech>/                 # [Infrastructure]
```

> **Rule**: Pick ONE variant per BC. Declare choice in DESIGN.md §3. Do NOT mix variants within a BC.

### Multi-BC Layout (≥2 independent processes)

```
project-root/
├── <bc-a>/                     # completely independent module
│   ├── cmd/
│   ├── internal/
│   ├── go.mod                  # own module
│   └── Makefile
├── <bc-b>/
│   ├── cmd/
│   ├── internal/
│   ├── go.mod
│   └── Makefile
└── docs/
    └── bc/
        ├── <bc-a>/
        └── <bc-b>/
```

**Zero shared code** — no `pkg/`, no cross-module imports. Cross-BC communication via messages only.

### Go Constraints

- `internal/domain/` imports ONLY stdlib (`fmt`, `errors`, `time`, `context`).
- Every port method's first param: `ctx context.Context`.
- Adapters return domain sentinel errors, never driver errors (`pgx.ErrNoRows` → `domain.ErrNotFound`).
- No `interface{}` / `any` in public port signatures.

---

## 3. Java (Kotlin-compatible)

### Multi-Module Gradle/Maven Layout

```
<bc-slug>/
├── domain/                          # [Domain] — zero framework deps
│   └── src/main/java/com/<org>/domain/
│       ├── model/                   #   entities (record / POJO)
│       ├── event/                   #   domain events
│       └── error/                   #   domain exceptions
├── application/                     # [Application + Port]
│   └── src/main/java/com/<org>/application/
│       ├── port/                    #   [Port] interfaces (in/out)
│       │   ├── in/                  #     driving ports (use case interfaces)
│       │   └── out/                 #     driven ports (repository, gateway)
│       └── usecase/                 #   use case implementations
│           └── <Feature>UseCase.java
├── infrastructure/                  # [Infrastructure]
│   └── src/main/java/com/<org>/infrastructure/
│       ├── persistence/             #   JPA entities + repositories + mappers
│       ├── messaging/               #   Kafka/RabbitMQ adapters
│       ├── client/                  #   outbound HTTP/gRPC clients
│       └── config/                  #   Spring @Configuration beans
├── bootstrap/                       # [Delivery] — composition root
│   └── src/main/java/com/<org>/
│       ├── Application.java         #   @SpringBootApplication main
│       ├── web/                     #   REST controllers
│       │   ├── <Feature>Controller.java
│       │   └── dto/                 #   request/response DTOs
│       └── grpc/                    #   gRPC service impls (if applicable)
├── build.gradle.kts                 # (or pom.xml)
└── settings.gradle.kts
```

### Java Constraints

- `domain` module: `dependencies {}` block is EMPTY (no Spring, no JPA, no Jackson).
- Every persistent entity has a separate `XxxJpaEntity` in infrastructure + MapStruct mapper.
- Use cases depend on port interfaces, NEVER on `JpaRepository` or `RestTemplate`.
- ArchUnit test in `bootstrap/src/test/` enforces dependency direction in CI.
- Validation: constructor guards in domain; `@Valid` only in bootstrap DTOs.

---

## 4. Python

### src-layout (recommended for services)

```
<bc-slug>/
├── src/
│   └── <package_name>/
│       ├── domain/                  # [Domain]
│       │   ├── models.py           #   @dataclass(frozen=True) entities + VOs
│       │   ├── events.py           #   domain events
│       │   └── errors.py           #   domain exceptions
│       ├── ports/                   # [Port]
│       │   ├── repositories.py     #   Protocol classes (driven)
│       │   └── services.py         #   Protocol classes (outbound)
│       ├── application/             # [Application]
│       │   ├── use_cases.py        #   UseCase classes
│       │   └── dto.py              #   request/response dataclasses
│       ├── infrastructure/          # [Infrastructure]
│       │   ├── persistence/        #   SQLAlchemy models + repository impls
│       │   │   ├── schema.py       #     ORM models (infra-only)
│       │   │   └── repository.py   #     implements ports.repositories
│       │   ├── messaging/          #   Kafka/RabbitMQ adapters
│       │   └── clients/            #   outbound HTTP clients
│       └── delivery/                # [Delivery]
│           ├── http/               #   FastAPI/Flask routers
│           │   ├── routes.py
│           │   ├── schemas.py      #   Pydantic request/response (edge validation)
│           │   └── deps.py         #   DI wiring (FastAPI Depends)
│           ├── cli/                #   Click/Typer commands
│           └── consumers/          #   MQ consumer entry points
├── tests/
│   ├── unit/                       #   domain + application tests (no I/O)
│   └── integration/                #   infrastructure + delivery tests
├── pyproject.toml
└── Makefile
```

### Python Constraints

- `domain/` imports ONLY stdlib + `typing` (no `sqlalchemy`, no `pydantic`, no `fastapi`).
- All ports are `typing.Protocol` subclasses (structural typing, no inheritance coupling).
- Pydantic models live in `delivery/http/schemas.py` (edge validation), NOT in domain.
- Async decision: all-async OR all-sync within one BC. Declare in DESIGN.md §3.
- ORM models (`schema.py`) are infra-only; mappers translate Row → Domain dataclass.

---

## 5. TypeScript / Node.js

### Standalone Service (NestJS or framework-agnostic)

```
<bc-slug>/
├── src/
│   ├── domain/                      # [Domain]
│   │   ├── entities/               #   entity classes / interfaces
│   │   ├── value-objects/          #   VO classes
│   │   ├── events/                 #   domain events
│   │   └── errors.ts              #   domain error classes
│   ├── ports/                       # [Port]
│   │   ├── repositories.ts        #   repository interfaces
│   │   └── gateways.ts            #   outbound service interfaces
│   ├── application/                 # [Application]
│   │   ├── use-cases/             #   one file per use case
│   │   │   └── create-order.use-case.ts
│   │   └── dto/                   #   request/response types
│   ├── infrastructure/              # [Infrastructure]
│   │   ├── persistence/           #   Prisma/TypeORM/Drizzle adapters
│   │   ├── messaging/             #   Kafka/RabbitMQ adapters
│   │   └── clients/              #   outbound HTTP clients (axios/fetch)
│   └── delivery/                    # [Delivery]
│       ├── http/                   #   Express/Fastify/NestJS controllers
│       │   ├── controllers/
│       │   ├── middleware/
│       │   └── routes.ts
│       ├── cli/                    #   Commander.js commands
│       └── consumers/             #   MQ consumer entry points
├── tests/
│   ├── unit/
│   └── integration/
├── package.json
├── tsconfig.json
└── Makefile
```

### TypeScript Constraints

- `domain/` has ZERO npm imports (no `@nestjs/*`, no `typeorm`, no `zod` in domain).
- Ports are TypeScript `interface` (not abstract class — prefer structural typing).
- Validation (zod / class-validator) lives in `delivery/http/` only.
- If using NestJS: modules map to use-case groups; `@Injectable()` only in application + infrastructure.
- `strict: true` in tsconfig. No `any` in port signatures.

---

## 6. Rust

### Cargo Workspace (single BC = single crate or workspace member)

```
<bc-slug>/
├── src/
│   ├── domain/                      # [Domain]
│   │   ├── mod.rs
│   │   ├── entities.rs            #   structs + impl (invariant methods)
│   │   ├── events.rs              #   domain events (enums)
│   │   └── errors.rs             #   thiserror domain errors
│   ├── ports/                       # [Port]
│   │   ├── mod.rs
│   │   └── repositories.rs       #   trait definitions (async_trait)
│   ├── application/                 # [Application]
│   │   ├── mod.rs
│   │   └── use_cases.rs          #   pub async fn or UseCase structs
│   ├── infrastructure/              # [Infrastructure]
│   │   ├── mod.rs
│   │   ├── postgres/             #   sqlx/tokio-postgres adapters
│   │   ├── redis/                #   cache adapters
│   │   └── http_client/         #   reqwest outbound calls
│   └── delivery/                    # [Delivery]
│       ├── mod.rs
│       ├── http/                  #   axum/actix-web handlers
│       │   ├── handlers.rs
│       │   ├── middleware.rs
│       │   └── routes.rs
│       └── cli.rs                 #   clap commands
├── tests/                           # integration tests
├── Cargo.toml
└── Makefile
```

### Multi-BC (Cargo workspace)

```
project-root/
├── crates/
│   ├── <bc-a>/                   # independent crate
│   │   └── src/ (same layout as above)
│   └── <bc-b>/
│       └── src/
├── Cargo.toml                    # [workspace] members
└── Makefile
```

### Rust Constraints

- `domain/` uses ONLY `std` + `thiserror` (for error derive). No `tokio`, no `serde` in domain structs (serde in infra/delivery DTOs).
- Ports are `trait` definitions with `#[async_trait]` if async.
- Domain entities: `#[derive(Clone, Debug)]`, invariant checks in `fn new() -> Result<Self, DomainError>`.
- No `unwrap()` / `expect()` in application or domain code.
- Adapters return `Result<T, DomainError>`, mapping driver errors at the boundary.

---

## 7. C# / .NET

### Multi-Project Solution

```
<bc-slug>/
├── src/
│   ├── <Bc>.Domain/                 # [Domain]
│   │   ├── Entities/
│   │   ├── ValueObjects/
│   │   ├── Events/
│   │   └── Errors/
│   ├── <Bc>.Application/            # [Application + Port]
│   │   ├── Ports/
│   │   │   ├── I<Order>Repository.cs
│   │   │   └── I<Payment>Gateway.cs
│   │   ├── UseCases/
│   │   │   └── CreateOrder/
│   │   │       ├── CreateOrderUseCase.cs
│   │   │       └── CreateOrderRequest.cs
│   │   └── DTOs/
│   ├── <Bc>.Infrastructure/         # [Infrastructure]
│   │   ├── Persistence/
│   │   │   ├── Entities/          #   EF Core entities (separate from domain)
│   │   │   ├── Repositories/
│   │   │   └── Mappings/          #   AutoMapper / manual mappers
│   │   ├── Messaging/
│   │   └── Clients/
│   └── <Bc>.Api/                    # [Delivery]
│       ├── Controllers/
│       ├── Middleware/
│       ├── Program.cs             #   composition root (MinimalAPI or Startup)
│       └── appsettings.json
├── tests/
│   ├── <Bc>.Domain.Tests/
│   ├── <Bc>.Application.Tests/
│   └── <Bc>.Integration.Tests/
├── <Bc>.sln
└── Makefile
```

### C# Constraints

- `Domain` project: `<PackageReference>` list is EMPTY (no EF Core, no Newtonsoft, no ASP.NET).
- Domain entities are POCOs with behavior methods; NOT EF Core entities.
- EF Core entities live in Infrastructure with explicit mapping (Fluent API or AutoMapper).
- Ports are C# `interface` (I-prefix convention: `IOrderRepository`).
- Use MediatR only in Application layer (commands/queries), NOT in Domain.
- `Program.cs` / `Startup.cs` is the ONLY place that references all layers.

---

## 8. Cross-Language Invariants (所有语言必须遵守)

| # | Rule | Verification |
|---|------|-------------|
| 1 | Domain layer has ZERO third-party imports | CI lint / ArchUnit / clippy / eslint rule |
| 2 | Port interfaces defined in CONSUMER-adjacent package, not in adapter | Code review + arch-review audit |
| 3 | Adapters translate external errors → domain errors at boundary | Grep for raw driver errors in app layer |
| 4 | Delivery layer is THIN: parse request → call use case → format response | No business logic in handlers |
| 5 | One BC = one deployable unit = one build module | Own go.mod / build.gradle / pyproject.toml / package.json / Cargo.toml / .csproj |
| 6 | Multi-BC: zero shared code, communication via messages only | No cross-module imports |
| 7 | OpenAPI declarations in `infra/http/openapi/` (or delivery equivalent) | devtdd HC#11 |
| 8 | Test directories mirror layer structure: `tests/unit/` (domain+app), `tests/integration/` (infra+delivery) | Test file location audit |

---

## 9. DESIGN.md §3 Generation Rule

When `arch-detail` generates DESIGN.md §3 Package Layout, it MUST:

1. Detect the project language from `ARCHITECTURE.md` or `AGENTS.md` tech stack declaration.
2. Load the corresponding layout from this file (§2–§7).
3. Produce a table mapping **every package/directory** to its layer and responsibility.
4. If the project uses Variant A vs B (Go), declare the choice explicitly.
5. If the language is not covered here, derive from §1 semantic definitions + language idioms, and document the mapping in DESIGN.md §3 for future reference.

Example output (Go):

```markdown
## §3 Package Layout

| Package | Layer | Responsibility |
|---------|-------|---------------|
| `internal/domain/order` | Domain | Order entity, OrderItem VO, OrderConfirmed event |
| `internal/port/orderrepo` | Port | OrderRepository interface (Save, GetByID, List) |
| `internal/app/order` | Application | CreateOrder, CancelOrder use cases |
| `internal/infra/postgres` | Infrastructure | OrderRepository PostgreSQL adapter |
| `internal/infra/http/handler` | Delivery | HTTP handlers + router |
| `internal/infra/http/openapi` | Delivery | OpenAPI spec declarations |
| `cmd/order-service` | Delivery | Composition root (DI wiring + server start) |
```
