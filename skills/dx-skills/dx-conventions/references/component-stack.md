# Component Stack — Recommended Initialization

Source: Web Artifacts Builder (Anthropic) + dx pipeline conventions.

Used by: dx-image-to-code, dx-url-to-code, dx-prototype (project initialization).

---

## Default Stack

When initializing a new frontend project (no existing project detected), use:

| Layer | Choice | Version |
|-------|--------|---------|
| Framework | React | 18+ |
| Language | TypeScript | 5+ (strict: true) |
| Build | Vite | 5+ |
| Styling | Tailwind CSS | 3.4+ |
| Components | shadcn/ui | latest (40+ components) |
| Icons | Lucide React | latest |
| State | React hooks + context (simple) / Zustand (complex) | — |
| Routing | React Router | 6+ |
| Bundling (single-file output) | Parcel + html-inline | — |

---

## Initialization Checklist

When dx-image-to-code or dx-url-to-code creates a new project:

1. **Scaffold**: `npm create vite@latest <name> -- --template react-ts`
2. **Tailwind**: Install + configure `tailwind.config.ts` with content paths
3. **shadcn/ui**: `npx shadcn-ui@latest init` → install ALL base components:
   - button, input, label, textarea, select, checkbox, radio-group, switch
   - card, dialog, dropdown-menu, popover, tooltip, sheet
   - tabs, accordion, collapsible, separator
   - table, badge, avatar, progress, skeleton, spinner
   - alert, toast, form
   - navigation-menu, menubar, breadcrumb, pagination
   - slider, calendar, command, combobox
4. **Path alias**: Configure `@/` → `./src/` in tsconfig + vite.config
5. **Design tokens**: Create CSS variables from `dx/design-system.md` palette/spacing in `src/index.css`
6. **Structure**:
   ```
   src/
   ├── components/       # shadcn/ui components (auto-generated)
   ├── components/ui/    # shadcn/ui primitives
   ├── features/         # feature-specific components
   ├── layouts/          # page layouts
   ├── pages/            # route pages
   ├── hooks/            # custom hooks
   ├── lib/              # utilities (cn(), etc.)
   ├── styles/           # global CSS, design tokens
   ├── App.tsx
   └── main.tsx
   ```

---

## Existing Project Detection

Before initializing, check if a project already exists:

```
IF package.json exists AND has "react" in dependencies
THEN → reuse existing project, do NOT reinitialize
  - Check if Tailwind is configured → if not, add it
  - Check if shadcn/ui is present → if not, offer to add (AskUserQuestion)
  - Read existing design tokens / CSS variables → use them
ELSE → full initialization per checklist above
```

---

## Design Token Integration

After generating `dx/design-system.md`, translate tokens into CSS variables:

```css
/* src/styles/tokens.css — generated from dx/design-system.md */
:root {
  --color-primary: #xxxxxx;
  --color-secondary: #xxxxxx;
  --color-accent: #xxxxxx;
  --color-surface: #xxxxxx;
  --color-text: #xxxxxx;
  --color-muted: #xxxxxx;

  --font-display: "Font Name", sans-serif;
  --font-body: "Font Name", sans-serif;
  --font-utility: "Font Name", monospace;

  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 32px;
  --space-xl: 64px;

  --container-max: 1200px;
  --content-max: 65ch;
}
```

Map to Tailwind config:

```typescript
// tailwind.config.ts
export default {
  theme: {
    extend: {
      colors: {
        primary: 'var(--color-primary)',
        secondary: 'var(--color-secondary)',
        accent: 'var(--color-accent)',
        surface: 'var(--color-surface)',
        // text and muted override Tailwind defaults
      },
      fontFamily: {
        display: 'var(--font-display)',
        body: 'var(--font-body)',
        utility: 'var(--font-utility)',
      },
      spacing: {
        xs: 'var(--space-xs)',
        sm: 'var(--space-sm)',
        md: 'var(--space-md)',
        lg: 'var(--space-lg)',
        xl: 'var(--space-xl)',
      },
      maxWidth: {
        container: 'var(--container-max)',
        content: 'var(--content-max)',
      },
    },
  },
}
```

---

## Anti-Slop Reminder

Per `anti-slop-rules.md`:
- Do NOT default to Inter font. Choose deliberately from design-system.md.
- Do NOT add purple gradients unless the design system calls for it.
- Do NOT center everything. Follow the Layout Concept from design-system.md.
- shadcn/ui components are a starting point — customize radius, colors, and shadows to match the design system.

---

## Single-File Bundle (Optional)

For artifact delivery (sharing in conversation, embedding):

```bash
# Install bundling deps
npm install -D parcel @parcel/config-default parcel-resolver-tspaths html-inline

# Bundle to single HTML
npx parcel build index.html --no-source-maps
npx html-inline dist/index.html > bundle.html
```

This is optional — most projects run as normal dev servers. Only bundle when the user needs a self-contained HTML file.
