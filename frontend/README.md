# Hospital staff workspace

The frontend serves the bounded synthetic staff workspace in local development and the recorded restricted preview. It is not approved for real hospital data.

## Pre-code review

The frozen `/api/v1/` contract in `../docs/implementation/phase-a-contract.md` governs this frontend. Every list, count, detail and mutation comes from the API. Session cookies remain browser-managed; mutations use the current CSRF cookie after bootstrap and after token rotation. No clinical records, credentials or tokens are persisted in browser storage.

Pages: sign-in/MFA challenge, Account security, branch-scoped dashboard, patient registration/search/demographics, appointments/check-in, bed board/initial admission, branch/bed and staff administration, scoped administration/self-security history, Network access and nonclinical master summary. API-backed selected-branch controls are implemented; backend permissions remain authoritative. Clinical/finance/dataops/document metadata UI remains unavailable. Browser/keyboard/staff and owner phone-import acceptance are still open; component tests do not close those gates. See [current inventory](../HMS.md#consolidated-current-status-2-november-2026).

Failure review: anonymous bootstrap returns login; denied requests retain a clear access message; connection failures offer retry; no patient results use an empty state; loading disables duplicate form submit; rejected forms retain values and field errors; branch switches remount scoped views; stale appointment/bed updates report backend conflict and require reload. Search is bounded and paginated. Status labels accompany colour; occupied/reserved beds are green and available beds red as specified by the owner.

Acceptance/test design: transport must attach cookies/current CSRF and propagate denied/field/offline errors; keyboard registration opens at its first field and Escape closes; rejected registration retains values; platform-only users have no patient navigation; invalid login preserves username. API fetch is replaced only at its network boundary in component tests, using synthetic records.

UI/UX Pro Max minimal enterprise guidance, high contrast and async form guidance applied. Marketing hero recommendation was rejected as unsuitable for staff work. System fonts avoid third-party font requests. CSS targets desktop and small screens, with reduced motion and visible keyboard focus.

## Run

Use Node 24 and npm 11. From this directory run `npm ci`, then `npm run dev`. Vite binds to `127.0.0.1`; `/api` proxies to the Django server at `127.0.0.1:8000`. Start that server and create an authorised synthetic account using the backend instructions. Never commit passwords.

Checks: `npm run typecheck`, `npm run test -- --run`, `npm run build`. `npm run lint` is currently a TypeScript static check, not a separate ESLint ruleset.

Production hosting must terminate HTTPS, enforce its own security headers and expose the UI and backend on one origin or configure the reviewed equivalent. Vite development server is not a production server.
