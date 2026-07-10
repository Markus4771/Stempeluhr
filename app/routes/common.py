from uuid import uuid4
import re
import hashlib
import secrets
import shutil
import tarfile
from fastapi import APIRouter, Depends, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, PlainTextResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, text
from datetime import datetime, timedelta, date
import os
import subprocess
import socket
import struct
from urllib.parse import quote
from pathlib import Path
import ipaddress
from app.database import get_db
from app.models import Employee, TimeEntry, Correction, Setting, Role, AuditLog, Terminal, Holiday, Project, Vehicle, Department, VacationRequest, PlausibilityIssue, MailDispatchLog, ApiToken, WorkTimeAccount, DsgvoLog, AbsenceType, AbsenceType
from app.security import hash_password, verify_password
from app.caldav_service import import_holidays_from_caldav, build_vacation_ical
from app.mailer import send_email_from_settings
from app.auth import login_user, logout_user, current_user, is_admin_user, is_system_admin


def is_fixed_admin_employee(employee) -> bool:
    """Erkennt den festen Notfall-/Systemadmin.

    Dieser Benutzer ist nur für Verwaltung/Notfallzugang gedacht und darf nicht
    in Zeiterfassung, Auswertung oder Arbeitszeitberechnung auftauchen.
    """
    if not employee:
        return False
    return (
        str(getattr(employee, "employee_number", "") or "").strip().lower() == "admin"
        or str(getattr(employee, "username", "") or "").strip().lower() == "admin"
        or (str(getattr(employee, "first_name", "") or "").strip().lower() == "fester"
            and str(getattr(employee, "last_name", "") or "").strip().lower() == "admin")
    )


def _exclude_fixed_admin(query, Employee):
    """Festen Notfall-Admin aus Zeiterfassung, Auswertungen und Statistiken herausrechnen."""
    for field in ("username", "employee_number", "email"):
        if hasattr(Employee, field):
            query = query.filter(getattr(Employee, field) != "admin")
    if hasattr(Employee, "first_name"):
        query = query.filter(Employee.first_name != "admin")
        query = query.filter(Employee.first_name != "Fester")
    if hasattr(Employee, "last_name"):
        query = query.filter(Employee.last_name != "admin")
        query = query.filter(Employee.last_name != "Admin")
    return query

from app.core.config import TEMPLATE_DIR, UPLOAD_DIR, BACKUP_DIR
from app.version import get_app_version, get_version_info
from app.services.employee_number import (
    ensure_employee_number_length_setting as service_ensure_employee_number_length_setting,
    get_employee_number_length as service_get_employee_number_length,
    normalize_employee_number as service_normalize_employee_number,
    validate_employee_number as service_validate_employee_number,
    clamp_employee_number_length,
)
from app.services.settings_service import set_setting as service_set_setting, settings_dict as service_settings_dict, get_setting as service_get_setting
from app.services.worktime import ensure_break_settings, calculate_period, calculate_worktime_account
from app.services.plausibility import ensure_plausibility_settings, get_plausibility_settings, scan_day, teamlead_summary, dispatch_daily_plausibility_mails, plausibility_scheduler_tick

templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
# Version nicht nur beim Start einmal setzen, sondern bei jeder Template-Antwort frisch einfügen.
templates.env.globals["app_version"] = get_app_version()
templates.env.globals["version_info"] = get_version_info()
_original_template_response = templates.TemplateResponse

def _inject_template_version(context):
    if context is None:
        context = {}
    try:
        context["app_version"] = get_app_version()
        context["version_info"] = get_version_info()
    except Exception:
        context.setdefault("app_version", "unbekannt")
    return context

def _template_response_with_version(*args, **kwargs):
    """Kompatibilitäts-Wrapper für Starlette/Jinja2 TemplateResponse.

    Der bestehende Quellcode nutzt noch die ältere Schreibweise
    TemplateResponse("template.html", {"request": request, ...}).
    Neuere Starlette-Versionen erwarten dagegen
    TemplateResponse(request, "template.html", context).
    Dieser Wrapper unterstützt beide Varianten und verhindert
    den Fehler "TypeError: unhashable type: 'dict'".
    """
    if args and isinstance(args[0], str):
        name = args[0]
        context = args[1] if len(args) > 1 else kwargs.pop("context", None)
        context = _inject_template_version(context)
        request = context.get("request") or kwargs.pop("request", None)
        remaining = args[2:] if len(args) > 2 else ()
        return _original_template_response(request=request, name=name, context=context, *remaining, **kwargs)

    if len(args) >= 3:
        args = list(args)
        args[2] = _inject_template_version(args[2])
        return _original_template_response(*args, **kwargs)

    if "context" in kwargs:
        kwargs["context"] = _inject_template_version(kwargs.get("context"))
    return _original_template_response(*args, **kwargs)

templates.TemplateResponse = _template_response_with_version



def ensure_module_visibility_settings(db: Session):
    """Standardwerte für aktivierbare Systemeinstellungs-Untermenüs.

    Allgemeine Einstellungen bleiben immer aktiv und werden hier bewusst nicht schaltbar gemacht.
    """
    defaults = {
        "module_settings_departments_enabled": "1",
        "module_settings_plausibility_enabled": "1",
        "module_settings_breaks_enabled": "1",
        "module_settings_backup_enabled": "1",
        "module_settings_email_enabled": "1",
        "module_settings_caldav_enabled": "1",
        "module_settings_api_enabled": "1",
        "module_settings_terminals_enabled": "1",
        "module_settings_time_enabled": "1",
        "module_settings_https_enabled": "1",
        "module_settings_security_enabled": "1",
        "module_settings_offboarding_enabled": "1",
        "module_settings_dsgvo_enabled": "1",
    }
    changed = False
    for key, value in defaults.items():
        if service_get_setting(db, key, None) is None:
            service_set_setting(db, key, value)
            changed = True
    if changed:
        db.commit()

def module_enabled(settings: dict, key: str) -> bool:
    return str(settings.get(key, "1")).lower() in ["1", "true", "on", "ja", "yes"]

def status_display_seconds(db: Session) -> int:
    try:
        value = int(service_get_setting(db, "booking_status_display_seconds", "5"))
    except Exception:
        value = 5
    return max(1, min(value, 60))

def auto_delay_seconds_setting(db: Session) -> int:
    try:
        value = int(service_get_setting(db, "booking_auto_delay_seconds", "3"))
    except Exception:
        value = 3
    return max(1, min(value, 30))
VALID_ENTRY_TYPES = {"kommen", "gehen", "pause_start", "pause_ende"}


def not_deleted_filter():
    """Kompatibilität: ältere Datenbankzeilen haben deleted ggf. NULL.
    NULL wird wie nicht gelöscht behandelt, damit Auto-Buchung/Status/Reports
    bestehende Buchungen weiterhin berücksichtigen.
    """
    return or_(TimeEntry.deleted == False, TimeEntry.deleted.is_(None))

# ---------------------------------------------------------------------------
# RFID-Lernmodus über Raspberry-Terminal
# ---------------------------------------------------------------------------
RFID_LEARN_EMPLOYEE_ID_KEY = "rfid_learn_pending_employee_id"
RFID_LEARN_STARTED_BY_KEY = "rfid_learn_pending_started_by"
RFID_LEARN_STARTED_AT_KEY = "rfid_learn_pending_started_at"

def _clear_pending_rfid_learn(db: Session):
    for key in (RFID_LEARN_EMPLOYEE_ID_KEY, RFID_LEARN_STARTED_BY_KEY, RFID_LEARN_STARTED_AT_KEY):
        row = db.query(Setting).filter(Setting.key == key).first()
        if row:
            db.delete(row)
    db.commit()

def _start_pending_rfid_learn(db: Session, employee: Employee, user: Employee):
    service_set_setting(db, RFID_LEARN_EMPLOYEE_ID_KEY, str(employee.id))
    service_set_setting(db, RFID_LEARN_STARTED_BY_KEY, getattr(user, "employee_number", "admin") or "admin")
    service_set_setting(db, RFID_LEARN_STARTED_AT_KEY, datetime.now().isoformat(timespec="seconds"))
    db.commit()

def _get_pending_rfid_employee(db: Session):
    value = service_settings_dict(db).get(RFID_LEARN_EMPLOYEE_ID_KEY, "")
    try:
        employee_id = int(value)
    except Exception:
        return None
    return db.query(Employee).filter(Employee.id == employee_id).first()

def _get_pending_rfid_status(db: Session):
    employee = _get_pending_rfid_employee(db)
    settings = service_settings_dict(db)
    if not employee:
        return {"active": False, "employee": None, "started_at": ""}
    return {
        "active": True,
        "employee": {
            "id": employee.id,
            "employee_number": employee.employee_number,
            "first_name": employee.first_name,
            "last_name": employee.last_name,
            "name": f"{employee.first_name} {employee.last_name}",
        },
        "started_at": settings.get(RFID_LEARN_STARTED_AT_KEY, ""),
    }

def _save_pending_rfid_from_terminal(request: Request, db: Session, rfid_code: str):
    """Speichert einen am Raspberry gescannten RFID-Code im aktiven Lernauftrag."""
    rfid_code = (rfid_code or "").strip().replace("\r", "").replace("\n", "")
    pending_employee = _get_pending_rfid_employee(db)
    if not pending_employee or not rfid_code:
        return None

    existing = db.query(Employee).filter(Employee.rfid_code == rfid_code, Employee.id != pending_employee.id).first()
    if existing:
        return templates.TemplateResponse("message.html", {
            "request": request,
            "title": "RFID bereits vergeben",
            "message": f"Dieser RFID-Code ist bereits bei {existing.first_name} {existing.last_name} hinterlegt. Lernmodus bleibt aktiv.",
            "return_to": "/raspberry"
        })

    old_rfid = pending_employee.rfid_code
    pending_employee.rfid_code = rfid_code
    pending_employee.updated_at = datetime.now()
    db.commit()

    log_action(
        db,
        "raspberry",
        "rfid_learned_on_terminal",
        "employees",
        str(pending_employee.id),
        f"RFID geändert von {old_rfid or '-'} auf {rfid_code}"
    )
    _clear_pending_rfid_learn(db)

    return templates.TemplateResponse("message.html", {
        "request": request,
        "title": "RFID gespeichert",
        "message": f"RFID wurde am Raspberry für {pending_employee.first_name} {pending_employee.last_name} gespeichert.",
        "return_to": "/raspberry",
        "status_display_seconds": status_display_seconds(db)
    })


# ---------------------------------------------------------------------------
# Auswertungsrechte
# ---------------------------------------------------------------------------
def role_name(user) -> str:
    return user.role.name if user and user.role else ""

def is_hr_or_admin(user) -> bool:
    return role_name(user) in ["Administrator", "Personal"]

def report_visible_employee_ids(db: Session, user):
    """Mitarbeiter-Sicht für Auswertungen.

    - Mitarbeiter: nur eigene Zeiten
    - Teamleiter: eigene Zeiten + Mitarbeiter der geleiteten Abteilungen
    - Personal/Administrator: alle aktiven Mitarbeiter
    """
    if not user:
        return []
    if is_hr_or_admin(user):
        return [e.id for e in _exclude_fixed_admin(db.query(Employee.id).filter(Employee.active == True), Employee).all()]
    if role_name(user) == "Teamleiter":
        dept_ids = [d.id for d in db.query(Department).filter(Department.manager_employee_id == user.id, Department.active == True).all()]
        ids = {user.id}
        if dept_ids:
            ids.update(e.id for e in _exclude_fixed_admin(db.query(Employee.id).filter(Employee.active == True, Employee.department_id.in_(dept_ids)), Employee).all())
        return sorted(ids)
    return [user.id]

def can_view_report_employee(db: Session, user, employee_id: int) -> bool:
    return int(employee_id or 0) in report_visible_employee_ids(db, user)

def log_action(db, actor, action, entity="", entity_id="", details=""):
    db.add(AuditLog(actor=actor, action=action, entity=entity, entity_id=entity_id, details=details))
    db.commit()

def require_admin_response(request: Request, db: Session):
    user = current_user(request, db)
    if not is_admin_user(user):
        return None, RedirectResponse("/login", status_code=303)
    return user, None


def can_manage_all_corrections(user) -> bool:
    return bool(user and (is_admin_user(user) or is_hr_or_admin(user)))

def can_use_corrections(user) -> bool:
    return bool(user and (can_manage_all_corrections(user) or getattr(user, "can_self_correct", False)))

def can_correct_entry(db: Session, user, entry: TimeEntry) -> bool:
    if not user or not entry:
        return False
    if can_manage_all_corrections(user):
        return True
    return bool(getattr(user, "can_self_correct", False) and entry.employee_id == user.id)

def correction_visible_employee_ids(db: Session, user):
    if can_manage_all_corrections(user):
        return [e.id for e in _exclude_fixed_admin(db.query(Employee.id).filter(Employee.active == True), Employee).all()]
    if getattr(user, "can_self_correct", False):
        return [user.id]
    return []

def require_corrections_response(request: Request, db: Session):
    user = current_user(request, db)
    if not can_use_corrections(user):
        return None, RedirectResponse("/login", status_code=303)
    return user, None

def require_system_admin_response(request: Request, db: Session):
    user = current_user(request, db)
    if not is_system_admin(user):
        return None, RedirectResponse("/login", status_code=303)
    return user, None


def sync_emergency_admin(db: Session):
    admin_role = db.query(Role).filter(Role.name == "Administrator").first()
    fixed_admin = db.query(Employee).filter(Employee.employee_number == "admin").first()
    if not admin_role or not fixed_admin:
        return
    real_admin_count = db.query(Employee).filter(
        Employee.employee_number != "admin",
        Employee.active == True,
        Employee.role_id == admin_role.id
    ).count()
    fixed_admin.active = False if real_admin_count > 0 else True
    db.commit()



def calculate_employee_vacation_used(db: Session, employee_id: int) -> float:
    """Berechnet genommene Abwesenheitstage aus genehmigten Abwesenheitsanträgen."""
    used = db.query(func.coalesce(func.sum(VacationRequest.days), 0.0)).filter(
        VacationRequest.employee_id == employee_id,
        VacationRequest.request_type == "abwesenheit",
        VacationRequest.status == "genehmigt"
    ).scalar()
    return float(used or 0.0)

def sync_employee_vacation_balance(db: Session, employee: Employee) -> None:
    """Synchronisiert genommene Abwesenheitstage und Resturlaub in der Mitarbeiter-Tabelle."""
    if not employee:
        return
    total = float(employee.vacation_days_total or 0.0)
    used = calculate_employee_vacation_used(db, employee.id) if employee.id else float(employee.vacation_days_used or 0.0)
    employee.vacation_days_used = used
    employee.vacation_days_remaining = total - used

def sync_all_vacation_balances(db: Session) -> None:
    for employee in db.query(Employee).all():
        sync_employee_vacation_balance(db, employee)

from app.services.booking_state import (
    normalize_entry_type,
    determine_auto_entry_type,
    get_booking_state,
    is_valid_transition_for_employee,
    latest_entry as latest_any_time_entry,
)


def get_latest_today_entry(db: Session, employee_id: int):
    """Kompatibilitätsfunktion für ältere Templates/Routen.

    Die eigentliche Entscheidung läuft ab 4.4.6/4.5.1 über den zentralen
    Zustandsautomaten in app.services.booking_state.
    """
    return get_booking_state(db, employee_id).last_entry


def is_duplicate_booking(db: Session, employee_id: int, seconds: int = 8):
    last = latest_any_time_entry(db, employee_id)
    if not last:
        return False, None
    delta = datetime.now() - last.timestamp
    if delta.total_seconds() < seconds:
        return True, last
    return False, last


def create_time_entry(db: Session, employee: Employee, entry_type: str, method: str, terminal: str = "web", note: str = "", duplicate_seconds: int = 8):
    """Erstellt eine Buchung nur über den zentralen Zustandsautomaten.

    Dadurch gelten für Raspberry, Schnellbuchung, Dashboard und API dieselben
    Regeln. Doppelte Kommen-Buchungen werden serverseitig blockiert.
    """
    entry_type = normalize_entry_type(entry_type)

    if is_fixed_admin_employee(employee):
        return None, None

    duplicate, last = is_duplicate_booking(db, employee.id, max(duplicate_seconds, 8))
    if duplicate:
        return None, last

    if not is_valid_transition_for_employee(db, employee.id, entry_type):
        state = get_booking_state(db, employee.id)
        return None, state.last_entry or state.last_valid_entry

    entry = TimeEntry(
        employee_id=employee.id,
        timestamp=datetime.now(),
        entry_type=entry_type,
        method=method,
        terminal=terminal,
        note=note
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    log_action(db, employee.employee_number, "time_entry_created", "time_entries", str(entry.id), entry_type)
    return entry, None


def create_admin_time_entry(db: Session, employee: Employee, entry_type: str, admin_user: Employee):
    if is_fixed_admin_employee(employee):
        return None

    """Erstellt eine manuelle Kommen-/Gehen-Buchung aus der Mitarbeiterverwaltung.

    Diese Funktion prüft bewusst nicht auf Doppelbuchung, weil ein Administrator
    den aktuellen Anwesenheitsstatus gezielt korrigieren können soll.
    """
    entry = TimeEntry(
        employee_id=employee.id,
        timestamp=datetime.now(),
        entry_type=entry_type,
        method="admin_manual",
        terminal="admin",
        note=f"Manuelle {entry_type}-Buchung durch {getattr(admin_user, 'employee_number', 'admin') or 'admin'}"
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    log_action(
        db,
        getattr(admin_user, "employee_number", "admin") or "admin",
        "admin_time_entry_created",
        "time_entries",
        str(entry.id),
        f"{entry_type} für {employee.employee_number}"
    )
    return entry

def latest_employee_statuses(db: Session, employee_ids):
    """Liefert den letzten Buchungsstatus pro Mitarbeiter für die Admin-Liste."""
    result = {}
    for employee_id in employee_ids:
        last = (
            db.query(TimeEntry)
            .filter(TimeEntry.employee_id == employee_id)
            .order_by(TimeEntry.timestamp.desc())
            .first()
        )
        if not last:
            result[employee_id] = {"label": "Keine Buchung", "entry_type": "", "timestamp": None, "present": False}
            continue
        present = last.entry_type in ["kommen", "pause_ende"]
        labels = {
            "kommen": "Anwesend",
            "gehen": "Abwesend",
            "pause_start": "Pause",
            "pause_ende": "Anwesend",
        }
        result[employee_id] = {
            "label": labels.get(last.entry_type, last.entry_type),
            "entry_type": last.entry_type,
            "timestamp": last.timestamp,
            "present": present,
        }
    return result

def _format_last_backup():
    backup_dir = BACKUP_DIR
    if not backup_dir.exists():
        return "Kein Backup gefunden"
    files = [p for p in backup_dir.rglob("*") if p.is_file() and p.suffix.lower() in [".zip", ".gz", ".tar", ".tgz", ".sql"]]
    if not files:
        return "Kein Backup gefunden"
    latest = max(files, key=lambda p: p.stat().st_mtime)
    return datetime.fromtimestamp(latest.stat().st_mtime).strftime("%d.%m.%Y %H:%M")


def _dashboard_stats(db: Session):
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = today_start + timedelta(days=1)

    active_employees = _exclude_fixed_admin(db.query(Employee).filter(Employee.active == True), Employee).count()

    latest_entries_subq = (
        _exclude_fixed_admin(
            db.query(TimeEntry.employee_id, func.max(TimeEntry.timestamp).label("last_ts")).join(Employee, TimeEntry.employee_id == Employee.id),
            Employee,
        )
        .filter(not_deleted_filter())
        .group_by(TimeEntry.employee_id)
        .subquery()
    )
    latest_entries = (
        db.query(TimeEntry)
        .join(latest_entries_subq, (TimeEntry.employee_id == latest_entries_subq.c.employee_id) & (TimeEntry.timestamp == latest_entries_subq.c.last_ts))
        .all()
    )
    present_entries = [e for e in latest_entries if e.entry_type in ["kommen", "pause_ende"]]
    present_employee_ids = {e.employee_id for e in present_entries}

    present_employees = (
        _exclude_fixed_admin(db.query(Employee).filter(Employee.id.in_(present_employee_ids)), Employee)
        .order_by(Employee.last_name.asc(), Employee.first_name.asc())
        .all()
        if present_employee_ids else []
    )
    absent_today_count = max(active_employees - len(present_entries), 0)

    today_entries = _exclude_fixed_admin(
        db.query(TimeEntry).join(Employee, TimeEntry.employee_id == Employee.id), Employee
    ).filter(TimeEntry.timestamp >= today_start, TimeEntry.timestamp < today_end, not_deleted_filter()).count()
    open_vacations = db.query(VacationRequest).filter(VacationRequest.status.in_(["beantragt", "offen", "Offen", "loeschung_beantragt"])).count()
    open_corrections = db.query(Correction).filter(Correction.status.in_(["offen", "beantragt", "Offen"])).count()
    open_plausibility = db.query(PlausibilityIssue).filter(PlausibilityIssue.status.in_(["offen", "geprueft"])).count()
    overtime_sum = db.query(func.coalesce(func.sum(Employee.overtime_balance), 0)).filter(Employee.active == True).scalar() or 0

    recent_entries = (
        _exclude_fixed_admin(db.query(TimeEntry).join(Employee, TimeEntry.employee_id == Employee.id), Employee)
        .filter(not_deleted_filter())
        .order_by(TimeEntry.timestamp.desc())
        .limit(8)
        .all()
    )
    recent_audit = (
        db.query(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .limit(8)
        .all()
    )

    return {
        "active_employees": active_employees,
        "present_count": len(present_entries),
        "present_employees": present_employees,
        "absent_today_count": absent_today_count,
        "today_entries": today_entries,
        "open_vacations": open_vacations,
        "open_corrections": open_corrections,
        "open_plausibility": open_plausibility,
        "overtime_sum": round(float(overtime_sum), 2),
        "last_backup": _format_last_backup(),
        "system_status": "OK",
        "system_details": {
            "database": "OK",
            "backup": _format_last_backup(),
            "open_plausibility": open_plausibility,
        },
        "recent_entries": recent_entries,
        "recent_audit": recent_audit,
    }



def ensure_employee_number_length_setting(db: Session):
    """Kompatibilitäts-Wrapper: Einstellung für Mitarbeiternummer-Länge anlegen."""
    return service_ensure_employee_number_length_setting(db)

def get_employee_number_length(db: Session) -> int:
    return service_get_employee_number_length(db)

def normalize_employee_number(value: str, length: int) -> str:
    return service_normalize_employee_number(value, length)

def validate_employee_number(value: str, length: int):
    return service_validate_employee_number(value, length)


# Export auch interne Hilfsfunktionen für die modularisierten Routen.
# Ohne __all__ importiert "from .common import *" keine Namen mit führendem Unterstrich.
# Das hat in 4.7.08 u.a. _get_pending_rfid_status() im Dashboard gebrochen.
__all__ = [name for name in globals().keys() if not name.startswith('__')]
