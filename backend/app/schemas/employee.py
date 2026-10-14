from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class EmployeeBase(BaseModel):
    employee_code: str = Field(..., min_length=1, max_length=30)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=1, max_length=255)
    country: str = Field(..., min_length=1, max_length=100)
    department: str = Field(..., min_length=1, max_length=100)
    job_title: str = Field(..., min_length=1, max_length=100)
    hire_date: date
    status: str = "active"


class EmployeeCreate(EmployeeBase):
    salary_amount: Decimal | None = None
    salary_currency: str | None = None
    salary_pay_frequency: str = "annual"
    salary_effective_from: date | None = None


class EmployeeUpdate(BaseModel):
    employee_code: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    country: str | None = None
    department: str | None = None
    job_title: str | None = None
    hire_date: date | None = None
    status: str | None = None


class EmployeeOut(EmployeeBase):
    id: int
    current_salary: Decimal | None = None
    current_currency: str | None = None

    model_config = {"from_attributes": True}
