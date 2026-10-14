from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class SalaryRecordBase(BaseModel):
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(..., min_length=3, max_length=3)
    pay_frequency: str = Field(default="annual", min_length=2, max_length=20)
    effective_from: date
    effective_to: date | None = None


class SalaryRecordCreate(SalaryRecordBase):
    pass


class SalaryRecordUpdate(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    pay_frequency: str | None = Field(default=None, min_length=2, max_length=20)
    effective_from: date | None = None
    effective_to: date | None = None


class SalaryRecordOut(SalaryRecordBase):
    id: int
    employee_id: int

    model_config = {"from_attributes": True}
