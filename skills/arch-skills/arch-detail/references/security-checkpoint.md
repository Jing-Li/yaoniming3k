# Security Checkpoint

Pre-implementation security review checklist for `/arch-detail` Step 4d. Run after completing each module's design. Security gaps are **blockers** — resolve before `/devtdd`.

---

## 0. STRIDE Threat Analysis (Design-Level)

Before running the checklist below, perform a STRIDE threat analysis for this module. For each component in the module, evaluate the six threat categories and document design-level mitigations.

| Threat Category | Design Question | Mitigation Pattern |
|----------------|----------------|-------------------|
| **S**poofing | Can an attacker impersonate a user or service? | Authentication mechanism (JWT/mTLS), service identity |
| **T**ampering | Can an attacker modify data in transit or at rest? | TLS, message signing, audit log |
| **R**epudiation | Can a user deny an action they performed? | Audit log with tamper-evidence (append-only) |
| **I**nformation Disclosure | Can an attacker read data they shouldn't? | Authorization checks, encryption at rest, field-level masking |
| **D**enial of Service | Can an attacker exhaust system resources? | Rate limiting, circuit breaker, request timeout, bulkhead |
| **E**levation of Privilege | Can a low-privilege user gain higher access? | Role-based access control, least-privilege principle, scope validation |

### STRIDE Output Template

Record in module.md after §5 GoF Patterns:

```markdown
## STRIDE Threat Analysis

| Component | Threat | Severity | Mitigation | Design Pattern |
|-----------|--------|----------|------------|----------------|
| API Gateway | Spoofing | High | JWT validation | Decorator (AuthMiddleware) |
| Order UseCase | Tampering | Medium | Audit log on state changes | Observer (AuditEventPublisher) |
| Payment Adapter | DoS | High | Circuit breaker + timeout | Circuit Breaker pattern |
```

### Security Design Patterns

These patterns complement GoF patterns (module.md §5) with security-specific concerns:

| Pattern | When to Apply | Implementation Location |
|---------|---------------|------------------------|
| **Circuit Breaker** | Calling external services (APIs, message brokers) | Infrastructure adapter — wrap external call |
| **Rate Limiter** | Public endpoints, expensive operations | Delivery layer — middleware/decorator |
| **Audit Trail** | State-changing operations, admin actions | Domain event + infrastructure subscriber |
| **Input Sanitizer** | User-generated content, file uploads | Adapter boundary — before use case |
| **Token Bucket** | Fine-grained per-user/per-endpoint throttling | Delivery layer — configurable per route |
| **Bulkhead** | Multi-tenant or multi-service isolation | Infrastructure — separate connection pools |
| **Outbox** | Reliable event publishing with exactly-once semantics | Domain + infrastructure — transactional outbox table |

---

## 1. Input Validation

- [ ] All input types defined (string length, numeric range, format regex)
- [ ] Validation occurs at **adapter boundary** (before entering use case)
- [ ] Domain types use value objects with built-in validation (no raw primitives)
- [ ] File uploads: type whitelist, size limit, virus scan requirement defined

## 2. Authentication & Authorization

- [ ] Authentication mechanism defined (JWT / OAuth2 / API Key / mTLS)
- [ ] Authorization checks in **use case layer** (not adapter, not domain)
- [ ] Default-deny policy: unauthenticated requests rejected before reaching business logic
- [ ] Role/permission model documented in LANGUAGE.md

## 3. Data Protection

- [ ] Encryption at rest specified for sensitive data (PII, credentials, financial)
- [ ] Encryption in transit specified (TLS version, certificate management)
- [ ] No hardcoded secrets in design (env vars or secrets manager only)
- [ ] Audit logging defined for sensitive operations (writes, admin actions)
- [ ] Data retention and deletion policy defined

## 4. Error Handling

- [ ] Error responses use RFC 7807 Problem Details format
- [ ] No stack traces or internal paths exposed in error responses
- [ ] Driver-specific errors translated at adapter boundary (no `pgx.ErrNoRows` leaking)
- [ ] Rate limiting defined for public endpoints

## 5. Dependency Security

- [ ] All third-party dependencies pinned to specific versions
- [ ] CVE scanning in CI pipeline specified
- [ ] No unused dependencies in module design
- [ ] Supply chain security: verified sources, signed packages

## Integration with Module Design

After completing a module.md, run this checkpoint. Record results in the module file:

```markdown
## Security Checkpoint (v3.1.0+)

| Area | Status | Notes |
|------|--------|-------|
| Input Validation | ✅ / ❌ | ... |
| Auth | ✅ / ❌ | ... |
| Data Protection | ✅ / ❌ | ... |
| Error Handling | ✅ / ❌ | ... |
| Dependencies | ✅ / ❌ | ... |
```

Mark security-related tasks in DESIGN.md §5 with 🔒 prefix (e.g., "🔒 Implement JWT middleware").
