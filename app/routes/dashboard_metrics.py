from __future__ import annotations

import shutil
from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import current_user
from app.core.config import BACKUP_DIR
from app.database import get_db
from app.models import Employee, PlausibilityIssue, Setting, TimeEntry
from .common import is_fixed_admin_employee, not_deleted_filter, report_visible_employee_ids, role_name

router = APIRouter()


def _latest_backup() -> dict:
    backup_dir = Path(BACKUP_DIR)
    candidates = []
    if backup_dir.exists():
        candidates = [
            path for path in backup_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in {".zip", ".gz", ".tar", ".tgz", ".sql"}
        ]
    if not candidates:
        return {"label": "Kein Backup", "age_hours": None, "age_label": "nicht vorhanden", "level": "danger"}
    latest = max(candidates, key=lambda path: path.stat().st_mtime)
    backup_time = datetime.fromtimestamp(latest.stat().st_mtime)
    age_hours = max((datetime.now() - backup_time).total_seconds() / 3600, 0)
    age_days = int(age_hours // 24)
    if age_hours < 24:
        age_label = f"{int(age_hours)} Std. alt"
    elif age_days == 1:
        age_label = "1 Tag alt"
    else:
        age_label = f"{age_days} Tage alt"
    level = "ok" if age_hours <= 24 else "warning" if age_hours <= 72 else "danger"
    return {
        "label": backup_time.strftime("%d.%m.%Y %H:%M"),
        "age_hours": round(age_hours, 1),
        "age_label": age_label,
        "level": level,
    }


def _disk_status() -> dict:
    try:
        usage = shutil.disk_usage("/")
        free_percent = usage.free / usage.total * 100 if usage.total else 0
        level = "ok" if free_percent >= 20 else "warning" if free_percent >= 10 else "danger"
        return {"label": f"{free_percent:.1f} % frei", "level": level}
    except Exception:
        return {"label": "Unbekannt", "level": "warning"}


def _settings_status(db: Session, keys: tuple[str, ...]) -> bool:
    rows = db.query(Setting).filter(Setting.key.in_(keys)).all()
    values = {row.key: str(row.value or "").strip() for row in rows}
    return any(values.get(key) for key in keys)


def _scope(db: Session, user) -> tuple[list[int], str]:
    role = role_name(user)
    if not user:
        return [], ""
    if role in {"Administrator", "Personal"} or str(getattr(user, "employee_number", "")).lower() == "admin":
        return report_visible_employee_ids(db, user), "Gesamt"
    if role == "Teamleiter":
        return report_visible_employee_ids(db, user), "Team"
    return [user.id], "Eigene"


def _system_summary(backup: dict, disk: dict) -> tuple[str, str, str]:
    if disk["level"] == "danger":
        return "Speicher knapp", "danger", disk["label"]
    if backup["level"] == "danger":
        return "Backup veraltet", "danger", backup["age_label"]
    if disk["level"] == "warning":
        return "Speicher prüfen", "warning", disk["label"]
    if backup["level"] == "warning":
        return "Backup fällig", "warning", backup["age_label"]
    return "System OK", "ok", "Datenbank, Backup und Speicher"


@router.get("/api/dashboard/metrics")
def dashboard_metrics(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return JSONResponse({"error": "Nicht angemeldet"}, status_code=401)

    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = today_start + timedelta(days=1)

    active_employees = [
        employee for employee in db.query(Employee).filter(Employee.active == True).all()
        if not is_fixed_admin_employee(employee)
    ]
    active_ids = [employee.id for employee in active_employees]

    present_count = 0
    for employee_id in active_ids:
        entry = db.query(TimeEntry).filter(
            TimeEntry.employee_id == employee_id,
            not_deleted_filter(),
        ).order_by(TimeEntry.timestamp.desc(), TimeEntry.id.desc()).first()
        if entry and entry.entry_type in {"kommen", "pause_ende"}:
            present_count += 1

    booking_rows = db.query(TimeEntry.entry_type, func.count(TimeEntry.id)).filter(
        TimeEntry.employee_id.in_(active_ids) if active_ids else False,
        TimeEntry.timestamp >= today_start,
        TimeEntry.timestamp < today_end,
        not_deleted_filter(),
    ).group_by(TimeEntry.entry_type).all()
    booking_counts = {str(entry_type or ""): int(count or 0) for entry_type, count in booking_rows}

    open_plausibility = db.query(PlausibilityIssue).filter(
        PlausibilityIssue.status.in_(["offen", "geprueft"])
    ).count()
    plausibility_level = "ok" if open_plausibility == 0 else "warning" if open_plausibility <= 10 else "danger"

    visible_ids, overtime_scope = _scope(db, user)
    overtime_sum = 0.0
    if visible_ids:
        overtime_sum = float(db.query(func.coalesce(func.sum(Employee.overtime_balance), 0)).filter(
            Employee.id.in_(visible_ids), Employee.active == True
        ).scalar() or 0)

    backup = _latest_backup()
    disk = _disk_status()
    mail_ready = _settings_status(db, ("smtp_host", "mail_smtp_host", "email_smtp_host"))
    github_token = Path("/etc/stempeluhr/secrets/github_token").exists()
    system_label, system_level, system_detail = _system_summary(backup, disk)

    return {
        "presence": {
            "present": present_count,
            "active": len(active_employees),
            "absent": max(len(active_employees) - present_count, 0),
        },
        "bookings": {
            "total": sum(booking_counts.values()),
            "kommen": booking_counts.get("kommen", 0),
            "gehen": booking_counts.get("gehen", 0),
            "pause_start": booking_counts.get("pause_start", 0),
            "pause_ende": booking_counts.get("pause_ende", 0),
        },
        "plausibility": {"open": open_plausibility, "level": plausibility_level},
        "overtime": {"hours": round(overtime_sum, 2), "scope": overtime_scope},
        "backup": backup,
        "system": {
            "label": system_label,
            "detail": system_detail,
            "level": system_level,
            "database": {"label": "OK", "level": "ok"},
            "backup": backup,
            "disk": disk,
            "email": {"label": "Konfiguriert" if mail_ready else "Nicht konfiguriert", "level": "ok" if mail_ready else "info"},
            "github": {"label": "Token vorhanden" if github_token else "Token fehlt", "level": "ok" if github_token else "info"},
        },
    }
