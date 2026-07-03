# Arch-Review — Reference

Detailed audit checklists, scoring rubric, per-language red flags, and refactoring templates for the `arch-review` skill. Loaded only when needed (progressive disclosure from [SKILL.md](SKILL.md)).

---

## 1. Audit Checklist

### Phase Scope Guide

| Rule Group | Phase 2 (ARCHITECTURE.md) | Phase 3 (DESIGN.md) | Notes |
|------------|:---:|:---:|-------|
| 1.1 Clean Architecture | ✅ | ✅ | Dependency flow, DIP, port placement |
| 1.2 PoEAA (Persistence) | — | ✅ | DDL, Data Mapper, ORM separation |
| 1.3 GoF Pattern Rules | — | ✅ | Pattern application, anti-pattern detection |
| 1.4 Naming & Language Drift | ✅ | ✅ | Cross-reference LANGUAGE.md |
| 1.5 Documentation Drift Detection | — | ✅ | Cross-check DESIGN.md Task Summary ↔ actual code |
| 1.6 Cross-Document Consistency | ✅ | ✅ | Inter-document staleness detection (ARCH↔SYSTEM, ARCH↔Code, LANG↔All, Cross-cutting docs↔BC docs) |

When `PHASES.md` indicates only Phase 2 is complete, focus on 1.1, 1.4, and 1.6. When Phase 3 is also complete, apply all rule groups.

### 1.1 Clean Architecture Rules (Phase 2 + 3)

| # | Rule | Detection | Card |
|---|------|-----------|------|
| C1 | Domain has zero outbound imports to outer layers | Grep `domain/**` for imports of `infrastructure/`, `proto/`, framework packages | 🔴 |
| C2 | Use Case depends only on Domain + Ports | Grep `usecase/**` for direct DB / HTTP client / SDK imports | 🔴 |
| C3 | Ports defined by consumer, not adapter | Locate interface declaration; if in `infrastructure/` → red | 🔴 |
| C4 | Composition root only in `cmd/` / `bootstrap/` | Search for `new(...)` of adapters outside composition root | 🟡 |
| C5 | gRPC/HTTP handlers convert proto↔domain at boundary | Inspect handler files for domain types in proto signatures | 🟡 |
| C6 | No use case directly instantiates an adapter | Grep `usecase/**` for `&PostgresXxx{}` / `new XxxAdapter(...)` | 🔴 |

### 1.2 PoEAA (Persistence) Rules (Phase 3)

| # | Rule | Detection | Card |
|---|------|-----------|------|
| P1 | Domain class is **not** a JPA `@Entity` / SQLAlchemy `Base` / pydantic ORM model | Inspect domain classes for ORM annotations or base classes | 🔴 |
| P2 | Persistence-side class (`XxxJpaEntity`, `XxxRow`) exists separately | Each domain entity that is persisted should have a paired infra type | 🟡 |
| P3 | Mapper layer translates row ↔ domain | Look for `XxxMapper`, `toDomain`, `toRow` functions | 🟡 |
| P4 | Repository returns Domain types, not rows | Inspect repository return types | 🔴 |
| P5 | Transactions controlled in Use Case via Unit-of-Work port | If transactions are in adapters, business invariants leak | 🟡 |
| P6 | Driver-specific errors translated at adapter boundary | Search for `pgx.Err…` / `sql.ErrNoRows` / `IntegrityError` leaking past port | 🟡 |

### 1.3 GoF Pattern Rules (Phase 3)

| # | Rule | Detection | Card |
|---|------|-----------|------|
| G1 | Long `if/else` / `switch` over a type-tag → Strategy or State | Functions with > 4 branches keyed on enum/string | 🟡 |
| G2 | Factory used when aggregate has invariants spanning many fields | Construction logic duplicated across 2+ call sites | 🟡 |
| G3 | Cross-cutting concerns wrapped via Decorator on a port | Tracing / retry / auth code inlined into use case | 🟡 |
| G4 | Domain events go through an Observer / Pub-Sub port | Direct calls to message broker SDK from use case | 🔴 |
| G5 | No "pattern for the sake of pattern" | Singletons / abstract factories with single implementation and no foreseen variability | 🟡 |

### 1.4 Naming & Language Drift (Phase 2 + 3)

| # | Rule | Detection | Card |
|---|------|-----------|------|
| N1 | Every class / table / field / method appears in `LANGUAGE.md` (or its mapping table) | Cross-reference identifier list against dictionary | 🟡 |
| N2 | English mappings consistent (e.g., 灵簿 always `Census`, never `Registry`) | Search for synonym drift | 🟡 |
| N3 | Bounded context names not crossed (no `census` package importing `intent` internals) | Inspect cross-context imports | 🔴 |
| N4 | **Go 文件名必须与主 struct 名对齐**：struct `ABody` → 文件 `abody.go`；struct `AManifest` → 文件 `amanifest.go`；测试文件同理（`abody_test.go`）。命名规范约定的前缀（如 A 前缀）必须反映在文件名中 | Grep 所有 Go 源文件：提取主 struct 名，比较小写形式与文件名是否一致 | 🟡 |
| N5 | **docs/design/modules/ 目录名必须与 domain struct 名对齐**：struct `ABody` → 目录 `abody/`；struct `AManifest` → 目录 `amanifest/`。使用小写前缀形式 | Compare `ls docs/design/modules/` against domain struct names from LANGUAGE.md | 🟡 |

### 1.5 Documentation Drift Detection (Phase 3)

| # | Rule | Detection | Card |
|---|------|-----------|------|
| D1 | DESIGN.md Task Summary status matches actual code | Tasks marked "complete" must have corresponding non-stub source files; implemented code must have a matching task | 🟡 |
| D2 | DESIGN.md §5 Task Summary not stale | Task table reflects current implementation state (no ghost tasks, no phantom completions) | 🟡 |
| D3 | Architecture diagrams match actual dependency flow | Mermaid diagrams in ARCHITECTURE.md reflect current import graph and adapter/constructor names | 🟡 |

### 1.6 Cross-Document Consistency (All Phases)

These rules catch staleness caused by documents evolving independently. Apply during Step 5 (Cross-Document Consistency Check).

| # | Rule | Detection | Card |
|---|------|-----------|------|
| X1 | ARCHITECTURE.md ↔ SYSTEM.md Communication Matrix | Every cross-BC arrow in sequence diagrams and Event Contract table rows must use a protocol declared in SYSTEM.md §3 | 🔴 |
| X2 | ARCHITECTURE.md ↔ Code adapter names | Adapter class names, constructor names, and port interface names in Mermaid diagrams must match current code | 🟡 |
| X3 | DESIGN.md ↔ ARCHITECTURE.md package structure | Package layout in DESIGN.md §3 must match the dependency structure shown in ARCHITECTURE.md §1 | 🟡 |
| X4 | LANGUAGE.md ↔ All docs adapter/port names | Adapter/port names registered in LANGUAGE.md must match names used in ARCHITECTURE.md, DESIGN.md, and module.md files | 🟡 |
| X5 | ARCHITECTURE.md Consumers / Open Questions vs SYSTEM.md | Every “Consumers” column entry and Open Questions item in ARCHITECTURE.md that references cross-BC communication MUST use a protocol declared in SYSTEM.md §3. Stale references to deprecated protocols (e.g., gRPC when matrix says MQ-only) are flagged | 🟡 |
| X6 | `docs/agents/domain.md` file structure ↔ actual BC docs | The file structure diagram in `docs/agents/domain.md` must reflect each BC’s actual docs/ contents (phases completed, directories present). Compare listed files against `find <bc>/docs -type f` | 🟡 |
| X7 | `docs/arch/SYSTEM.md` Last-updated staleness | SYSTEM.md “Last updated” comment must describe the most recent change, not a stale historical one. If the comment references a change that was later superseded, flag it | 🟡 |
| X8 | **BC `README.md` ↔ Code consistency** | Each BC's README.md must match actual code: (a) directory tree matches current `ls internal/` output (no ghost directories), (b) architecture/component diagrams match current domain struct names and responsibilities, (c) config/env var defaults match `config.go` actual defaults. Run `ls -d internal/*/` and compare against README tree | 🟡 |

---

## 2. Scoring Rubric (out of 100)

### 2.1 Axes

| Axis | Weight | Source |
|------|--------|--------|
| Dependency Rule | 30 | C1, C2, C3, C6 |
| Domain Purity | 25 | C1, P1, framework annotations check |
| Persistence Decoupling | 20 | P1–P6 |
| Pattern Application | 15 | G1–G5 |
| Naming Alignment | 10 | N1–N5, X1–X8 |

### 2.2 Deduction policy

For each axis, start at the full weight. Deduct:

- **Critical violation (🔴)** in that axis → −50 % of the axis weight.
- **Warning (🟡)** → −10 % of the axis weight, capped at −50 % per axis.
- Floor each axis at 0.

### 2.3 Verdict thresholds

| Total | Verdict | Action |
|-------|---------|--------|
| ≥ 85 | 🟢 Healthy | Mergeable; address yellows in follow-up |
| 60–84 | 🟡 At Risk | Mergeable only after critical fixes |
| < 60 | 🔴 Critical | Block merge; refactor required |

### 2.4 Worked example

> 1 Critical in Dependency Rule (−15), 2 Warnings in Persistence (−4), 1 Warning in Naming (−1).
> Score = (30−15) + 25 + (20−4) + 15 + (10−1) = **80 — 🟡 At Risk**.

---

## 3. Per-Language Red Flags

### 3.1 Go

```bash
# Domain pollution
grep -rn "google.golang.org/grpc\|gorm.io\|gin-gonic" domain/         # ❌
grep -rn "proto/" domain/                                              # ❌

# Port in wrong place
grep -rn "^type .* interface" internal/infrastructure/                 # ❌ (should be in usecase/)

# Driver error leak
grep -rn "sql.ErrNoRows\|pgx.ErrNoRows" internal/usecase/              # ❌

# Missing context
grep -rnP "func \([^)]+\) \w+\([^)]*\) " internal/usecase/ | grep -v "context.Context"   # ⚠
```

### 3.2 Java

```bash
# Domain has framework annotations
grep -rn "@Entity\|@Component\|@Service\|@Autowired\|@Table" src/main/java/.../domain/  # ❌

# Use case touches JPA repo directly
grep -rn "JpaRepository\|EntityManager" src/main/java/.../application/                  # ❌

# Missing ArchUnit
find src/test -name "*ArchTest*"                                                         # ⚠ if absent
```

### 3.3 Python

```bash
# Domain inherits from ORM
grep -rn "declarative_base\|DeclarativeBase\|Base = " domain/                            # ❌
grep -rn "from sqlalchemy" domain/                                                       # ❌

# abc.ABC instead of Protocol
grep -rn "class .*\(ABC\)" domain/                                                       # ⚠ (prefer typing.Protocol)

# Pydantic in domain entity
grep -rn "from pydantic" domain/                                                         # ⚠ (acceptable at boundaries only)
```

---

## 4. Refactoring Diff Templates

### 4.1 Data Mapper split (Java)

**Before:**
```java
@Entity @Table(name = "orders")
public class Order {
    @Id @GeneratedValue Long id;
    @Column BigDecimal total;
    @ManyToOne Customer customer;
}
```

**After:**
```java
// domain/Order.java
public record Order(OrderId id, CustomerId customer, Money total) {
    public Order {
        if (total == null || total.isNegative())
            throw new IllegalArgumentException("invalid total");
    }
}

// infrastructure/persistence/OrderJpaEntity.java
@Entity @Table(name = "orders")
class OrderJpaEntity {
    @Id Long id;
    BigDecimal total;
    Long customerId;
}

// infrastructure/persistence/OrderMapper.java
@Mapper interface OrderMapper {
    Order toDomain(OrderJpaEntity e);
    OrderJpaEntity toJpa(Order d);
}
```

### 4.2 Strategy split (long if/else, Go)

**Before:**
```go
func (uc *Charge) Apply(o Order) Money {
    switch o.Channel {
    case "card":   return o.Total.Mul(0.97)
    case "wechat": return o.Total.Mul(0.985)
    case "alipay": return o.Total.Mul(0.985)
    default:       return o.Total
    }
}
```

**After:**
```go
// domain/pricing.go
type FeeStrategy interface {
    Apply(total Money) Money
}

// internal/infrastructure/pricing/card.go
type CardFee struct{}
func (CardFee) Apply(t Money) Money { return t.Mul(0.97) }

// internal/usecase/order/charge.go
type Charge struct {
    fees map[Channel]FeeStrategy   // injected at composition root
}
func (uc *Charge) Apply(ctx context.Context, o Order) Money {
    return uc.fees[o.Channel].Apply(o.Total)
}
```

### 4.3 ISP port split

**Before:**
```go
type CensusStore interface {
    Save(ctx context.Context, e AgentEntry) error
    List(ctx context.Context, f Filter) ([]AgentEntry, error)
    Sweep(ctx context.Context, before time.Time) (int, error)
}
```

**After:**
```go
type CensusWriter interface {
    Save(ctx context.Context, e AgentEntry) error
}
type CensusReader interface {
    List(ctx context.Context, f Filter) ([]AgentEntry, error)
}
type CensusSweeper interface {
    Sweep(ctx context.Context, before time.Time) (int, error)
}
```

### 4.4 Port-in-adapter relocation

**Before** (`internal/infrastructure/postgres/store.go`):
```go
package postgres

type CensusStore interface { ... }     // ❌ port in adapter package

type pgStore struct{ db *sql.DB }
func (s *pgStore) Save(...) { ... }
```

**After** — port moves to consumer (use case package):
```go
// internal/usecase/census/ports.go
package census

type Writer interface { Save(...) }     // ✅ port owned by consumer

// internal/infrastructure/postgres/census_store.go
package postgres

type CensusStore struct{ db *sql.DB }
func (s *CensusStore) Save(...) { ... } // implements census.Writer implicitly
```

---

## 5. Output Discipline

- Default mode is **read-only**. Never call Edit/Write unless the user explicitly authorizes "apply / fix / 执行重构".
- All diffs are rendered inside fenced ` ```diff ` blocks for copy-paste.
- Cite the source rule (`Clean Arch §11`, `PoEAA Data Mapper`, `GoF Strategy`) on each Critical finding.
- Do not propose a refactor without naming the **pattern** behind it.
- If the codebase already passes (score ≥ 95), say so plainly — do not invent violations.

---

## 6. Clarification Protocol

If scope is ambiguous (e.g., monorepo with multiple bounded contexts), ask exactly one question and wait. Examples:

> "The repo contains 3 bounded contexts (`census`, `intent`, `imprint`). Which one should I audit, or all three? — Pick one."

> "No `ARCHITECTURE.md` was found. Should I (a) halt and ask you to run `/arch-design` first, or (b) audit only against `LANGUAGE.md` (lower confidence)? — Pick one."

---

## 7. Route Decision Matrix (分流决策矩阵)

Every Architecture Debt item MUST be assigned exactly one Route. Use this table — route by **document ownership**, not by problem type:

| Finding Type | Route | Document Owner | Example |
|-------------|-------|---------------|--------|
| Terminology drift / BC boundary shift / glossary gap | `/arch-align` | LANGUAGE.md, CONTEXT.md | Code uses "Registry" but LANGUAGE.md says "Census" |
| ARCHITECTURE.md inconsistency / sequence diagram drift / port table mismatch | `/arch-design` | ARCHITECTURE.md, SYSTEM.md | ARCHITECTURE.md says "Engine constructs outbox" but code says "ABody RunLoop" |
| Structural violation: DIP / package layout / port placement | `/arch-design` | ARCHITECTURE.md | Domain imports infrastructure package |
| Design gap: missing interface / missing DDL / module omission | `/arch-detail` | DESIGN.md, module.md, interfaces/ | No Data Mapper for a persisted entity |
| Code implementation issue: missing file / missing test / TODO stub | `/devtdd` | source code, test files | Port interface has no adapter implementation |
| Skill self-defect: checklist missing a rule / rubric gap | `/arch-review-self` | REVIEW.md, reference.md | No check for Go `embed` misuse in §1.1 |

### Priority When Multiple Routes Apply

If a finding could match multiple routes, pick the **earliest phase** that can resolve it:

`/arch-align` (Phase 1) > `/arch-design` (Phase 2) > `/arch-detail` (Phase 3) > `/devtdd` (Implementation)

The `/arch-review-self` route is orthogonal — it applies when arch-review itself failed to detect the issue in a prior run.

### Route Tag Format

Always use backtick-wrapped skill name with leading slash: `` `/devtdd` ``

---

## 8. Root Cause Analysis Template (根因分析模板)

Every Architecture Debt item MUST include a Root Cause Analysis answering: **"Why was this not caught by the phase that should have caught it?"**

### Structured Analysis Format

```
Root Cause Analysis:
  Missed By:    <phase/skill that should have caught this>
  Miss Reason:  <one of the categories below>
  Evidence:     <specific gap in the originating skill's output>
  Correction:   <what the originating skill should add/change>
```

### Miss Reason Categories

| Category | Description | Example |
|----------|-------------|---------|
| **Checklist Gap** | The originating skill's checklist does not cover this rule | arch-detail reference.md has no rule for Go `embed` in domain |
| **Scope Blind Spot** | The skill's scope explicitly excludes this area | arch-align only covers terminology, not structural rules |
| **Naming Not Covered** | LANGUAGE.md lacks the term or its banned synonyms | "Registry" used in code but LANGUAGE.md never listed it as banned |
| **Rule Too Vague** | The rule exists but is ambiguous enough to miss the case | "No framework pollution" doesn't specify Go embed as framework |
| **Cross-Cutting Miss** | The finding spans multiple phases, none owns it fully | Port placement is both arch-design (boundary) and arch-detail (interface) |
| **Regression** | Previously caught and fixed, but the fix was reverted | devtdd implemented correctly, later change reintroduced the violation |

### Special Case: First Review

On the first review (no prior REVIEW.md), all findings default to:
- Missed By: the phase most relevant to the finding
- Miss Reason: Checklist Gap (assume the checklist hasn't been battle-tested yet)

---

## 9. Architecture Debt Item Template

Full structure for each AD entry in REVIEW.md:

```markdown
### AD-NNN: <Short Title>

| Field | Value |
|-------|-------|
| **ID** | AD-NNN (sequential, never reused) |
| **Severity** | 🔴 Critical / 🟡 Warning |
| **Route** | `/arch-align` \| `/arch-design` \| `/arch-detail` \| `/devtdd` \| `/arch-review-self` |
| **Violation IDs** | R-x, Y-x (cross-reference to audit report sections 2 & 3) |
| **Location** | `path/to/file:line-range` |
| **Description** | One-sentence description of the architectural finding |
| **Root Cause Analysis** | Why was this missed by the originating phase? (see §8) |
| **Missed By** | The skill/phase that should have caught this |
| **Miss Reason** | Category from §8 table |
| **Status** | 🆕 New / 🔄 Recurring / 🔧 In Progress / ✅ Resolved |
| **First Seen** | v<N> (YYYY-MM-DD) |
| **Last Seen** | v<N> (YYYY-MM-DD) |
| **Suggested Action** | Concrete next step for the target skill to execute |
```

### Status Lifecycle

```
🆕 New → 🔄 Recurring (still open in next review)
       → 🔧 In Progress (target skill is actively working on it)
       → ✅ Resolved (verified fixed in next review)
       → 🔄 Recurring (regression — was resolved, now reappeared)
```

### ID Assignment Rules

- IDs are **sequential integers** starting from 001
- IDs are **never reused** — even after resolution, the ID remains in history
- When a resolved item regresses, it gets its original ID back with Status 🔄 Recurring
- IDs are scoped to a single BC's REVIEW.md; cross-BC reference format: `<bc-slug>/AD-NNN`

---

## 10. Skill Evolution Suggestions Template

Suggestions for improving arch-review itself or other pipeline skills.

### SE Item Structure

```markdown
| Field | Value |
|-------|-------|
| **ID** | SE-NNN (sequential) |
| **Target Skill** | `/arch-align` \| `/arch-design` \| `/arch-detail` \| `/devtdd` \| `/arch-review-self` |
| **Suggestion** | Concrete improvement (add rule X, clarify section Y, etc.) |
| **Priority** | P1 (blocks correct auditing) / P2 (improves accuracy) / P3 (nice-to-have) |
| **Status** | 🆕 New / ✅ Adopted |
| **Related AD** | AD-NNN that triggered this suggestion |
```

### When to Create SE Items

1. **Root Cause = Checklist Gap** → SE targeting the skill whose checklist is incomplete
2. **Root Cause = Rule Too Vague** → SE targeting the skill with the ambiguous rule
3. **Root Cause = Scope Blind Spot** → SE noting the scope boundary (may not be actionable)
4. **Route = `/arch-review-self`** → SE targets arch-review's own reference.md

### Consumption Protocol

When a skill is invoked, it SHOULD check `docs/bc/<bc-slug>/REVIEW.md` for any SE items targeting it (Status 🆕) and consider incorporating them before proceeding.

---

## 11. Version Comparison Protocol (版本对比协议)

### When to Compare

- After scoring (Step 7) and before writing REVIEW.md (Step 10)
- Only when a previous REVIEW.md exists (skip on first review)

### Comparison Algorithm

1. **Parse Previous Architecture Debt Table**: Extract all items with Status != ✅ Resolved from the previous REVIEW.md.
2. **Match Current Findings to Previous ADs**:
   - Match by: Location + Violation type + Description similarity
   - If matched → mark as 🔄 Recurring (if still open) or ✅ Resolved (if fixed)
   - If no match → mark as 🆕 New
3. **Identify Regressions**:
   - Compare current findings against previously archived reviews in `reviews/done/`
   - If any previously resolved item reappears in current findings → flag as Regression, restore original AD-ID
4. **Compute Score Delta**:
   - For each axis: Current − Previous = Delta
   - Positive = improved, Negative = degraded
5. **Produce Version Diff Summary**:

```markdown
### Version Diff Summary (v{N-1} → v{N})

**Score**: NN → NN (Δ +/-N) — 🟢/🟡/🔴

| Category | Count |
|----------|-------|
| New Findings | N |
| Resolved | N |
| Recurring | N |
| Regressions | N |

**New**: AD-xxx, AD-xxx, ...
**Resolved**: AD-xxx (resolution: ...), ...
**Regressions**: AD-xxx (was resolved in v{M}, reappeared)
```

### Archive Naming Convention

- Current file: `REVIEW.md` (always at BC root for easy access by other skills)
- Active archive: `reviews/v{N}.md` — contains unresolved AD items (full snapshot at time of archiving)
- Closed archive: `reviews/done/v{N}.md` — all AD items resolved (full snapshot preserved)

### Archive Lifecycle

1. When `/arch-review` runs and a previous `REVIEW.md` exists:
   a. Check all AD items in the current `REVIEW.md`.
   b. If **all AD Status = ✅ Resolved** → move to `reviews/done/v{N}.md`.
   c. If **any AD Status ≠ ✅ Resolved** → move to `reviews/v{N}.md`.
2. Create `reviews/` and `reviews/done/` directories if they don't exist.
3. Archives are NEVER deleted — they form an immutable audit trail.
4. **REVIEW.md is a lightweight dashboard** — it does NOT contain a Resolved Debt table. Resolved items exist only in archives and in the stdout Version Diff Summary.
5. Other skills consume REVIEW.md for active debt tracking only — source documents (ARCHITECTURE.md, DESIGN.md, code) are the authoritative record of what was fixed.
