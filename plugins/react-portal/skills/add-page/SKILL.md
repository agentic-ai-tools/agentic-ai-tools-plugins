---
name: add-page
description: Add a portal page built and tested against MSW handlers driven by the contract fixtures, before the API exists. Use when asked to add a page, view, or route to a portal or SPA.
---

# Add a page against MSW fixtures

1. Find the operations the page calls in the published contract and its fixtures. Add MSW handlers that serve those fixtures, including the problem+json error fixtures.
2. Write the failing Vitest and Testing Library test: the page renders the fixture data, shows the loading state in a `role="status"` region, and shows each error.
3. Add the route with React Router and fetch with TanStack Query. Never hard-code data the API returns.
4. Build the page from shared components and tokens only. One primary action per view. Hide any feature the API reports as off.
5. Add a Playwright test that completes the page's flow by keyboard.
6. Run `oxlint`, `tsc -b`, and the tests until clean.
