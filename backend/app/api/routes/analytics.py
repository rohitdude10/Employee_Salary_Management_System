from collections import defaultdict
from datetime import date
from statistics import median

from fastapi import APIRouter, Depends
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.security import require_roles
from app.database import get_db
from app.models.employee import Employee
from app.models.salary_record import SalaryRecord
from app.models.user import User

router = APIRouter()


@router.get("", response_model=dict)
def get_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("hr_manager", "admin")),
):
    employee_rows = db.execute(
        select(Employee.country, Employee.department, Employee.job_title, Employee.status)
    ).all()
    country_totals: dict[str, int] = defaultdict(int)
    department_totals: dict[str, int] = defaultdict(int)
    job_title_totals: dict[str, int] = defaultdict(int)

    for country, department, job_title, _ in employee_rows:
        country_totals[country] += 1
        department_totals[department] += 1
        job_title_totals[job_title] += 1

    latest_effective_date = (
        select(
            SalaryRecord.employee_id.label("employee_id"),
            func.max(SalaryRecord.effective_from).label("effective_from"),
        )
        .where(SalaryRecord.effective_from <= date.today())
        .group_by(SalaryRecord.employee_id)
        .subquery()
    )
    current_salary_rows = db.execute(
        select(SalaryRecord.currency, SalaryRecord.amount)
        .join(
            latest_effective_date,
            and_(
                SalaryRecord.employee_id == latest_effective_date.c.employee_id,
                SalaryRecord.effective_from == latest_effective_date.c.effective_from,
            ),
        )
        .where(
            or_(
                SalaryRecord.effective_to.is_(None),
                SalaryRecord.effective_to >= date.today(),
            )
        )
    ).all()

    salaries_by_currency: dict[str, list[float]] = defaultdict(list)
    for currency, amount in current_salary_rows:
        salaries_by_currency[currency].append(float(amount))

    by_currency = [
        {
            "currency": currency,
            "employee_count": len(values),
            "average_salary": round(sum(values) / len(values), 2),
            "median_salary": round(median(values), 2),
            "min_salary": min(values),
            "max_salary": max(values),
        }
        for currency, values in sorted(salaries_by_currency.items())
    ]

    total_employees = len(employee_rows)
    active_employees = sum(1 for row in employee_rows if row.status == "active")
    inactive_employees = sum(1 for row in employee_rows if row.status == "inactive")

    return {
        "summary": {
            "total_employees": total_employees,
            "active_employees": active_employees,
            "inactive_employees": inactive_employees,
            "employees_with_current_salary": len(current_salary_rows),
            "currency_count": len(by_currency),
        },
        "by_country": dict(sorted(country_totals.items())),
        "by_department": dict(sorted(department_totals.items())),
        "by_job_title": dict(sorted(job_title_totals.items())),
        "by_currency": by_currency,
    }


@router.get("/summary")
def get_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("hr_manager", "admin")),
):
    return get_analytics(db=db, current_user=current_user)
