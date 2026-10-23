# Phase A backend (development foundation)

Use Python 3.13. In this directory:

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python manage.py migrate
# Supply HMS_DEMO_PASSWORD through a private environment, never a committed file.
.venv/Scripts/python manage.py seed_demo --username YOUR_LOCAL_USERNAME
.venv/Scripts/python manage.py runserver 127.0.0.1:8000
.venv/Scripts/python -m pytest
```

The development database is SQLite and contains synthetic data only. `HMS_ENV=production` requires explicit secret key, allowed hosts and PostgreSQL host/name/user/password. This scaffolding has no production deployment, MFA, remote OAuth, backup/restore, clinical-signing or financial capability. Do not use real records. PostgreSQL concurrency testing and independent production security review remain release gates.

All browser mutation calls use Django sessions and CSRF (`GET /api/v1/auth/csrf/`, then `X-CSRFToken` header). No Django admin mutation routes are installed. `master_admin` alone has configuration inventory access; assign an operational role separately to access patient data.

Pre-code cases: anonymous/CSRF rejection; invalid-login enumeration and throttle; explicit organisation/branch membership; role mutation limits; duplicate phone identities; appointment check-in retry/version; bed and patient active-allocation uniqueness; cross-branch rejection; scoped dashboard and master configuration inventory. SQL constraints and transactions protect serial allocation; SQLite tests do not establish PostgreSQL concurrency behavior.

Network policy environment: comma-separated `HMS_TRUSTED_PROXIES`, `HMS_IP_ALLOWLIST`, `HMS_IP_BLOCKLIST`; `HMS_IP_ALLOWLIST_ONLY=1`. No forwarded proxy settings are enabled automatically. Production must have an approved edge-only origin path and policy/recovery configuration before exposure.

Patients currently have an immutable registration branch which determines organisation identity, with globally unique UHIDs. This slice restricts operational use to that branch; organisation-wide sharing across branches remains planned and must retain the existing UHID rather than duplicate patients. Room/villa exclusivity, reservations, transfer and discharge/cleaning workflows remain planned.

To run PostgreSQL checks locally/CI, set `HMS_DB_ENGINE=postgresql`, `HMS_DB_NAME`, `HMS_DB_USER`, `HMS_DB_PASSWORD`, `HMS_DB_HOST`, `HMS_ALLOWED_HOSTS`; optional `HMS_DB_PORT` (5432) and `HMS_DB_SSLMODE` (disable in local development only). Run the same pytest command. The concurrent two-allocator test explicitly skips on SQLite. Login throttling currently uses per-process Django cache: durable shared throttling/edge abuse protection remains a production gate. Audit rows record mutations but are not a complete immutable production access audit.
