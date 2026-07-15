from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth import current_user
from app.database import get_db
from .common import (
    create_time_entry,
    is_fixed_admin_employee,
    log_action,
    require_system_admin_response,
    role_name,
    service_get_setting,
    service_set_setting,
    templates,
)

router = APIRouter()
SETTING_KEY = "dashboard_logged_in_self_booking_enabled"


def self_booking_enabled(db: Session) -> bool:
    value = str(service_get_setting(db, SETTING_KEY, "0") or "0").lower()
    return value in {"1", "true", "on", "yes", "ja"}


@router.get("/api/dashboard/self-booking")
def dashboard_self_booking_status(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return JSONResponse({"enabled": False, "configured": self_booking_enabled(db), "authenticated": False}, status_code=401)
    configured = self_booking_enabled(db)
    allowed = configured and not is_fixed_admin_employee(user)
    return {
        "enabled": allowed,
        "configured": configured,
        "authenticated": True,
        "role": role_name(user),
        "employee_name": f"{user.first_name} {user.last_name}".strip(),
    }


@router.post("/dashboard/self-book")
def dashboard_self_book(request: Request, entry_type: str = Form(...), db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if not self_booking_enabled(db):
        return RedirectResponse("/dashboard?error=" + quote("Die direkte Eigenbuchung ist deaktiviert."), status_code=303)
    if is_fixed_admin_employee(user):
        return RedirectResponse("/dashboard?error=" + quote("Der Systemadministrator darf keine Arbeitszeit buchen."), status_code=303)
    if entry_type not in {"kommen", "gehen"}:
        return RedirectResponse("/dashboard?error=" + quote("Nur Kommen oder Gehen ist hier zulässig."), status_code=303)

    entry, conflicting = create_time_entry(
        db, user, entry_type, "dashboard_session", "dashboard",
        "Selbstbuchung durch angemeldeten Benutzer", duplicate_seconds=8,
    )
    if not entry:
        detail = "Die Buchung wurde wegen einer doppelten oder unzulässigen Buchungsfolge nicht gespeichert."
        if conflicting and getattr(conflicting, "entry_type", None):
            detail += f" Letzte Buchung: {conflicting.entry_type}."
        return RedirectResponse("/dashboard?error=" + quote(detail), status_code=303)

    log_action(db, user.employee_number, "dashboard_self_booking", "time_entries", str(entry.id), entry_type)
    label = "Kommen" if entry_type == "kommen" else "Gehen"
    return RedirectResponse("/dashboard?message=" + quote(f"{label} wurde für dich gebucht."), status_code=303)


@router.get("/system/settings/general/self-booking", response_class=HTMLResponse)
def dashboard_self_booking_setting_page(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    return templates.TemplateResponse("system_dashboard_self_booking.html", {
        "request": request,
        "user": user,
        "enabled": self_booking_enabled(db),
        "saved": request.query_params.get("saved") == "1",
    })


@router.post("/system/settings/general/self-booking")
def dashboard_self_booking_setting(request: Request, enabled: str = Form("0"), db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    value = "1" if str(enabled).lower() in {"1", "true", "on", "yes", "ja"} else "0"
    service_set_setting(db, SETTING_KEY, value)
    db.commit()
    log_action(db, user.employee_number, "dashboard_self_booking_setting_changed", "settings", SETTING_KEY, value)
    return RedirectResponse("/system/settings/general/self-booking?saved=1", status_code=303)
