from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class SalaryRecordBase(BaseModel):
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(..., pattern=r"^[A-Z]{3}$")
    pay_frequency: Literal["annual", "monthly", "weekly", "hourly"] = "annual"
    effective_from: date
    effective_to: date | None = None


class SalaryRecordCreate(SalaryRecordBase):
    pass


class SalaryRecordUpdate(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    pay_frequency: Literal["annual", "monthly", "weekly", "hourly"] | None = None
    effective_from: date | None = None
    effective_to: date | None = None


class SalaryRecordOut(SalaryRecordBase):
    id: int
    employee_id: int

    model_config = {"from_attributes": True}
