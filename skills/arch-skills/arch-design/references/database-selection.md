# Database Selection Guide

Decision framework for selecting database technology based on access patterns and Clean Architecture mapping.

## Type Comparison

| Type | Examples | Best For | Anti-Indicator | Port | Adapter |
|------|----------|----------|---------------|------|---------|
| Relational | PostgreSQL, MySQL | ACID, joins, structured data | Variable schemas, simple KV | `Repository` | `postgres/` |
| Document | MongoDB, Couchbase | Flexible schemas, nested data | Complex joins, strong cross-doc consistency | `DocumentStore` | `mongo/` |
| Key-Value | Redis, DynamoDB | Session cache, rate limiting | Complex queries, relationships | `Cache` | `redis/` |
| Time-Series | InfluxDB, TimescaleDB | Metrics, K-lines, sensor data | Non-temporal data, CRUD | `MetricsStore` | `influxdb/` |
| Graph | Neo4j, TigerGraph | Relationships, recommendations | Simple CRUD, tabular data | `GraphQuery` | `neo4j/` |
| Search | Elasticsearch, Meilisearch | Full-text search, log analysis | Primary store, transactional writes | `SearchIndex` | `elasticsearch/` |

## Decision Tree

```
Primary access pattern?
├── Structured + ACID + joins → Relational
├── Flexible schema + document reads → Document
├── Get/set by key + sub-ms → Key-Value
├── Timestamp + time-range → Time-Series
├── Relationship traversal → Graph
└── Full-text + faceted → Search
```

## Multi-Database Architecture

Most systems use multiple types. Each gets its own port + adapter:
```
Ports:
  CensusStore (Relational)    → postgres adapter
  MetricsWriter (Time-Series) → influxdb adapter
  SessionCache (Key-Value)    → redis adapter
```

## Recording in ARCHITECTURE.md

```markdown
### Persistence Technology Selection

| Store | Type | Rationale | Port |
|-------|------|-----------|------|
| Census data | PostgreSQL | ACID + complex queries | CensusStore |
| K-line metrics | InfluxDB | Time-series + high write | MetricsWriter |
```
