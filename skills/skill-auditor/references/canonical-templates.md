# Canonical Templates & Cross-Validation Tables

> Reference material for D1 structure compliance checking and SkillzWave cross-validation.
> Load ONLY when needed (Step 0 on-demand rule).

---

## Universal Template (all skills)

```
---
name: <kebab-case>
description: "<200-400 chars>"
version: <semver>
---

# <Title>

> Scope Declaration (Input/Output/Does/Does NOT)

You are a [Role Title]. <One-sentence mission>.

Enforcement level: **Rigid | Flexible | Advisory**

## Hard Constraints

## Refusal Protocol

## Steps to Execute

## Output Format (optional, if skill produces structured output)

## Additional Resources (optional)
```

### Section ordering rationale

1. Frontmatter → machine-readable identity
2. Scope Declaration → immediate boundary setting (context position: top = high compliance)
3. Role statement → behavior space constraint
4. Hard Constraints → BEFORE steps (position effect: top-loaded = higher compliance)
5. Refusal Protocol → adjacent to constraints (boundary enforcement cluster)
6. Steps → core execution content
7. Output Format → terminal anchor (position effect: bottom = high compliance)

---

## Pipeline Extension Template (only if skill is part of a pipeline)

```
> Pipeline Context Table (Upstream/Downstream/Owns/Does/Does NOT)

## Hand-off Trigger

## Manifest Protocol (reads/writes declaration)

## [Pipeline-specific Protocol] (e.g., Kanban, Convention refs)
```

**When to apply**: Only when the skill declares Upstream/Downstream relationships or equivalent pipeline positioning.

---

## SkillzWave Cross-Validation Mapping

When a skill scores below 3.5 weighted, cross-validate against the SkillzWave 100-point model:

| SkillzWave Pillar | Max | Maps to Our Dim |
|---|:---:|---|
| Progressive Disclosure Architecture | 30 | D2 |
| Ease of Use | 25 | D3 + D4 |
| Spec Compliance | 15 | D1 |
| Writing Style | 10 | D5 |
| Utility | 20 | D6 |
| Modifiers | ±15 | D7 |

### Scoring conversion

- Our weighted 1-5 scale → SkillzWave 0-100: multiply by 20
- Discrepancy > 15 points between models requires written explanation
- Report both scores in the audit report when cross-validation is performed
