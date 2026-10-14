
import random
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from sqlalchemy import func

# Allow execution from the backend directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from app.database import Base, SessionLocal, engine
from app.models import Employee, SalaryRecord


TOTAL_EMPLOYEES = 10_000
SEED = 20261014
INITIAL_SALARY_DATE = date(2026, 1, 1)

COUNTRIES = [
    # Country, currency, annual salary minimum, annual salary maximum
    ("India", "INR", 600_000, 3_000_000),
    ("United States", "USD", 60_000, 180_000),
    ("United Kingdom", "GBP", 40_000, 120_000),
    ("Germany", "EUR", 45_000, 130_000),
    ("Canada", "CAD", 65_000, 160_000),
    ("Australia", "AUD", 70_000, 170_000),
    ("Singapore", "SGD", 60_000, 150_000),
    ("Japan", "JPY", 5_000_000, 15_000_000),
]

FIRST_NAMES = [
    "Aarav", "Aditi", "Alex", "Amelia", "Daniel",
    "Emma", "Ishaan", "Liam", "Maya", "Noah",
    "Olivia", "Priya", "Rahul", "Sophia", "Vikram",
]

LAST_NAMES = [
    "Anderson", "Brown", "Chen", "Garcia", "Gupta",
    "Johnson", "Khan", "Martin", "Patel", "Sharma",
    "Singh", "Taylor", "Thomas", "Williams", "Wilson",
]

DEPARTMENTS = [
    "Engineering",
    "Human Resources",
    "Finance",
    "Sales",
    "Marketing",
    "Operations",
    "Customer Support",
    "Data",
]

JOB_TITLES = [
    "Software Engineer",
    "Senior Software Engineer",
    "Data Analyst",
    "Data Engineer",
    "HR Specialist",
    "Financial Analyst",
    "Sales Executive",
    "Product Manager",
    "Operations Manager",
    "Marketing Specialist",
]

STATUSES = ["active"] * 9 + ["inactive"]


def generate_employee(index: int) -> dict:
    rng = random.Random(SEED + index)

    country, _, _, _ = COUNTRIES[(index - 1) % len(COUNTRIES)]

    hire_date = date(2015, 1, 1) + timedelta(
        days=rng.randint(0, (date(2025, 12, 31) - date(2015, 1, 1)).days)
    )

    return {
        "employee_code": f"EMP{index:05d}",
        "first_name": rng.choice(FIRST_NAMES),
        "last_name": rng.choice(LAST_NAMES),
        "email": f"employee{index:05d}@example.com",
        "country": country,
        "department": rng.choice(DEPARTMENTS),
        "job_title": rng.choice(JOB_TITLES),
        "hire_date": hire_date,
        "status": rng.choice(STATUSES),
    }


def generate_salary(employee: Employee) -> dict:
    # Stable per employee: reruns produce the same salary.
    index = int(employee.employee_code[3:])
    rng = random.Random(SEED + 100_000 + index)

    country, currency, minimum, maximum = next(
        item for item in COUNTRIES if item[0] == employee.country
    )

    amount = Decimal(rng.randint(minimum, maximum))

    return {
        "employee_id": employee.id,
        "amount": amount,
        "currency": currency,
        "pay_frequency": "annual",
        "effective_from": employee.hire_date,
        "effective_to": None,
    }


def seed() -> None:
    # Convenient for a fresh local database.
    # For a migrated database, run `alembic upgrade head` first.
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        existing_codes = set(
            session.scalars(select(Employee.employee_code)).all()
        )

        new_employees = [
            Employee(**generate_employee(index))
            for index in range(1, TOTAL_EMPLOYEES + 1)
            if f"EMP{index:05d}" not in existing_codes
        ]

        if new_employees:
            session.add_all(new_employees)
            session.commit()

        # Retrieve all seeded employees, including existing ones.
        employees = session.scalars(
            select(Employee).where(
                Employee.employee_code.like("EMP%")
            )
        ).all()

        existing_salary_keys = set(
            session.execute(
                select(
                    SalaryRecord.employee_id,
                    SalaryRecord.effective_from,
                )
            ).all()
        )

        new_salaries = []

        for employee in employees:
            # Keep the initial salary date consistent with the hire date.
            key = (employee.id, employee.hire_date)

            if key not in existing_salary_keys:
                new_salaries.append(
                    SalaryRecord(**generate_salary(employee))
                )

        if new_salaries:
            session.add_all(new_salaries)
            session.commit()

        employee_count = session.scalar(
            select(func.count()).select_from(Employee)
        )
        salary_count = session.scalar(
            select(func.count()).select_from(SalaryRecord)
        )

        print("Seeding complete.")
        print(f"Employees in database: {employee_count}")
        print(f"Salary records in database: {salary_count}")
        print(f"New employees inserted: {len(new_employees)}")
        print(f"New salary records inserted: {len(new_salaries)}")


if __name__ == "__main__":    

    seed()
