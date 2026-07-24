# Research Brief Examples

Golden examples of research briefs following the Standard Output format defined in SKILL.md.

---

## Example 1: Event-Driven Order Processing System

**Context**: User is building an order processing system with real-time inventory sync across warehouses.

### research/research.md

```markdown
# Research Brief: Order Processing System

## Domain Conventions
- Order lifecycle follows state machine pattern (Created → Paid → Shipped → Delivered → Closed)
- Inventory reservation uses "hold-then-confirm" pattern (reserve on order creation, confirm on payment)
- Compensation pattern (Saga) is standard for cross-warehouse coordination
- Idempotency keys are expected on all write operations

## Technology Consensus
| Concern | Community Default | Alternatives |
|---------|------------------|--------------|
| Message Broker | Apache Kafka | RabbitMQ (simpler), NATS (lighter) |
| Event Schema | Avro + Schema Registry | Protobuf (smaller), JSON Schema (simpler) |
| Ordering | Per-partition (by order_id) | Global ordering (rare, expensive) |
| Delivery | At-least-once + idempotent consumer | Exactly-once (Kafka transactions) |
| Database | PostgreSQL (orders) + Redis (inventory cache) | CockroachDB (distributed) |

## Competitor Landscape
| System | Architecture Style | Notable Choice |
|--------|-------------------|----------------|
| Shopify | Modular monolith → services | Event-driven inventory, eventual consistency |
| WooCommerce | Monolith + plugins | Synchronous inventory, simple but limited |
| Custom (mid-market) | Microservices + Kafka | Saga for fulfillment, CQRS for read models |

## Community Pain Points
- Inventory overselling under concurrent orders (most common complaint)
- Event ordering lost when scaling Kafka partitions
- Saga timeout handling is poorly documented in most tutorials
- Schema evolution breaks downstream consumers silently

## Open Questions for Alignment
- [ ] Consistency requirement: Is 2-second inventory lag acceptable? (affects architecture complexity)
- [ ] Scale: Expected orders/second at peak? (affects partitioning strategy)
- [ ] Multi-warehouse: Can one order split across warehouses? (affects Saga vs simple flow)
```

### Why this is a good brief
- **Domain Conventions**: States what the industry does, not what the user should do
- **Technology Consensus**: Table format, shows default + alternatives without recommending
- **Competitor Landscape**: Real systems with observable architecture choices
- **Pain Points**: Recurring issues that will inform design decisions
- **Open Questions**: Directly feed into arch-align's grilling dialogue

---

## Example 2: Developer API Platform

**Context**: User is building a public API platform for third-party integrations.

### research/research.md

```markdown
# Research Brief: Developer API Platform

## Domain Conventions
- API versioning: URL path (`/v1/`, `/v2/`) is most common; header-based is "purer" but less discoverable
- Authentication: OAuth2 client_credentials for server-to-server; API keys for simple integrations
- Rate limiting: Token bucket per API key, communicated via `X-RateLimit-*` headers
- Error format: RFC 7807 Problem Details is emerging standard
- Pagination: Cursor-based preferred over offset for large datasets

## Technology Consensus
| Concern | Community Default | Alternatives |
|---------|------------------|--------------|
| API Style | REST + OpenAPI 3.x | GraphQL (flexible queries), gRPC (internal) |
| Auth | OAuth2 + JWT | API keys (simpler), mTLS (high security) |
| Rate Limiting | Redis-backed token bucket | In-memory (single node), Kong/APISIX (gateway) |
| Documentation | OpenAPI → generated portal | Manual docs (drifts), GraphQL Playground |
| SDK Generation | OpenAPI Generator / Speakeasy | Manual SDKs (per-language) |

## Competitor Landscape
| Platform | Versioning | Auth | Notable |
|----------|-----------|------|---------|
| Stripe | Date-based headers | API keys + OAuth | Idempotency keys on all writes |
| GitHub | URL path + media type | OAuth2 + fine-grained tokens | GraphQL + REST dual API |
| Twilio | URL path (/v1/) | Basic auth (key:secret) | Auto-generated SDKs for 7 languages |

## Community Pain Points
- Breaking changes without proper deprecation cycle
- Rate limit headers inconsistent across providers
- SDK drift: generated clients lag behind API changes
- Sandbox/test environment data doesn't match production behavior
- Webhook reliability: retries without idempotency cause duplicates

## Open Questions for Alignment
- [ ] Versioning strategy: URL path vs date-based? (affects long-term maintenance)
- [ ] SDK commitment: How many languages at launch? (affects OpenAPI-first vs code-first)
- [ ] Sandbox: Full environment simulation or mock responses? (affects infra complexity)
```

### Why this is a good brief
- Follows the exact output format from SKILL.md
- Each section provides **signal** (what the industry does) not **decision** (what user should do)
- Open Questions are phrased as binary/trade-off choices suitable for AskUserQuestion in arch-align
- Competitor choices are observable facts, not opinions
