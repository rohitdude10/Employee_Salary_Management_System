from statistics import median

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import require_roles
from app.database import get_db
from app.models.employee import Employee
from app.models.salary_record import SalaryRecord
from app.models.user import User

router = APIRouter()


def _latest_salary_for_employee(db: Session, employee_id: int):
    return (
        db.query(SalaryRecord)
        .filter(SalaryRecord.employee_id == employee_id)
        .order_by(SalaryRecord.effective_from.desc(), SalaryRecord.created_at.desc())
        .first()
    )


@router.get("", response_model=dict)
def get_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("hr_manager", "admin")),
):
    employees = db.query(Employee).all()
    salary_values = []
    country_totals = {}
    department_totals = {}
    job_title_totals = {}

    for employee in employees:
        latest_salary = _latest_salary_for_employee(db, employee.id)
        if latest_salary:
            salary_values.append(float(latest_salary.amount))
            country_totals[employee.country] = country_totals.get(employee.country, 0) + 1
            department_totals[employee.department] = department_totals.get(employee.department, 0) + 1
            job_title_totals[employee.job_title] = job_title_totals.get(employee.job_title, 0) + 1

    summary = {
        "total_employees": len(employees),
        "active_employees": db.query(Employee).filter(Employee.status == "active").count(),
        "inactive_employees": db.query(Employee).filter(Employee.status == "inactive").count(),
        "average_salary": round(sum(salary_values) / len(salary_values), 2) if salary_values else 0,
        "median_salary": round(median(salary_values), 2) if salary_values else 0,
        "min_salary": min(salary_values) if salary_values else 0,
        "max_salary": max(salary_values) if salary_values else 0,
    }

    return {
        "summary": summary,
        "by_country": dict(sorted(country_totals.items())),
        "by_department": dict(sorted(department_totals.items())),
        "by_job_title": dict(sorted(job_title_totals.items())),
    }


@router.get("/summary")
def get_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("hr_manager", "admin")),
):
    return get_analytics(db=db, current_user=current_user)
