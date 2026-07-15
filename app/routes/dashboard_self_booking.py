from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth import current_user
from app.database import get_db
from .common import create_time_entry, is_fixed_admin_employee, log_action, service_get_setting, service_set_setting

router = APIRouter()
SETTING_PREFIX = "employee_dashboard_self_booking_"


def employee_setting_key(employee_id: int) -> str:
    return f"{SETTING_PREFIX}{int(employee_id)}"


def employee_self_booking_enabled(db: Session, employee_id: int) -> bool:
    value = str(service_get_setting(db, employee_setting_key(employee_id), "0") or "0").lower()
    return value in {"1", "true", "on", "yes", "ja"}


@router.get("/api/dashboard/self-booking")
def dashboard_self_booking_status(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return JSONResponse({"enabled": False, "authenticated": False}, status_code=401)
    allowed = employee_self_booking_enabled(db, user.id) and not is_fixed_admin_employee(user)
    return {"enabled": allowed, "authenticated": True, "employee_name": f"{user.first_name} {user.last_name}".strip()}


@router.get("/api/admin/employees/{employee_id}/self-booking")
def employee_self_booking_status_admin(employee_id: int, request: Request, db: Session = Depends(get_db)):
    from .common import Employee, require_admin_response

    admin_user, redirect = require_admin_response(request, db)
    if redirect:
        return JSONResponse({"enabled": False}, status_code=403)
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        return JSONResponse({"enabled": False}, status_code=404)
    return {"enabled": employee_self_booking_enabled(db, employee.id)}


@router.post("/dashboard/self-book")
def dashboard_self_book(request: Request, entry_type: str = Form(...), db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if not employee_self_booking_enabled(db, user.id):
        return RedirectResponse("/dashboard?error=" + quote("Die eigene Buchung ohne erneute Passworteingabe ist für deinen Benutzer nicht freigegeben."), status_code=303)
    if is_fixed_admin_employee(user):
        return RedirectResponse("/dashboard?error=" + quote("Der Systemadministrator darf keine Arbeitszeit buchen."), status_code=303)
    if entry_type not in {"kommen", "gehen"}:
        return RedirectResponse("/dashboard?error=" + quote("Nur Kommen oder Gehen ist hier zulässig."), status_code=303)

    entry, conflicting = create_time_entry(
        db, user, entry_type, "dashboard_session", "dashboard",
        "Selbstbuchung durch angemeldeten Benutzer ohne erneute Passworteingabe", duplicate_seconds=8,
    )
    if not entry:
        detail = "Die Buchung wurde wegen einer doppelten oder unzulässigen Buchungsfolge nicht gespeichert."
        if conflicting and getattr(conflicting, "entry_type", None):
            detail += f" Letzte Buchung: {conflicting.entry_type}."
        return RedirectResponse("/dashboard?error=" + quote(detail), status_code=303)

    log_action(db, user.employee_number, "dashboard_self_booking", "time_entries", str(entry.id), entry_type)
    label = "Kommen" if entry_type == "kommen" else "Gehen"
    return RedirectResponse("/dashboard?message=" + quote(f"{label} wurde für dich gebucht."), status_code=303)


@router.post("/admin/employees/{employee_id}/self-booking")
def employee_self_booking_setting(employee_id: int, request: Request, enabled: str = Form("0"), db: Session = Depends(get_db)):
    from .common import Employee, require_admin_response

    admin_user, redirect = require_admin_response(request, db)
    if redirect:
        return redirect
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        return RedirectResponse("/admin", status_code=303)
    value = "1" if str(enabled).lower() in {"1", "true", "on", "yes", "ja"} else "0"
    service_set_setting(db, employee_setting_key(employee.id), value)
    db.commit()
    log_action(db, admin_user.employee_number, "employee_dashboard_self_booking_changed", "employees", str(employee.id), f"enabled={value}")
    return RedirectResponse(f"/admin/employees/{employee.id}/edit?saved=1", status_code=303)
