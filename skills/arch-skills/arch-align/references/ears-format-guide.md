# EARS Format Guide

EARS (Easy Approach to Requirements Syntax) provides a structured way to formalize requirements during the Grilling phase of `/arch-align`.

## Why EARS?

Natural language requirements are ambiguous. EARS enforces a syntax that makes requirements:
- **Unambiguous** — one interpretation only
- **Testable** — each requirement maps to at least one test
- **Atomic** — one requirement, one behavior
- **Technology-neutral** — describes *what*, not *how*

## The 4 EARS Patterns

### 1. Ubiquitous (泛在型)

For behaviors that are **always active** — no trigger, no condition.

```
The system shall <action>.
```

**Examples:**
- "The system shall maintain an audit log of all state transitions."
- "The system shall encrypt data at rest using AES-256."

**When to use:** Invariants, continuous behaviors, global constraints.

### 2. Event-Driven (事件驱动型)

For behaviors triggered by a **specific event**.

```
When <event>, the system shall <response>.
```

**Examples:**
- "When a new agent registers, the system shall assign it a unique CensusID."
- "When a manifest expires, the system shall mark the agent as offline."

**When to use:** Reactive behaviors, event handlers, callbacks, notifications.

### 3. State-Driven (状态驱动型)

For behaviors active **during a specific state**.

```
While <state>, the system shall <action>.
```

**Examples:**
- "While the system is in maintenance mode, the system shall reject all write operations."
- "While an agent is in quarantine, the system shall isolate its network access."

**When to use:** Mode-dependent behaviors, temporary restrictions, lifecycle phases.

### 4. Conditional (条件型)

For behaviors evaluated at a **decision point**.

```
If <condition>, the system shall <action>.
```

**Examples:**
- "If the agent's heartbeat is older than 5 minutes, the system shall mark it as offline."
- "If the order total exceeds the credit limit, the system shall reject the order."

**When to use:** Predicates, validation rules, threshold checks, branching logic.

## Quality Checklist

After writing a requirement in EARS format, verify:

| Check | Question |
|-------|----------|
| Unambiguous | Can only one person interpret this the same way? |
| Testable | Can I write a Given/When/Then test for this? |
| Atomic | Does it describe exactly ONE behavior? |
| Technology-neutral | Does it avoid naming frameworks, protocols, or implementations? |
| BC-bounded | Does it belong to exactly one Bounded Context? |
| Complete | Are all inputs, outputs, and error cases covered? |

## Integration with arch-align

During the Grilling Process (Step 3), when the user's requirements are vague:

1. **Detect vagueness** — phrases like "handle errors", "process data", "manage users"
2. **Apply EARS** — ask the user to rephrase using one of the 4 patterns
3. **Record in LANGUAGE.md** — add the formalized requirement as a use case entry
4. **Cross-reference in BRD.md** — link to the Tracer Bullet Goal

### Example Grilling Flow

```
User: "系统需要处理代理注册"
Agent: "处理注册的具体行为是什么？让我们用 EARS 格式明确：
        When a new agent submits a registration request,
        the system shall validate the agent's identity,
        assign a unique CensusID,
        and record the registration in the Census ledger.
        这样对吗？还是有其他步骤？"
```

## Further Reading

- Alistair Mavin's original EARS paper
- IREB (International Requirements Engineering Board) CPRE syllabus
