# ACME Employee Salary Management System — Requirements

## 1. Goal

Replace spreadsheet-based salary management with a centralized web application that allows authorized HR managers to manage employee records, maintain salary information, and analyze compensation across countries.

## 2. Users

- **HR Manager:** Manage employee information and salary records, import/export data, and access salary analytics.

- **Administrator:** Manage access and user accounts, if included in the MVP.

## 3. Scope and Features

### Employee Management

- View, search, sort, and paginate employee records.

- Filter by country, department, job title, and employment status.

- Create, edit, view, and deactivate employee records.

### Salary Management

- Record salary amount, currency, pay frequency, and effective date.

- Maintain salary history instead of overwriting previous salary records.

- Validate salary inputs and prevent invalid or overlapping effective periods.

### Dashboard and Reporting

- Display employee count, average salary, and median salary.

- Analyze compensation by country, department, and job title.

- Filter analytics by relevant employee attributes.

- Clearly distinguish currencies and avoid misleading cross-currency comparisons.

### Data Import and Export

- Import employees and salary records through CSV.

- Validate uploaded rows and report errors before committing changes.

- Export filtered employee and salary data to CSV.

### Security and Auditability

- Authenticate users and restrict access to salary information.

- Record who changed salary data, when it changed, and the previous and new values.

- Validate inputs and handle errors without exposing sensitive information.

### Quality and Delivery

- Seed 10,000 realistic synthetic employees across multiple countries.

- Provide automated backend, frontend, and critical workflow tests.

- Deploy the frontend, API, and database.

- Provide setup instructions, architecture notes, and a short video demonstration.

## 4. Deliberately Out of Scope

- **Payroll processing and payslips:** Requires tax, deductions, benefits, and country-specific payroll rules.

- **Tax and legal compliance automation:** Requires jurisdiction-specific expertise and ongoing regulatory updates.

- **Employee self-service:** Not essential for the initial HR-focused workflow.

- **Real-time foreign exchange integration:** Introduces external dependencies; initial reports remain currency-specific or use explicitly documented conversion data.

- **AI-generated compensation recommendations:** Not required to demonstrate reliable employee management and analytics.

- **Complex enterprise integrations:** HRIS, accounting, and identity-provider integrations can follow after the MVP.

## 5. Assumptions and Success Criteria

- The application initially serves authorized HR users managing 10,000 synthetic employee records.

- Each salary record has a currency, pay frequency, and effective date.

- Core workflows operate through the UI and documented APIs.

- Users can search and filter employees, update salary records, and view accurate analytics.

- Tests verify important business rules and API behavior.

- The deployed application persists data, documents its limitations, and can be demonstrated end to end.

## 6. Key Risks

Salary data is sensitive. Access control, audit logging, secure configuration, and careful handling of exported files are essential. Production use requires additional security review, backup procedures, and country-specific compliance validation.