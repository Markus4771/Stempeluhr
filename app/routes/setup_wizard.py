from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from .common import require_system_admin_response, templates
from app.database import get_db
from app.models import Employee, RaspberryClient
from app.services.diagnostics import collect_diagnostics
from app.services.settings_service import get_setting, set_setting

router = APIRouter()

STEPS = [
    (1, "Willkommen"),
    (2, "Unternehmen"),
    (3, "Administrator"),
    (4, "PostgreSQL"),
    (5, "Arbeitszeit"),
    (6, "Kommunikation"),
    (7, "Raspberry"),
    (8, "Abschluss"),
]

SETUP_KEYS = [
    "setup_completed", "setup_current_step", "setup_last_saved_at",
    "company_name", "company_street", "company_postal_code", "company_city",
    "company_phone", "company_email", "language", "timezone",
    "weekly_hours", "daily_hours", "auto_break_enabled", "federal_state",
    "email_enabled", "api_enabled", "https_enabled", "backup_enabled",
]


def _settings(db: Session) -> dict[str, str]:
    return {key: get_setting(db, key, "") for key in SETUP_KEYS}


def _bool(value: object) -> str:
    return "true" if str(value or "").lower() in {"1", "true", "on", "yes", "ja"} else "false"


def _step(value: object) -> int:
    try:
        return max(1, min(int(value), len(STEPS)))
    except (TypeError, ValueError):
        return 1


def _status(db: Session) -> dict:
    administrator_count = db.query(Employee).filter(Employee.is_admin.is_(True), Employee.active.is_(True)).count()
    raspberry_total = db.query(RaspberryClient).count()
    raspberry_online = 0
    try:
        from app.routes.monitoring import raspberry_online as is_online
        raspberry_online = sum(1 for client in db.query(RaspberryClient).all() if is_online(client))
    except Exception:
        raspberry_online = 0

    database = {"ok": False, "version": "unbekannt", "message": "Verbindung nicht geprüft"}
    try:
        database["version"] = str(db.execute(text("SHOW server_version")).scalar() or "unbekannt")
        db.execute(text("SELECT 1"))
        database.update({"ok": True, "message": "PostgreSQL ist erreichbar"})
    except Exception:
        db.rollback()
        database["message"] = "PostgreSQL-Verbindung fehlgeschlagen"

    return {
        "administrator_count": administrator_count,
        "database": database,
        "raspberry_total": raspberry_total,
        "raspberry_online": raspberry_online,
    }


@router.get("/setup", response_class=HTMLResponse)
def setup_page(request: Request, step: int | None = None, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect

    settings = _settings(db)
    current_step = _step(step if step is not None else settings.get("setup_current_step") or 1)
    diagnostics = collect_diagnostics(db) if current_step == 8 else None
    return templates.TemplateResponse("setup_wizard.html", {
        "request": request,
        "user": user,
        "settings": settings,
        "steps": STEPS,
        "current_step": current_step,
        "progress_percent": round((current_step / len(STEPS)) * 100),
        "setup_status": _status(db),
        "diagnostics": diagnostics,
    })


@router.post("/setup")
async def setup_save(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect

    form = await request.form()
    current_step = _step(form.get("current_step", 1))
    direction = str(form.get("direction", "next"))

    if direction == "reset":
        set_setting(db, "setup_completed", "false")
        set_setting(db, "setup_current_step", "1")
        set_setting(db, "setup_last_saved_at", datetime.now().isoformat(timespec="seconds"))
        db.commit()
        return RedirectResponse("/setup?step=1", status_code=303)

    if current_step == 2:
        for key in (
            "company_name", "company_street", "company_postal_code", "company_city",
            "company_phone", "company_email", "language", "timezone",
        ):
            if key in form:
                set_setting(db, key, str(form.get(key, "")).strip())

    elif current_step == 5:
        for key in ("weekly_hours", "daily_hours", "federal_state"):
            if key in form:
                set_setting(db, key, str(form.get(key, "")).strip())
        set_setting(db, "auto_break_enabled", _bool(form.get("auto_break_enabled")))

    elif current_step == 6:
        set_setting(db, "email_enabled", _bool(form.get("email_enabled")))
        set_setting(db, "api_enabled", _bool(form.get("api_enabled")))
        set_setting(db, "https_enabled", _bool(form.get("https_enabled")))
        set_setting(db, "backup_enabled", _bool(form.get("backup_enabled")))

    if direction == "finish" and current_step == len(STEPS):
        set_setting(db, "setup_completed", "true")
        next_step = len(STEPS)
    elif direction == "back":
        next_step = max(1, current_step - 1)
    else:
        next_step = min(len(STEPS), current_step + 1)

    set_setting(db, "setup_current_step", str(next_step))
    set_setting(db, "setup_last_saved_at", datetime.now().isoformat(timespec="seconds"))
    db.commit()
    return RedirectResponse(f"/setup?step={next_step}", status_code=303)
