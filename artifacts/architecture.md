# Architecture

## System context

```mermaid
flowchart LR
    HR[HR manager / administrator]
    Browser[React 19 browser application]
    Vite[Vite development server / API proxy]
    API[FastAPI application]
    Auth[Authentication and role checks]
    Services[Employee, salary, analytics, CSV routes]
    DB[(SQLite database)]
    Audit[(Audit log table)]

    HR --> Browser
    Browser -->|HTTP and bearer token| Vite
    Vite -->|/api rewritten to backend routes| API
    API --> Auth
    API --> Services
    Auth --> DB
    Services --> DB
    Services --> Audit
```

In local development, Vite proxies `/api/*` and `/health` to the API at `http://localhost:8000`. The frontend can be configured with `VITE_API_URL` for a different API base URL. Production hosting and proxy/TLS configuration are deployment concerns and are not defined by this local Vite setup.

## Backend component view

```mermaid
flowchart TB
    Client[Browser or API client]
    App[FastAPI app and lifespan]
    AuthRoutes[Auth routes]
    EmployeeRoutes[Employee and CSV routes]
    SalaryRoutes[Salary history routes]
    AnalyticsRoutes[Analytics routes]
    Security[Token validation, password verification, role dependencies]
    Schemas[Pydantic request/response validation]
    ORM[SQLAlchemy models and sessions]
    Tables[(users, employees, salary_records, audit_logs)]

    Client --> App
    App --> AuthRoutes
    App --> EmployeeRoutes
    App --> SalaryRoutes
    App --> AnalyticsRoutes
    AuthRoutes --> Security
    EmployeeRoutes --> Security
    SalaryRoutes --> Security
    AnalyticsRoutes --> Security
    AuthRoutes --> Schemas
    EmployeeRoutes --> Schemas
    SalaryRoutes --> Schemas
    AuthRoutes --> ORM
    EmployeeRoutes --> ORM
    SalaryRoutes --> ORM
    AnalyticsRoutes --> ORM
    Security --> ORM
    ORM --> Tables
```

## Core data relationships

```mermaid
erDiagram
    USER ||--o{ AUDIT_LOG : performs
    EMPLOYEE ||--o{ SALARY_RECORD : has
    EMPLOYEE ||--o{ AUDIT_LOG : is_subject_of
    SALARY_RECORD ||--o{ AUDIT_LOG : is_subject_of

    USER {
        int id
        string username
        string email
        string password_hash
        string role
    }
    EMPLOYEE {
        int id
        string employee_code
        string email
        string country
        string department
        date hire_date
        string status
    }
    SALARY_RECORD {
        int id
        int employee_id
        decimal amount
        string currency
        string pay_frequency
        date effective_from
        date effective_to
    }
    AUDIT_LOG {
        int id
        int user_id
        int employee_id
        int salary_record_id
        string action
        json details
        datetime created_at
    }
```

## Request and mutation flow

1. FastAPI resolves the database session and the current user for protected routes.
2. Route dependencies enforce the allowed role before business operations.
3. Pydantic schemas validate request shape and field constraints.
4. Route logic enforces cross-record rules, such as hire date and salary-period consistency.
5. SQLAlchemy persists business changes and their audit record in the same transaction where implemented.
6. Response models or explicit route payloads return the result; errors use explicit HTTP status codes.

## Operational notes

- Database setup currently creates tables through SQLAlchemy metadata during app startup; this is not a substitute for a production migration/backup plan.
- SQLite foreign-key enforcement is enabled on each connection.
- The backend's current database module selects its SQLite file directly; configure-and-migrate for a server database before multi-instance production deployment.
