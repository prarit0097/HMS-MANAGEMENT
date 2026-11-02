# The Circadian Rhythm Hospital HMS

An API-first hospital workspace under active development. Phase A covers a bounded synthetic-data foundation; this repository is **not a deployed production hospital system**.

Owner-authorised authenticated preview: https://hms.praritsidana.com . Synthetic testing only; [deployment evidence, isolation and operations](docs/operations/HOSTINGER-PREVIEW.md). Credentials are private and never in this repository.

Read [HMS.md](HMS.md), [plan.md](plan.md) and [AGENTS.md](AGENTS.md) before changing the project. The [current capability inventory](HMS.md#consolidated-current-status-2-november-2026), [task completion map](plan.md#current-task-completion-map-2-november-2026) and [execution ledger](docs/implementation/ledger.md) identify delivered scope, remaining work and evidence. The Phase A contract is the historical initial slice.

- [Local Windows setup and optional Compose stack](docs/operations/LOCAL-DEVELOPMENT.md)
- [OpenAPI v1 source](docs/api/openapi-v1.yaml), [page-action map](docs/api/page-actions-v1.json) and [API compatibility/security notes](docs/api/README.md)
- [Backend instructions](backend/README.md) and [frontend instructions](frontend/README.md)
- [Automated CI checks](.github/workflows/checks.yml)

The frontend calls versioned authorised APIs using a session cookie and CSRF. No default staff credentials, patient data, backups or cloud resources are included. Bounded MFA/session/recovery codes, scoped staff/resources/history/network and reception are implemented in the recorded restricted preview. Document foundations through B2a-L are deployed with the feature disabled; metadata business services/HTTP/UI, clinical signing, full department workflows, data movement and remote MCP remain gated work. GitHub publication does not deploy the application.
