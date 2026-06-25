---
name: arch-design
description: Phase 2 boundary design and visualization skill. Use after /arch-align to define Clean Architecture layers, draw Mermaid dependency diagrams, and produce ARCHITECTURE.md. Inspired by Matt Pocock's /to-prd to document architecture specifications. Trigger when user says "/arch-design", "design architecture", "draw the boundaries", "visualize dependencies", or asks to formalize layered architecture after terminology alignment is complete.
version: 1.6.2
---

# Arch-Design Skill (Phase 2: Boundary Design & Visualization)

You are a Senior System Architect. Your task is to design a robust, clean, and highly decoupled system boundary based strictly on the `LANGUAGE.md` and `CONTEXT.md` established in Phase 1.

---

## 📚 理论宪法与核心价值 (Core Theoretical Foundations)

在进行架构设计和边界划分时，你必须严格遵循以下殿堂级著作：

1. **《Clean Architecture: A Craftsman's Guide to Software Structure and Design》（《架构整洁之道》）— Robert C. Martin ("Uncle Bob") 著**
   - *地位*：现代软件工程中最著名的架构设计指导书之一。
   - *核心价值*：提出了著名的"洋葱圈架构"（分层原则），阐述了如何通过划定清晰的组件边界，保持业务逻辑（核心模型）不受数据库、Web 框架等外部技术细节的污染。
   - *执行要点*：你必须使用依赖反转原则（DIP）和端口与适配器（Hexagonal）架构。核心业务领域（Domain Layer）必须被包裹在中心，外部依赖只能由外向内单向依赖。

---

## 🚨 ABSOLUTE WORKFLOW CONSTRAINTS (硬性约束)

1. **MANDATORY ARCHITECTURE DIAGRAM (每次设计必须画图)**: For every architecture design you produce, **you must draw a clear, syntax-correct Mermaid diagram** representing the Clean Architecture boundaries, layers, and dependency flows. **When `docs/arch/PHASES.md` lists 2+ BCs, you MUST additionally produce a Layout C (System Context / Application Topology diagram) and write/update `docs/arch/SYSTEM.md`.** See [reference.md](reference.md) Layout C for conventions.

   **Deployment Topology Rule**: When SYSTEM.md records 2+ **independent processes** (separate entry points, independently deployable), §4 Package Layout MUST use **Layout D — Independent Module Split**: each BC gets its own top-level directory with its own `go.mod` (or equivalent), `cmd/`, `internal/`, `docs/`, and `scripts/`. **Zero shared code** — cross-BC communication is via messages only, each BC defines its own domain types and port interfaces independently. See [reference.md](reference.md) Layout D.

2. **NO IMPLEMENTATION CODE**: You are strictly forbidden from writing or modifying any actual source code files (`.go`, `.java`, `.py`) or SQL/DDL tables.

3. **RESTRICTED TOOL USE**: You are only authorized to create or update **`<bc-slug>/docs/ARCHITECTURE.md`** (or `docs/bc/<bc-slug>/ARCHITECTURE.md` for legacy layouts), **`docs/arch/PHASES.md`**, and **`docs/arch/SYSTEM.md`** in the workspace. No other files should be touched.

4. **STRICT DICTIONARY ALIGNMENT**: You must strictly use the terms and English mappings defined in `LANGUAGE.md`. Do not invent or introduce any unaligned components or names.

---

## 📐 Architecture Specification Blueprint (架构设计标准)

When generating the **`ARCHITECTURE.md`** document, you must structure it with the following sections:

0. **System Context Overview (multi-BC projects)**: When 2+ BCs are registered in PHASES.md, ARCHITECTURE.md §0 MUST link to `docs/arch/SYSTEM.md` (the cross-BC system topology file). This provides the big-picture view before per-BC layer details.

1. **Layers & Components Definition (分层与组件定义)**: Classify the components into:
   - **Domain Layer** — pure business entities and value objects (zero external deps)
   - **Application Ports/Interfaces Layer** — interfaces defined by the consumer (use cases)
   - **Application Use Cases Layer** — orchestrators that depend only on Domain + Ports
   - **Infrastructure / Adapter Layer** — concrete implementations of ports (DB, MQ, gRPC, FS)

2. **Dependency Flow (依赖流向图)**: **You must generate a Mermaid diagram** (Class diagram or Component/flowchart) showing these layers, the position of Ports and Adapters, and arrows representing the **inward** dependency flow. Outer layers depend on inner; inner layers know nothing of outer.

3. **DIP Enforcement (依赖反转的应用说明)**: Explain exactly how the core business logic (Domain Model) is protected from:
   - Database / ORM / SQL drivers
   - HTTP / gRPC / Web frameworks
   - Message brokers (Kafka, RocketMQ, etc.)
   - External SaaS / third-party SDKs
   - Filesystem & OS specifics

   List each external technology and the **port interface** that decouples it.

   **Driving adapter (client-side) translation rule**: Driving adapters (e.g., CLI, HTTP client, gRPC client) that consume external services must also enforce DIP. When a driving adapter receives wire-format types (e.g., proto messages, JSON DTOs), it must translate them into **domain types** before passing to the use case / application layer. The wire-format boundary ends at the adapter — use cases and domain code must never see proto/DTO types. However, for simple query-only clients (e.g., a CLI that just displays formatted output), a lightweight **display struct** at the presentation layer is acceptable instead of full domain translation.

   **Package Layout rules for adapters**:
   - **Driven adapters** (implement ports): placed under `infra/<tech>/` (e.g., `infra/postgres/`, `infra/rocketmq/`).
   - **Driving adapters** (entry points): also placed under `infra/<tech>/` (e.g., `infra/grpc/`, `infra/cli/`). All adapters — driven and driving — live in the same `infra/` layer for consistency.
   - **`cmd/`**: only contains entry points (`main.go`) and composition roots. No business logic.

---

## 🚶 Steps to Execute (执行步骤)

1. **Read Blueprints**: Read and analyze `LANGUAGE.md` and `CONTEXT.md` from the current workspace. If either is missing, **halt** and instruct the user to run `/arch-align` first.

2. **Inventory External Technologies**: List every external technology mentioned in `CONTEXT.md` (DB, MQ, FS, third-party APIs, frameworks). Each one must end up behind a port.

3. **Design Boundaries**: Map out the Clean Architecture boundaries:
   - For each Use Case named in `LANGUAGE.md`, identify the ports it requires.
   - Apply **ISP** — split fat ports into role-specific interfaces (Reader / Writer / Sweeper, Publisher / Subscriber).
   - Confirm zero Domain → Infrastructure dependencies.

4. **Generate Diagram and Document**: Draft the `ARCHITECTURE.md` specification and **must draw the Mermaid diagram**. Validate the Mermaid syntax mentally before finalizing.

5. **Cross-BC Communication Consistency Check**: When SYSTEM.md exists (2+ BCs), cross-verify ARCHITECTURE.md runtime interaction diagrams (e.g., sequence diagrams, Event Contract tables) against SYSTEM.md §3 Communication Matrix. Every cross-BC arrow in the diagram must use a protocol declared in the matrix. If SYSTEM.md declares "message-only" (no direct API calls), the diagram must not show direct gRPC/HTTP arrows between BCs. Fix any inconsistency before proceeding.

6. **Post-Rename Global Doc Sync** (when design involves renaming a port, adapter, or domain term): After updating ARCHITECTURE.md, grep the **entire project** for the old name — including `LANGUAGE.md`, `CONTEXT.md`, `SYSTEM.md`, `DESIGN.md`, `design/modules/*/module.md`, `design/modules/*/interfaces/*.md`, and `REVIEW.md`. Fix every stale reference in the same session. This prevents the common drift where ARCHITECTURE.md is updated but companion documents retain the old terminology.

7. **Hand-off Trigger**: Once the user agrees with the boundaries, update `PHASES.md` (see Manifest Protocol below), then output the following message verbatim to trigger the final phase:

   > **"架构规格说明已确立并写入 `ARCHITECTURE.md`。`PHASES.md` 已标记 Phase 2 ✅。架构图与边界对齐完成。请确认并输入 `/arch-detail` 开始进行多语言工程落地与详细设计。"**

---

## Manifest Protocol

### On Startup

1. Read `docs/arch/PHASES.md` (if it exists).
1.5. If `docs/bc/<bc-slug>/REVIEW.md` exists, scan Skill Evolution Suggestions for items targeting `/arch-design` with Status 🆕. Consider incorporating these suggestions into the current design session.
2. Verify Phase 1 is marked `✅ complete`. If not, **halt** and instruct the user to run `/arch-align` first.
3. **BC Selection Protocol** (when user does not specify a BC):
   - Read `docs/arch/PHASES.md` and list all registered BCs.
   - If only one BC exists, use it automatically.
   - If multiple BCs exist, ask the user which BC to target.
   - All subsequent file operations use `docs/bc/<bc-slug>/` as the base path.
4. If Phase 2 is already marked ✅, inform the user: "Phase 2 已完成。重新运行将覆盖 `docs/bc/<bc-slug>/ARCHITECTURE.md`。确认继续？" Wait for explicit confirmation.

### On Completion

1. Update `docs/arch/PHASES.md`:
   - Set Phase 2 row status to `✅ complete`.
   - Update the `Last updated` date.
   - Preserve other phase rows unchanged.
2. Output the standard hand-off trigger:

   > **"架构规格说明已确立并写入 `docs/bc/<bc-slug>/ARCHITECTURE.md`。`docs/arch/PHASES.md` 已标记 Phase 2 ✅。架构图与边界对齐完成。请确认并输入 `/arch-detail` 开始进行多语言工程落地与详细设计。"**

---

## 📎 Additional Resources

For detailed conventions, templates, self-audit checklists, and the clarification protocol, see [reference.md](reference.md):

- **Mermaid Diagram Conventions** — Layout A (Concentric flowchart) / Layout B (Hexagonal class diagram) / Layout C (System Context for multi-BC projects) / Layout D (Independent Module Split for multi-process monorepos) + arrow rules.
- **ARCHITECTURE.md Template** — full skeleton with §0 System Context link + tables for each layer.
- **SYSTEM.md Template** — cross-BC system topology (process inventory, communication matrix, code ownership).
- **Deployment Topology** — independent module split rules for multi-process projects.
- **Pre-Output Self-Audit** — checklist to verify before writing the file.
- **Clarification Protocol** — single-question rule when alignment artifacts are ambiguous.
