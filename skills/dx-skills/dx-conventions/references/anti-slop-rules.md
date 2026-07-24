# Anti-Slop Rules — AI Template Detection

Source: Anthropic Frontend Design skill + community observations.

These rules detect when AI-generated UI falls into generic "AI slop" patterns. Used by:
- dx-image-to-code / dx-url-to-code: to AVOID these patterns during generation
- dx-review: to DETECT these patterns during conformance audit

---

## The Three Default Looks (CRITICAL)

AI-generated design currently clusters around three aesthetics. They are legitimate for SOME briefs, but they are **defaults rather than choices**. If the brief does NOT explicitly request one of these looks and the output matches → **P0 DRIFT**.

### Default 1: "Warm Artisan"

| Signal | Threshold |
|--------|-----------|
| Background | Near #F4F1EA (warm cream / off-white) |
| Display font | High-contrast serif (Playfair, Cormorant, DM Serif) |
| Accent | Terracotta / burnt orange (#C4553D range) |
| Vibe | "Handmade pottery studio" |

### Default 2: "Dark Neon"

| Signal | Threshold |
|--------|-----------|
| Background | Near-black (#0A0A0A – #1A1A1A) |
| Accent | Single acid-green (#39FF14) or vermilion (#FF3B30) |
| Typography | Monospace or geometric sans |
| Vibe | "Hacker terminal / crypto dashboard" |

### Default 3: "Broadsheet"

| Signal | Threshold |
|--------|-----------|
| Layout | Dense newspaper-like columns |
| Rules | Hairline borders (1px solid #E0E0E0) everywhere |
| Border-radius | 0 across all elements |
| Typography | Serif body, small caps labels |
| Vibe | "Editorial / literary magazine" |

### Detection Logic

```
IF brief does NOT specify visual direction
AND output matches ≥2 signals of any Default
THEN → P0 DRIFT: "Output matches AI default style '{name}'. Brief did not request this aesthetic."
```

---

## Generic Anti-Patterns (HIGH)

These patterns appear across ALL AI-generated UI regardless of style. Each hit = **P1 DRIFT** unless the brief explicitly calls for it.

| # | Anti-Pattern | What to Look For | Why It's Slop |
|---|-------------|-----------------|---------------|
| 1 | **Excessive centering** | Everything text-align:center, max-w-md mx-auto | Real products have asymmetric structure |
| 2 | **Purple gradient** | `from-purple-600 to-blue-500` or similar | The "AI startup" gradient, used regardless of brand |
| 3 | **Uniform large radius** | rounded-2xl / rounded-3xl on everything | No hierarchy — buttons, cards, inputs all same radius |
| 4 | **Inter everywhere** | font-family: Inter (no display/body distinction) | The "I didn't think about typography" choice |
| 5 | **Meaningless numbering** | 01 / 02 / 03 markers on non-sequential content | Decorative structure that encodes nothing |
| 6 | **Hero big-number** | Large stat + tiny label as the opening statement | The "dashboard landing page" template answer |
| 7 | **Gradient text** | bg-clip-text text-transparent on headings | Overused "modern" signal |
| 8 | **Blob shapes** | SVG blobs / amoeba shapes as decoration | The "SaaS landing page" filler |
| 9 | **Generic icons** | Lucide/Heroicons used without customization | Every AI project uses the same 20 icons |
| 10 | **Cookie-cutter sections** | Hero → Features (3 cards) → Testimonials → CTA | The "landing page template" sequence |

---

## Structural Anti-Patterns (MEDIUM)

These are composition-level issues. Each hit = **P2 DRIFT**.

| # | Anti-Pattern | Description |
|---|-------------|-------------|
| 1 | **No visual hierarchy** | All sections same weight/size — nothing stands out |
| 2 | **Decoration without information** | Dividers, badges, eyebrows that encode nothing about content |
| 3 | **Animation scatter** | Multiple unrelated animations competing (vs one orchestrated moment) |
| 4 | **Responsive afterthought** | Desktop layout shrunk, not redesigned for mobile |
| 5 | **Placeholder copy** | "Lorem ipsum" or "Your amazing product" instead of real content |

---

## How to Use During Generation (dx-image-to-code / dx-url-to-code)

Before writing code, check your design plan:

1. Does my palette match any of the 3 Defaults? → If brief didn't ask for it, revise.
2. Am I reaching for Inter + purple gradient + centered layout? → Stop. Choose deliberately.
3. Is my Signature Element actually specific to THIS brief? → If it could work on any project, it's not a signature.
4. Would I produce something similar for a completely different brief? → If yes, revise.

The goal: **a design that could not be mistaken for any other project's output**.

---

## How to Use During Review (dx-review)

In Pass 1 (Visual Conformance):

1. Screenshot the implementation.
2. Check against the 3 Defaults (≥2 signals = P0 DRIFT).
3. Check against Generic Anti-Patterns (each hit = P1 DRIFT).
4. Check against Structural Anti-Patterns (each hit = P2 DRIFT).
5. Cross-reference with `dx/design-system.md` Anti-Patterns section (project-specific).
6. Report all hits in the Drift List with severity and location.
