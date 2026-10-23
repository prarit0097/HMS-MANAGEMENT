# Local development

Use synthetic fixtures only. Read [HMS.md](../../HMS.md), [plan.md](../../plan.md), the [active contract](../implementation/phase-a-contract.md) and [ledger](../implementation/ledger.md) first. Production, staging, cloud credentials and real patient records are outside this local setup.

The host workflow uses Python3.13 and Node24/npm11, with Python packages pinned in [backend/requirements.txt](../../backend/requirements.txt) and frontend packages in [package-lock.json](../../frontend/package-lock.json). The optional container definitions pin Python3.13.17, Node24.22.1 and PostgreSQL17.11 image tags. Tags are not immutable digests; image pull/build/runtime and vulnerability review still require verification. [PostgreSQL version policy](https://www.postgresql.org/support/versioning/) and the official [Python](https://hub.docker.com/_/python) / [Node](https://hub.docker.com/_/node) image catalogues informed these local image choices. Docker is unavailable in the implementation workspace, so no Compose startup or container test pass is claimed.

## Windows without Docker

From the repository root in PowerShell:

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
$env:HMS_ENV = 'development'
$env:HMS_DB_ENGINE = 'sqlite'
$env:HMS_SECRET_KEY = (backend/.venv/Scripts/python.exe -c "import secrets; print(secrets.token_urlsafe(48))")
Push-Location backend
.venv/Scripts/python.exe manage.py migrate
$demoUsername = Read-Host 'Choose a new synthetic demo username'
$demoPassword = Read-Host 'Choose a private demo password (at least 12 characters)' -AsSecureString
$env:HMS_DEMO_PASSWORD = [System.Net.NetworkCredential]::new('', $demoPassword).Password
.venv/Scripts/python.exe manage.py seed_demo --username "$demoUsername"
Remove-Item Env:HMS_DEMO_PASSWORD
.venv/Scripts/python.exe manage.py runserver 127.0.0.1:8000
```

Keep that terminal open. In another PowerShell terminal from the repository root:

```powershell
Set-Location frontend
npm ci --no-audit --no-fund
npm run dev
```

Open [the local workspace](http://127.0.0.1:5173) and sign in with the individual username/password you chose. The seed command is development-only and refuses to reset an existing username. It creates clearly synthetic patients, appointments and beds. No default administrator exists. The seed account has explicit reception and master-admin assignments; master-admin alone does not grant clinical access. SQLite is a fast development option; it does not verify row-lock or PostgreSQL concurrency behavior.

For native PostgreSQL instead, provision an isolated local database and an individual local development role first. Before starting Django, set `HMS_DB_ENGINE=postgresql`, `HMS_DB_NAME`, `HMS_DB_USER`, private `HMS_DB_PASSWORD`, `HMS_DB_HOST=127.0.0.1`, `HMS_DB_PORT=5432`, `HMS_ALLOWED_HOSTS=127.0.0.1,localhost,testserver` and `HMS_DB_SSLMODE=disable`. Set environment variables in the backend terminal without pasting credentials into committed files. `disable` is accepted only in development; staging/production require PostgreSQL/TLS and explicit configuration. PostgreSQL pytest needs permission to create/drop its isolated test database; never point tests at a production database.

## Optional local containers

Install Docker with Compose support separately. From repository root, copy the template, fill it with private local values, then validate/build:

```powershell
Copy-Item infra/.env.example infra/.env.local
# Edit infra/.env.local privately: nonempty DB name/user/password and session secret.
docker compose --env-file infra/.env.local config --quiet
docker compose --env-file infra/.env.local up --build -d
docker compose --env-file infra/.env.local ps
```

Do not print rendered `docker compose config` in shared logs; it can reveal environment secrets. Missing values intentionally stop startup. No automatic account creation or production credentials are supplied. After services become healthy, create a new synthetic account:

```powershell
$demoUsername = Read-Host 'Choose a new synthetic demo username'
$demoPassword = Read-Host 'Choose a private demo password (at least 12 characters)' -AsSecureString
$env:HMS_DEMO_PASSWORD = [System.Net.NetworkCredential]::new('', $demoPassword).Password
docker compose --env-file infra/.env.local exec -e HMS_DEMO_PASSWORD backend python manage.py seed_demo --username "$demoUsername"
Remove-Item Env:HMS_DEMO_PASSWORD
```

The workspace uses [127.0.0.1:5173](http://127.0.0.1:5173), and the minimal API probe is [127.0.0.1:8000/api/v1/health/](http://127.0.0.1:8000/api/v1/health/). PostgreSQL has no published host port. The frontend talks to backend over an internal web network; backend alone joins the internal data network. Both published application ports bind loopback. No proxy range is implicitly trusted, so development IP restrictions cannot be treated as a production edge design. The local stack deliberately uses Django runserver, Vite and HTTP; production requires a reviewed edge/TLS setup, application server, secret store, database identities/TLS, worker/storage/network limits, monitoring and recovery.

`docker compose --env-file infra/.env.local down` stops containers and preserves the named development database volume. `down --volumes` destroys that local database and requires deliberately choosing to discard it; do not use it to solve an unexplained data issue. These volumes do not constitute tested backups. Rebuild after source changes because this stack copies source rather than mounting the host checkout.

## Checks and evidence

Backend (from `backend/`):

```powershell
.venv/Scripts/python.exe manage.py check
.venv/Scripts/python.exe manage.py makemigrations --check --dry-run
.venv/Scripts/python.exe -m pytest -q
```

Frontend (from `frontend/`):

```powershell
npm run typecheck
npm test -- --run
npm run build
```

Repository checks (from root):

```powershell
python -m venv infra/.venv
infra/.venv/Scripts/python.exe -m pip install -r infra/requirements-checks.txt
python -m unittest discover -s scripts/tests -v
infra/.venv/Scripts/python.exe -m openapi_spec_validator docs/api/openapi-v1.yaml
python scripts/check_project_docs.py --links-only --api-contract
# After a completed commit, choose its prior commit SHA:
python scripts/check_project_docs.py --base <prior-sha> --head HEAD --api-contract
```

The [CI workflow](../../.github/workflows/checks.yml) runs documentation/usage guard tests, OpenAPI/map checks, Compose configuration validation, backend tests against disposable PostgreSQL, and frontend type checks/tests/build. A workflow file is not evidence of a successful GitHub run. The documentation gate checks every nonmerge commit in the range for meaningful `HMS.md` and `plan.md` updates; it checks synchronization, not factual correctness. Planned future paths in inline/fenced code are not treated as broken Markdown links.

CSRF errors require a current cookie and `X-CSRFToken`; reauthenticate after a server secret change. Permission errors require the correct assignment at the selected branch. A bed/version conflict requires refresh and review before retry. Backend and frontend servers, seed data, PostgreSQL transaction checks, container startup and cloud deployment are distinct evidence; report exactly what was executed.
