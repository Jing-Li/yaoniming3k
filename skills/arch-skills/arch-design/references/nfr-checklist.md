# NFR (Non-Functional Requirements) Checklist

Structured checklist for capturing quality attributes before boundary design. Use during `/arch-design` Step 2.5.

## 1. Scalability

| Question | Metric Template |
|----------|----------------|
| Concurrent users/connections? | `N at peak` |
| Data growth rate? | `N GB/month` |
| Peak throughput? | `N req/s` or `N events/s` |
| Horizontal scaling? | `Yes/No` |

**Architecture implications:** High concurrency → CQRS, caching. Rapid growth → partitioning. Horizontal → stateless design.

## 2. Performance

| Question | Metric Template |
|----------|----------------|
| p50/p95/p99 latency? | `< N ms` |
| Batch throughput? | `N records in < N seconds` |
| Cold start tolerance? | `< N seconds` |

**Architecture implications:** Tight p95 → caching, connection pooling. Batch → bulk port, streaming adapter.

## 3. Availability

| Question | Metric Template |
|----------|----------------|
| Uptime SLA? | `99.9% / 99.95% / 99.99%` |
| RTO / RPO? | `< N minutes` |
| Failover strategy? | `Active-passive / Active-active` |

**Architecture implications:** High availability → redundancy, health checks. Tight RPO → sync replication.

## 4. Security

| Question | Metric Template |
|----------|----------------|
| Auth mechanism? | `JWT / OAuth2 / mTLS` |
| Authorization model? | `RBAC / ABAC` |
| Encryption at rest/transit? | `AES-256 / TLS 1.3` |
| Compliance? | `GDPR / SOC2 / none` |
| Audit logging? | `All writes / admin only` |

**Architecture implications:** Auth → port + decorator. Encryption → adapter concern. Audit → Observer pattern.

## 5. Cost

| Question | Metric Template |
|----------|----------------|
| Monthly budget? | `< $N/month` |
| Team size? | `N developers` |
| Deploy frequency? | `N times/day/week` |

**Architecture implications:** Small team → monolith. Tight budget → serverless. High frequency → feature flags.

## Recording in ARCHITECTURE.md

```markdown
## NFR Summary

| Dimension | Key Requirement | Metric | Architecture Response |
|-----------|----------------|--------|----------------------|
| Scalability | ... | ... | ... |
| Performance | ... | ... | ... |
| Availability | ... | ... | ... |
| Security | ... | ... | ... |
| Cost | ... | ... | ... |

### Open Questions
- [ ] <dimension>: <unanswered question>
```
