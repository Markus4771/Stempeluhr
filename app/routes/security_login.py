from __future__ import annotations

import hashlib
from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth import login_user
from app.database import get_db
from app.models import Employee, PasswordResetToken
from app.routes.common import (
    get_employee_number_length,
    is_fixed_admin_employee,
    log_action,
    normalize_employee_number,
    templates,
    validate_employee_number,
)
from app.security import hash_password, verify_password
from app.services.security_policy import (
    clear_login_failures,
    default_admin_password_active,
    login_block_status,
    record_login_failure,
    validate_password,
)

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
def secure_login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login")
def secure_login_submit(
    request: Request,
    employee_number: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    raw_identifier = (employee_number or "").strip()
    ip_address = request.client.host if request.client else ""
    blocked, remaining = login_block_status(db, raw_identifier, ip_address)
    if blocked:
        try:
            log_action(db, raw_identifier or "unbekannt", "login_blocked", "security", "login", f"Anmeldung gesperrt; Restdauer ca. {remaining} Minuten; IP={ip_address}")
        except Exception:
            pass
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": f"Anmeldung vorübergehend gesperrt. Bitte in etwa {remaining} Minute(n) erneut versuchen.",
        }, status_code=429)

    if raw_identifier.lower() == "admin":
        normalized_identifier = "admin"
    else:
        normalized_identifier = normalize_employee_number(raw_identifier, get_employee_number_length(db))
        valid, _ = validate_employee_number(normalized_identifier, get_employee_number_length(db))
        if not valid:
            record_login_failure(db, raw_identifier, ip_address)
            return templates.TemplateResponse("login.html", {"request": request, "error": "Mitarbeiternummer oder Passwort falsch."})

    employee = db.query(Employee).filter(Employee.employee_number == normalized_identifier, Employee.active == True).first()
    if not employee or not verify_password(password or "", employee.password_hash):
        state = record_login_failure(db, raw_identifier, ip_address)
        try:
            log_action(db, raw_identifier or "unbekannt", "login_failed", "security", "login", f"Fehlgeschlagene Anmeldung; IP={ip_address}; gesperrt={state.get('locked', False)}")
        except Exception:
            pass
        error = "Mitarbeiternummer oder Passwort falsch."
        if state.get("locked"):
            error = f"Zu viele Fehlversuche. Anmeldung für etwa {state.get('remaining_minutes', 0)} Minute(n) gesperrt."
        return templates.TemplateResponse("login.html", {"request": request, "error": error})

    clear_login_failures(db, raw_identifier, ip_address)
    login_user(request, employee)
    request.session["default_admin_password_active"] = default_admin_password_active(employee)
    request.session["login_at"] = datetime.now().isoformat(timespec="seconds")
    log_action(db, employee.employee_number, "login", "employees", str(employee.id), f"Login; IP={ip_address}")
    try:
        from app.routes.onboarding import _privacy_required
        if _privacy_required(employee, db):
            return RedirectResponse("/onboarding/privacy", status_code=303)
    except Exception:
        pass
    return RedirectResponse("/dashboard", status_code=303)


@router.get("/password-reset/{token}", response_class=HTMLResponse)
def secure_password_reset_form(request: Request, token: str, db: Session = Depends(get_db)):
    token_hash = hashlib.sha256((token or "").encode("utf-8")).hexdigest()
    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == token_hash,
        PasswordResetToken.used_at.is_(None),
        PasswordResetToken.expires_at >= datetime.now(),
    ).first()
    if not reset_token:
        return templates.TemplateResponse("password_reset.html", {"request": request, "token": "", "error": "Dieser Link ist ungültig oder abgelaufen.", "message": None})
    return templates.TemplateResponse("password_reset.html", {"request": request, "token": token, "error": None, "message": None})


@router.post("/password-reset/{token}", response_class=HTMLResponse)
def secure_password_reset_submit(
    request: Request,
    token: str,
    password: str = Form(...),
    password_repeat: str = Form(...),
    db: Session = Depends(get_db),
):
    token_hash = hashlib.sha256((token or "").encode("utf-8")).hexdigest()
    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == token_hash,
        PasswordResetToken.used_at.is_(None),
        PasswordResetToken.expires_at >= datetime.now(),
    ).first()
    if not reset_token:
        return templates.TemplateResponse("password_reset.html", {"request": request, "token": "", "error": "Dieser Link ist ungültig oder abgelaufen.", "message": None})

    employee = db.query(Employee).filter(Employee.id == reset_token.employee_id, Employee.active == True).first()
    if not employee or is_fixed_admin_employee(employee):
        reset_token.used_at = datetime.now()
        db.commit()
        return templates.TemplateResponse("password_reset.html", {"request": request, "token": "", "error": "Dieser Link ist ungültig oder abgelaufen.", "message": None})
    if password != password_repeat:
        return templates.TemplateResponse("password_reset.html", {"request": request, "token": token, "error": "Die Passwörter stimmen nicht überein.", "message": None})

    valid, message = validate_password(password, db, [employee.employee_number, employee.first_name, employee.last_name, employee.email])
    if not valid:
        return templates.TemplateResponse("password_reset.html", {"request": request, "token": token, "error": message, "message": None})

    employee.password_hash = hash_password(password)
    employee.updated_at = datetime.now()
    reset_token.used_at = datetime.now()
    db.commit()
    log_action(db, employee.employee_number, "password_reset_completed", "employees", str(employee.id), "Passwort nach konfigurierter Richtlinie geändert")
    return templates.TemplateResponse("password_reset.html", {"request": request, "token": "", "error": None, "message": "Dein Passwort wurde geändert. Du kannst dich jetzt anmelden."})
