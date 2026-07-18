# devtdd Golden Examples

Examples based on a fictional **Order Service** BC (Go, Clean Architecture).
Task: "Implement CreateOrder use case with persistence."

---

## Example 1: Micro-Cycle Plan (Step 3 Output)

Given the Task's acceptance scenarios from `interfaces/create_order.md`, decompose into cycles:

| Cycle # | Scenario | Test Name | Layers Implemented | Mock Boundary |
|---------|----------|-----------|-------------------|---------------|
| 1 | Given valid request, When CreateOrder, Then returns OrderID | `TestCreateOrder_Success` | Domain(Order, OrderFactory) → App(CreateOrderUseCase) | Fake OrderRepository |
| 2 | Given duplicate OrderID, When CreateOrder, Then returns ErrOrderExists | `TestCreateOrder_DuplicateID` | Domain(Order) → App(CreateOrderUseCase) | Fake OrderRepository (pre-seeded) |
| 3 | Given invalid quantity (≤0), When CreateOrder, Then returns ErrInvalidQuantity | `TestCreateOrder_InvalidQuantity` | Domain(Order, validation) → App(CreateOrderUseCase) | None (domain-only) |

**Why this is good**:
- Deepest layer first (Domain), not thinnest layer first
- Cycle 3 tests domain validation without any mocks — purest test possible
- Each cycle is independently valuable (can demo after any cycle)

---

## Example 2: One Complete Micro-Cycle (Red → Green → Refactor)

### RED — Write the failing test first

```go
// internal/app/order/create_order_test.go
func TestCreateOrder_Success(t *testing.T) {
    repo := &fakeOrderRepo{}  // system boundary fake
    uc := order.NewCreateOrderUseCase(repo)

    id, err := uc.Execute(t.Context(), order.CreateOrderRequest{
        CustomerID: "cust-001",
        Items: []order.LineItem{
            {ProductID: "prod-A", Quantity: 2, UnitPrice: 1000},
        },
    })

    require.NoError(t, err)
    assert.NotEmpty(t, id)
    assert.Equal(t, 1, repo.saveCount)
}

// fakeOrderRepo implements port.OrderRepository
type fakeOrderRepo struct {
    saved     []order.Order
    saveCount int
}

func (f *fakeOrderRepo) Save(ctx context.Context, o order.Order) error {
    f.saved = append(f.saved, o)
    f.saveCount++
    return nil
}

func (f *fakeOrderRepo) FindByID(ctx context.Context, id string) (order.Order, error) {
    for _, o := range f.saved {
        if o.ID == id {
            return o, nil
        }
    }
    return order.Order{}, order.ErrOrderNotFound
}
```

### GREEN — Minimum code to pass

```go
// internal/app/order/create_order.go
type CreateOrderUseCase struct {
    repo port.OrderRepository
}

func NewCreateOrderUseCase(repo port.OrderRepository) *CreateOrderUseCase {
    return &CreateOrderUseCase{repo: repo}
}

func (uc *CreateOrderUseCase) Execute(ctx context.Context, req CreateOrderRequest) (string, error) {
    o, err := NewOrder(req.CustomerID, req.Items)
    if err != nil {
        return "", err
    }
    if err := uc.repo.Save(ctx, o); err != nil {
        return "", err
    }
    return o.ID, nil
}
```

### REFACTOR — Extract only after ALL tests pass

```go
// Domain validation extracted from NewOrder (DRY for Cycle 2+3)
func validateQuantity(q int) error {
    if q <= 0 {
        return ErrInvalidQuantity
    }
    return nil
}
```

### BOUNDARY CHECK — After GREEN, verify imports

```bash
# Domain layer: zero external imports ✅
$ go list -f '{{.Imports}}' ./internal/domain/order/
# Output: [context errors time]  ← all stdlib

# App layer: no infra imports ✅
$ go list -f '{{.Imports}}' ./internal/app/order/
# Output: [...domain ...port context]  ← no infra packages
```

**Why this is good**:
- Test uses the **public interface** (Execute method), not internal helpers
- Fake implements the **port interface** (`port.OrderRepository`), not the adapter
- Boundary check runs AFTER every GREEN cycle, not just at task end
- Refactor only happened after all 3 cycles passed (not on RED)

---

## Example 3: Code Craftsmanship Check (post-Refactor)

After Cycle 2 (duplicate ID test), the code might look like this:

```go
// ❌ BEFORE — magic string, duplicated error construction
func (uc *CreateOrderUseCase) Execute(ctx context.Context, req CreateOrderRequest) (string, error) {
    if req.CustomerID == "" {
        return "", fmt.Errorf("customer ID is required")  // magic string
    }
    existing, _ := uc.repo.FindByID(ctx, req.CustomerID)
    if existing.ID != "" {
        return "", fmt.Errorf("order already exists for customer: %s", req.CustomerID)
    }
    // ...
}
```

```go
// ✅ AFTER — constants, no magic strings, no dead code
const (
    ErrCustomerIDRequired = "customer ID is required"
    ErrOrderAlreadyExists = "order already exists for customer: %s"
)

func (uc *CreateOrderUseCase) Execute(ctx context.Context, req CreateOrderRequest) (string, error) {
    if req.CustomerID == "" {
        return "", errors.New(ErrCustomerIDRequired)
    }
    // ...
}
```

**Craftsmanship checklist applied**:
- [x] No magic strings (error messages → named constants)
- [x] No dead code (removed unused `existing` variable from Cycle 1's first pass)
- [x] Standard library first (using `errors.New`, not a custom error package)
- [x] Test uses same constants (test assertion references `ErrCustomerIDRequired`)

---

## Example 4: State Synchronization (Step 5 Output)

After all cycles pass and craftsmanship checks are clean:

**DESIGN.md §5 update**:
```markdown
| # | Task | Module | Status |
|---|------|--------|--------|
| 1 | Implement CreateOrder use case | [order](./detail/modules/order/module.md) | ✅ |
| 2 | Implement GetOrder use case | [order](./detail/modules/order/module.md) | ☐ |
```

**module.md §7 DoD update**:
```markdown
#### Task 1: Implement CreateOrder use case
- [x] CreateOrderUseCase exists with Execute method
- [x] All 3 acceptance scenarios pass
- [x] Domain layer has zero external imports
- [x] Port interface consumed by use case (no direct adapter coupling)
- [x] Unit tests cover happy path + all error paths
```

**Why this is good**:
- Both files updated atomically in the same commit
- DoD items are specific and verifiable (not "code is clean")
- Task status is `✅` only after ALL DoD items are checked
