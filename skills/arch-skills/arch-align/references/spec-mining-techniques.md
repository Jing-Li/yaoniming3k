# Spec Mining Techniques

Protocol for reverse-engineering domain terms and specifications from existing codebases. Designed for legacy projects where `/arch-align` needs to bootstrap a LANGUAGE.md from code artifacts rather than from scratch.

## When to Use

- Target project already has source code but no formal domain documentation
- Inherited codebase with no LANGUAGE.md or BRD.md
- Migration/modernization scenarios where understanding existing domain is prerequisite

## The Dual-Hat Approach

### Arch Hat (架构师视角)

Focus: **What domain concepts exist?**

Scan targets:
- Struct/class definitions → candidate domain entities
- Interface/protocol definitions → candidate ports
- Constants/enums → candidate domain values and states
- Package/module names → candidate bounded contexts
- Error types → candidate domain sentinels
- Function signatures → candidate use cases

### QA Hat (质量分析师视角)

Focus: **What's missing, inconsistent, or undocumented?**

Scan targets:
- Naming inconsistencies → candidate drift / banned terms
- Undocumented side effects → candidate hidden invariants
- Missing error handling → candidate edge cases
- Cross-module dependencies → candidate BC boundary violations

## Mining Depth Levels

| Level | Scope | Time | Output |
|-------|-------|------|--------|
| **Surface Scan** | Type definitions only (structs, interfaces, constants) | ~15 min | Draft term list |
| **Deep Scan** | Function bodies, control flow, error paths | ~45 min | Invariants, use cases, edge cases |
| **Full Archaeology** | Git history, PR descriptions, commit messages | ~2 h | Evolution context, deprecated terms |

**Start with Surface Scan.** Only go deeper when the user confirms value.

## Step-by-Step Protocol

### Step 1: Structural Scan (Arch Hat)

```bash
# Go projects
grep -rn "^type .* struct" internal/domain/ internal/port/
grep -rn "^type .* interface" internal/port/ internal/usecase/

# Python projects
grep -rn "class .*:" src/*/domain/
grep -rn "class .*Protocol" src/*/port/

# Java projects
grep -rn "public class\|public record\|public interface" src/main/java/*/domain/
```

### Step 2: Build Draft Dictionary

Map extracted identifiers to draft LANGUAGE.md entries:

| Code Identifier | Draft Chinese | Draft English | Layer | Notes |
|----------------|---------------|---------------|-------|-------|
| `AgentEntry` | 代理条目 | Agent Entry | Domain | Main entity |
| `CensusStore` | 灵簿存储 | Census Store | Port | Interface |

### Step 3: Gap Analysis (QA Hat)

For each draft entry: Is there a definition? Synonyms to ban? Correct layer? Undocumented behaviors?

### Step 4: User Confirmation

Present draft dictionary. User marks: ✅ Correct / ✏️ Modify / ❌ Delete / ❓ Discuss.

### Step 5: Normal Grilling

Switch to standard arch-align Grilling to fill remaining gaps, confirm PoEAA pattern, define Tracer Bullet.

## Anti-Patterns to Avoid

- **Don't mine test files first** — tests describe expected behavior, not actual domain
- **Don't trust comments** — prefer structure over prose
- **Don't mine infrastructure types** — `PostgresAdapter` is not a domain term
- **Don't skip user confirmation** — extracted terms are hypotheses, not facts
