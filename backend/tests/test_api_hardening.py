import csv
import hashlib
import hmac
import io
import json
import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import event, func, select

from app.core.security import SECRET_KEY
from app.core.security import hash_password
from app.models.audit_log import AuditLog
from app.models.employee import Employee
from app.models.salary_record import SalaryRecord
from app.models.user import User


def test_employee_and_salary_routes_require_authorized_role(client, db):
    employee = Employee(
        employee_code="AUTH-1",
        first_name="Auth",
        last_name="Target",
        email="auth-target@example.com",
        country="India",
        department="Engineering",
        job_title="Engineer",
        hire_date=date(2020, 1, 1),
        status="active",
    )
    viewer = User(
        username="viewer",
        email="viewer@example.com",
        password_hash=hash_password("viewer-password"),
        role="viewer",
    )
    db.add_all([employee, viewer])
    db.commit()

    assert client.get("/employees").status_code == 401
    assert client.get("/analytics/summary").status_code == 401

    login = client.post(
        "/auth/login",
        json={"username": "viewer", "password": "viewer-password"},
    )
    assert login.status_code == 200
    viewer_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.get("/employees", headers=viewer_headers).status_code == 403
    assert client.get("/analytics/summary", headers=viewer_headers).status_code == 403
    assert client.get(
        f"/salary/{employee.id}",
        headers=viewer_headers,
    ).status_code == 403


def test_malformed_signed_token_returns_401_not_server_error(client):
    header = encode_segment({"alg": "HS256", "typ": "JWT"})
    payload = encode_segment({"sub": ["not", "a", "string"], "exp": "not-a-timestamp"})
    message = f"{header}.{payload}"
    signature = hmac.new(
        SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256,
    ).digest()
    token = f"{message}.{encode_bytes(signature)}"

    with type(client)(client.app, raise_server_exceptions=False) as safe_client:
        response = safe_client.get(
            "/employees",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 401


def test_production_requires_a_configured_signing_secret():
    environment = os.environ.copy()
    environment.pop("SECRET_KEY", None)
    environment["APP_ENV"] = "production"
    result = subprocess.run(
        [sys.executable, "-c", "import app.core.security"],
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Production requires a SECRET_KEY" in result.stderr


def test_admin_user_management_is_forbidden_to_hr_manager(client, auth_headers):
    registration = {
        "username": "new-hr",
        "email": "new-hr@example.com",
        "password": "a-long-test-password",
        "role": "hr_manager",
    }
    assert client.post("/auth/register", json=registration).status_code == 401
    assert (
        client.post(
            "/auth/register",
            headers=auth_headers["hr_manager"],
            json=registration,
        ).status_code
        == 403
    )
    created = client.post(
        "/auth/register",
        headers=auth_headers["admin"],
        json=registration,
    )
    assert created.status_code == 200, created.text
    assert created.json()["role"] == "hr_manager"
    assert "password" not in created.json()


def test_salary_history_closes_previous_record_and_audits_change(
    client,
    db,
    auth_headers,
    employee_factory,
    salary_factory,
):
    employee = employee_factory("SALARY-1")
    first = salary_factory(employee, "70000", effective_from=date(2020, 1, 1))
    db.commit()

    response = client.post(
        f"/salary/{employee.id}",
        headers=auth_headers["hr_manager"],
        json={
            "amount": 80000,
            "currency": "INR",
            "pay_frequency": "annual",
            "effective_from": "2022-01-01",
        },
    )

    assert response.status_code == 200, response.text
    db.refresh(first)
    assert first.effective_to == date(2021, 12, 31)
    history = client.get(
        f"/salary/{employee.id}",
        headers=auth_headers["hr_manager"],
    ).json()["records"]
    assert len(history) == 2
    assert history[0]["effective_from"] == "2022-01-01"

    audit = db.scalar(
        select(AuditLog).where(
            AuditLog.action == "salary_record_created",
            AuditLog.employee_id == employee.id,
        )
    )
    assert audit is not None
    assert audit.details["closed_periods"] == [
        {
            "salary_record_id": first.id,
            "previous_effective_to": None,
            "effective_to": "2021-12-31",
        }
    ]


def test_salary_period_rejects_overlap_invalid_bounds_and_pre_hire_date(
    client,
    db,
    auth_headers,
    employee_factory,
    salary_factory,
):
    employee = employee_factory("SALARY-2", hire_date=date(2020, 1, 1))
    current = salary_factory(employee, "70000", effective_from=date(2020, 1, 1))
    db.commit()

    cases = [
        (
            {"amount": 0, "currency": "INR", "effective_from": "2022-01-01"},
            422,
        ),
        (
            {"amount": 80000, "currency": "INR", "effective_from": "2019-12-31"},
            400,
        ),
        (
            {
                "amount": 80000,
                "currency": "INR",
                "effective_from": "2022-01-01",
                "effective_to": "2021-12-31",
            },
            400,
        ),
    ]
    for payload, expected_status in cases:
        response = client.post(
            f"/salary/{employee.id}",
            headers=auth_headers["hr_manager"],
            json=payload,
        )
        assert response.status_code == expected_status, response.text

    overlap_response = client.post(
        f"/salary/{employee.id}",
        headers=auth_headers["hr_manager"],
        json={
            "amount": 80000,
            "currency": "INR",
            "effective_from": "2022-01-01",
        },
    )
    assert overlap_response.status_code == 200
    db.refresh(current)
    assert current.effective_to == date(2021, 12, 31)

    overlap_again = client.post(
        f"/salary/{employee.id}",
        headers=auth_headers["hr_manager"],
        json={
            "amount": 90000,
            "currency": "INR",
            "effective_from": "2021-06-01",
        },
    )
    assert overlap_again.status_code == 400
    db.refresh(current)
    assert current.effective_to == date(2021, 12, 31)


def test_employee_search_filter_and_server_pagination(
    client,
    auth_headers,
    employee_factory,
):
    employee_factory(
        "SEARCH-1",
        first_name="Amelia",
        last_name="Garcia",
        department="Engineering",
        country="India",
    )
    employee_factory(
        "SEARCH-2",
        first_name="Amelia",
        last_name="Chen",
        department="Finance",
        country="India",
    )
    employee_factory(
        "SEARCH-3",
        first_name="Priya",
        last_name="Patel",
        department="Engineering",
        country="Canada",
    )

    response = client.get(
        "/employees?search=amelia&country=India&size=1&page=2",
        headers=auth_headers["hr_manager"],
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total"] == 2
    assert payload["page"] == 2
    assert payload["size"] == 1
    assert payload["pages"] == 2
    assert len(payload["items"]) == 1
    assert payload["items"][0]["last_name"] == "Chen"

    invalid_page = client.get(
        "/employees?page=0",
        headers=auth_headers["hr_manager"],
    )
    assert invalid_page.status_code == 422


def test_employee_update_audit_is_json_safe_and_hire_date_preserves_salary_rules(
    client,
    db,
    auth_headers,
    employee_factory,
    salary_factory,
):
    employee = employee_factory("AUDIT-1", hire_date=date(2020, 1, 1))
    salary_factory(employee, "70000", effective_from=date(2020, 1, 1))
    db.commit()

    invalid_hire_date = client.put(
        f"/employees/{employee.id}",
        headers=auth_headers["hr_manager"],
        json={"hire_date": "2021-01-01"},
    )
    assert invalid_hire_date.status_code == 400

    updated = client.put(
        f"/employees/{employee.id}",
        headers=auth_headers["hr_manager"],
        json={"hire_date": "2019-01-01", "department": "Finance"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["hire_date"] == "2019-01-01"

    audit = db.scalar(
        select(AuditLog).where(
            AuditLog.action == "employee_updated",
            AuditLog.employee_id == employee.id,
        )
    )
    assert audit is not None
    assert audit.details["before"]["hire_date"] == "2020-01-01"
    assert audit.details["after"]["hire_date"] == "2019-01-01"
    assert audit.details["after"]["department"] == "Finance"


def test_analytics_counts_and_currency_aggregates_are_correct(
    client,
    auth_headers,
    employee_factory,
    salary_factory,
    db,
):
    india_one = employee_factory("ANALYTICS-1", country="India", department="Engineering")
    india_two = employee_factory("ANALYTICS-2", country="India", department="Engineering")
    canada = employee_factory("ANALYTICS-3", country="Canada", department="Finance", status="inactive")
    salary_factory(india_one, "50000", currency="INR", effective_from=date(2020, 1, 1))
    salary_factory(india_two, "70000", currency="INR", effective_from=date(2020, 1, 1))
    salary_factory(canada, "90000", currency="CAD", effective_from=date(2020, 1, 1))
    salary_factory(
        india_one,
        "100000",
        currency="INR",
        effective_from=date.today() + timedelta(days=30),
    )
    db.commit()

    response = client.get("/analytics/summary", headers=auth_headers["hr_manager"])
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["summary"] == {
        "total_employees": 3,
        "active_employees": 2,
        "inactive_employees": 1,
        "employees_with_current_salary": 3,
        "currency_count": 2,
    }
    assert payload["by_country"] == {"Canada": 1, "India": 2}
    assert payload["by_department"] == {"Engineering": 2, "Finance": 1}
    reports = {item["currency"]: item for item in payload["by_currency"]}
    assert reports["INR"] == {
        "currency": "INR",
        "employee_count": 2,
        "average_salary": 60000.0,
        "median_salary": 60000.0,
        "min_salary": 50000.0,
        "max_salary": 70000.0,
    }
    assert reports["CAD"]["average_salary"] == 90000.0


def test_csv_import_validates_all_rows_before_creating_records(
    client,
    auth_headers,
    db,
):
    file = (
        "employee_code,first_name,last_name,email,country,department,job_title,hire_date,"
        "salary_amount,salary_currency,salary_effective_from\n"
        "CSV-GOOD,Valid,Employee,valid@example.com,India,Engineering,Engineer,2020-01-01,50000,INR,2020-01-01\n"
        "CSV-BAD,Invalid,Salary,invalid@example.com,India,Engineering,Engineer,2020-01-01,0,INR,2020-01-01\n"
    )

    response = client.post(
        "/employees/import-csv",
        headers=auth_headers["hr_manager"],
        files={"file": ("employees.csv", file.encode(), "text/csv")},
    )

    assert response.status_code == 400, response.text
    assert "row" in response.json()["detail"]["errors"][0]
    assert db.scalar(select(func.count(Employee.id))) == 0
    assert db.scalar(select(func.count(SalaryRecord.id))) == 0


def test_csv_import_and_export_support_utf8_and_keep_history(
    client,
    auth_headers,
    db,
):
    file = (
        "employee_code,first_name,last_name,email,country,department,job_title,hire_date,"
        "salary_amount,salary_currency,salary_effective_from\n"
        "CSV-OK,Zoë,Nguyen,zoe@example.com,Canada,Data,Analyst,2021-03-04,75000,CAD,2021-03-04\n"
    )
    imported = client.post(
        "/employees/import-csv",
        headers=auth_headers["hr_manager"],
        files={"file": ("employees.csv", file.encode("utf-8"), "text/csv")},
    )
    assert imported.status_code == 200, imported.text
    assert imported.json() == {"inserted": 1, "updated": 0, "errors": []}

    updated = client.post(
        "/employees/import-csv",
        headers=auth_headers["hr_manager"],
        files={
            "file": (
                "employees.csv",
                (
                    "employee_code,first_name,last_name,email,country,department,job_title,hire_date,"
                    "salary_amount,salary_currency,salary_effective_from\n"
                    "CSV-OK,Zoë,Nguyen,zoe@example.com,Canada,Engineering,Analyst,2021-03-04,"
                    "80000,CAD,2022-03-04\n"
                ).encode("utf-8"),
                "text/csv",
            )
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json() == {"inserted": 0, "updated": 1, "errors": []}

    export = client.get(
        "/employees/export-csv?country=Canada",
        headers=auth_headers["hr_manager"],
    )
    assert export.status_code == 200
    rows = list(csv.DictReader(io.StringIO(export.text)))
    assert len(rows) == 1
    assert rows[0]["first_name"] == "Zoë"
    assert rows[0]["department"] == "Engineering"
    assert rows[0]["current_salary"] == "80000.00"
    assert rows[0]["current_currency"] == "CAD"

    db.expire_all()
    employee = db.scalar(select(Employee).where(Employee.employee_code == "CSV-OK"))
    assert employee is not None
    history = client.get(
        f"/salary/{employee.id}",
        headers=auth_headers["hr_manager"],
    )
    assert history.status_code == 200
    records = history.json()["records"]
    assert len(records) == 2
    assert records[1]["effective_to"] == "2022-03-03"


def test_csv_upload_rejects_invalid_encoding_and_oversized_file(
    client,
    auth_headers,
):
    invalid_encoding = client.post(
        "/employees/import-csv",
        headers=auth_headers["hr_manager"],
        files={"file": ("employees.csv", b"\xff\xfe\x00", "text/csv")},
    )
    assert invalid_encoding.status_code == 400
    assert invalid_encoding.json()["detail"] == "CSV file must use UTF-8 encoding"

    oversized = client.post(
        "/employees/import-csv",
        headers=auth_headers["hr_manager"],
        files={
            "file": (
                "employees.csv",
                b"x" * (5 * 1024 * 1024 + 1),
                "text/csv",
            )
        },
    )
    assert oversized.status_code == 413


def test_employee_list_query_count_does_not_grow_with_page_size(
    client,
    auth_headers,
    employee_factory,
    salary_factory,
    test_engine,
):
    for index in range(5):
        employee = employee_factory(f"QUERY-{index}")
        salary_factory(employee, "50000", effective_from=date(2020, 1, 1))
    statements = []

    def count_statement(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith(("SELECT", "WITH")):
            statements.append(statement)

    event.listen(test_engine, "before_cursor_execute", count_statement)
    try:
        response = client.get(
            "/employees?size=5",
            headers=auth_headers["hr_manager"],
        )
    finally:
        event.remove(test_engine, "before_cursor_execute", count_statement)

    assert response.status_code == 200, response.text
    assert len(response.json()["items"]) == 5
    assert len(statements) <= 3


def encode_segment(value: dict) -> str:
    return encode_bytes(json.dumps(value, separators=(",", ":")).encode())


def encode_bytes(value: bytes) -> str:
    import base64

    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()
