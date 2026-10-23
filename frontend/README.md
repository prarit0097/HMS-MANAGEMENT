# Hospital staff workspace

Phase A is a local development slice. It is not approved for production or real patient data.

## Pre-code review

The frozen `/api/v1/` contract in `../docs/implementation/phase-a-contract.md` governs this frontend. Every list, count, detail and mutation comes from the API. Session cookies remain browser-managed; mutations use the current CSRF cookie after bootstrap and after token rotation. No clinical records, credentials or tokens are persisted in browser storage.

Pages: sign in; branch-scoped dashboard; patient search, registration and demographics; appointment scheduling and versioned status; bed board and admission; permissioned nonclinical master summary. Primary actions are role-gated conveniences; backend permissions remain authoritative. Unsupported clinical, financial, backup and MFA operations are labelled unavailable.

Failure review: anonymous bootstrap returns login; denied requests retain a clear access message; connection failures offer retry; no patient results use an empty state; loading disables duplicate form submit; rejected forms retain values and field errors; branch switches remount scoped views; stale appointment/bed updates report backend conflict and require reload. Search is bounded and paginated. Status labels accompany colour; occupied/reserved beds are green and available beds red as specified by the owner.

Acceptance/test design: transport must attach cookies/current CSRF and propagate denied/field/offline errors; keyboard registration opens at its first field and Escape closes; rejected registration retains values; platform-only users have no patient navigation; invalid login preserves username. API fetch is replaced only at its network boundary in component tests, using synthetic records.

UI/UX Pro Max minimal enterprise guidance, high contrast and async form guidance applied. Marketing hero recommendation was rejected as unsuitable for staff work. System fonts avoid third-party font requests. CSS targets desktop and small screens, with reduced motion and visible keyboard focus.

## Run

Use Node 24 and npm 11. From this directory run `npm ci`, then `npm run dev`. Vite binds to `127.0.0.1`; `/api` proxies to the Django server at `127.0.0.1:8000`. Start that server and create an authorised synthetic account using the backend instructions. Never commit passwords.

Checks: `npm run typecheck`, `npm run test -- --run`, `npm run build`. `npm run lint` is currently a TypeScript static check, not a separate ESLint ruleset.

Production hosting must terminate HTTPS, enforce its own security headers and expose the UI and backend on one origin or configure the reviewed equivalent. Vite development server is not a production server.
