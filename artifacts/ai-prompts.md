# AI Tool Prompts and Instructions

This note records the project-task prompts present in the conversation history. It does not claim to reproduce hidden system/developer instructions, tool configuration, or intermediate prompts that were not captured in that history.

## User-provided project prompts

The initial exploration request was:

> understand the project

The backend implementation request was:

> understand the backend code and now we need to implement the api . first analsye only then implement the code.  
> Backend APls  
> . Implement employee CRUD, pagination and filters.  
> . Implement salary history and salary change validation.  
> . Add authentication, authorization and audit logging.  
> . Add analytics and CSV endpoints.

The frontend implementation request was:

> understand the frontend code Employee_Salary_Management_System\frontend  
> first analyse the code and then implement it .  
>   
> and we need to build frontend UI  
> . Build the dashboard and KPI cards.  
> . Build the employee table with server-side pagination.  
> . Add employee forms and salary history screens.  
> . Add filters, charts, CSV import and export.  
> . Implement loading, empty, validation and error states.  
> . we need to bind the backend api with frontend

The testing and hardening request was:

> thanks everything is working , now we need to testing and hardening  
> Testing and hardening  
> . Test salary rules and authorization.  
> . Test employee search and analytics calculations.  
> . Test CSV validation and salary history.  
> . Run critical end-to-end browser workflows.  
> . Check database query performance and error handling.

The documentation request was:

> can you also provide these as well  
> - Requirements document  
> - Planning or design notes  
> - Architecture diagrams  
> - Prompts or instructions used with AI tools  
> - Trade-off explanations  
> - Performance considerations

## Reusable task brief

For future work on this codebase, the combined project brief can be stated as:

> Work in the Employee Salary Management System. First inspect the existing backend and frontend, then make targeted changes that fit the current FastAPI/SQLAlchemy and React/Vite structure. Preserve salary history and validate salary periods, enforce server-side authentication and roles, audit mutations, and keep employee search/pagination and analytics accurate. Validate CSV files before committing writes. Add isolated tests for business rules and error cases, run the backend test suite and frontend lint/build, and verify important browser workflows when feasible. Document implementation boundaries and measured performance without presenting local measurements as production guarantees.

## Working principles reflected by the delivered work

- Inspect existing implementation and tests before changing behavior.
- Prefer narrowly scoped validation, tests, and fixes over unrelated refactoring.
- Keep authorization and business-rule enforcement on the API.
- Use isolated test data for backend tests.
- Run targeted validation and report limitations, warnings, and observed measurements explicitly.
