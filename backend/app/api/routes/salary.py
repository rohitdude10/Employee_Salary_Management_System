from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.security import require_roles
from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.employee import Employee
from app.models.salary_record import SalaryRecord
from app.models.user import User
from app.schemas.salary import SalaryRecordCreate, SalaryRecordOut, SalaryRecordUpdate

router = APIRouter()


def _log_audit(db: Session, user_id: int | None, employee_id: int | None, salary_record_id: int | None, action: str, details: dict, summary: str | None = None) -> None:
    audit = AuditLog(
        user_id=user_id,
        employee_id=employee_id,
        salary_record_id=salary_record_id,
        action=action,
        details=details,
        summary=summary,
    )
    db.add(audit)


@router.get("/{employee_id:int}")
def get_salary_history(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("hr_manager", "admin")),
):
    employee = db.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    records = (
        db.query(SalaryRecord)
        .filter(SalaryRecord.employee_id == employee_id)
        .order_by(SalaryRecord.effective_from.desc())
        .all()
    )
    return {
        "employee_id": employee_id,
        "records": [
            {
                "id": record.id,
                "amount": float(record.amount),
                "currency": record.currency,
                "pay_frequency": record.pay_frequency,
                "effective_from": record.effective_from.isoformat(),
                "effective_to": record.effective_to.isoformat() if record.effective_to else None,
                "created_at": record.created_at.isoformat(),
            }
            for record in records
        ],
    }


@router.post("/{employee_id:int}", response_model=SalaryRecordOut)
def create_salary_record(
    employee_id: int,
    payload: SalaryRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("hr_manager", "admin")),
):
    employee = db.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    if payload.amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Salary amount must be greater than zero")
    if payload.effective_from < employee.hire_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Effective date cannot be before hire date")
    if payload.effective_to is not None and payload.effective_to < payload.effective_from:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Effective-to date cannot be before effective-from date")

    existing = (
        db.query(SalaryRecord)
        .filter(SalaryRecord.employee_id == employee_id)
        .order_by(SalaryRecord.effective_from.asc())
        .all()
    )

    new_period_end = payload.effective_to or date.max
    closed_periods = []
    for record in existing:
        record_period_end = record.effective_to or date.max

        if (
            record.effective_from < payload.effective_from
            and record.effective_to is None
        ):
            closed_periods.append(
                {
                    "salary_record_id": record.id,
                    "previous_effective_to": None,
                    "effective_to": (payload.effective_from - timedelta(days=1)).isoformat(),
                }
            )
            record.effective_to = payload.effective_from - timedelta(days=1)
            continue

        if (
            record.effective_from <= new_period_end
            and payload.effective_from <= record_period_end
        ):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Salary period overlaps with an existing record")

    new_record = SalaryRecord(
        employee_id=employee_id,
        amount=payload.amount,
        currency=payload.currency,
        pay_frequency=payload.pay_frequency,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
    )
    db.add(new_record)
    db.flush()

    _log_audit(
        db,
        user_id=current_user.id,
        employee_id=employee_id,
        salary_record_id=new_record.id,
        action="salary_record_created",
        details={
            "amount": str(payload.amount),
            "currency": payload.currency,
            "effective_from": payload.effective_from.isoformat(),
            "closed_periods": closed_periods,
        },
        summary=f"Created salary record for employee {employee.employee_code}",
    )

    db.commit()
    db.refresh(new_record)
    return new_record


@router.get("/export-csv")
def export_salary_history_csv(
    employee_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("hr_manager", "admin")),
):
    records = db.query(SalaryRecord).order_by(SalaryRecord.employee_id, SalaryRecord.effective_from).all()
    if employee_id is not None:
        records = [record for record in records if record.employee_id == employee_id]

    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "employee_id", "amount", "currency", "pay_frequency", "effective_from", "effective_to", "created_at"])
    for record in records:
        writer.writerow([
            record.id,
            record.employee_id,
            str(record.amount),
            record.currency,
            record.pay_frequency,
            record.effective_from.isoformat(),
            record.effective_to.isoformat() if record.effective_to else "",
            record.created_at.isoformat(),
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=salary_history.csv"},
    )
