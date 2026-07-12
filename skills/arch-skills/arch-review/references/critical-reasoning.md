# Critical Reasoning Patterns

5 structured patterns for challenging architectural decisions, integrated into `/arch-review` Step 8e. These patterns expose hidden risks in architectural decisions through adversarial scrutiny.

**Core philosophy**:
- Every architectural decision carries hidden assumptions — find them
- The strongest designs survive adversarial scrutiny — test them
- Failure is predictable in hindsight — simulate it now
- Evidence beats authority — demand data over convention
- The goal is not to tear down, but to **strengthen** through challenge

---

## Pattern 1: Expose Assumptions (暴露假设)

**Question:** What hidden assumption does this decision reveal? What if it's wrong?

**Process:**
1. Identify the architectural decision under scrutiny
2. List every implicit assumption (things taken for granted, not explicitly stated)
3. For each assumption, ask: "What evidence supports this? What if this assumption is false?"
4. Rate assumption risk: High (unsupported + high impact), Medium (partially supported), Low (well-supported)
5. If any assumption is unsupported, the decision needs revision

### Assumption Categories

| Category | Examples | Detection Question |
|----------|----------|-------------------|
| **Technical** | "PostgreSQL handles our scale" | Has load testing been done? |
| **Team** | "We have Go expertise" | How many team members have shipped Go in production? |
| **Business** | "Users need real-time data" | What's the actual staleness tolerance? |
| **Timeline** | "We can build this in 3 months" | Is this based on estimates or historical data? |
| **Integration** | "Service A can call Service B" | Is the API stable? What about latency? |

**Worked Example:**
```
Decision: "Use event sourcing for all state changes"

Assumptions found:
1. [Technical] Team can implement event sourcing correctly
   Evidence: No team member has done this before → HIGH RISK
2. [Business] All consumers need full audit trail
   Evidence: Only compliance needs it; other consumers need current state → MEDIUM RISK
3. [Technical] Storage cost of full event history is acceptable
   Evidence: No projection of event volume → HIGH RISK
4. [Timeline] Event sourcing doesn't add significant development time
   Evidence: Industry reports 2-3x development time increase → HIGH RISK

Recommendation: Consider CQRS without event sourcing as a simpler alternative.
Reserve event sourcing for the audit-critical aggregate only.
```

---

## Pattern 2: Argue the Opposite (论证反面)

**Question:** What's the strongest case AGAINST the current decision?

**Process:**
1. State the current decision clearly
2. Build the strongest possible argument for the opposite choice (steelmanning — best possible case)
3. Evaluate: Is the opposite argument compelling?
4. Resolution: Either revise the decision, or document WHY the original survives

### Steelman Rules

- Never use a strawman (weak version of the opposite)
- Give the opposite argument the benefit of the doubt
- Cite real-world examples where the opposite worked
- Quantify the trade-offs, don't just list pros/cons

**Worked Example:**
```
Decision: "Monorepo for all 3 bounded contexts"

Steelman for polyrepo:
- Independent versioning: each BC can evolve at its own pace
- Smaller CI/CD: changes to BC-A don't trigger BC-B's pipeline
- Clearer ownership: each team owns their repo entirely
- Industry evidence: Netflix, Amazon use polyrepo at scale

Counter-arguments for monorepo:
- Cross-BC refactoring is atomic (single commit)
- Shared tooling and CI configuration
- Team size (5 people) doesn't justify repo management overhead
- Google, Meta use monorepo at scale (different scale though)

Assessment: For team of 5 with tightly coupled BCs, monorepo survives scrutiny.
Revisit when team exceeds 15 or BCs become independently deployable.
```

---

## Pattern 3: Pre-Mortem (预验尸)

**Question:** If this project failed in 12 months, would this decision be the cause?

**Process:**
1. Imagine the project has failed spectacularly — set the date to 12 months from now
2. Brainstorm failure reasons — list top 5 plausible failure modes
3. For each reason, trace back: does the current decision contribute to that failure?
4. Define mitigations — what would prevent this failure path?

### Failure Mode Categories

| Category | Example Failures |
|----------|-----------------|
| **Technical debt** | Velocity dropped to zero, rewrite needed |
| **Operational** | On-call burnout, 3AM pages every week |
| **Team** | Key person left, no one understands the system |
| **Business** | Feature delivery too slow, lost to competitors |
| **Security** | Data breach, compliance violation |

**Worked Example:**
```
Decision: "gRPC for all inter-service communication"

Pre-mortem failures:
1. "Debugging production issues took 10x longer" → gRPC tooling less mature than REST
   Mitigation: Budget for distributed tracing (Jaeger/Zipkin) from day 1
2. "New team members took 3 months to be productive" → protobuf learning curve
   Mitigation: Invest in onboarding docs and proto linting
3. "Browser clients couldn't connect directly" → gRPC-web adds complexity
   Mitigation: Define BFF (Backend-for-Frontend) pattern for web clients

2 of 3 failures have clear mitigations. Failure #3 requires architectural decision.
Recommendation: Use gRPC for service-to-service, REST for client-facing APIs.
```

---

## Pattern 4: Red Team Attack (红队攻击)

**Question:** How could an adversary exploit this architectural weakness?

**Process:**
1. Adopt the attacker mindset — view the architecture as a target
2. Map the attack surface — entry points, trust boundaries, data flows
3. Identify the crown jewels — what data/assets are most valuable?
4. Trace attack paths — from entry to target, step by step
5. Check defenses — is there a defense at each step?

### Attack Surface Categories

| Surface | Examples | Defense Check |
|---------|----------|--------------|
| **External APIs** | REST/gRPC endpoints, webhooks | Auth, rate limiting, input validation |
| **Internal APIs** | Inter-service calls, message queues | mTLS, service mesh, authorization |
| **Data stores** | Databases, caches, file storage | Encryption, access control, audit |
| **Supply chain** | Dependencies, CI/CD, build artifacts | Signing, SBOM, vulnerability scanning |
| **Human** | Social engineering, insider threat | Least privilege, separation of duties |

**Worked Example:**
```
Decision: "Shared database schema across all services"

Attack surface:
- Service A has SQL injection vulnerability
- Attacker gains access to Service A's database connection
- Shared schema means attacker can read/write Service B's data
- No service-level isolation at the data layer

Attack path:
  User input → Service A API → SQL injection → shared DB → Service B data

Defenses missing:
  - No database-level isolation (schemas per service)
  - No column-level encryption for sensitive data
  - No query audit logging

Recommendation: Each service gets its own database schema (minimum)
or its own database instance (for high-security domains).
```

---

## Pattern 5: Audit Evidence (审计证据)

**Question:** Is this decision backed by data, or by authority/convention?

**Process:**
1. State the rationale for the decision
2. Classify the evidence type:
   - 🟢 **Data** — benchmarks, load tests, production metrics, A/B tests
   - 🟡 **Experience** — team has done this before with known outcomes
   - 🟠 **Authority** — "Google does it", "Martin Fowler recommends it"
   - 🔴 **Convention** — "industry standard", "best practice", "everyone uses it"
   - ⚫ **None** — no stated rationale
3. If evidence is Authority/Convention/None: demand data-backed validation before proceeding

### Evidence Upgrade Path

```
Convention → Authority → Experience → Data
   (weakest)                           (strongest)
```

To upgrade:
- Convention → Authority: Find a specific case study
- Authority → Experience: Has this team succeeded with this before?
- Experience → Data: Run a benchmark, load test, or spike

**Worked Example:**
```
Decision: "Use Kubernetes for container orchestration"

Evidence check: "Kubernetes is the industry standard" → Convention (🔴)

Missing evidence:
- What's the actual scale? (3 services, 5 instances → K8s is overkill)
- What's the team's K8s experience? (None → 6-month learning curve)
- What's the operational budget? (No dedicated SRE → who maintains K8s?)

Recommendation: Start with Docker Compose or a PaaS (Fly.io, Railway).
Upgrade to K8s when:
- Service count > 10, OR
- Need auto-scaling based on custom metrics, OR
- Team has dedicated infrastructure engineer
```

---

## When-to-Apply Matrix

| Scenario | P1 Expose | P2 Opposite | P3 Pre-Mortem | P4 Red Team | P5 Evidence |
|----------|:---------:|:-----------:|:-------------:|:-----------:|:-----------:|
| **Score < 60 (Critical verdict)** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Critical severity AD** | ✅ | | ✅ | | |
| **Technology selection** | ✅ | ✅ | | | ✅ |
| **BC boundary decision** | | ✅ | ✅ | | |
| **Security-sensitive design** | | | | ✅ | |
| **Team disagreement** | | ✅ | | | |
| **"Best practice" justification** | | | | | ✅ |
| **New project kickoff** | | | ✅ | | |
| **Post-incident analysis** | ✅ | | ✅ | ✅ | |
| **Pre-production review** | | | ✅ | ✅ | |

---

## Critique Severity Guide

| Level | Symbol | Meaning | Action |
|-------|--------|---------|--------|
| **High Risk** | 🔴 | Decision likely to cause project failure or major rework | Block progress until addressed |
| **Medium Risk** | 🟡 | Decision has unvalidated assumptions that may cause problems | Address in next iteration |
| **Low Risk** | 🟢 | Decision survives scrutiny, minor improvements possible | Document and proceed |

---

## Decision Inventory Template

Before applying patterns, inventory the key decisions in the target deliverable:

| # | Decision | Source | Risk Level |
|---|----------|--------|-----------|
| D1 | <decision description> | <file:section> | High/Medium/Low |
| D2 | ... | ... | ... |

Prioritize scrutiny: BC boundaries > persistence technology > communication patterns > GoF patterns > naming.
