# Review Feedback Rules

4-level severity grading system for Architecture Debt items. Use in `/arch-review` to ensure consistent, actionable feedback.

## Severity Levels

### 🔴 Critical

**Definition:** Blocks merge/deploy. Fundamental architecture violation that will cause cascading problems.

**Score impact:** −50% of the axis weight.

**Examples:**
- Domain layer imports infrastructure package (dependency rule violation)
- Domain entity annotated with `@Entity` or ORM base class (persistence leak)
- Use case directly instantiates concrete adapter (no DI)
- Port interface defined in adapter package (ownership violation)
- Bounded context boundary crossed with direct internal access

**Required output:** Code location + evidence snippet + refactoring diff + root cause analysis.

### 🟠 Major

**Definition:** Should fix before next release. Significant violation that increases maintenance cost.

**Score impact:** −20% of the axis weight.

**Examples:**
- Fat port combining read/write/admin (ISP violation)
- Missing GoF pattern where long if/else chain exists (4+ branches)
- Adapter leaking driver-specific errors past the port
- Cross-BC import without going through communication port

**Required output:** Code location + concern description + suggested fix direction.

### 🟡 Minor

**Definition:** Can defer to follow-up. Improvement opportunity that doesn't block progress.

**Score impact:** −10% of the axis weight (capped at −50% per axis).

**Examples:**
- Naming drift from LANGUAGE.md (synonym usage)
- Missing context propagation in Go function signature
- Inconsistent error sentinel naming convention
- Suboptimal but not incorrect package placement

**Required output:** Concern description + suggested improvement.

### 🟢 Positive

**Definition:** Notable good practice worth calling out. Reinforces correct patterns.

**Score impact:** No deduction.

**Examples:**
- Excellent use of Decorator pattern for cross-cutting concerns
- Clean Data Mapper split with zero domain pollution
- Well-structured error sentinel hierarchy
- Exceptional naming consistency across layers

**Required output:** Brief description of what makes it good.

## Balance Rule

For every 3+ Critical/Major findings, include at least 1 Positive finding. Pure criticism without recognition demoralizes and misses teaching opportunities.

## Disagreement Protocol

When the developer disagrees with a finding:

1. **Acknowledge** — restate their position fairly (steelman, not strawman)
2. **Evidence check** — is the disagreement about facts or opinions?
3. **If factual** — re-verify with grep/code evidence
4. **If opinion** — present the trade-off explicitly: "Your approach optimizes X, the rule optimizes Y"
5. **Resolution** — either update the finding (if developer is right) or document the disagreement with rationale

## Code Comparison Examples

For each Critical/Major finding, provide a before/after code comparison:

```
Before (violation):
  usecase/order.go:
    import "project/infrastructure/postgres"  // ❌ domain→infra

After (fix):
  usecase/order.go:
    // import only domain + port interfaces
    type OrderStore interface { ... }  // ✅ port defined by consumer
```
