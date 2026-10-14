# ACME People & Pay frontend

The frontend is a React 19 and Vite application for the Employee Salary
Management System. It provides authenticated dashboard, employee directory,
salary history, analytics, and CSV workflows.

## Run locally

1. Start the backend from `backend/`:

   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
   ```

2. Start the frontend from `frontend/`:

   ```powershell
   npm install
   npm run dev
   ```

Vite proxies `/api/*` and `/health` to `http://localhost:8000`. Set
`VITE_API_URL` to an API base URL when using a different deployment topology.

The development backend creates demo accounts on startup:

- `hr_manager` / `hr123`
- `admin` / `admin123`

Change these credentials and configure a strong `SECRET_KEY` before exposing
the backend outside a local development environment.

## Checks

```powershell
npm run lint
npm run build
```
