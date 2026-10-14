import csv
import io
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import or_, select, func
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_roles
from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.employee import Employee
from app.models.salary_record import SalaryRecord
from app.models.user import User
from app.schemas.employee import EmployeeCreate, EmployeeOut, EmployeeUpdate

router = APIRouter()


def _serialize_employee(employee: Employee, db: Session) -> EmployeeOut:
    latest_salary = (
        db.query(SalaryRecord)
        .filter(SalaryRecord.employee_id == employee.id)
        .order_by(SalaryRecord.effective_from.desc(), SalaryRecord.created_at.desc())
        .first()
    )
    return EmployeeOut(
        id=employee.id,
        employee_code=employee.employee_code,
        first_name=employee.first_name,
        last_name=employee.last_name,
        email=employee.email,
        country=employee.country,
        department=employee.department,
        job_title=employee.job_title,
        hire_date=employee.hire_date,
        status=employee.status,
        current_salary=latest_salary.amount if latest_salary else None,
        current_currency=latest_salary.currency if latest_salary else None,
    )


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


@router.get("", response_model=dict)
def list_employees(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    search: str | None = None,
    country: str | None = None,
    department: str | None = None,
    job_title: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("hr_manager", "admin")),
):
    statement = select(Employee)
    count_statement = select(func.count(Employee.id))
    filters = []

    if search:
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                Employee.first_name.ilike(term),
                Employee.last_name.ilike(term),
                Employee.employee_code.ilike(term),
                Employee.email.ilike(term),
                Employee.department.ilike(term),
                Employee.job_title.ilike(term),
            )
        )
    if country:
        filters.append(Employee.country == country)
    if department:
        filters.append(Employee.department == department)
    if job_title:
        filters.append(Employee.job_title == job_title)
    if status:
        filters.append(Employee.status == status)

    if filters:
        statement = statement.where(*filters)
        count_statement = count_statement.where(*filters)

    total = db.scalar(count_statement) or 0
    offset = (page - 1) * size
    rows = db.scalars(statement.order_by(Employee.id).offset(offset).limit(size)).all()

    payload = {
        "items": [_serialize_employee(employee, db).model_dump() for employee in rows],
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size if total else 0,
    }
    return payload


@router.get("/{employee_id:int}", response_model=dict)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("hr_manager", "admin")),
):
    employee = db.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    salary_history = (
        db.query(SalaryRecord)
        .filter(SalaryRecord.employee_id == employee_id)
        .order_by(SalaryRecord.effective_from.desc())
        .all()
    )
    return {
        "employee": _serialize_employee(employee, db).model_dump(),
        "salary_history": [
            {
                "id": record.id,
                "employee_id": record.employee_id,
                "amount": float(record.amount),
                "currency": record.currency,
                "pay_frequency": record.pay_frequency,
                "effective_from": record.effective_from.isoformat(),
                "effective_to": record.effective_to.isoformat() if record.effective_to else None,
            }
            for record in salary_history
        ],
    }


@router.post("", response_model=EmployeeOut)
def create_employee(
    payload: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("hr_manager", "admin")),
):
    if db.query(Employee).filter(Employee.employee_code == payload.employee_code).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Employee code already exists")
    if db.query(Employee).filter(Employee.email == payload.email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")

    employee = Employee(
        employee_code=payload.employee_code,
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        country=payload.country,
        department=payload.department,
        job_title=payload.job_title,
        hire_date=payload.hire_date,
        status=payload.status,
    )
    db.add(employee)
    db.flush()

    if payload.salary_amount is not None:
        salary_effective_from = payload.salary_effective_from or payload.hire_date
        if payload.salary_amount <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Salary amount must be greater than zero")
        if salary_effective_from < payload.hire_date:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Salary effective date cannot be before employee hire date")

        country_currency = payload.salary_currency or (payload.country[:3].upper() if len(payload.country) >= 3 else "USD")
        salary_record = SalaryRecord(
            employee_id=employee.id,
            amount=Decimal(str(payload.salary_amount)),
            currency=country_currency,
            pay_frequency=payload.salary_pay_frequency,
            effective_from=salary_effective_from,
            effective_to=None,
        )
        db.add(salary_record)

    db.commit()
    db.refresh(employee)
    _log_audit(
        db,
        user_id=current_user.id,
        employee_id=employee.id,
        salary_record_id=None,
        action="employee_created",
        details={"employee_code": employee.employee_code, "status": employee.status},
        summary=f"Created employee {employee.employee_code}",
    )
    db.commit()
    return _serialize_employee(employee, db)


@router.put("/{employee_id:int}", response_model=EmployeeOut)
def update_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("hr_manager", "admin")),
):
    employee = db.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    old_values = {
        "employee_code": employee.employee_code,
        "first_name": employee.first_name,
        "last_name": employee.last_name,
        "email": employee.email,
        "country": employee.country,
        "department": employee.department,
        "job_title": employee.job_title,
        "hire_date": employee.hire_date.isoformat(),
        "status": employee.status,
    }

    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "employee_code" and value is not None and value != employee.employee_code:
            existing = db.query(Employee).filter(Employee.employee_code == value).first()
            if existing and existing.id != employee_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Employee code already exists")
        if field == "email" and value is not None and value != employee.email:
            existing = db.query(Employee).filter(Employee.email == value).first()
            if existing and existing.id != employee_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")
        setattr(employee, field, value)

    db.commit()
    db.refresh(employee)
    _log_audit(
        db,
        user_id=current_user.id,
        employee_id=employee.id,
        salary_record_id=None,
        action="employee_updated",
        details={"before": old_values, "after": _serialize_employee(employee, db).model_dump()},
        summary=f"Updated employee {employee.employee_code}",
    )
    db.commit()
    return _serialize_employee(employee, db)


@router.delete("/{employee_id:int}")
def deactivate_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("hr_manager", "admin")),
):
    employee = db.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    employee.status = "inactive"
    db.commit()
    _log_audit(
        db,
        user_id=current_user.id,
        employee_id=employee.id,
        salary_record_id=None,
        action="employee_deactivated",
        details={"employee_code": employee.employee_code},
        summary=f"Deactivated employee {employee.employee_code}",
    )
    db.commit()
    return {"message": "Employee deactivated", "employee_id": employee_id}


@router.get("/export-csv")
def export_employees_csv(
    search: str | None = None,
    country: str | None = None,
    department: str | None = None,
    job_title: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("hr_manager", "admin")),
):
    statement = select(Employee)
    if search:
        term = f"%{search.strip()}%"
        statement = statement.where(
            or_(
                Employee.first_name.ilike(term),
                Employee.last_name.ilike(term),
                Employee.employee_code.ilike(term),
                Employee.email.ilike(term),
                Employee.department.ilike(term),
                Employee.job_title.ilike(term),
            )
        )
    if country:
        statement = statement.where(Employee.country == country)
    if department:
        statement = statement.where(Employee.department == department)
    if job_title:
        statement = statement.where(Employee.job_title == job_title)
    if status:
        statement = statement.where(Employee.status == status)

    employees = db.scalars(statement.order_by(Employee.id)).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id",
        "employee_code",
        "first_name",
        "last_name",
        "email",
        "country",
        "department",
        "job_title",
        "hire_date",
        "status",
        "current_salary",
        "current_currency",
    ])
    for employee in employees:
        latest_salary = (
            db.query(SalaryRecord)
            .filter(SalaryRecord.employee_id == employee.id)
            .order_by(SalaryRecord.effective_from.desc(), SalaryRecord.created_at.desc())
            .first()
        )
        writer.writerow([
            employee.id,
            employee.employee_code,
            employee.first_name,
            employee.last_name,
            employee.email,
            employee.country,
            employee.department,
            employee.job_title,
            employee.hire_date.isoformat(),
            employee.status,
            str(latest_salary.amount) if latest_salary else "",
            latest_salary.currency if latest_salary else "",
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=employees.csv"},
    )


@router.post("/import-csv")
def import_employees_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("hr_manager", "admin")),
):
    content = file.file.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    fieldnames = set(reader.fieldnames or [])
    required = {"employee_code", "first_name", "last_name", "email", "country", "department", "job_title", "hire_date"}
    missing = required - fieldnames
    if missing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Missing required columns: {sorted(missing)}")

    inserted = 0
    updated = 0
    errors = []

    for row in reader:
        try:
            payload = {
                "employee_code": (row.get("employee_code") or "").strip(),
                "first_name": (row.get("first_name") or "").strip(),
                "last_name": (row.get("last_name") or "").strip(),
                "email": (row.get("email") or "").strip(),
                "country": (row.get("country") or "").strip(),
                "department": (row.get("department") or "").strip(),
                "job_title": (row.get("job_title") or "").strip(),
                "hire_date": date.fromisoformat((row.get("hire_date") or "").strip()),
                "status": (row.get("status") or "active").strip() or "active",
            }
            if not all(payload.values()):
                raise ValueError("One or more required fields are empty")

            employee = db.query(Employee).filter(Employee.employee_code == payload["employee_code"]).first()
            if employee:
                for key, value in payload.items():
                    setattr(employee, key, value)
                updated += 1
            else:
                employee = Employee(**payload)
                db.add(employee)
                db.flush()
                inserted += 1

            salary_amount = (row.get("salary_amount") or "").strip()
            if salary_amount:
                salary_currency = (row.get("salary_currency") or "USD").strip() or "USD"
                pay_frequency = (row.get("salary_pay_frequency") or "annual").strip() or "annual"
                salary_effective_from = row.get("salary_effective_from")
                effective_from = date.fromisoformat(salary_effective_from.strip()) if salary_effective_from else payload["hire_date"]
                salary = SalaryRecord(
                    employee_id=employee.id,
                    amount=Decimal(salary_amount),
                    currency=salary_currency,
                    pay_frequency=pay_frequency,
                    effective_from=effective_from,
                )
                db.add(salary)

            _log_audit(
                db,
                user_id=current_user.id,
                employee_id=employee.id,
                salary_record_id=None,
                action="employee_imported_csv",
                details={"employee_code": employee.employee_code},
                summary=f"Imported employee {employee.employee_code}",
            )
        except Exception as exc:
            errors.append({"row": reader.line_num, "error": str(exc)})

    if errors:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"errors": errors})

    db.commit()
    return {"inserted": inserted, "updated": updated, "errors": []}
