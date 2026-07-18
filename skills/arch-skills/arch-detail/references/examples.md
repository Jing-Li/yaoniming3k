# arch-detail Golden Examples

Examples based on a fictional **Order Service** BC (Go, Modular Monolith, PostgreSQL).

---

## Example 1: DESIGN.md Index (Phase 3 Output)

```markdown
# Detailed Design Specification — E-Commerce Order Service

> Phase 3 output. Translates Phase 2 boundaries into Go 1.22 code structures, DDL, GoF patterns, and vertical-slice tasks.
> Aligned with: [ARCHITECTURE.md](./ARCHITECTURE.md) (Phase 2 boundaries), [LANGUAGE.md](./LANGUAGE.md), [BRD.md](./BRD.md)
> Target language: **Go 1.22**
> Last updated: 2026-07-10

---

## 1. Database Schema (DDL)

### 1.1 PostgreSQL DDL

```sql
CREATE TABLE orders (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id  UUID NOT NULL,
    status       VARCHAR(20) NOT NULL DEFAULT 'pending',
    total_amount BIGINT NOT NULL DEFAULT 0,  -- stored in cents
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at   TIMESTAMPTZ  -- soft-delete
);
```

### 1.2 Domain-to-Table Mapping (Data Mapper)

| Domain Entity | Table | Mapper |
|--------------|-------|--------|
| Order | orders | OrderRowMapper |
| LineItem | order_items | LineItemRowMapper |

## 2. GoF Design Patterns (Global Decisions)

| Pattern | Applied To | Rationale |
|---------|-----------|-----------|
| Factory Method | Order.NewOrder() | Complex creation with validation |
| Strategy | PaymentMethod interface | Swap payment providers |
| Observer (domain events) | OrderConfirmed event | Decouple side effects from core |

## 3. Go Package Layout (Final)

| Package | Layer | Responsibility |
|---------|-------|---------------|
| `internal/domain/order` | Domain | Order entity, value objects, domain events |
| `internal/domain/payment` | Domain | Payment value objects |
| `internal/port/orderrepo` | Port | OrderRepository interface (read+write) |
| `internal/port/paymentgw` | Port | PaymentGateway interface |
| `internal/app/order` | Application | CreateOrder, GetOrder use cases |
| `internal/infra/postgres` | Infrastructure | OrderRepository PostgreSQL adapter |
| `internal/infra/stripe` | Infrastructure | PaymentGateway Stripe adapter |
| `cmd/order-service` | Delivery | Composition root + HTTP handlers |

## 4. Module Index

| Module | Port Interface | Design | Methods |
|--------|---------------|--------|---------|
| order | OrderRepository | [module.md](./detail/modules/order/module.md) | [create_order](./detail/modules/order/interfaces/create_order.md), [get_order](...) |
| payment | PaymentGateway | [module.md](./detail/modules/payment/module.md) | [charge](./detail/modules/payment/interfaces/charge.md) |

## 5. Vertical-Slice Task Summary

| # | Task | Module | Interface Contracts | Definition of Done |
|---|------|--------|--------------------|--------------------|
| 1 | Implement CreateOrder with persistence | [order](./detail/modules/order/module.md#vertical-slice-tasks) | [create_order](./detail/modules/order/interfaces/create_order.md) | CreateOrder returns OrderID, persists to DB |
| 2 | Implement GetOrder by ID | [order](...) | [get_order](...) | GetOrder returns full Order with items |
| 3 | Implement Charge for confirmed order | [payment](...) | [charge](...) | Charge calls gateway, updates order status |

## 6. Dependency Injection Wiring (Composition Root)

```go
func main() {
    db := postgres.Open(cfg.DatabaseURL)
    orderRepo := postgres.NewOrderRepository(db)
    paymentGW := stripe.NewGateway(cfg.StripeKey)

    createOrder := order.NewCreateOrderUseCase(orderRepo)
    getOrder := order.NewGetOrderUseCase(orderRepo)
    charge := payment.NewChargeUseCase(orderRepo, paymentGW)

    http.Start(cfg.Port, createOrder, getOrder, charge)
}
```
```

**Why this is good**:
- Module Index links to actual files (not placeholder text)
- Task Summary is an index only — full details live in module.md
- Composition Root shows the real DI wiring order
- DDL uses `BIGINT` for money (cents), not `DECIMAL` — matches domain decision

---

## Example 2: module.md (Order Module)

```markdown
# Module Design: order

> Port: `OrderRepository`
> Layer: Domain → Port → Application → Infrastructure

## 1. Entities

### Order
| Field | Type | Constraints |
|-------|------|-------------|
| ID | string | UUID, auto-generated |
| CustomerID | string | required |
| Items | []LineItem | 1..N |
| Status | OrderStatus | pending / confirmed / shipped |
| TotalAmount | int64 | cents, computed from items |

## 2. Port Interface

```go
type OrderRepository interface {
    Save(ctx context.Context, o Order) error
    FindByID(ctx context.Context, id string) (Order, error)
}
```

## 3. Interface Contracts

| Method | File | Scenarios |
|--------|------|-----------|
| CreateOrder | [create_order.md](./interfaces/create_order.md) | 3 |
| GetOrder | [get_order.md](./interfaces/get_order.md) | 2 |

## 4. Error Domain

| Error | When |
|-------|------|
| ErrOrderNotFound | FindByID finds no matching row |
| ErrInvalidQuantity | LineItem.Quantity ≤ 0 |
| ErrOrderAlreadyExists | Save finds duplicate ID |

## 7. Vertical-Slice Tasks

### Task 1: Implement CreateOrder use case

**Tracer slice**: HTTP request → CreateOrderUseCase.Execute → OrderRepository.Save

**Interface contracts**: [create_order.md](./interfaces/create_order.md)

**Acceptance scenarios** (from contract §6):
1. Given valid request → returns OrderID, persists order
2. Given duplicate OrderID → returns ErrOrderAlreadyExists
3. Given invalid quantity → returns ErrInvalidQuantity

**Definition of Done**:
- [ ] CreateOrderUseCase exists with Execute method
- [ ] All 3 acceptance scenarios pass as unit tests
- [ ] Domain layer has zero external imports
- [ ] Port interface consumed by use case (no direct adapter coupling)
- [ ] Unit tests cover happy path + all error paths
- [ ] Code craftsmanship checks pass (no magic strings, DRY, no dead code)

**Layers touched**: Domain (Order, OrderFactory), App (CreateOrderUseCase), Port (OrderRepository)
```

**Why this is good**:
- Port interface is minimal (2 methods, ISP-compliant)
- Error domain is explicitly documented (not ad-hoc)
- DoD items are checkboxes (not prose) — verifiable and binary
- Task references the interface contract file (single source of truth)
