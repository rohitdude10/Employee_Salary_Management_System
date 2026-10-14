# Planning and Design Notes

## Product objective

Provide HR staff with one authenticated interface for employee records, salary history, workforce summaries, and controlled CSV workflows. Preserve compensation changes as dated records rather than overwriting salary values.

## Primary users and permissions

- **HR manager:** View and manage employees, salary records, analytics, and CSV workflows.
- **Administrator:** Use the same HR workflows and register user accounts.
- **Unauthenticated user:** Sign in; protected endpoints reject unauthenticated requests.

Access is checked by backend dependencies, not merely by hiding frontend controls. Both roles can use the HR APIs; user registration is administrator-only.

## Main workflows

1. **Sign in:** The user posts credentials to `/auth/login`; the frontend stores the returned bearer token in browser local storage and attaches it to protected API calls.
2. **Review workforce:** The dashboard loads employee analytics. The directory requests a server-side page and can filter/search employee data.
3. **Create or edit employee:** The UI submits validated profile data. Optional starting compensation creates a salary-history record as part of employee creation.
4. **Change salary:** HR enters a new salary amount, currency, frequency, and effective date. The API rejects invalid or overlapping periods and closes a previous open period when a later record is added.
5. **Import/export:** CSV import validates the file and rows before applying staged writes; export endpoints return CSV for employee or salary data.
6. **Audit:** Employee, salary, and import mutations add audit records alongside the business change.

## Data design

- `Employee` stores the current employee profile and status.
- `SalaryRecord` stores amount, ISO-like currency code, pay frequency, and inclusive effective dates. History belongs to an employee; the records are not intended to overlap.
- `User` stores a username, email, role, and password hash.
- `AuditLog` records actor, affected employee/salary record, action, structured details, and timestamp.

Foreign keys are enabled in SQLite. Salary values use decimal storage and are grouped by currency for analytics; amounts from different currencies are never directly added or averaged together.

## API and frontend boundary

FastAPI is the authoritative boundary for validation, authorization, salary rules, and persistence. React/Vite owns presentation and user interaction, calling the backend through the Vite `/api` proxy in local development. The frontend does not calculate salary-period validity as a substitute for the API.

Core route families:

| Route family | Responsibility |
|---|---|
| `/auth` | Login, current user, administrator-only user registration |
| `/employees` | Employee CRUD, filtered/paginated list, employee CSV import/export |
| `/salary` | Salary history, salary record creation, salary-history CSV export |
| `/analytics` | Workforce dimensions and salary aggregates by currency |
| `/health` | API liveness check |

## Validation and failure behavior

- API schemas validate required profile fields, email, status, salary amount, currency, frequency, and dates.
- Employee listing uses a bounded page size; invalid page inputs return validation errors.
- CSV import limits payloads to 5 MiB, requires UTF-8, checks headers and row values, and validates all rows before writing.
- Authentication failures return 401; role failures return 403; invalid business input returns a client error; missing records return 404.
- Database conflicts are translated into explicit API errors instead of silently reporting success.

## Quality strategy

- Use isolated in-memory SQLite fixtures for API tests so tests do not mutate the seeded local database.
- Assert business outcomes and error status/body, not only that requests complete.
- Test authorization, malformed tokens, salary intervals, employee filtering/pagination, analytics values, CSV atomicity/history, and query-count bounds.
- Run frontend lint/build and manually exercise the highest-value browser flows.

## Known scope boundaries

- This is an HR employee/salary record system, not a payroll processor.
- No currency conversion or external exchange-rate service is used.
- Local development bootstraps demo accounts. Production mode requires a configured signing secret and first-admin bootstrap credentials.
- The present database implementation uses a local SQLite file. The sample `DATABASE_URL` variable is not currently consumed by the database module; deploying to another database requires implementing and validating configurable database setup.
- Employee ordering is currently by employee ID; the UI does not expose user-selectable sorting. Analytics expose grouped breakdowns but not query-time filters.
- Critical browser workflows were manually exercised during hardening; the repository does not currently contain an automated browser end-to-end test suite.
- Production deployment additionally needs environment-specific backup, monitoring, retention, HTTPS, and operational procedures.
