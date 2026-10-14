# Employee Salary Management System

ACME People & Pay is an HR application for managing employee profiles and salary history. It includes a React/Vite frontend, a FastAPI backend, SQLAlchemy persistence, authenticated HR workflows, currency-aware analytics, and CSV import/export.

## Contents

- [Features](#features)
- [Technology](#technology)
- [Prerequisites](#prerequisites)
- [Setup from a fresh checkout](#setup-from-a-fresh-checkout)
- [Seed the sample data](#seed-the-sample-data)
- [Run the application](#run-the-application)
- [Sign in](#sign-in)
- [Run tests and checks](#run-tests-and-checks)
- [API overview](#api-overview)
- [CSV import format](#csv-import-format)
- [Configuration](#configuration)
- [Database and backups](#database-and-backups)
- [Deploy for production](#deploy-for-production)
- [Production considerations](#production-considerations)
- [Troubleshooting](#troubleshooting)
- [Project layout](#project-layout)

## Features

- Employee create, update, deactivate, search, filtering, and server-side pagination.
- Salary records retained as dated history, with positive-amount, effective-date, and overlapping-period validation.
- Role-protected access for HR managers and administrators; administrator-only user registration.
- Audit records for employee, salary, and CSV-import changes.
- Workforce analytics and compensation statistics grouped by currency to avoid invalid cross-currency comparisons.
- Employee CSV import with validation before writes, and employee and salary-history CSV export.
- Dashboard, employee directory, profile forms, salary-history screens, reports, and loading/error/empty UI states.

This application manages HR employee and compensation records; it is not a payroll processor. It does not calculate taxes or convert currencies.

## Technology

- **Frontend:** React 19, Vite, JavaScript, npm.
- **Backend:** Python, FastAPI, Pydantic, SQLAlchemy, Uvicorn.
- **Database:** SQLite for the current implementation.
- **Tests:** pytest and FastAPI TestClient.

## Prerequisites

On Windows, install:

- Python 3.11 (recommended; Python 3.10+ is needed for the syntax used).
- Node.js `^20.19.0` or `>=22.12.0` and npm (required by the Vite 8 version in this project).
- Git, if cloning the repository.

Check the tools in PowerShell:

```powershell
py --version
node --version
npm --version
```

## Setup from a fresh checkout

### 1. Get the source

```powershell
git clone <repository-url>
Set-Location .\Employee_Salary_Management_System
```

If you already have the project folder, open PowerShell there instead.

### 2. Create the backend virtual environment and install dependencies

```powershell
Set-Location .\backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell prevents virtual-environment activation, either enable script execution for your user according to your organization’s policy or use the interpreter directly:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 3. Configure the backend for local development

The defaults are suitable for local development. `backend/.env.example` documents the available settings, but the current backend reads environment variables directly and does **not** automatically load a `.env` file.

The database module currently fixes the SQLite file location at `backend\data\salary_management.db`; the `DATABASE_URL` entry in `.env.example` is documentation only and is not currently used to select another database.

Optional local configuration for the current PowerShell session:

```powershell
$env:APP_ENV = "development"
$env:FRONTEND_ORIGIN = "http://localhost:5173"
```

On startup, the backend creates the database tables and, in development mode, creates these demo users if they do not already exist:

| Username | Password | Role |
|---|---|---|
| `hr_manager` | `hr123` | HR manager |
| `admin` | `admin123` | Administrator |

These are local demo credentials only. Do not expose them on a public deployment.

### 4. Install frontend dependencies

Open a **second** PowerShell terminal at the repository root:

```powershell
Set-Location .\frontend
npm ci
```

## Seed the sample data

To generate the 10,000 deterministic synthetic employee records and corresponding initial salary records, run this from the backend directory:

```powershell
Set-Location .\backend
.\.venv\Scripts\python.exe .\scripts\seed_data.py
```

The seed script adds missing seeded employee codes and salary records; it does not clear the database. It uses fictional/sample records and may be run again to fill missing rows.

You may skip this step for an empty application. The dashboard and directory will start with no employee records, and employees can be added in the UI.

## Run the application

Start each service in its own terminal.

### Backend API

```powershell
Set-Location .\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Confirm it is running:

- Health check: <http://127.0.0.1:8000/health>
- API root: <http://127.0.0.1:8000/>
- Interactive API documentation: <http://127.0.0.1:8000/docs>

### Frontend

In a second terminal:

```powershell
Set-Location .\frontend
npm run dev
```

Open the local URL printed by Vite, normally <http://localhost:5173/>.
During development, Vite proxies `/api/*` to `http://localhost:8000` and forwards `/health` to the backend. Keep both services running while using the application.

## Sign in

Use either demo account for local development:

- HR workflows: `hr_manager` / `hr123`
- Admin workflows: `admin` / `admin123`

The UI stores the returned bearer token in browser local storage. Signing out removes the stored session. Tokens expire after 24 hours; restarting the development backend without a configured `SECRET_KEY` generates a new process-local secret, which invalidates existing tokens. Sign in again after a backend restart if necessary.

## Run tests and checks

Run backend tests from the backend folder so pytest does not discover unrelated tests in a parent directory:

```powershell
Set-Location .\backend
.\.venv\Scripts\python.exe -m pytest -q
```

Run frontend lint and production build:

```powershell
Set-Location .\frontend
npm run lint
npm run build
```

The hardening tests use an isolated in-memory SQLite database and do not require or intentionally modify the seeded local database. Manual browser workflows have been exercised, but there is not currently an automated end-to-end browser test suite in the repository.

## API overview

All protected routes require an `Authorization: Bearer <token>` header. Authenticate using `POST /auth/login`.

| Method | Route | Purpose |
|---|---|---|
| `POST` | `/auth/login` | Authenticate and obtain an access token |
| `GET` | `/auth/me` | Get the authenticated user |
| `POST` | `/auth/register` | Register a user (administrator only) |
| `GET` | `/employees` | Search/filter employees and return a page |
| `POST` | `/employees` | Create an employee, optionally with initial salary |
| `GET` | `/employees/{id}` | Get employee profile and salary history |
| `PUT` | `/employees/{id}` | Update an employee |
| `DELETE` | `/employees/{id}` | Deactivate an employee |
| `POST` | `/employees/import-csv` | Validate and import employee CSV |
| `GET` | `/employees/export-csv` | Export employees, optionally filtered |
| `GET` | `/salary/{employee_id}` | Get an employee’s salary history |
| `POST` | `/salary/{employee_id}` | Add a dated salary record |
| `GET` | `/salary/export-csv` | Export salary history, optionally for one employee |
| `GET` | `/analytics/summary` | Get workforce and currency-specific salary analytics |
| `GET` | `/health` | Check API liveness |

Employee listing supports `page` (starts at 1), `size` (1–200), `search`, `country`, `department`, `job_title`, and `status`. User-selectable sorting and query-time analytics filters are not currently implemented.

The interactive OpenAPI page at `/docs` is the best reference for request/response schemas and exact API behavior.

## CSV import format

Employee import requires these column headers:

```csv
employee_code,first_name,last_name,email,country,department,job_title,hire_date
```

Optional fields include `status`, `salary_amount`, `salary_currency`, `salary_pay_frequency`, and `salary_effective_from`. Dates use `YYYY-MM-DD`; salary currencies use a three-letter uppercase code such as `USD` or `CAD`; pay frequency must be `annual`, `monthly`, `weekly`, or `hourly`.

The upload limit is 5 MiB and the file must be UTF-8 (a UTF-8 BOM is accepted). Rows are staged and validated before the import is committed. Invalid rows cause the request to fail with row-level validation details rather than partially importing valid rows.

Exported CSV files contain compensation information and must be handled as sensitive data.

## Configuration

| Variable | Purpose | Current behavior |
|---|---|---|
| `APP_ENV` | Select development or production startup behavior | Defaults to `development` |
| `SECRET_KEY` | Signs bearer tokens | Random process-local key if unset in development; required in production and at least 32 characters |
| `FRONTEND_ORIGIN` | CORS allowed frontend origin | Defaults to `http://localhost:5173` |
| `BOOTSTRAP_ADMIN_USERNAME` | Initial production admin username | Required only if production starts with no admin account |
| `BOOTSTRAP_ADMIN_EMAIL` | Initial production admin email | Required only if production starts with no admin account |
| `BOOTSTRAP_ADMIN_PASSWORD` | Initial production admin password | Required only if production starts with no admin; minimum 12 characters |
| `VITE_API_URL` | Frontend API base prefix | Defaults to `/api`; in local dev Vite strips `/api` and proxies to port 8000 |
| `DATABASE_URL` | Documented database URL example | Not currently read by `backend/app/database.py`; SQLite path is fixed in code |

PowerShell environment variables set with `$env:NAME = "value"` apply only to the current terminal and processes started from it. Do not commit real secrets to source control.

## Database and backups

- The SQLite database file is created at `backend\data\salary_management.db`.
- Tables are created by SQLAlchemy at backend startup.
- SQLite foreign-key enforcement is enabled.
- Database files are excluded from Git.
- For a local backup, stop the backend first, then copy `backend\data\salary_management.db` to a secure backup location. Restore only after stopping the backend and protect backups as sensitive salary data.

There is no production backup/restore automation or configurable database engine in this repository. Validate backups and recovery procedures before production use.

## Deploy for production

This section describes a provider-neutral deployment process. It is an operational checklist, not a platform-specific copy/paste recipe: configure networking, secrets, database, build pipeline, and monitoring using the chosen hosting provider’s supported services.

### Production readiness: current code limitation

**The repository is not deployable as a production system by configuration alone.** Before exposing it to real users or sensitive data, complete and test these application changes:

1. **Make database configuration real.** `backend/app/database.py` currently constructs a SQLite engine at a fixed local path and ignores `DATABASE_URL`. Implement environment-driven database configuration, add the chosen production database driver, and test the application against that database.
2. **Add and exercise schema migrations.** Tables are currently created with SQLAlchemy metadata on startup. Provide a checked-in migration configuration/history and a tested upgrade/rollback procedure before operating a persistent production database.
3. **Use a persistent managed database.** Do not deploy the current SQLite file on ephemeral/container-local storage or share it across API instances. Restrict database network access to the backend.
4. **Review transaction and concurrency behavior.** Exercise concurrent employee edits, salary changes, and CSV imports on the chosen database. Add database constraints or locking where needed to enforce salary-period invariants under concurrent requests.
5. **Choose the frontend/API topology.** The Vite proxy is development-only. Production must configure the static frontend hosting and reverse proxy/API base path (or separate frontend/API origins) deliberately.
6. **Add operational controls.** Define health/readiness checks, structured logs without sensitive data, metrics/alerts, backup and restore, retention, and incident procedures.

Do not skip these items by merely setting `DATABASE_URL`: it currently has no effect. Until they are completed and validated, treat the project as a local development/demo application, not as fully production-ready software.

### Recommended production topology

Use a static frontend host or CDN for the built React assets, a managed backend application service for FastAPI, and a managed PostgreSQL database in a private network. Put HTTPS at a trusted load balancer/reverse proxy, and expose only the frontend and required API entry point to users.

```text
Browser --HTTPS--> Frontend host / CDN
   |                    |
   | same-origin /api   +--> static React build
   v
Trusted HTTPS proxy / load balancer
   |
   +--> FastAPI service --private connection--> Managed PostgreSQL
```

The diagram is a recommended target architecture, not an existing deployment configuration. Hosting products, DNS, proxy rules, database provisioning, and secrets management are environment-specific.

### Deployment sequence

#### 1. Prepare and validate the release

- Select a hosting region, frontend/API topology, managed database, and backup/retention policy.
- Pin and review dependency versions; build from a known source revision in CI.
- Run the backend test suite from `backend` and frontend lint/build from `frontend`.
- Add integration tests against the production database engine, including migrations and concurrent salary updates.
- Produce and scan a deployable backend artifact/container and static frontend build. Do not include `.env` files, local SQLite databases, demo data, or credentials in artifacts.
- Record the release revision and database migration version.

#### 2. Provision the database

- Provision the selected managed database with encryption and private network access.
- Create a least-privilege application account; do not use a database owner/superuser credential for normal API traffic.
- Configure the backend with a secret database connection string through the host’s secret manager.
- Apply migrations as a controlled release step, before sending application traffic.
- Enable automated backups and point-in-time recovery where available. Test restoring a backup to a separate instance.
- Seed synthetic sample data only in non-production environments. Do not load demo or synthetic identities into a real production tenant unless explicitly intended.

#### 3. Configure and deploy the backend

Provide environment values through the hosting platform’s secret/configuration facility. Do not put secrets in source control or public build arguments.

Required or relevant settings:

| Setting | Production guidance |
|---|---|
| `APP_ENV` | Set to `production` |
| `SECRET_KEY` | Generate a cryptographically random secret with at least 32 characters; keep stable across backend instances and restarts; define a controlled rotation plan |
| `FRONTEND_ORIGIN` | Set to the exact trusted frontend origin. Current CORS configuration accepts one origin value |
| `BOOTSTRAP_ADMIN_USERNAME` | Set only for initial production startup if no administrator exists |
| `BOOTSTRAP_ADMIN_EMAIL` | Set only for initial production startup if no administrator exists |
| `BOOTSTRAP_ADMIN_PASSWORD` | Initial password of at least 12 characters; use a unique strong secret and remove it from runtime configuration after bootstrap |
| Database URL | The app must first be changed to consume the configured production database URL; current code ignores `DATABASE_URL` |

Production startup deliberately does not create the local demo users. It requires a valid signing key and, while no administrator exists, the initial administrator settings. Verify this bootstrap path in a staging environment before production. Never use `admin123` or `hr123` in production.

Run the backend with a production ASGI process configuration appropriate to the host (workers, concurrency, graceful shutdown, and health checks). Do not use Uvicorn `--reload` in production. Keep debug/error responses from exposing secrets or database details.

#### 4. Build and deploy the frontend

Build the static frontend in CI from `frontend`:

```powershell
Set-Location .\frontend
npm ci
npm run lint
npm run build
```

Publish the generated `frontend\dist` directory to the selected static host/CDN. Vite’s configured proxy is only active for `npm run dev`; it does not proxy requests from the production static build.

Choose one production request arrangement:

- **Same origin (recommended):** Configure the trusted edge proxy to serve the static frontend and forward `/api/*` to FastAPI while removing the `/api` prefix, matching the current frontend API client’s default `/api` prefix. Forward `/health` only if it is intended to be publicly reachable.
- **Separate origins:** Build with `VITE_API_URL` set to the absolute API base URL (without an extra `/api` path unless the API actually serves that prefix), configure the backend CORS origin to the exact frontend origin, and require HTTPS on both origins.

`VITE_API_URL` is embedded into frontend build assets. Treat it as public configuration, not a secret. After changing it, rebuild and redeploy the frontend. Validate that frontend requests reach the intended API, not a development proxy or an unintended origin.

#### 5. Bootstrap access and promote traffic

- Start the backend against the migrated production database with the production signing secret.
- Create the initial administrator through the controlled bootstrap environment settings.
- Remove bootstrap password settings from the running service once an administrator exists.
- Sign in as that administrator and create individual named HR accounts; do not share accounts.
- Verify authorization for both allowed roles and confirm that an unauthorized role and an unauthenticated request are rejected.
- Run smoke/acceptance checks in staging first. Promote traffic only after they pass.

#### 6. Operate and recover

- Monitor backend availability, error rates, latency, database health, disk/storage, and failed login patterns.
- Alert on repeated 5xx responses, failed migrations, exhausted database connections, and backup failures.
- Retain audit logs and backups according to an approved policy; restrict access to both.
- Test restore and rollback procedures periodically. Application rollback must account for whether the new schema migration is backward compatible.
- Rotate credentials and signing secrets using a planned procedure that considers active tokens and all running application instances.

### Production acceptance checklist

Before calling a deployment complete, verify each item in the target environment:

- [ ] Frontend is served over HTTPS and the correct production API is configured.
- [ ] `/health` and host-level readiness checks report healthy; backend startup fails safely on invalid production configuration.
- [ ] Production database connectivity, migrations, persistence across restarts, and tested backup restore all work.
- [ ] Initial admin bootstrap works once; demo accounts do not exist; HR users can be created by an admin.
- [ ] Unauthenticated API requests return 401 and disallowed roles return 403.
- [ ] Employee create, search/filter, pagination, edit, and deactivate workflows work through the deployed UI.
- [ ] Salary changes preserve history, reject invalid/overlapping periods, and create audit records.
- [ ] CSV import handles a valid UTF-8 file, reports invalid input without partial writes, and enforces the configured request-size limit.
- [ ] Employee and salary CSV exports contain the expected filtered data and are treated as sensitive downloads.
- [ ] Analytics match known test data and report compensation by currency without mixing currencies.
- [ ] Logs/alerts, audit retention, backup schedule, restore drill, and incident owner are documented.
- [ ] Security, privacy, accessibility, and applicable jurisdiction-specific reviews are complete.

### Remaining production security considerations

- The frontend currently stores bearer tokens in JavaScript-accessible local storage, which increases exposure if an XSS issue occurs. Consider a secure `HttpOnly`, `SameSite` cookie design with CSRF protection if appropriate to the deployment threat model.
- The current API does not provide a token refresh or explicit revocation workflow; tokens expire after 24 hours. Define operational behavior for lost accounts, role changes, and signing-key rotation.
- Ensure reverse-proxy upload limits are consistent with the backend 5 MiB CSV limit and reject oversized requests at the edge as well.
- This README does not certify legal, payroll, privacy, or security compliance.

## Production considerations

The system currently has functional local-development workflows and hardening tests, but it is not yet a fully production-deployable system. Production readiness requires implementing and validating the database configuration/migrations and operational controls described above, in addition to selecting a hosting provider and completing the acceptance checklist.

## Troubleshooting

### Frontend reports that the API is disconnected

- Confirm the backend is running on port `8000`.
- Open `http://127.0.0.1:8000/health` and check for `{"status":"ok"}`.
- If Vite chose a port other than `5173`, check that `FRONTEND_ORIGIN` matches the frontend origin for direct cross-origin API access. The normal development proxy avoids most CORS issues.

### Login fails

- Confirm `APP_ENV` is not `production` when using demo credentials.
- In development, verify the backend can connect to/create `backend\data\salary_management.db`.
- If the backend has restarted, sign in again because the development signing secret may have changed.

### Dependency or interpreter errors

- Run backend commands with `backend\.venv\Scripts\python.exe` to ensure they use the project environment.
- Run `python -m pip install -r requirements.txt` from `backend`.
- Run `npm install` from `frontend`.

### PowerShell refuses to activate `.venv`

Activation is optional. Use the full interpreter path shown in the setup and run commands instead.

### Pytest collects tests outside this repository

Run pytest from the `backend` directory as shown above, rather than from a common parent directory.

## Project layout

```text
Employee_Salary_Management_System/
├── README.md
├── backend/
│   ├── app/
│   │   ├── api/routes/       # Auth, employees/CSV, salary, analytics
│   │   ├── core/             # Authentication and security helpers
│   │   ├── models/           # SQLAlchemy entities
│   │   ├── schemas/          # Pydantic request/response validation
│   │   ├── database.py       # SQLite engine and DB sessions
│   │   └── main.py           # FastAPI app and startup
│   ├── scripts/seed_data.py  # Deterministic 10,000-employee sample seed
│   ├── tests/                # Backend API and hardening tests
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── services/         # API client
    │   ├── App.jsx           # Main UI and workflows
    │   └── *.css             # Application styles
    ├── package.json
    └── vite.config.js        # Local API proxy
```
