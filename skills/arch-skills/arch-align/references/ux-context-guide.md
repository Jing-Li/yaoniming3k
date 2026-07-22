# UX Context Clarification Checklist

Used during arch-align Phase D (optional) to capture user experience layer context for the dx pipeline.

## Device & Platform
- [ ] Target platforms: desktop web / mobile web / native iOS / native Android / cross-platform
- [ ] Responsive requirements: which breakpoints matter?
- [ ] Offline support needed?

## Visual Constraints
- [ ] Existing brand guidelines? (colors, typography, logo usage)
- [ ] Existing design system? (component library, token system)
- [ ] Design token source: Figma / Style Dictionary / Tailwind config / other
- [ ] Accessibility standard: WCAG 2.1 AA / AAA / internal standard

## Key User Journeys (frontend surface)
- [ ] Which user flows need UI design? (list from BRD business flows)
- [ ] Priority order of flows
- [ ] Any existing UI to redesign vs greenfield?

## Interaction Preferences
- [ ] Navigation pattern: sidebar / top nav / tab bar / other
- [ ] Data density preference: compact / comfortable / spacious
- [ ] Animation/motion: minimal / moderate / rich
- [ ] Real-time updates: needed? (WebSocket / SSE / polling)

## Constraints & Non-Goals
- [ ] Browser support requirements (evergreen / IE11 / specific versions)
- [ ] Performance targets for frontend (TTI, FCP, LCP)
- [ ] Third-party integrations visible in UI (SSO, payment widgets, maps)
