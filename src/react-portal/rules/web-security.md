---
description: Security and resilience rules for portals and SPAs - tokens, rendering untrusted content, CSP, and failure states
globs: ["**/*.tsx", "**/*.ts", "**/*.html"]
---

# Web security and resilience

- Sign-in is OIDC authorization code with PKCE. Access tokens stay in memory or in `HttpOnly` cookies, never in `localStorage` or `sessionStorage`.
- Never use `dangerouslySetInnerHTML`, `innerHTML`, or `eval`. Render user and model content as text. Markdown from a model or a user is rendered with HTML disabled and links sanitised.
- Links to other origins use `rel="noopener noreferrer"`. Never build a URL, a route, or a CSS value from model output without validating it.
- The page is served with a strict content security policy (no `unsafe-inline` scripts, no `unsafe-eval`), HSTS, `frame-ancestors 'none'`, and `X-Content-Type-Options: nosniff`. Do not add a third-party script or CDN without a review.
- Everything in the built bundle is public. `VITE_` variables and source maps never contain secrets.
- The portal never decides access. It hides what the API refuses and handles 401 and 403 from the API.
- Wrap each route in an error boundary that shows a recoverable error, not a blank page.
- Queries retry only idempotent reads, with backoff. Mutations do not retry automatically. Polling backs off and stops when the resource is final or the page is hidden.
- Every asynchronous view has explicit loading, failed, and retry states. Work still pending past its server timeout is shown as failed with a retry.
- A test covers each: a token absent from storage, model markup rendered as text, an error boundary, and a failed-then-retried request.
