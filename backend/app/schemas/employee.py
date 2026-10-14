from datetime import date
from decimal import Decimal

from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


class EmployeeBase(BaseModel):
    employee_code: str = Field(..., min_length=1, max_length=30)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    country: str = Field(..., min_length=1, max_length=100)
    department: str = Field(..., min_length=1, max_length=100)
    job_title: str = Field(..., min_length=1, max_length=100)
    hire_date: date
    status: Literal["active", "inactive"] = "active"

    @field_validator(
        "employee_code",
        "first_name",
        "last_name",
        "country",
        "department",
        "job_title",
        mode="before",
    )
    @classmethod
    def strip_text_fields(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class EmployeeCreate(EmployeeBase):
    salary_amount: Decimal | None = Field(default=None, gt=0)
    salary_currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    salary_pay_frequency: Literal["annual", "monthly", "weekly", "hourly"] = "annual"
    salary_effective_from: date | None = None


class EmployeeUpdate(BaseModel):
    employee_code: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    country: str | None = None
    department: str | None = None
    job_title: str | None = None
    hire_date: date | None = None
    status: Literal["active", "inactive"] | None = None

    @field_validator(
        "employee_code",
        "first_name",
        "last_name",
        "country",
        "department",
        "job_title",
        mode="before",
    )
    @classmethod
    def strip_optional_text_fields(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("status", mode="before")
    @classmethod
    def normalize_optional_status(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class EmployeeOut(EmployeeBase):
    id: int
    current_salary: Decimal | None = None
    current_currency: str | None = None

    model_config = {"from_attributes": True}
