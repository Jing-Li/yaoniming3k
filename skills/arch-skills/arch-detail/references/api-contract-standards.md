# API Contract Standards

Standards for generating REST API contracts during `/arch-detail` Step 4c.

## OpenAPI 3.1 Fragment Template

For each port method exposed as a REST endpoint, generate an OpenAPI fragment:

```yaml
paths:
  /api/v1/{resource}:
    get:
      operationId: list{Resources}
      summary: List {resource description}
      parameters:
        - name: limit
          in: query
          schema: { type: integer, default: 20, maximum: 100 }
        - name: offset
          in: query
          schema: { type: integer, default: 0 }
      responses:
        '200':
          description: Success
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    type: array
                    items: { $ref: '#/components/schemas/{Resource}' }
                  total: { type: integer }
        '400': { $ref: '#/components/responses/BadRequest' }
        '401': { $ref: '#/components/responses/Unauthorized' }
```

## Error Response Format (RFC 7807)

All error responses MUST use `application/problem+json`:

```yaml
components:
  responses:
    BadRequest:
      description: Invalid request parameters
      content:
        application/problem+json:
          schema: { $ref: '#/components/schemas/ProblemDetail' }
    NotFound:
      description: Resource not found
      content:
        application/problem+json:
          schema: { $ref: '#/components/schemas/ProblemDetail' }
    InternalError:
      description: Unexpected server error
      content:
        application/problem+json:
          schema: { $ref: '#/components/schemas/ProblemDetail' }

  schemas:
    ProblemDetail:
      type: object
      required: [type, title, status]
      properties:
        type: { type: string, format: uri }
        title: { type: string }
        status: { type: integer }
        detail: { type: string }
        instance: { type: string, format: uri }
```

## Pagination

### Offset-Based (Default)

```yaml
parameters:
  - name: limit
    in: query
    schema: { type: integer, default: 20, maximum: 100 }
  - name: offset
    in: query
    schema: { type: integer, default: 0 }
```

Response includes `total` count and `data` array.

### Cursor-Based (Large Datasets)

```yaml
parameters:
  - name: cursor
    in: query
    schema: { type: string }
  - name: limit
    in: query
    schema: { type: integer, default: 20, maximum: 100 }
```

Response includes `next_cursor` (null when exhausted).

## Versioning

### Versioning Strategy Decision Tree

| Condition | Strategy | Path Example | Rationale |
|-----------|----------|--------------|----------|
| API is internal (single consumer) | **No version** | `/api/{resource}` | Overhead outweighs benefit |
| API is external, breaking changes expected | **URI path** (default) | `/api/v1/{resource}`, `/api/v2/{resource}` | Simplest routing, clear deprecation |
| API needs content negotiation | **Header** | `Accept: application/vnd.api+json;version=1` | URI stays clean, version in media type |
| API has additive-only changes | **No version bump** | Same path, add fields | Backward-compatible additions don’t need versioning |

### Version Lifecycle

| Stage | Status Header | Behavior |
|-------|---------------|----------|
| Current | (none) | Full support |
| Deprecated | `Sunset: <date>` header | 6-month deprecation window minimum |
| Retired | — | Return `410 Gone` with ProblemDetail |

## Idempotency

### Idempotency Key Requirements

| HTTP Method | Idempotent? | Idempotency-Key Header? |
|-------------|-------------|------------------------|
| GET / PUT / DELETE | Yes (by nature) | No |
| POST (create) | No | **Required** for write APIs |
| POST (custom action) | Depends | Required if side-effects |

```yaml
# Idempotency header template
post:
  parameters:
    - name: Idempotency-Key
      in: header
      required: true
      schema: { type: string, format: uuid }
  responses:
    '409':
      description: Duplicate idempotency key with different payload
```

## Rate Limiting

Rate limiting headers in every response:

```yaml
# Response headers (IETF draft standard)
headers:
  RateLimit-Limit: { schema: { type: integer }, description: Request quota per window }
  RateLimit-Remaining: { schema: { type: integer }, description: Remaining requests }
  RateLimit-Reset: { schema: { type: integer }, description: Seconds until reset }
  Retry-After: { schema: { type: integer }, description: Seconds to wait (only on 429) }
```

### Rate Limit Policy Table

| Endpoint Pattern | Limit | Window | Rationale |
|-----------------|-------|--------|----------|
| `GET /api/v1/{resources}` | 100 req | 1 min | Read-heavy, cache-friendly |
| `POST /api/v1/{resources}` | 20 req | 1 min | Write protection |
| `POST /api/v1/{resources}/{id}/{action}` | 10 req | 1 min | Expensive operations |

## Bulk Operations

### Bulk Pattern Decision

| Condition | Pattern | Endpoint |
|-----------|---------|----------|
| Create ≤ 50 items at once | **Batch POST** | `POST /api/v1/{resources}/batch` |
| Update multiple items | **Batch PATCH** | `PATCH /api/v1/{resources}/batch` |
| Delete multiple items | **Batch DELETE** | `DELETE /api/v1/{resources}/batch` with body `{ "ids": [...] }` |
| Import large dataset (> 1000) | **Async import** | `POST /api/v1/{resources}/imports` → returns job ID |

```yaml
# Batch create template
paths:
  /api/v1/{resources}/batch:
    post:
      operationId: batchCreate{Resources}
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                items:
                  type: array
                  maxItems: 50
                  items: { $ref: '#/components/schemas/{Resource}Input' }
      responses:
        '207':
          description: Multi-status (partial success)
          content:
            application/json:
              schema:
                type: object
                properties:
                  results:
                    type: array
                    items:
                      type: object
                      properties:
                        index: { type: integer }
                        status: { type: integer }
                        data: { $ref: '#/components/schemas/{Resource}' }
                        error: { $ref: '#/components/schemas/ProblemDetail' }
```

## HATEOAS / Resource Links

### When to Include Links

| Condition | Include `_links`? | Rationale |
|-----------|-------------------|----------|
| Resource has related sub-resources | **Yes** | Client discovers related endpoints |
| Stateful resource (state machine) | **Yes** — include allowed transitions | Client knows valid next actions |
| Simple CRUD, single consumer | **No** | Overhead without benefit |
| Public API, multiple consumers | **Consider** | Reduces coupling to URL structure |

```yaml
# HATEOAS response example
{
  "data": {
    "id": "abc",
    "status": "confirmed",
    "_links": {
      "self": { "href": "/api/v1/orders/abc" },
      "cancel": { "href": "/api/v1/orders/abc/cancel", "method": "POST" },
      "items": { "href": "/api/v1/orders/abc/items" }
    }
  }
}
```

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Paths | kebab-case | `/api/v1/agent-entries` |
| Query params | camelCase or snake_case | `pageSize` or `page_size` |
| JSON fields | Match target language convention | `agentId` (JS) or `agent_id` (Python) |
| operationId | camelCase | `listAgentEntries` |

## Port Method → REST Operation Mapping

| Port Method Pattern | HTTP Method | Path |
|--------------------|-------------|------|
| `List(filter)` | GET | `/api/v1/{resources}` |
| `Get(id)` | GET | `/api/v1/{resources}/{id}` |
| `Create(entity)` | POST | `/api/v1/{resources}` |
| `Update(id, entity)` | PUT | `/api/v1/{resources}/{id}` |
| `Delete(id)` | DELETE | `/api/v1/{resources}/{id}` |
| `Upsert(id, entity)` | PUT | `/api/v1/{resources}/{id}` |
| Custom action | POST | `/api/v1/{resources}/{id}/{action}` |
