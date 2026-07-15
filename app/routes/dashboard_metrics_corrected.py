from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Employee, TimeEntry
from app.services.worktime import calculate_period
from .common import not_deleted_filter, report_visible_employee_ids, role_name
from .dashboard_metrics import dashboard_metrics as original_dashboard_metrics

router = APIRouter()


def _visible_scope(db: Session, user):
    role = role_name(user)
    if role in {"Administrator", "Personal"} or str(getattr(user, "employee_number", "")).lower() == "admin":
        return report_visible_employee_ids(db, user), "Gesamt"
    if role == "Teamleiter":
        return report_visible_employee_ids(db, user), "Team"
    return [user.id], "Eigene"


def _employee_balance(db: Session, employee: Employee, end_day: date) -> float:
    baseline = 0.0
    first_entry = db.query(TimeEntry).filter(
        TimeEntry.employee_id == employee.id,
        not_deleted_filter(),
    ).order_by(TimeEntry.timestamp.asc(), TimeEntry.id.asc()).first()

    start_day = first_entry.timestamp.date() if first_entry else (employee.entry_date or end_day)
    if employee.entry_date and employee.entry_date > start_day:
        start_day = employee.entry_date

    try:
        from .overtime_adjustments import OvertimeAdjustment
        adjustment = db.query(OvertimeAdjustment).filter(
            OvertimeAdjustment.employee_id == employee.id,
            OvertimeAdjustment.status == "applied",
            OvertimeAdjustment.applied_at.is_not(None),
        ).order_by(OvertimeAdjustment.effective_at.desc(), OvertimeAdjustment.id.desc()).first()
        if adjustment:
            baseline = float(adjustment.target_balance or 0.0)
            start_day = adjustment.effective_at.date() + timedelta(days=1)
    except Exception:
        baseline = float(employee.overtime_balance or 0.0)

    if start_day > end_day:
        return round(baseline, 2)

    result = calculate_period(db, start_day, end_day, employee.id, [employee.id])
    rows = [
        row for row in (result.get("rows") or [])
        if getattr(row, "date", end_day) <= end_day and not bool(getattr(row, "incomplete", False))
    ]
    accrued = sum(float(getattr(row, "overtime_hours", 0.0) or 0.0) for row in rows)
    return round(baseline + accrued, 2)


@router.get("/api/dashboard/metrics")
def corrected_dashboard_metrics(request: Request, db: Session = Depends(get_db)):
    data = original_dashboard_metrics(request, db)
    if not isinstance(data, dict):
        return data

    from app.auth import current_user
    user = current_user(request, db)
    if not user:
        return data

    employee_ids, scope = _visible_scope(db, user)
    employees = db.query(Employee).filter(Employee.id.in_(employee_ids), Employee.active == True).all() if employee_ids else []
    total = sum(_employee_balance(db, employee, date.today()) for employee in employees)
    data["overtime"] = {"hours": round(total, 2), "scope": scope}
    return data
