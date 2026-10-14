const API_PREFIX = import.meta.env.VITE_API_URL || "/api";

const getErrorMessage = async (response) => {
  const payload = await response.json().catch(() => null);
  if (typeof payload?.detail === "string") return payload.detail;
  if (Array.isArray(payload?.detail)) {
    return payload.detail.map((issue) => issue.msg).join(", ");
  }
  if (Array.isArray(payload?.detail?.errors)) {
    return payload.detail.errors
      .map((issue) => `Row ${issue.row}: ${issue.error}`)
      .join("\n");
  }
  return `Request failed (${response.status})`;
};

const request = async (path, { token, ...options } = {}) => {
  const headers = new Headers(options.headers || {});
  if (!(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API_PREFIX}${path}`, { ...options, headers });
  if (!response.ok) {
    if (response.status === 401) {
      window.dispatchEvent(new Event("acme-auth-expired"));
    }
    const error = new Error(await getErrorMessage(response));
    error.status = response.status;
    throw error;
  }
  if (response.status === 204) return null;
  return response;
};

const jsonRequest = async (path, options) => {
  const response = await request(path, options);
  return response.json();
};

export const checkBackend = async () => {
  const response = await fetch("/health");
  if (!response.ok) throw new Error("Backend is unavailable");
  return response.json();
};

export const login = (credentials) =>
  jsonRequest("/auth/login", {
    method: "POST",
    body: JSON.stringify(credentials),
  });

export const getAnalytics = (token) =>
  jsonRequest("/analytics/summary", { token });

export const getEmployees = (token, filters) => {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== "" && value !== undefined && value !== null) {
      params.set(key, value);
    }
  });
  return jsonRequest(`/employees?${params.toString()}`, { token });
};

export const saveEmployee = (token, employee, id) =>
  jsonRequest(id ? `/employees/${id}` : "/employees", {
    token,
    method: id ? "PUT" : "POST",
    body: JSON.stringify(employee),
  });

export const getSalaryHistory = (token, employeeId) =>
  jsonRequest(`/salary/${employeeId}`, { token });

export const createSalaryRecord = (token, employeeId, salary) =>
  jsonRequest(`/salary/${employeeId}`, {
    token,
    method: "POST",
    body: JSON.stringify(salary),
  });

export const deactivateEmployee = (token, employeeId) =>
  jsonRequest(`/employees/${employeeId}`, { token, method: "DELETE" });

export const importEmployees = async (token, file) => {
  const body = new FormData();
  body.append("file", file);
  const response = await request("/employees/import-csv", {
    token,
    method: "POST",
    body,
  });
  return response.json();
};

export const downloadCsv = async (token, path, filename, query = {}) => {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value !== "" && value !== undefined && value !== null) {
      params.set(key, value);
    }
  });
  const queryString = params.toString();
  const response = await request(`${path}${queryString ? `?${queryString}` : ""}`, { token });
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
};
