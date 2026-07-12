from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Employee
from app.routes.common import log_action, require_system_admin_response
from app.security import hash_password, verify_password
from app.services.security_policy import DEFAULT_ADMIN_PASSWORD, ensure_security_policy_defaults, validate_password
from app.services.settings_service import set_setting

router = APIRouter()


def _flag(value: str) -> str:
    return "true" if str(value).lower() in {"1", "true", "on", "yes", "ja"} else "false"


@router.post("/system/settings/general/security-policy")
def save_security_policy(
    request: Request,
    security_login_protection_enabled: str = Form("0"),
    security_login_max_attempts: int = Form(5),
    security_login_lock_minutes: int = Form(15),
    security_login_ip_enabled: str = Form("0"),
    security_login_ip_lock_minutes: int = Form(15),
    security_password_min_length: int = Form(12),
    security_password_require_upper: str = Form("0"),
    security_password_require_lower: str = Form("0"),
    security_password_require_digit: str = Form("0"),
    security_password_require_special: str = Form("0"),
    security_password_allow_spaces: str = Form("0"),
    security_password_forbid_identity: str = Form("0"),
    db: Session = Depends(get_db),
):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect

    ensure_security_policy_defaults(db)
    values = {
        "security_login_protection_enabled": _flag(security_login_protection_enabled),
        "security_login_max_attempts": str(max(1, min(int(security_login_max_attempts or 5), 20))),
        "security_login_lock_minutes": str(max(1, min(int(security_login_lock_minutes or 15), 1440))),
        "security_login_ip_enabled": _flag(security_login_ip_enabled),
        "security_login_ip_lock_minutes": str(max(1, min(int(security_login_ip_lock_minutes or 15), 1440))),
        "security_password_min_length": str(max(8, min(int(security_password_min_length or 12), 64))),
        "security_password_require_upper": _flag(security_password_require_upper),
        "security_password_require_lower": _flag(security_password_require_lower),
        "security_password_require_digit": _flag(security_password_require_digit),
        "security_password_require_special": _flag(security_password_require_special),
        "security_password_allow_spaces": _flag(security_password_allow_spaces),
        "security_password_forbid_identity": _flag(security_password_forbid_identity),
    }
    for key, value in values.items():
        set_setting(db, key, value)
    db.commit()
    log_action(db, user.employee_number, "security_policy_saved", "settings", "security-policy", "Login- und Passwortrichtlinien geändert")
    return RedirectResponse("/system/settings/general?saved=1&message=" + quote("Sicherheitsrichtlinien gespeichert."), status_code=303)


@router.post("/system/settings/general/admin-password")
def change_fixed_admin_password(
    request: Request,
    current_password: str = Form(""),
    new_password: str = Form(""),
    new_password_repeat: str = Form(""),
    db: Session = Depends(get_db),
):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    fixed_admin = db.query(Employee).filter(Employee.employee_number == "admin").first()
    if not fixed_admin:
        return RedirectResponse("/system/settings/general?error=" + quote("Der feste Benutzer admin wurde nicht gefunden."), status_code=303)
    if not verify_password(current_password or "", fixed_admin.password_hash):
        return RedirectResponse("/system/settings/general?error=" + quote("Das aktuelle Admin-Passwort ist falsch."), status_code=303)
    if new_password != new_password_repeat:
        return RedirectResponse("/system/settings/general?error=" + quote("Die neuen Passwörter stimmen nicht überein."), status_code=303)
    if new_password == DEFAULT_ADMIN_PASSWORD:
        return RedirectResponse("/system/settings/general?error=" + quote("Das Standardpasswort admin123 darf nicht erneut verwendet werden."), status_code=303)

    valid, message = validate_password(new_password, db, ["admin", fixed_admin.first_name, fixed_admin.last_name])
    if not valid:
        return RedirectResponse("/system/settings/general?error=" + quote(message), status_code=303)

    fixed_admin.password_hash = hash_password(new_password)
    db.commit()
    request.session["default_admin_password_active"] = False
    log_action(db, user.employee_number, "default_admin_password_changed", "security", "admin", "Standardpasswort des festen Administrators wurde ersetzt")
    return RedirectResponse("/system/settings/general?saved=1&message=" + quote("Das Passwort des festen Administrators wurde sicher geändert."), status_code=303)
