import csv
import io
from datetime import date, timedelta
from decimal import Decimal
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from fastapi.encoders import jsonable_encoder
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


MAX_CSV_BYTES = 5 * 1024 * 1024


def _serialize_employee(
    employee: Employee,
    latest_salary: SalaryRecord | None = None,
) -> EmployeeOut:
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
        count_statement = count_statement.where(*filters)

    total = db.scalar(count_statement) or 0
    offset = (page - 1) * size
    latest_salary_id = (
        select(SalaryRecord.id)
        .where(SalaryRecord.employee_id == Employee.id)
        .order_by(SalaryRecord.effective_from.desc(), SalaryRecord.created_at.desc())
        .limit(1)
        .correlate(Employee)
        .scalar_subquery()
    )
    rows = db.execute(
        select(Employee, SalaryRecord)
        .outerjoin(SalaryRecord, SalaryRecord.id == latest_salary_id)
        .where(*filters)
        .order_by(Employee.id)
        .offset(offset)
        .limit(size)
    ).all()

    payload = {
        "items": [
            _serialize_employee(employee, salary).model_dump()
            for employee, salary in rows
        ],
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
        "employee": _serialize_employee(
            employee,
            salary_history[0] if salary_history else None,
        ).model_dump(),
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

    _log_audit(
        db,
        user_id=current_user.id,
        employee_id=employee.id,
        salary_record_id=None,
        action="employee_created",
        details={"employee_code": employee.employee_code, "status": employee.status},
        summary=f"Created employee {employee.employee_code}",
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Employee code or email already exists",
        ) from exc
    db.refresh(employee)
    current_salary = (
        db.query(SalaryRecord)
        .filter(SalaryRecord.employee_id == employee.id)
        .order_by(SalaryRecord.effective_from.desc(), SalaryRecord.created_at.desc())
        .first()
    )
    return _serialize_employee(employee, current_salary)


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

    updates = payload.model_dump(exclude_unset=True)
    if updates.get("hire_date") is not None:
        existing_salary = db.scalar(
            select(SalaryRecord.id)
            .where(
                SalaryRecord.employee_id == employee_id,
                SalaryRecord.effective_from < updates["hire_date"],
            )
            .limit(1)
        )
        if existing_salary:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Hire date cannot be later than an existing salary effective date",
            )

    for field, value in updates.items():
        if field == "employee_code" and value is not None and value != employee.employee_code:
            existing = db.query(Employee).filter(Employee.employee_code == value).first()
            if existing and existing.id != employee_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Employee code already exists")
        if field == "email" and value is not None and value != employee.email:
            existing = db.query(Employee).filter(Employee.email == value).first()
            if existing and existing.id != employee_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")
        setattr(employee, field, value)

    _log_audit(
        db,
        user_id=current_user.id,
        employee_id=employee.id,
        salary_record_id=None,
        action="employee_updated",
        details=jsonable_encoder(
            {
                "before": old_values,
                "after": {
                    field: getattr(employee, field)
                    for field in old_values
                },
            }
        ),
        summary=f"Updated employee {employee.employee_code}",
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Employee code or email already exists",
        ) from exc
    db.refresh(employee)
    current_salary = (
        db.query(SalaryRecord)
        .filter(SalaryRecord.employee_id == employee.id)
        .order_by(SalaryRecord.effective_from.desc(), SalaryRecord.created_at.desc())
        .first()
    )
    return _serialize_employee(employee, current_salary)


@router.delete("/{employee_id:int}")
def deactivate_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("hr_manager", "admin")),
):
    employee = db.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    previous_status = employee.status
    employee.status = "inactive"
    _log_audit(
        db,
        user_id=current_user.id,
        employee_id=employee.id,
        salary_record_id=None,
        action="employee_deactivated",
        details={
            "employee_code": employee.employee_code,
            "before": {"status": previous_status},
            "after": {"status": employee.status},
        },
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

    latest_salary_id = (
        select(SalaryRecord.id)
        .where(SalaryRecord.employee_id == Employee.id)
        .order_by(SalaryRecord.effective_from.desc(), SalaryRecord.created_at.desc())
        .limit(1)
        .correlate(Employee)
        .scalar_subquery()
    )
    employees = db.execute(
        select(Employee, SalaryRecord)
        .outerjoin(SalaryRecord, SalaryRecord.id == latest_salary_id)
        .where(*filters)
        .order_by(Employee.id)
    ).all()
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
    for employee, latest_salary in employees:
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
    content_bytes = file.file.read(MAX_CSV_BYTES + 1)
    if len(content_bytes) > MAX_CSV_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"CSV file exceeds the {MAX_CSV_BYTES // (1024 * 1024)} MB limit",
        )
    try:
        content = content_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV file must use UTF-8 encoding",
        ) from exc

    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV file must include a header row",
        )

    normalized_headers = [name.strip() for name in reader.fieldnames]
    if len(normalized_headers) != len(set(normalized_headers)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV file contains duplicate column names",
        )
    reader.fieldnames = normalized_headers
    fieldnames = set(normalized_headers)
    required = {
        "employee_code",
        "first_name",
        "last_name",
        "email",
        "country",
        "department",
        "job_title",
        "hire_date",
    }
    missing = required - fieldnames
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required columns: {sorted(missing)}",
        )

    staged_rows = []
    seen_codes: set[str] = set()
    seen_emails: set[str] = set()
    errors: list[dict[str, object]] = []
    for row_number, row in enumerate(reader, start=2):
        if not any(value and value.strip() for value in row.values() if isinstance(value, str)):
            continue
        if None in row:
            errors.append({"row": row_number, "error": "Row has more values than the header"})
            continue

        try:
            row_data: dict[str, object] = {
                key: (value or "").strip()
                for key, value in row.items()
                if key is not None
            }
            if not row_data.get("status"):
                row_data["status"] = "active"
            salary_amount = row_data.get("salary_amount")
            if not salary_amount:
                for key in (
                    "salary_amount",
                    "salary_currency",
                    "salary_pay_frequency",
                    "salary_effective_from",
                ):
                    row_data.pop(key, None)
            elif not row_data.get("salary_currency"):
                row_data["salary_currency"] = "USD"

            payload = EmployeeCreate.model_validate(row_data)
            effective_from = payload.salary_effective_from or payload.hire_date
            if payload.salary_amount is not None and effective_from < payload.hire_date:
                errors.append(
                    {
                        "row": row_number,
                        "error": "Salary effective date cannot be before employee hire date",
                    }
                )
                continue

            if payload.employee_code in seen_codes:
                errors.append(
                    {"row": row_number, "error": "Duplicate employee code in CSV"}
                )
                continue
            email = str(payload.email).casefold()
            if email in seen_emails:
                errors.append({"row": row_number, "error": "Duplicate email in CSV"})
                continue
            seen_codes.add(payload.employee_code)
            seen_emails.add(email)
            staged_rows.append((row_number, payload, effective_from))
        except ValidationError as exc:
            messages = [
                f"{'.'.join(str(part) for part in issue['loc'])}: {issue['msg']}"
                for issue in exc.errors()
            ]
            errors.append({"row": row_number, "error": "; ".join(messages)})

    if errors:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"errors": errors})

    if not staged_rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV file contains no employee rows",
        )

    employee_codes = [payload.employee_code for _, payload, _ in staged_rows]
    emails = [str(payload.email) for _, payload, _ in staged_rows]
    existing_employees = db.scalars(
        select(Employee).where(
            or_(
                Employee.employee_code.in_(employee_codes),
                Employee.email.in_(emails),
            )
        )
    ).all()
    employees_by_code = {employee.employee_code: employee for employee in existing_employees}
    employees_by_email = {employee.email.casefold(): employee for employee in existing_employees}

    for row_number, payload, effective_from in staged_rows:
        employee_with_email = employees_by_email.get(str(payload.email).casefold())
        employee_with_code = employees_by_code.get(payload.employee_code)
        if employee_with_email and (
            employee_with_code is None or employee_with_email.id != employee_with_code.id
        ):
            errors.append(
                {"row": row_number, "error": "Email belongs to another employee"}
            )

    if errors:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"errors": errors})

    salary_employee_ids = [
        employees_by_code[payload.employee_code].id
        for _, payload, _ in staged_rows
        if payload.salary_amount is not None
        and payload.employee_code in employees_by_code
    ]
    existing_salaries: dict[int, list[SalaryRecord]] = {}
    if salary_employee_ids:
        salary_records = db.scalars(
            select(SalaryRecord)
            .where(SalaryRecord.employee_id.in_(salary_employee_ids))
            .order_by(SalaryRecord.employee_id, SalaryRecord.effective_from)
        ).all()
        for salary_record in salary_records:
            existing_salaries.setdefault(salary_record.employee_id, []).append(salary_record)

    for row_number, payload, effective_from in staged_rows:
        employee = employees_by_code.get(payload.employee_code)
        if employee is None or payload.salary_amount is None:
            continue
        for record in existing_salaries.get(employee.id, []):
            if record.effective_from < effective_from and record.effective_to is None:
                continue
            if record.effective_from <= effective_from <= (record.effective_to or date.max):
                errors.append(
                    {
                        "row": row_number,
                        "error": "Salary period overlaps with an existing salary record",
                    }
                )
                break
            if record.effective_from > effective_from:
                errors.append(
                    {
                        "row": row_number,
                        "error": "Salary period overlaps with a later salary record",
                    }
                )
                break

    if errors:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"errors": errors})

    inserted = 0
    updated = 0
    for _, payload, effective_from in staged_rows:
        employee = employees_by_code.get(payload.employee_code)
        employee_values = payload.model_dump(
            exclude={
                "salary_amount",
                "salary_currency",
                "salary_pay_frequency",
                "salary_effective_from",
            }
        )
        if employee is None:
            employee = Employee(**employee_values)
            db.add(employee)
            db.flush()
            employees_by_code[employee.employee_code] = employee
            inserted += 1
        else:
            for field, value in employee_values.items():
                setattr(employee, field, value)
            updated += 1

        salary_record = None
        closed_periods = []
        if payload.salary_amount is not None:
            for previous in existing_salaries.get(employee.id, []):
                if previous.effective_from < effective_from and previous.effective_to is None:
                    previous.effective_to = effective_from - timedelta(days=1)
                    closed_periods.append(previous.id)

            salary_record = SalaryRecord(
                employee_id=employee.id,
                amount=payload.salary_amount,
                currency=payload.salary_currency or "USD",
                pay_frequency=payload.salary_pay_frequency,
                effective_from=effective_from,
            )
            db.add(salary_record)
            db.flush()

        _log_audit(
            db,
            user_id=current_user.id,
            employee_id=employee.id,
            salary_record_id=salary_record.id if salary_record else None,
            action="employee_imported_csv",
            details={
                "employee_code": employee.employee_code,
                "closed_salary_record_ids": closed_periods,
                "salary_amount": str(payload.salary_amount) if payload.salary_amount else None,
            },
            summary=f"Imported employee {employee.employee_code}",
        )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="CSV import conflicts with existing employee or salary records",
        ) from exc

    return {"inserted": inserted, "updated": updated, "errors": []}
