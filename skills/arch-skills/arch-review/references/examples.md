# arch-review Golden Examples

Examples based on a fictional **Order Service** BC (Go, Modular Monolith, 2 ports, 2 adapters).

---

## Example 1: Complete AD Entry (with Routing + Root Cause)

A well-formed Architecture Debt item as it should appear in `T{N}.md`:

```markdown
### AD-003: Domain entity imports infrastructure logger
- **Severity**: 🔴 Critical
- **Route**: `/devtdd`
- **Violation IDs**: R-2
- **Status**: 🆕 New

**Finding**: `internal/domain/order/order.go:L12` imports `go.uber.org/zap`.
The domain layer must have zero external imports (only stdlib). Using a structured
logger in domain entities couples business logic to a specific logging framework,
violating the Dependency Rule and making unit tests depend on logger initialization.

**Evidence** (from code):
```go
import "go.uber.org/zap"  // ❌ domain → infrastructure

type Order struct {
    logger *zap.Logger  // ❌ framework type in domain entity
}
```

**Root Cause Analysis**:
- Missed By: `/devtdd` (implementation phase)
- Miss Reason: **Checklist Gap** — devtdd Constraint #3 says "Domain layer has zero
  external imports" but the boundary check after GREEN cycle did not catch the logger
  import because the test file imported the same package (test passed, boundary check
  only grepped for `internal/infra`).
- Evidence: The test file `order_test.go` also imports `zap`, masking the violation.
- Correction: devtdd boundary check should scan ALL imports in domain files (not just
  `internal/infra` patterns) and reject any non-stdlib import.

**Code Comparison** (before/after):
```go
// BEFORE ❌
type Order struct {
    logger *zap.Logger
}
func (o *Order) Confirm() {
    o.logger.Info("order confirmed", zap.String("id", o.ID))
}

// AFTER ✅ — domain emits events, adapter logs
type Order struct {}
func (o *Order) Confirm() []DomainEvent {
    return []DomainEvent{OrderConfirmed{OrderID: o.ID}}
}
```
```

**Why this is good**:
- Single route tag (`/devtdd`) — the code implementation issue, not a design gap
- Root cause names the specific miss reason and identifies WHY the check failed
- Code comparison shows the actual refactoring path (event emission instead of logging)

---

## Example 2: Route Decision Walkthrough

A finding that could be routed to multiple skills — here's how to pick:

**Finding**: ARCHITECTURE.md §2 sequence diagram shows `OrderRepo.Save()` returning `*Order`,
but the actual code `internal/infra/postgres/order_repo.go` returns `(Order, error)`.

**Route analysis**:
1. Is it a terminology issue? No — names match.
2. Is it a design gap (missing interface)? No — the interface exists.
3. Is it a code implementation issue? No — code correctly returns `(Order, error)`.
4. Is it an ARCHITECTURE.md inconsistency? **YES** — the diagram is stale.

**Route**: `/arch-design` (ARCHITECTURE.md is owned by arch-design).

**Why NOT `/devtdd`**: The code is correct; the diagram is wrong. Routing to devtdd
would "fix" working code to match a stale diagram.

---

## Example 3: Report §1 Health Score (well-formatted)

```
Score: 72 / 100
  - Dependency Rule        : 18 / 25  (−7: domain imports zap in 2 files)
  - Domain Purity          : 16 / 20  (−4: Order struct holds *zap.Logger)
  - Persistence Decoupling : 20 / 20  (clean — OrderRow maps via DataMapper)
  - Pattern Application    : 12 / 15  (−3: OrderService is a fat use case)
  - Naming Alignment       : 8 / 10   (−2: "OrderRepo" vs LANGUAGE.md "OrderRepository")
  - Security Posture       : 8 / 10   (−2: no input validation on CreateOrder request)
Verdict: 🟡 At Risk
```

**Why this is good**:
- Each axis deduction has a parenthetical reason
- Deductions are traceable to specific findings (R-2, Y-1, etc.)
- Verdict emoji matches the score band

---

## Example 4: Severity Grading Table (Report §5)

| ID | Title | Severity | Route | Violation IDs | Root Cause | Status |
|----|-------|----------|-------|---------------|------------|--------|
| AD-001 | OrderRepo naming drift | 🟡 Minor | `/arch-align` | Y-3 | LANGUAGE.md predates code refactor | 🆕 New |
| AD-002 | Fat OrderService (SRP violation) | 🟠 Major | `/arch-design` | Y-1 | arch-design §0 overview did not decompose use cases | 🆕 New |
| AD-003 | Domain imports zap logger | 🔴 Critical | `/devtdd` | R-2 | devtdd boundary check missed non-stdlib imports | 🆕 New |
| AD-004 | OrderConfirmed event emitted cleanly | 🟢 Positive | — | — | — | ✅ Noted |

**Why this is good**:
- Critical/Major/Minor/Positive distribution follows the "for every 3+ Critical/Major, include 1+ Positive" rule
- Each AD has exactly one route tag
- Root cause is actionable (tells the target skill what to fix)
