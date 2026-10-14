from collections.abc import Generator
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.database import Base, get_db
from app.main import app
from app.models.employee import Employee
from app.models.salary_record import SalaryRecord
from app.models.user import User


@pytest.fixture
def test_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_session_factory(test_engine):
    return sessionmaker(
        bind=test_engine,
        autoflush=False,
        expire_on_commit=False,
    )


@pytest.fixture
def db(db_session_factory) -> Generator[Session, None, None]:
    session = db_session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session_factory):
    def override_get_db():
        with db_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def users(db: Session):
    hr_manager = User(
        username="test-hr",
        email="test-hr@example.com",
        password_hash=hash_password("hr-test-password"),
        role="hr_manager",
    )
    admin = User(
        username="test-admin",
        email="test-admin@example.com",
        password_hash=hash_password("admin-test-password"),
        role="admin",
    )
    db.add_all([hr_manager, admin])
    db.commit()
    return {"hr_manager": hr_manager, "admin": admin}


@pytest.fixture
def auth_headers(client, users):
    def headers_for(username: str, password: str) -> dict[str, str]:
        response = client.post(
            "/auth/login",
            json={"username": username, "password": password},
        )
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return {
        "hr_manager": headers_for("test-hr", "hr-test-password"),
        "admin": headers_for("test-admin", "admin-test-password"),
    }


@pytest.fixture
def employee_factory(db: Session):
    def create_employee(
        employee_code: str,
        *,
        first_name: str = "Test",
        last_name: str = "Employee",
        email: str | None = None,
        country: str = "India",
        department: str = "Engineering",
        job_title: str = "Software Engineer",
        status: str = "active",
        hire_date: date = date(2020, 1, 1),
    ) -> Employee:
        employee = Employee(
            employee_code=employee_code,
            first_name=first_name,
            last_name=last_name,
            email=email or f"{employee_code.lower()}@example.com",
            country=country,
            department=department,
            job_title=job_title,
            status=status,
            hire_date=hire_date,
        )
        db.add(employee)
        db.flush()
        return employee

    return create_employee


@pytest.fixture
def salary_factory(db: Session):
    def create_salary(
        employee: Employee,
        amount: str,
        *,
        currency: str = "INR",
        effective_from: date = date(2020, 1, 1),
        effective_to: date | None = None,
        pay_frequency: str = "annual",
    ) -> SalaryRecord:
        record = SalaryRecord(
            employee_id=employee.id,
            amount=amount,
            currency=currency,
            pay_frequency=pay_frequency,
            effective_from=effective_from,
            effective_to=effective_to,
        )
        db.add(record)
        db.flush()
        return record

    return create_salary
