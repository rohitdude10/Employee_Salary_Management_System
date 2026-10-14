
import { useEffect, useState } from "react";
import "./App.css";

const menuItems = ["Dashboard", "Employees", "Salary Reports"];

function App() {
  const [activePage, setActivePage] = useState("Dashboard");
  const [apiStatus, setApiStatus] = useState("Checking...");

  useEffect(() => {
    fetch("/health")
      .then((response) => {
        if (!response.ok) throw new Error("Backend unavailable");
        return response.json();
      })
      .then((data) => setApiStatus(data.status === "ok" ? "Connected" : "Error"))
      .catch(() => setApiStatus("Disconnected"));
  }, []);

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">A</div>
          <div>
            <h2>ACME</h2>
            <span>Salary Management</span>
          </div>
        </div>

        <p className="nav-label">WORKSPACE</p>

        <nav>
          {menuItems.map((item) => (
            <button
              key={item}
              className={`nav-item ${activePage === item ? "active" : ""}`}
              onClick={() => setActivePage(item)}
            >
              {item}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <span className="status-dot" />
          Backend: {apiStatus}
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <h1>{activePage}</h1>
            <p>ACME Employee Salary Management</p>
          </div>
          <div className="user-profile">
            <div className="avatar">HR</div>
            <span>HR Manager</span>
          </div>
        </header>

        {activePage === "Dashboard" && (
          <>
            <section className="welcome">
              <h2>Welcome to ACME</h2>
              <p>Manage employees and review salary information.</p>
            </section>

            <section className="stats-grid">
              <StatCard title="Total Employees" value="—" />
              <StatCard title="Average Salary" value="—" />
              <StatCard title="Countries" value="—" />
              <StatCard title="Departments" value="—" />
            </section>

            <section className="content-card">
              <h3>Getting started</h3>
              <p>
                Your dashboard is ready. Connect the employee and analytics
                APIs to display real data.
              </p>
              <button
                className="primary-button"
                onClick={() => setActivePage("Employees")}
              >
                View Employees
              </button>
            </section>
          </>
        )}

        {activePage === "Employees" && (
          <section className="content-card">
            <h3>Employee Directory</h3>
            <p>
              Employee search, filters, pagination, and salary details
              will be implemented here.
            </p>
          </section>
        )}

        {activePage === "Salary Reports" && (
          <section className="content-card">
            <h3>Salary Reports</h3>
            <p>
              Country-wise and department-wise salary analytics
              will be implemented here.
            </p>
          </section>
        )}
      </main>
    </div>
  );
}

function StatCard({ title, value }) {
  return (
    <article className="stat-card">
      <p>{title}</p>
      <h2>{value}</h2>
    </article>
  );
}

export default App;
