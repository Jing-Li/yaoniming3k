# Frontend Performance Rules — Top 30 for AI-Generated Code

Source: Vercel React Best Practices (70 rules, 8 categories). Curated to the 30 most relevant for AI-generated frontend code.

Used by: dx-review Pass 2 (Performance Audit).

---

## How to Use

Scan generated code against these rules in priority order. Report format:

```
rule-id | file:line | problem description | fix suggestion
```

Severity mapping:
- P1 (CRITICAL) hit → BLOCKING (must fix before PASS)
- P2 (HIGH) hit → WARNING (should fix, does not block alone)
- P3 (MEDIUM) hit → INFO (record, fix if convenient)
- P4 (LOW) hit → INFO (optional polish)

---

## P1 — CRITICAL

| Rule ID | One-liner | Bad Pattern | Good Pattern |
|---------|-----------|-------------|--------------|
| bundle-barrel-imports | Import directly, never from index/barrel files | `import { Button } from '@/components'` | `import { Button } from '@/components/button'` |
| bundle-dynamic-imports | Lazy-load heavy components not needed on first paint | `import Chart from './Chart'` (static) | `const Chart = dynamic(() => import('./Chart'))` |
| async-parallel | Independent async ops must run concurrently | `await a(); await b(); await c();` | `await Promise.all([a(), b(), c()])` |
| async-suspense-boundaries | Use Suspense to stream content, not block entire page | Single loading spinner for whole page | `<Suspense fallback={<Skeleton/>}><Data/></Suspense>` per section |

---

## P2 — HIGH

| Rule ID | One-liner | Bad Pattern | Good Pattern |
|---------|-----------|-------------|--------------|
| rendering-content-visibility | Skip rendering off-screen content | All 500 list items render immediately | `content-visibility: auto` on below-fold sections |
| server-hoist-static-io | Static assets (fonts, logos) load at module level | Font fetched inside component render | `const font = loadFont()` at module top |
| bundle-defer-third-party | Analytics/logging load AFTER hydration | `<Script src="analytics.js">` in head | Load on `window.onload` or `requestIdleCallback` |
| rendering-resource-hints | Preload critical resources explicitly | Browser discovers resources late | `<link rel="preload" href="/hero.webp" as="image">` |
| bundle-conditional | Load feature modules only when activated | Import all features upfront | `if (featureFlag) { import('./Feature') }` |

---

## P3 — MEDIUM

| Rule ID | One-liner | Bad Pattern | Good Pattern |
|---------|-----------|-------------|--------------|
| rerender-no-inline-components | Never define components inside components | `function Parent() { function Child() {...} }` | Define Child outside Parent |
| rerender-derived-state-no-effect | Derive state during render, not in useEffect | `useEffect(() => setFiltered(...), [items])` | `const filtered = useMemo(() => ..., [items])` |
| rendering-hydration-no-flicker | Client-only data must not cause hydration flash | Render server → client mismatch visible | Inline script sets initial state before hydration |
| rerender-functional-setstate | Use functional form for state updates in callbacks | `onClick={() => setCount(count + 1)}` | `onClick={() => setCount(c => c + 1)}` |
| rendering-conditional-render | Use ternary for conditionals, not && | `{show && <Modal/>}` (renders `false`) | `{show ? <Modal/> : null}` |
| rerender-defer-reads | Don't subscribe to state only used in callbacks | `const { data } = useQuery(); onClick uses data` | Read data inside the callback |
| rerender-memo | Extract expensive subtrees into memoized components | Heavy list re-renders on parent state change | `const MemoList = memo(ExpensiveList)` |
| rerender-split-combined-hooks | Split hooks with independent dependencies | One hook returns [a, b] with different update cycles | Separate hooks for a and b |
| rendering-hoist-jsx | Static JSX (no props/state) lives outside component | `<Footer/>` re-created every render | `const footer = <Footer/>` at module level |
| rerender-transitions | Non-urgent updates use startTransition | Filter update blocks input typing | `startTransition(() => setFilter(val))` |
| client-swr-dedup | Use SWR/React Query for automatic request dedup | Multiple components fetch same endpoint | Shared SWR key deduplicates automatically |

---

## P4 — LOW

| Rule ID | One-liner | Bad Pattern | Good Pattern |
|---------|-----------|-------------|--------------|
| js-set-map-lookups | Use Set/Map for O(1) lookups in loops | `array.includes()` inside loop | `const set = new Set(array); set.has()` |
| js-early-exit | Return early to reduce nesting | Deep if/else pyramid | Guard clauses at top |
| js-combine-iterations | One pass instead of chained filter/map | `arr.filter(...).map(...).filter(...)` | Single `reduce` or `flatMap` |
| js-cache-function-results | Memoize expensive pure functions | Recalculate on every call | Module-level Map cache |
| rendering-svg-precision | Reduce SVG coordinate decimal places | `d="M10.123456 20.654321..."` | Round to 2 decimals |
| js-request-idle-callback | Defer non-critical work to browser idle | Heavy computation on main thread at load | `requestIdleCallback(() => heavyWork())` |

---

## Scan Procedure (dx-review Pass 2)

1. Identify all `.tsx` / `.jsx` / `.ts` / `.js` files in the generated frontend.
2. For each file, check rules in priority order (P1 first).
3. P1 hit → add to Drift List as BLOCKING.
4. P2 hit → add as WARNING.
5. P3/P4 hit → add as INFO.
6. If ≥1 BLOCKING → Performance verdict = FAIL.
7. If 0 BLOCKING but ≥3 WARNING → Performance verdict = FAIL.
8. Otherwise → Performance verdict = PASS.
