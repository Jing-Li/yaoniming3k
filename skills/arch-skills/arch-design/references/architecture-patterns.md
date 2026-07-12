# Architecture Patterns Decision Matrix

Comparison of 6 architecture patterns with decision scoring for `/arch-design` Step 2.6.

## Pattern Comparison

| Pattern | Best For | Anti-Indicator | Team Size | Deploy Model |
|---------|----------|---------------|-----------|-------------|
| **Monolith** | Simple domain, rapid prototyping | Team >8, independent scaling needed | 1-5 | Single artifact |
| **Modular Monolith** | Multiple BCs, shared deployment | Need independent deploy | 5-15 | Single artifact, module boundaries |
| **Microservices** | Independent deploy, large teams | Small team, no CI/CD maturity | 15+ | Multiple artifacts |
| **Event-Driven** | Async workflows, temporal decoupling | Simple CRUD, team unfamiliar with eventual consistency | Any | Event backbone |
| **Serverless** | Variable load, cost-optimized | Long-running processes, cold start sensitive | Any | Function deployments |
| **CQRS** | Read/write asymmetry (100:1+ ratio) | Simple CRUD, team unfamiliar with eventual consistency | Any | Separate read/write paths |

## Decision Matrix

Score each pattern (0-3) against your project's needs. Highest total = recommended starting point.

| Criterion | Weight | Monolith | Modular Mono | Microservices | Event-Driven | Serverless | CQRS |
|-----------|--------|----------|-------------|---------------|-------------|-----------|------|
| Team size match | 2x | 3 if ≤5 | 3 if 5-15 | 3 if 15+ | 2 if any | 2 if any | 1 if any |
| Deploy independence needed | 2x | 0 | 1 | 3 | 2 | 3 | 2 |
| Domain complexity | 1x | 1 if simple | 3 if multi-BC | 2 if multi-BC | 1 if async | 1 if simple | 2 if asymmetric |
| Consistency requirements | 2x | 3 if strong | 3 if strong | 1 if eventual | 1 if eventual | 2 if any | 1 if eventual |
| Operational maturity | 1x | 3 if low | 2 if medium | 0 if low | 1 if medium | 3 if low | 1 if medium |
| Cost sensitivity | 1x | 2 | 2 | 1 | 1 | 3 | 1 |

## Clean Architecture Mapping

| Pattern | Domain Layer | Use Cases | Adapters | Special Considerations |
|---------|-------------|-----------|----------|----------------------|
| Monolith | Standard | Standard | Standard | Module boundaries via packages |
| Modular Monolith | Per-module domain | Per-module use cases | Shared infra | Module API surface = internal ports |
| Microservices | Per-service BC | Per-service | Per-service + API gateway | Inter-service communication port |
| Event-Driven | Event + handler entities | Event orchestrators | Event bus adapter | Event sourcing optional, saga port |
| Serverless | Standard | Handler = use case | Cloud SDK adapters | Cold start awareness, stateless |
| CQRS | Command + Query models | Command handlers + Query handlers | Separate read/write adapters | Eventual consistency, projection port |

## ADR Template

Use this template when recording the pattern decision:

```markdown
## ADR-NNN: Architecture Pattern Selection

**Status:** Accepted
**Date:** YYYY-MM-DD

### Context
- Team size: N
- Deploy model: ...
- Key NFR: ...

### Decision
Selected **<pattern>** based on decision matrix scoring.

| Pattern | Score |
|---------|-------|
| <selected> | NN (highest) |
| <runner-up> | NN |

### Consequences
- (+) <benefit 1>
- (+) <benefit 2>
- (-) <trade-off 1>
- (!) <risk requiring mitigation>

### Alternatives Considered
- <alternative 1>: rejected because ...
- <alternative 2>: rejected because ...
```
