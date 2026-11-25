---
name: ui-foundations
description: Tokens, themes, type, layout, motion, and accessibility rules for every Agentic AI Tools web UI. Use when reading or editing **/*.tsx, **/*.ts, **/*.css.
---

# UI foundations

Stack: TypeScript, React 19, Vite, React Router, TanStack Query. Plain CSS with custom-property tokens, no CSS framework. Shared tokens, fonts, icons, and components come from `@agentic-ai-tools/ui` once it exists.

- Components reference tokens only. A hard-coded colour breaks the light theme and review rejects it. Dark values live on `:root`, light values on `[data-theme="light"]` and `@media print`. Dark is the default.
- The cyan, blue, and violet ring (`--grad-brand`) marks only the active step, a selected card, a panel's top edge, and a hero. Never body text, never data colour.
- `--signal` is for reached steps, checked controls, focus, status dots, and links. `--grad-action` with `--on-action` is for the one primary button per view.
- Spacing uses `--space-1` to `--space-7`, corners use `--radius-sm`, `--radius-md`, `--radius-lg`, `--radius-pill`. Breakpoints are 860px and 560px.
- Fonts are self-hosted WOFF2 (Syne for display, Figtree for body, system monospace for code). No Google Fonts CDN.
- Numbers in tables, metrics, and money use `font-variant-numeric: tabular-nums`.
- Interaction transitions are 160 to 180ms `ease`. `prefers-reduced-motion: reduce` turns off non-essential animation.
- WCAG 2.2 AA in both themes. Every interactive element shows `--focus` on `:focus-visible`. Never remove an outline without that replacement.
- Native radios, checkboxes, and selects stay native. A radio group is a `fieldset` named by a `legend`.
- Colour is never the only signal: status, decisions, evidence type, and validation carry text or a labelled icon.
- Asynchronous status uses `role="status"` with `aria-live="polite"`. A blocking error uses `role="alert"`. A field error sets `aria-invalid` and links its message with `aria-describedby`.
- Icons render with `aria-hidden="true"` unless they carry meaning alone, then they get a `label`.
- Every flow can be completed by keyboard, and a Playwright test covers it.
- A feature the API reports as off is hidden. The portal never decides on its own.
- Every product page shows the ecosystem lockup in the header and the standard footer.
