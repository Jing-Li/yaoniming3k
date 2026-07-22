# Research Methodology — Scanning Checklists

## Domain Type: Data-Intensive Systems
- [ ] Data modeling conventions (relational vs document vs graph)
- [ ] Query patterns (OLTP vs OLAP vs HTAP)
- [ ] Consistency requirements (strong vs eventual)
- [ ] Scaling patterns (sharding, partitioning, replication)

## Domain Type: Real-Time / Event-Driven Systems
- [ ] Message broker conventions (Kafka vs RabbitMQ vs NATS)
- [ ] Event schema standards (Avro vs Protobuf vs JSON Schema)
- [ ] Ordering guarantees (per-partition vs global)
- [ ] Exactly-once vs at-least-once semantics

## Domain Type: User-Facing Web Applications
- [ ] API design norms (REST vs GraphQL vs tRPC)
- [ ] Auth patterns (OAuth2 vs OIDC vs session)
- [ ] Frontend architecture (SPA vs SSR vs islands)
- [ ] Real-time update patterns (WebSocket vs SSE vs polling)

## Domain Type: Platform / API Products
- [ ] API versioning strategies
- [ ] Rate limiting conventions
- [ ] SDK/API client expectations
- [ ] Developer onboarding patterns

## General Technology Consensus Checklist
- [ ] Database: what does the community use for this workload?
- [ ] Cache: is caching expected? What layer?
- [ ] Search: full-text search requirements?
- [ ] File storage: object store vs filesystem?
- [ ] Deployment: container vs serverless vs VM?
- [ ] Observability: logging/metrics/tracing standards?
