import { useCallback, useEffect, useState } from "react";
import {
  checkBackend,
  createSalaryRecord,
  deactivateEmployee,
  downloadCsv,
  getAnalytics,
  getEmployees,
  getSalaryHistory,
  importEmployees,
  login,
  saveEmployee,
} from "./services/api";
import "./App.css";

const navigation = [
  { id: "dashboard", label: "Overview", icon: "grid" },
  { id: "employees", label: "Employees", icon: "users" },
  { id: "reports", label: "Salary reports", icon: "chart" },
];

const emptyEmployee = {
  employee_code: "",
  first_name: "",
  last_name: "",
  email: "",
  country: "",
  department: "",
  job_title: "",
  hire_date: "",
  status: "active",
};

function Icon({ name, size = 18 }) {
  const paths = {
    grid: <><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></>,
    users: <><path d="M16 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="10" cy="7" r="4" /><path d="M20 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" /></>,
    chart: <><path d="M3 3v18h18" /><path d="m19 9-5 5-4-4-5 5" /></>,
    search: <><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></>,
    plus: <><path d="M12 5v14M5 12h14" /></>,
    download: <><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><path d="m7 10 5 5 5-5M12 15V3" /></>,
    upload: <><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><path d="m17 8-5-5-5 5M12 3v12" /></>,
    chevron: <path d="m9 18 6-6-6-6" />,
    left: <path d="m15 18-6-6 6-6" />,
    right: <path d="m9 18 6-6-6-6" />,
    close: <><path d="m18 6-12 12M6 6l12 12" /></>,
    clock: <><circle cx="12" cy="12" r="10" /><path d="M12 6v6l4 2" /></>,
    briefcase: <><rect x="3" y="7" width="18" height="14" rx="2" /><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 12h18M10 12v2h4v-2" /></>,
    logout: <><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><path d="m16 17 5-5-5-5M21 12H9" /></>,
    more: <><circle cx="5" cy="12" r="1" /><circle cx="12" cy="12" r="1" /><circle cx="19" cy="12" r="1" /></>,
    filter: <><path d="M4 7h16M7 12h10M10 17h4" /></>,
    edit: <><path d="M12 20h9" /><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L8 18l-4 1 1-4Z" /></>,
    deactivate: <><circle cx="12" cy="12" r="9" /><path d="M5.6 5.6 18.4 18.4" /></>,
  };
  return (
    <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      {paths[name] || paths.grid}
    </svg>
  );
}

function readSession() {
  try {
    return JSON.parse(localStorage.getItem("acme-session") || "null");
  } catch {
    return null;
  }
}

function App() {
  const [session, setSession] = useState(readSession);
  const [activePage, setActivePage] = useState("dashboard");
  const [apiStatus, setApiStatus] = useState("checking");
  const [analytics, setAnalytics] = useState(null);
  const [employees, setEmployees] = useState({ items: [], total: 0, pages: 0, page: 1, size: 10 });
  const [filters, setFilters] = useState({ search: "", country: "", department: "", job_title: "", status: "", page: 1, size: 10 });
  const [searchInput, setSearchInput] = useState("");
  const [loadingEmployees, setLoadingEmployees] = useState(false);
  const [loadingAnalytics, setLoadingAnalytics] = useState(false);
  const [pageError, setPageError] = useState("");
  const [modal, setModal] = useState(null);
  const [toast, setToast] = useState("");

  const token = session?.access_token;
  const showToast = useCallback((message) => {
    setToast(message);
    window.setTimeout(() => setToast(""), 3500);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("acme-session");
    setSession(null);
    setAnalytics(null);
    setEmployees({ items: [], total: 0, pages: 0, page: 1, size: 10 });
  }, []);

  useEffect(() => {
    checkBackend()
      .then((response) => setApiStatus(response.status === "ok" ? "connected" : "disconnected"))
      .catch(() => setApiStatus("disconnected"));
    const onExpired = () => {
      logout();
      setPageError("Your session expired. Please sign in again.");
    };
    window.addEventListener("acme-auth-expired", onExpired);
    return () => window.removeEventListener("acme-auth-expired", onExpired);
  }, [logout]);

  const loadAnalytics = useCallback(async () => {
    if (!token) return;
    setLoadingAnalytics(true);
    try {
      setAnalytics(await getAnalytics(token));
      setPageError("");
    } catch (error) {
      setPageError(error.message);
    } finally {
      setLoadingAnalytics(false);
    }
  }, [token]);

  const loadEmployees = useCallback(async (currentFilters = filters) => {
    if (!token) return;
    setLoadingEmployees(true);
    try {
      setEmployees(await getEmployees(token, currentFilters));
      setPageError("");
    } catch (error) {
      setPageError(error.message);
    } finally {
      setLoadingEmployees(false);
    }
  }, [filters, token]);

  useEffect(() => {
    if (!token) return;
    Promise.resolve().then(loadAnalytics);
  }, [loadAnalytics, token]);

  useEffect(() => {
    if (!token || activePage !== "employees") return;
    Promise.resolve().then(() => loadEmployees(filters));
  }, [activePage, filters, loadEmployees, token]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setFilters((current) => current.search === searchInput ? current : { ...current, search: searchInput, page: 1 });
    }, 300);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  const handleLogin = async (credentials) => {
    const nextSession = await login(credentials);
    localStorage.setItem("acme-session", JSON.stringify(nextSession));
    setSession(nextSession);
    setPageError("");
  };

  const updateFilter = (key, value) => {
    setFilters((current) => ({ ...current, [key]: value, page: 1 }));
  };

  const openEmployeeForm = (employee = null) => {
    setModal({ type: "employee-form", employee });
  };

  const openSalaryHistory = (employee) => {
    setModal({ type: "salary", employee });
  };

  const handleEmployeeSave = async (values, id) => {
    await saveEmployee(token, values, id);
    setModal(null);
    showToast(id ? "Employee details updated" : "Employee added successfully");
    await Promise.all([loadAnalytics(), loadEmployees(filters)]);
  };

  const handleSalarySave = async (employeeId, salary) => {
    await createSalaryRecord(token, employeeId, salary);
    setModal(null);
    showToast("Salary update added to history");
    await Promise.all([loadAnalytics(), loadEmployees(filters)]);
  };

  const handleDeactivate = async (employee) => {
    if (!window.confirm(`Deactivate ${employee.first_name} ${employee.last_name}?`)) return;
    try {
      await deactivateEmployee(token, employee.id);
      showToast("Employee deactivated");
      await Promise.all([loadAnalytics(), loadEmployees(filters)]);
    } catch (error) {
      setPageError(error.message);
    }
  };

  const handleImport = async (file) => {
    try {
      const result = await importEmployees(token, file);
      showToast(`Import complete · ${result.inserted} added, ${result.updated} updated`);
      await Promise.all([loadAnalytics(), loadEmployees(filters)]);
    } catch (error) {
      setPageError(error.message);
    }
  };

  if (!session?.access_token) {
    return <LoginScreen onLogin={handleLogin} apiStatus={apiStatus} error={pageError} />;
  }

  const titles = {
    dashboard: ["Good morning", "Here’s what’s happening across your workforce today."],
    employees: ["Employee directory", "Manage people, roles and compensation details."],
    reports: ["Salary reports", "Explore compensation with currency-aware comparisons."],
  };
  const [pageTitle, pageSubtitle] = titles[activePage];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#" onClick={(event) => { event.preventDefault(); setActivePage("dashboard"); }}>
          <span className="brand-mark"><span /></span>
          <span className="brand-copy"><strong>acme</strong><small>PEOPLE & PAY</small></span>
        </a>
        <div className="workspace-label">WORKSPACE</div>
        <nav className="side-nav" aria-label="Main navigation">
          {navigation.map((item) => (
            <button key={item.id} className={`nav-item ${activePage === item.id ? "active" : ""}`} onClick={() => { setActivePage(item.id); setPageError(""); }}>
              <Icon name={item.icon} size={18} />
              <span>{item.label}</span>
              {item.id === "employees" && <span className="nav-count">{analytics?.summary?.total_employees ?? "—"}</span>}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className={`backend-status ${apiStatus}`}><i /> API {apiStatus === "connected" ? "connected" : apiStatus === "checking" ? "checking" : "offline"}</div>
          <div className="sidebar-divider" />
          <button className="profile-button" onClick={logout}>
            <span className="avatar avatar-small">{initials(session.user?.username || "HR")}</span>
            <span className="profile-copy"><strong>{session.user?.username || "HR Manager"}</strong><small>{session.user?.role || "hr_manager"}</small></span>
            <Icon name="logout" size={17} />
          </button>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="mobile-brand"><span className="brand-mark"><span /></span><strong>acme</strong></div>
          <div className="breadcrumb"><span>Workspace</span><Icon name="chevron" size={14} /><strong>{navigation.find((item) => item.id === activePage)?.label}</strong></div>
          <div className="topbar-actions">
            <span className="today-label">{new Intl.DateTimeFormat("en", { weekday: "short", month: "short", day: "numeric" }).format(new Date())}</span>
            <button className="top-avatar" aria-label="Sign out" title="Sign out" onClick={logout}>{initials(session.user?.username || "HR")}</button>
          </div>
        </header>

        <div className="page-content">
          <section className="page-heading">
            <div>
              <div className="eyebrow">{activePage === "dashboard" ? "PEOPLE OVERVIEW" : "PEOPLE OPERATIONS"}</div>
              <h1>{pageTitle}{activePage === "dashboard" && <span className="heading-dot">.</span>}</h1>
              <p>{pageSubtitle}</p>
            </div>
            {activePage !== "reports" && (
              <button className="button button-primary" onClick={() => openEmployeeForm()}>
                <Icon name="plus" size={17} /> Add employee
              </button>
            )}
          </section>

          {pageError && <div className="alert alert-error" role="alert"><span>{pageError}</span><button aria-label="Dismiss" onClick={() => setPageError("")}><Icon name="close" size={16} /></button></div>}

          {activePage === "dashboard" && (
            <Dashboard analytics={analytics} loading={loadingAnalytics} onNavigate={setActivePage} />
          )}
          {activePage === "employees" && (
            <EmployeesPage
              data={employees}
              filters={filters}
              searchInput={searchInput}
              loading={loadingEmployees}
              onSearch={setSearchInput}
              onFilter={updateFilter}
              onPage={(page) => setFilters((current) => ({ ...current, page }))}
              onEdit={openEmployeeForm}
              onSalary={openSalaryHistory}
              onDeactivate={handleDeactivate}
              onExport={() => downloadCsv(token, "/employees/export-csv", "employees.csv", filters).catch((error) => setPageError(error.message))}
              onImport={handleImport}
            />
          )}
          {activePage === "reports" && (
            <ReportsPage analytics={analytics} loading={loadingAnalytics} onRefresh={loadAnalytics} onExport={() => downloadCsv(token, "/salary/export-csv", "salary_history.csv").catch((error) => setPageError(error.message))} />
          )}
        </div>
        <footer className="app-footer"><span>ACME PEOPLE & PAY</span><span>Compensation data · Internal use only</span></footer>
      </main>

      {modal?.type === "employee-form" && (
        <EmployeeForm
          employee={modal.employee}
          onClose={() => setModal(null)}
          onSave={handleEmployeeSave}
        />
      )}
      {modal?.type === "salary" && (
        <SalaryModal
          employee={modal.employee}
          token={token}
          onClose={() => setModal(null)}
          onSave={handleSalarySave}
        />
      )}
      {toast && <div className="toast" role="status">{toast}</div>}
    </div>
  );
}

function LoginScreen({ onLogin, apiStatus, error: appError }) {
  const [username, setUsername] = useState("hr_manager");
  const [password, setPassword] = useState("hr123");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await onLogin({ username, password });
    } catch (loginError) {
      setError(loginError.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="login-screen">
      <section className="login-art">
        <div className="login-art-brand"><span className="brand-mark"><span /></span><strong>acme</strong></div>
        <div className="login-art-content">
          <div className="eyebrow">PEOPLE, IN FOCUS</div>
          <h1>Good work<br />deserves <em>good pay.</em></h1>
          <p>A clearer view of your people, compensation and the work that moves your organization forward.</p>
          <div className="art-stack"><span /><span /><span /></div>
          <small>PEOPLE & PAY PLATFORM</small>
        </div>
        <div className="login-art-foot">© 2026 ACME · INTERNAL WORKSPACE</div>
      </section>
      <section className="login-panel">
        <div className="login-form-wrap">
          <div className="login-mobile-brand"><span className="brand-mark"><span /></span><strong>acme</strong></div>
          <div className="eyebrow">WELCOME BACK</div>
          <h2>Sign in to your workspace</h2>
          <p className="login-caption">Enter your account details to continue.</p>
          {(error || appError) && <div className="alert alert-error">{error || appError}</div>}
          <form className="login-form" onSubmit={submit}>
            <label>Username<input autoComplete="username" required value={username} onChange={(event) => setUsername(event.target.value)} /></label>
            <label>Password<input type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} /></label>
            <button className="button button-primary login-submit" disabled={submitting}>{submitting ? "Signing in…" : "Sign in"}<Icon name="right" size={17} /></button>
          </form>
          <div className="demo-note"><span className={`status-pill ${apiStatus}`}>{apiStatus === "connected" ? "API connected" : apiStatus === "checking" ? "Connecting to API" : "API unavailable"}</span><span>Demo account · hr_manager / hr123</span></div>
        </div>
        <div className="login-legal">Protected workspace · Access is monitored</div>
      </section>
    </main>
  );
}

function Dashboard({ analytics, loading, onNavigate }) {
  const summary = analytics?.summary;
  const countries = Object.entries(analytics?.by_country || {});
  const departments = Object.entries(analytics?.by_department || {});
  const latest = [...departments].sort((a, b) => b[1] - a[1]).slice(0, 5);

  return (
    <>
      <section className="kpi-grid">
        <KpiCard title="Total employees" value={summary?.total_employees} icon="users" accent="purple" note={summary ? "Across all locations" : "Loading workforce data"} loading={loading} />
        <KpiCard title="Active employees" value={summary?.active_employees} icon="briefcase" accent="green" note={summary ? `${percentage(summary.active_employees, summary.total_employees)}% of workforce` : "Loading workforce data"} loading={loading} />
        <KpiCard title="Countries" value={analytics ? countries.length : undefined} icon="grid" accent="blue" note={analytics ? "With employee records" : "Loading workforce data"} loading={loading} />
        <KpiCard title="Departments" value={analytics ? departments.length : undefined} icon="chart" accent="amber" note={analytics ? "Across the organization" : "Loading workforce data"} loading={loading} />
      </section>

      <section className="dashboard-grid">
        <article className="panel workforce-panel">
          <div className="panel-heading">
            <div><div className="eyebrow">WORKFORCE DISTRIBUTION</div><h2>Team composition</h2></div>
            <button className="text-button" onClick={() => onNavigate("reports")}>View reports <Icon name="right" size={15} /></button>
          </div>
          {loading && !analytics ? <PanelLoading /> : departments.length === 0 ? <EmptyState title="No workforce data yet" text="Add employees to see how teams are distributed." /> : (
            <div className="bars-list">
              {latest.map(([label, count], index) => <BarRow key={label} label={label} count={count} total={summary?.total_employees || 1} index={index} />)}
            </div>
          )}
          <div className="panel-footer"><span><i className="legend-dot purple" /> Employees by department</span><button onClick={() => onNavigate("employees")}>Browse directory <Icon name="right" size={14} /></button></div>
        </article>
        <article className="panel country-panel">
          <div className="panel-heading">
            <div><div className="eyebrow">GLOBAL PRESENCE</div><h2>By location</h2></div>
            <span className="country-total">{countries.length} countries</span>
          </div>
          {loading && !analytics ? <PanelLoading /> : countries.length === 0 ? <EmptyState title="No locations yet" text="Country totals will appear as employees are added." /> : (
            <div className="country-list">
              {[...countries].sort((a, b) => b[1] - a[1]).slice(0, 6).map(([country, count], index) => (
                <div className="country-row" key={country}>
                  <span className={`country-badge color-${index % 5}`}>{country.slice(0, 2).toUpperCase()}</span>
                  <span className="country-name">{country}</span>
                  <strong>{count}</strong>
                  <span className="country-share">{percentage(count, summary?.total_employees)}%</span>
                </div>
              ))}
            </div>
          )}
        </article>
      </section>

      <section className="panel salary-note-panel">
        <div className="salary-note-icon"><Icon name="chart" size={20} /></div>
        <div><div className="eyebrow">COMPENSATION INSIGHTS</div><h2>Salary reporting, by currency</h2><p>Compensation is grouped by currency to avoid misleading comparisons across countries.</p></div>
        <button className="button button-secondary" onClick={() => onNavigate("reports")}>Explore salary reports <Icon name="right" size={16} /></button>
      </section>
    </>
  );
}

function KpiCard({ title, value, icon, accent, note, loading }) {
  return (
    <article className="kpi-card">
      <div className="kpi-top"><span className="kpi-title">{title}</span><span className={`kpi-icon ${accent}`}><Icon name={icon} size={17} /></span></div>
      {loading && value === undefined ? <div className="skeleton kpi-skeleton" /> : <strong className="kpi-value">{formatNumber(value)}</strong>}
      <div className="kpi-note"><span className={`mini-status ${accent}`} />{note}</div>
    </article>
  );
}

function EmployeesPage({ data, filters, searchInput, loading, onSearch, onFilter, onPage, onEdit, onSalary, onDeactivate, onExport, onImport }) {
  const first = data.total ? (data.page - 1) * data.size + 1 : 0;
  const last = Math.min(data.page * data.size, data.total);
  const [importing, setImporting] = useState(false);

  return (
    <section className="panel employee-panel">
      <div className="table-toolbar">
        <div><div className="eyebrow">DIRECTORY</div><h2>All employees <span className="inline-count">{formatNumber(data.total)}</span></h2></div>
        <div className="toolbar-actions">
          <label className="button button-secondary upload-button"><Icon name="upload" size={16} /> Import CSV<input type="file" accept=".csv,text/csv" disabled={importing} onChange={async (event) => { const file = event.target.files?.[0]; if (file) { setImporting(true); await onImport(file); setImporting(false); event.target.value = ""; } }} /></label>
          <button className="button button-secondary" onClick={onExport}><Icon name="download" size={16} /> Export</button>
        </div>
      </div>
      <div className="filter-row">
        <label className="search-box"><Icon name="search" size={17} /><input placeholder="Search name, email, role…" value={searchInput} onChange={(event) => onSearch(event.target.value)} /></label>
        <div className="filter-select"><Icon name="filter" size={15} /><select aria-label="Country filter" value={filters.country} onChange={(event) => onFilter("country", event.target.value)}><option value="">All countries</option>{countryChoices.map((country) => <option key={country}>{country}</option>)}</select></div>
        <select className="filter-select compact-filter" aria-label="Department filter" value={filters.department} onChange={(event) => onFilter("department", event.target.value)}><option value="">All departments</option>{departmentChoices.map((department) => <option key={department}>{department}</option>)}</select>
        <select className="filter-select compact-filter" aria-label="Job title filter" value={filters.job_title} onChange={(event) => onFilter("job_title", event.target.value)}><option value="">All job titles</option>{jobTitleChoices.map((jobTitle) => <option key={jobTitle}>{jobTitle}</option>)}</select>
        <select className="filter-select compact-filter" aria-label="Status filter" value={filters.status} onChange={(event) => onFilter("status", event.target.value)}><option value="">Any status</option><option value="active">Active</option><option value="inactive">Inactive</option></select>
      </div>
      <div className="table-wrap">
        <table className="employee-table">
          <thead><tr><th>EMPLOYEE</th><th>DEPARTMENT</th><th>LOCATION</th><th>STATUS</th><th>COMPENSATION</th><th><span className="sr-only">Actions</span></th></tr></thead>
          <tbody>
            {loading ? Array.from({ length: 5 }, (_, index) => <tr className="loading-row" key={index}><td colSpan="6"><div className="skeleton table-skeleton" /></td></tr>) :
              data.items.length === 0 ? <tr><td colSpan="6"><EmptyState title="No employees found" text={data.total ? "Try changing or clearing your filters." : "Add an employee to get your directory started."} /></td></tr> :
                data.items.map((employee) => (
                  <tr key={employee.id}>
                    <td><div className="employee-cell"><span className={`employee-avatar tone-${employee.id % 6}`}>{initials(`${employee.first_name} ${employee.last_name}`)}</span><span><strong>{employee.first_name} {employee.last_name}</strong><small>{employee.employee_code} <span>·</span> {employee.email}</small></span></div></td>
                    <td><strong className="table-primary">{employee.department}</strong><small className="cell-subtitle">{employee.job_title}</small></td>
                    <td><span className="location-cell"><span className="location-pin" />{employee.country}</span></td>
                    <td><span className={`employee-status ${employee.status}`}>{employee.status}</span></td>
                    <td>{employee.current_salary ? <><strong className="table-primary">{formatMoney(employee.current_salary, employee.current_currency)}</strong><small className="cell-subtitle">Current salary</small></> : <span className="muted">Not set</span>}</td>
                    <td><div className="row-actions"><button title="Salary history" aria-label={`Salary history for ${employee.first_name}`} onClick={() => onSalary(employee)}><Icon name="clock" size={16} /></button><button title="Edit employee" aria-label={`Edit ${employee.first_name}`} onClick={() => onEdit(employee)}><Icon name="edit" size={15} /></button><button className="deactivate-action" title="Deactivate" aria-label={`Deactivate ${employee.first_name}`} onClick={() => onDeactivate(employee)}><Icon name="deactivate" size={15} /></button></div></td>
                  </tr>
                ))}
          </tbody>
        </table>
      </div>
      <div className="table-pagination">
        <span>Showing <strong>{first}–{last}</strong> of <strong>{formatNumber(data.total)}</strong> employees</span>
        <div><button aria-label="Previous page" disabled={data.page <= 1 || loading} onClick={() => onPage(data.page - 1)}><Icon name="left" size={16} /></button><span>Page <strong>{data.page}</strong> of <strong>{Math.max(1, data.pages)}</strong></span><button aria-label="Next page" disabled={data.page >= data.pages || loading} onClick={() => onPage(data.page + 1)}><Icon name="right" size={16} /></button></div>
      </div>
    </section>
  );
}

const countryChoices = ["Australia", "Canada", "Germany", "India", "Japan", "Singapore", "United Kingdom", "United States"];
const departmentChoices = ["Customer Support", "Data", "Engineering", "Finance", "Human Resources", "Marketing", "Operations", "Sales"];
const jobTitleChoices = ["Data Analyst", "Data Engineer", "Financial Analyst", "HR Specialist", "Marketing Specialist", "Operations Manager", "Product Manager", "Sales Executive", "Senior Software Engineer", "Software Engineer"];
const countryCurrencies = { Australia: "AUD", Canada: "CAD", Germany: "EUR", India: "INR", Japan: "JPY", Singapore: "SGD", "United Kingdom": "GBP", "United States": "USD" };

function ReportsPage({ analytics, loading, onRefresh, onExport }) {
  const currencyReports = analytics?.by_currency || [];
  const departments = Object.entries(analytics?.by_department || {}).sort((a, b) => b[1] - a[1]);
  return (
    <>
      <div className="report-intro panel">
        <span className="report-icon"><Icon name="chart" size={20} /></span>
        <div><h2>Compensation overview</h2><p>Salary figures are summarized separately for each currency. No exchange-rate conversion is applied.</p></div>
        <button className="button button-secondary" onClick={onRefresh} disabled={loading}>{loading ? "Refreshing…" : "Refresh data"}</button>
      </div>
      {loading && !analytics ? <div className="panel"><PanelLoading /></div> : currencyReports.length === 0 ? (
        <div className="panel"><EmptyState title="No salary records yet" text="Add salary history to generate currency-specific compensation reports." /></div>
      ) : (
        <div className="currency-grid">
          {currencyReports.map((report) => (
            <article className="panel currency-card" key={report.currency}>
              <div className="currency-card-head"><span className="currency-symbol">{currencySymbol(report.currency)}</span><div><div className="eyebrow">CURRENCY</div><h2>{report.currency}</h2></div><span className="currency-people">{report.employee_count} people</span></div>
              <div className="currency-metrics">
                <div><span>Average salary</span><strong>{formatMoney(report.average_salary, report.currency)}</strong></div>
                <div><span>Median salary</span><strong>{formatMoney(report.median_salary, report.currency)}</strong></div>
                <div><span>Salary range</span><strong>{formatMoney(report.min_salary, report.currency)} – {formatMoney(report.max_salary, report.currency)}</strong></div>
              </div>
            </article>
          ))}
        </div>
      )}
      <section className="panel report-departments">
        <div className="panel-heading"><div><div className="eyebrow">HEADCOUNT</div><h2>Employees by department</h2></div><span className="country-total">{departments.length} teams</span></div>
        {departments.length ? <div className="bars-list report-bars">{departments.map(([label, count], index) => <BarRow key={label} label={label} count={count} total={analytics?.summary?.total_employees || 1} index={index} />)}</div> : <EmptyState title="No employee data" text="Department headcount will appear here." />}
      </section>
      <div className="report-export-row"><p>Need the underlying records? Export employee and salary history data as CSV.</p><button className="button button-secondary" onClick={onExport}><Icon name="download" size={16} /> Export salary history</button></div>
    </>
  );
}

function EmployeeForm({ employee, onClose, onSave }) {
  const editing = Boolean(employee);
  const [values, setValues] = useState(employee ? { ...emptyEmployee, ...employee } : { ...emptyEmployee });
  const [salary, setSalary] = useState({ amount: "", currency: "", pay_frequency: "annual", effective_from: "" });
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const setField = (field, value) => setValues((current) => ({ ...current, [field]: value }));

  const submit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    const payload = {
      employee_code: values.employee_code,
      first_name: values.first_name,
      last_name: values.last_name,
      email: values.email,
      country: values.country,
      department: values.department,
      job_title: values.job_title,
      hire_date: values.hire_date,
      status: values.status,
    };
    if (!editing && salary.amount) {
      payload.salary_amount = salary.amount;
      payload.salary_currency = salary.currency || countryCurrencies[values.country] || "USD";
      payload.salary_pay_frequency = salary.pay_frequency;
      payload.salary_effective_from = salary.effective_from || values.hire_date;
    }
    try {
      await onSave(payload, employee?.id);
    } catch (saveError) {
      setError(saveError.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title={editing ? "Edit employee" : "Add employee"} subtitle={editing ? "Update this employee’s profile information." : "Create a profile and optionally add their starting salary."} onClose={onClose}>
      <form className="form-content" onSubmit={submit}>
        {error && <div className="alert alert-error">{error}</div>}
        <div className="form-grid">
          <FormField label="Employee ID" required><input required maxLength="30" value={values.employee_code} onChange={(event) => setField("employee_code", event.target.value)} /></FormField>
          <FormField label="Hire date" required><input type="date" required value={dateOnly(values.hire_date)} onChange={(event) => setField("hire_date", event.target.value)} /></FormField>
          <FormField label="First name" required><input required value={values.first_name} onChange={(event) => setField("first_name", event.target.value)} /></FormField>
          <FormField label="Last name" required><input required value={values.last_name} onChange={(event) => setField("last_name", event.target.value)} /></FormField>
          <FormField label="Work email" required><input type="email" required value={values.email} onChange={(event) => setField("email", event.target.value)} /></FormField>
          <FormField label="Country" required><input required value={values.country} onChange={(event) => setField("country", event.target.value)} /></FormField>
          <FormField label="Department" required><input required value={values.department} onChange={(event) => setField("department", event.target.value)} /></FormField>
          <FormField label="Job title" required><input required value={values.job_title} onChange={(event) => setField("job_title", event.target.value)} /></FormField>
          {editing && <FormField label="Status"><select value={values.status} onChange={(event) => setField("status", event.target.value)}><option value="active">Active</option><option value="inactive">Inactive</option></select></FormField>}
        </div>
        {!editing && (
          <div className="salary-form-block">
            <div className="form-section-heading"><span><Icon name="briefcase" size={16} /></span><div><strong>Starting salary <small>(optional)</small></strong><p>Salary history can also be added after creating the employee.</p></div></div>
            <div className="form-grid salary-fields">
              <FormField label="Annual / period amount"><input type="number" min="0.01" step="0.01" placeholder="e.g. 75000" value={salary.amount} onChange={(event) => setSalary({ ...salary, amount: event.target.value })} /></FormField>
              <FormField label="Currency"><input maxLength="3" placeholder="USD" value={salary.currency} onChange={(event) => setSalary({ ...salary, currency: event.target.value.toUpperCase() })} /></FormField>
              <FormField label="Pay frequency"><select value={salary.pay_frequency} onChange={(event) => setSalary({ ...salary, pay_frequency: event.target.value })}><option value="annual">Annual</option><option value="monthly">Monthly</option><option value="hourly">Hourly</option><option value="weekly">Weekly</option></select></FormField>
              <FormField label="Effective from"><input type="date" value={salary.effective_from || values.hire_date} onChange={(event) => setSalary({ ...salary, effective_from: event.target.value })} /></FormField>
            </div>
          </div>
        )}
        <div className="modal-actions"><button type="button" className="button button-secondary" onClick={onClose}>Cancel</button><button className="button button-primary" disabled={saving}>{saving ? "Saving…" : editing ? "Save changes" : "Create employee"}</button></div>
      </form>
    </Modal>
  );
}

function SalaryModal({ employee, token, onClose, onSave }) {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [values, setValues] = useState({ amount: "", currency: employee.current_currency || "", pay_frequency: "annual", effective_from: "", effective_to: "" });

  useEffect(() => {
    getSalaryHistory(token, employee.id)
      .then((data) => setRecords(data.records || []))
      .catch((fetchError) => setError(fetchError.message))
      .finally(() => setLoading(false));
  }, [employee.id, token]);

  const submit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      await onSave(employee.id, { ...values, amount: Number(values.amount), currency: values.currency.toUpperCase(), effective_to: values.effective_to || null });
    } catch (saveError) {
      setError(saveError.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title="Salary history" subtitle={`${employee.first_name} ${employee.last_name} · ${employee.employee_code}`} onClose={onClose} wide>
      <div className="salary-modal-body">
        <div className="history-section">
          <div className="eyebrow">COMPENSATION TIMELINE</div>
          {loading ? <PanelLoading /> : records.length === 0 ? <EmptyState title="No salary history" text="Add an effective-dated salary record below." /> : (
            <div className="history-list">{records.map((record, index) => (
              <div className="history-row" key={record.id}>
                <span className={`history-marker ${index === 0 ? "current" : ""}`}><Icon name="briefcase" size={15} /></span>
                <div className="history-info"><strong>{formatMoney(record.amount, record.currency)} <small>/ {record.pay_frequency}</small></strong><span>Effective {formatDate(record.effective_from)}{record.effective_to ? ` — ${formatDate(record.effective_to)}` : " — Present"}</span></div>
                {index === 0 && !record.effective_to && <span className="employee-status active">Current</span>}
              </div>
            ))}</div>
          )}
        </div>
        <form className="salary-add-form" onSubmit={submit}>
          <div className="form-section-heading"><span><Icon name="plus" size={16} /></span><div><strong>Add salary change</strong><p>Records are retained as history and cannot overlap.</p></div></div>
          {error && <div className="alert alert-error">{error}</div>}
          <div className="form-grid salary-fields">
            <FormField label="Salary amount" required><input type="number" min="0.01" step="0.01" required value={values.amount} onChange={(event) => setValues({ ...values, amount: event.target.value })} /></FormField>
            <FormField label="Currency" required><input minLength="3" maxLength="3" required value={values.currency} onChange={(event) => setValues({ ...values, currency: event.target.value.toUpperCase() })} /></FormField>
            <FormField label="Pay frequency" required><select value={values.pay_frequency} onChange={(event) => setValues({ ...values, pay_frequency: event.target.value })}><option value="annual">Annual</option><option value="monthly">Monthly</option><option value="hourly">Hourly</option><option value="weekly">Weekly</option></select></FormField>
            <FormField label="Effective from" required><input type="date" required min={dateOnly(employee.hire_date)} value={values.effective_from} onChange={(event) => setValues({ ...values, effective_from: event.target.value })} /></FormField>
          </div>
          <div className="modal-actions"><button type="button" className="button button-secondary" onClick={onClose}>Close</button><button className="button button-primary" disabled={saving}>{saving ? "Saving…" : "Add salary record"}</button></div>
        </form>
      </div>
    </Modal>
  );
}

function Modal({ title, subtitle, onClose, wide = false, children }) {
  useEffect(() => {
    const onKeyDown = (event) => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);
  return (
    <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className={`modal ${wide ? "wide" : ""}`} role="dialog" aria-modal="true" aria-labelledby="modal-title">
        <header className="modal-header"><div><h2 id="modal-title">{title}</h2><p>{subtitle}</p></div><button className="icon-button" aria-label="Close dialog" onClick={onClose}><Icon name="close" size={19} /></button></header>
        {children}
      </section>
    </div>
  );
}

function FormField({ label, required, children }) {
  return <label className="form-field"><span>{label}{required && <i> *</i>}</span>{children}</label>;
}

function BarRow({ label, count, total, index }) {
  return (
    <div className="bar-row"><div className="bar-label"><span>{label}</span><strong>{count}</strong></div><div className="bar-track"><span className={`bar-fill bar-${index % 5}`} style={{ width: `${Math.max(count ? 2 : 0, (count / total) * 100)}%` }} /></div></div>
  );
}

function EmptyState({ title, text }) {
  return <div className="empty-state"><span><Icon name="search" size={20} /></span><strong>{title}</strong><p>{text}</p></div>;
}

function PanelLoading() {
  return <div className="panel-loading"><div className="skeleton" /><div className="skeleton" /><div className="skeleton" /></div>;
}

function initials(value) {
  return value.split(/[\s._-]+/).filter(Boolean).slice(0, 2).map((part) => part[0]?.toUpperCase()).join("");
}

function formatNumber(value) {
  return value === undefined || value === null ? "—" : new Intl.NumberFormat("en").format(value);
}

function formatMoney(value, currency = "USD") {
  if (value === undefined || value === null || value === "") return "—";
  try {
    return new Intl.NumberFormat("en", { style: "currency", currency: currency || "USD", maximumFractionDigits: 0 }).format(value);
  } catch {
    return `${currency || ""} ${formatNumber(value)}`;
  }
}

function currencySymbol(currency) {
  try {
    return new Intl.NumberFormat("en", { style: "currency", currency, maximumFractionDigits: 0 }).formatToParts(0).find((part) => part.type === "currency")?.value || currency;
  } catch {
    return currency;
  }
}

function percentage(value, total) {
  return total ? Math.round((Number(value || 0) / Number(total)) * 100) : 0;
}

function dateOnly(value) {
  return value ? String(value).slice(0, 10) : "";
}

function formatDate(value) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric", year: "numeric" }).format(new Date(`${dateOnly(value)}T00:00:00`));
}

export default App;
