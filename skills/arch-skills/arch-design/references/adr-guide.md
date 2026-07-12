# ADR Guide — Architecture Decision Records

ADR（Architecture Decision Record）是架构决策的结构化记录，回答"为什么这样选"而不是"选了什么"。由 `/arch-design` 独占管理。

---

## 1. 何时写 ADR

并非所有设计选择都需要 ADR。以下决策矩阵帮助你判断：

### 必须写 ADR 的场景

| 场景 | 示例 |
|------|------|
| 选择持久化技术 | PostgreSQL vs MySQL vs MongoDB |
| 选择通信模式 | 同步 gRPC vs 异步 MQ vs REST |
| 选择架构模式 | Monolith vs Microservices vs Modular Monolith |
| 选择 CQRS / Event Sourcing | 读写分离、事件溯源 |
| 选择不采用常见模式（需论证） | 不用 ORM、不做微服务拆分 |
| 选择第三方服务或 SaaS | 支付网关、认证提供商 |
| 跨 BC 通信协议选择 | Kafka vs RocketMQ vs gRPC streaming |

### 不需要 ADR 的场景

| 场景 | 原因 |
|------|------|
| 标准 Clean Architecture 分层 | 这是管线默认方法论，不需要论证 |
| 端口命名、实体命名 | 由 LANGUAGE.md 管理 |
| Go/Java/Python 语言选择 | 这是项目级约束，在 BRD.md 中声明 |
| 纯粹的代码实现选择 | 属于 `/arch-detail` 或 `/devtdd` 的范畴 |

---

## 2. ADR 模板

```markdown
# ADR-{NNN}: {Title}

> BC: {BC Name}
> Phase: 2 (arch-design)
> Date: {YYYY-MM-DD}

## Status

{Proposed | Accepted | Deprecated | Superseded by ADR-{NNN}}

## Context

{描述当前面临的问题和约束。为什么需要做出这个决策？}
{列出关键约束：团队规模、预算、技术栈、性能需求等。}

## Decision

{清晰陈述决策内容。}

## Alternatives Considered

### {Alternative A}

- **描述**: {一句话描述}
- **优势**: {列出 1-3 个优势}
- **劣势**: {列出 1-3 个劣势}
- **否决原因**: {为什么没选这个}

### {Alternative B}

- **描述**: {一句话描述}
- **优势**: {列出 1-3 个优势}
- **劣势**: {列出 1-3 个劣势}
- **否决原因**: {为什么没选这个}

## Consequences

### 正面影响
- {正面影响 1}
- {正面影响 2}

### 负面影响
- {负面影响 1}
- {负面影响 2}

### 缓解措施
- {针对负面影响的缓解方案}

## Cross-References

- ARCHITECTURE.md §{section}: {how this decision manifests in the architecture}
- LANGUAGE.md: {any terms introduced or affected}
- NFR Checklist: {which NFR axis this decision serves}
```

---

## 3. 命名规范

文件名格式：`{NNN}-{kebab-case-title}.md`

```
docs/bc/order-management/design/adr/
├── 001-use-postgresql-storage.md
├── 002-adopt-event-driven-communication.md
├── 003-choose-cqrs-for-order-queries.md
└── 004-superseded-rest-to-grpc-migration.md
```

规则：
- **NNN** 是三位数序号（001, 002, ...），从不复用已删除的编号
- **kebab-case-title** 用英文短横线连接，简要描述决策内容
- 序号在整个 BC 内单调递增，不按 Phase 或 Cycle 重置

---

## 4. 状态生命周期

```
Proposed → Accepted           (Phase 2 完成前必须达到)
         → Superseded by ADR-X (被新决策取代)
Accepted → Deprecated         (不再适用但未被取代)
         → Superseded by ADR-X (被新决策取代)
Superseded → (终态，不可再变更)
Deprecated → (终态，不可再变更)
```

### 状态语义

| Status | 含义 | 在 ARCHITECTURE.md §5 索引中 |
|--------|------|------------------------------|
| **Proposed** | 正在讨论，未最终确定 | Phase 2 完成前必须转为 Accepted 或 Superseded |
| **Accepted** | 已确定，当前有效 | 正常显示 |
| **Deprecated** | 已弃用（技术淘汰或业务变更） | 显示为 ~~Deprecated~~，保留历史记录 |
| **Superseded by ADR-X** | 被 ADR-X 取代 | 显示为 ~~Superseded~~ → 链接到新 ADR |

### Phase 2 完成约束

当 arch-design 标记 Phase 2 ✅ 时：
- **所有 ADR 的 Status 必须是 `Accepted` 或 `Superseded`**
- 不允许存在 `Proposed` 状态的 ADR（有未决决策不能完成 Phase 2）
- 如果某个决策无法达成共识，应保留在 ARCHITECTURE.md §6 Open Questions 中，不出 ADR

---

## 5. ARCHITECTURE.md §5 索引表

ARCHITECTURE.md 的 §5 作为 ADR 的入口索引：

```markdown
## 5. Architecture Decision Records

| ADR | Title | Status | Key Decision | Date |
|-----|-------|--------|-------------|------|
| [ADR-001](./adr/001-use-postgresql-storage.md) | PostgreSQL 作为主存储 | Accepted | ACID 事务 + JSONB 灵活性 | 2025-01-15 |
| [ADR-002](./adr/002-adopt-event-driven.md) | BC 间事件驱动通信 | Accepted | 时间解耦优先于强一致性 | 2025-01-15 |
| ~~[ADR-001](./adr/001-use-postgresql-storage.md)~~ | ~~PostgreSQL 作为主存储~~ | Superseded by ADR-005 | ... | ... |
```

索引表与 `adr/` 目录必须保持严格一致：
- 每个 `adr/` 中的文件必须在索引表中有对应行
- 索引表中的每一行必须有对应文件
- Status 列必须与 ADR 文件内部的 Status 一致

---

## 6. 示例：一个完整的 ADR

```markdown
# ADR-001: Use PostgreSQL for Order Storage

> BC: Order Management
> Phase: 2 (arch-design)
> Date: 2025-01-15

## Status

Accepted

## Context

Order Management BC 需要持久化以下聚合：
- Order（订单）— 含复杂状态机（Pending → Paid → Shipped → Delivered）
- OrderItem（订单项）— 与 Product 关联的多对关系
- Payment（支付记录）— 需要 ACID 保证的金融数据

约束：
- 团队 3 人，均有 PostgreSQL 经验
- 预算有限，倾向开源方案
- NFR 要求 p99 延迟 < 200ms
- 需要 JSONB 支持灵活的订单项属性存储

## Decision

使用 PostgreSQL 15 作为 Order Management BC 的主存储。
通过 Data Mapper 模式（PoEAA）将持久化实体与领域实体解耦。

## Alternatives Considered

### MySQL 8

- **描述**: 成熟的开源关系数据库
- **优势**: 团队熟悉、生态成熟
- **劣势**: JSON 支持不如 PostgreSQL 强大、缺少 CTE recursive 高级特性
- **否决原因**: 订单项的灵活属性需要 JSONB 索引能力，MySQL 的 JSON 类型不支持 GIN 索引

### MongoDB

- **描述**: 文档型数据库
- **优势**: Schema 灵活、水平扩展容易
- **劣势**: 跨文档事务支持有限、不支持复杂 JOIN
- **否决原因**: Order ↔ OrderItem 的关系查询和金融级 ACID 需求不适合文档模型

### CockroachDB

- **描述**: 分布式 SQL 数据库
- **优势**: 自动分片、强一致性
- **劣势**: 运维复杂度高、成本高、团队无经验
- **否决原因**: 当前数据量不需要分布式方案，运维成本不合理

## Consequences

### 正面影响
- ACID 事务满足金融级一致性要求
- JSONB + GIN 索引满足灵活属性查询
- 丰富的窗口函数和 CTE 支持复杂报表
- 团队已有经验，学习成本低

### 负面影响
- 垂直扩展有上限（需读写分离应对增长）
- 高可用部署需要 DBA 知识

### 缓解措施
- 读写分离：主库写入 + 只读副本查询（架构已预留 ReadOnly 端口）
- 使用托管 PostgreSQL 服务（如 AWS RDS / 阿里云 RDS）降低运维负担

## Cross-References

- ARCHITECTURE.md §1.4: PostgresOrderRepo adapter
- ARCHITECTURE.md §3 DIP Enforcement: PostgreSQL → OrderRepository port
- NFR Checklist: Performance (p99 < 200ms), Availability (RTO 4h)
```

---

## 7. Redo 时的 ADR 处理

当 arch-review 发现 AD 路由到 `/arch-design`，触发 Phase 2 redo：

1. **评估现有 ADR**：检查每条 ADR 是否仍然有效
2. **修改 ADR**：如果决策需要调整，创建新 ADR 并将旧 ADR 标记为 `Superseded by ADR-{new}`
3. **新增 ADR**：如果 redo 过程中产生了新决策，按序号递增创建
4. **不删除旧 ADR**：ADR 是不可变的历史记录，只能 Supersede 不能删除
5. **更新 ARCHITECTURE.md §5 索引**：确保索引表反映最新状态
