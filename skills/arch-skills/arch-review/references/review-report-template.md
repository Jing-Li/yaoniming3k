# Standard Review Report Template

The canonical report structure for `arch-review` Audit Mode. Every review response **must** use exactly these sections, in this order.

---

## 1. Architecture Health Score

```
Score: NN / 100
  - Dependency Rule        : nn / 25
  - Domain Purity          : nn / 20
  - Persistence Decoupling : nn / 20
  - Pattern Application    : nn / 15
  - Naming Alignment       : nn / 10
  - Security Posture       : nn / 10   (v2.9.0+)
Verdict: 🟢 Healthy (≥85) | 🟡 At Risk (60–84) | 🔴 Critical (<60)
```

## 2. Critical Violations (must block merge)

For each violation:

```
[R-1] <Short title>
  Location  : path/to/file.go:Lxx-Lyy
  Violation : <one-sentence rule broken>
  Evidence  : <quoted code snippet, ≤6 lines>
  Impact    : <long-term cost: testability, change amplification, framework lock-in, etc.>
  Reference : <Clean Arch / PoEAA / GoF chapter>
```

Red-card categories (any of these = automatic Critical):
- Domain → Infrastructure / Framework / Driver import
- Domain class annotated with framework metadata (`@Entity`, `@Component`, `Mapped[...]`, etc.)
- Port interface defined inside an adapter package
- Use case directly instantiating a concrete adapter (no DI)
- Persistence row class used as domain entity in business logic

## 3. Warnings & Suggestions (optimization recommended)

For each warning:

```
[Y-1] <Short title>
  Location   : path/to/file.go:Lxx
  Concern    : <ISP violation / naming drift / missing pattern / fat use case>
  Suggestion : <concrete next step>
```

Yellow-card categories:
- Naming drift from `LANGUAGE.md`
- Fat port (mixed read/write/admin) — ISP candidate
- Missing pattern (long `if-else` chain — Strategy / State candidate)
- Missing context propagation (Go) / missing async boundary (Python)
- Adapter leaking driver-specific errors past the port

## 4. Refactoring Diff

Provide a clear, language-specific **before / after** diff per Critical violation. See [reference.md](../reference.md) §4 for templates.

## 5. Architecture Debt Routing & Introspection

For each finding (R-x, Y-x), produce one Architecture Debt entry:

```
| ID | Title | Severity | Route | Violation IDs | Root Cause | Status |
|----|-------|----------|-------|---------------|------------|--------|
| AD-001 | <title> | 🔴 Critical | `/devtdd` | R-1 | <why missed> | 🆕 New |

**Severity Grading (v2.9.0+)**: Every AD MUST carry a severity grade:
- 🔴 **Critical** — blocks merge/deploy, −50% axis weight
- 🟠 **Major** — should fix before next release, −20% axis weight
- 🟡 **Minor** — can defer, −10% axis weight (capped −50% per axis)
- 🟢 **Positive** — notable good practice, no deduction
For every 3+ Critical/Major findings, include 1+ Positive finding.
See [review-feedback-rules.md](review-feedback-rules.md) for full grading criteria.
```

Then output Skill Evolution as ADs (routed to the skill itself):

> **Note**: Skill Evolution is expressed as AD entries routed to the target skill (e.g., `AD-R1 → arch-review-self`). There is no separate SE table. See Constraint #7 (Introspection).

## 6. Version Diff

If T{N}.md Change History contains previous review scores, output:

```
Δ Score: NN → NN (+/-N)
New findings: N | Resolved: N | Regressions: N
```

List each regression explicitly (a previously resolved item that reappeared).

## 7. Resolution Verification

If T{N}.md has any ADs previously marked ✅ Resolved, output:

```
Verified N previously resolved ADs:
  ✅ AD-xxx: <brief description> — fix confirmed
  ✅ AD-yyy: <brief description> — fix confirmed
  ⚠️ AD-zzz: REGRESSION — <what reappeared>
```

If no previously resolved ADs exist, output: "No previously resolved ADs to verify."

## 8. Pipeline Health (cross-phase task tracking)

Output the open AD/SE counts for ALL BCs:

```
[ayuan]          AD: N open
[taiyi-platform] AD: N open
```

Flag stale debt (open for 2+ review versions) and list specific SE items awaiting adoption.

## 9. Decision Challenge Summary (v3.0.0+)

After applying critical reasoning patterns (Step 8e), output:

```
Decisions challenged: N
| # | Decision | Pattern Applied | Risk | Outcome |
|---|----------|----------------|------|--------|
| C1 | <decision> | <pattern> | 🔴/🟡/🟢 | survived / needs revision / needs data |

Recommendations:
- <recommendation for each needs-revision decision>
- <specific data to collect for each needs-data decision>
```

This section consolidates the critical reasoning output that was previously handled by the separate `/arch-critic` skill (now merged into arch-review).
