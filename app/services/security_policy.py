"""Zentrale Login- und Passwortrichtlinien für Stempeluhr Professional."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.models import Setting
from app.security import verify_password
from app.services.settings_service import get_setting, set_setting

DEFAULT_ADMIN_PASSWORD = "admin123"
DEFAULTS = {
    "security_login_protection_enabled": "true",
    "security_login_max_attempts": "5",
    "security_login_lock_minutes": "15",
    "security_login_ip_enabled": "true",
    "security_login_ip_lock_minutes": "15",
    "security_password_min_length": "12",
    "security_password_require_upper": "true",
    "security_password_require_lower": "true",
    "security_password_require_digit": "true",
    "security_password_require_special": "true",
    "security_password_allow_spaces": "false",
    "security_password_forbid_identity": "true",
}


def _flag(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "on", "yes", "ja"}


def _integer(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(parsed, maximum))


def ensure_security_policy_defaults(db: Session) -> None:
    changed = False
    for key, value in DEFAULTS.items():
        if get_setting(db, key, None) is None:
            set_setting(db, key, value)
            changed = True
    if changed:
        db.commit()


def get_security_policy(db: Session) -> dict[str, Any]:
    ensure_security_policy_defaults(db)
    return {
        "login_protection_enabled": _flag(get_setting(db, "security_login_protection_enabled", "true"), True),
        "login_max_attempts": _integer(get_setting(db, "security_login_max_attempts", "5"), 5, 1, 20),
        "login_lock_minutes": _integer(get_setting(db, "security_login_lock_minutes", "15"), 15, 1, 1440),
        "login_ip_enabled": _flag(get_setting(db, "security_login_ip_enabled", "true"), True),
        "login_ip_lock_minutes": _integer(get_setting(db, "security_login_ip_lock_minutes", "15"), 15, 1, 1440),
        "password_min_length": _integer(get_setting(db, "security_password_min_length", "12"), 12, 8, 64),
        "password_require_upper": _flag(get_setting(db, "security_password_require_upper", "true"), True),
        "password_require_lower": _flag(get_setting(db, "security_password_require_lower", "true"), True),
        "password_require_digit": _flag(get_setting(db, "security_password_require_digit", "true"), True),
        "password_require_special": _flag(get_setting(db, "security_password_require_special", "true"), True),
        "password_allow_spaces": _flag(get_setting(db, "security_password_allow_spaces", "false"), False),
        "password_forbid_identity": _flag(get_setting(db, "security_password_forbid_identity", "true"), True),
    }


def validate_password(password: str, db: Session, identity_values: list[str] | None = None) -> tuple[bool, str]:
    policy = get_security_policy(db)
    password = password or ""
    if len(password) < policy["password_min_length"]:
        return False, f"Das Passwort muss mindestens {policy['password_min_length']} Zeichen lang sein."
    if policy["password_require_upper"] and not any(char.isupper() for char in password):
        return False, "Das Passwort muss mindestens einen Großbuchstaben enthalten."
    if policy["password_require_lower"] and not any(char.islower() for char in password):
        return False, "Das Passwort muss mindestens einen Kleinbuchstaben enthalten."
    if policy["password_require_digit"] and not any(char.isdigit() for char in password):
        return False, "Das Passwort muss mindestens eine Zahl enthalten."
    if policy["password_require_special"] and not any(not char.isalnum() and not char.isspace() for char in password):
        return False, "Das Passwort muss mindestens ein Sonderzeichen enthalten."
    if not policy["password_allow_spaces"] and any(char.isspace() for char in password):
        return False, "Leerzeichen sind im Passwort nicht erlaubt."
    if policy["password_forbid_identity"]:
        lowered = password.casefold()
        for value in identity_values or []:
            candidate = str(value or "").strip().casefold()
            if len(candidate) >= 3 and candidate in lowered:
                return False, "Das Passwort darf Benutzername, Mitarbeiternummer oder Namen nicht enthalten."
    return True, "OK"


def default_admin_password_active(employee: Any) -> bool:
    return bool(
        employee
        and str(getattr(employee, "employee_number", "")).lower() == "admin"
        and verify_password(DEFAULT_ADMIN_PASSWORD, getattr(employee, "password_hash", None))
    )


def _state_key(kind: str, value: str) -> str:
    digest = hashlib.sha256(str(value or "").strip().casefold().encode("utf-8")).hexdigest()[:32]
    return f"security_login_state_{kind}_{digest}"


def _read_state(db: Session, kind: str, value: str) -> dict[str, Any]:
    raw = get_setting(db, _state_key(kind, value), "") or ""
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_state(db: Session, kind: str, value: str, state: dict[str, Any]) -> None:
    set_setting(db, _state_key(kind, value), json.dumps(state, separators=(",", ":")))
    db.commit()


def _locked_until(state: dict[str, Any]) -> datetime | None:
    raw = str(state.get("locked_until") or "")
    try:
        return datetime.fromisoformat(raw) if raw else None
    except ValueError:
        return None


def login_block_status(db: Session, identifier: str, ip_address: str) -> tuple[bool, int]:
    policy = get_security_policy(db)
    if not policy["login_protection_enabled"]:
        return False, 0
    now = datetime.now()
    remaining = 0
    for kind, value, enabled in (("user", identifier, True), ("ip", ip_address, policy["login_ip_enabled"])):
        if not enabled or not value:
            continue
        until = _locked_until(_read_state(db, kind, value))
        if until and until > now:
            remaining = max(remaining, int((until - now).total_seconds() // 60) + 1)
    return remaining > 0, remaining


def record_login_failure(db: Session, identifier: str, ip_address: str) -> dict[str, Any]:
    policy = get_security_policy(db)
    result = {"locked": False, "remaining_minutes": 0}
    if not policy["login_protection_enabled"]:
        return result
    now = datetime.now()
    for kind, value, enabled, lock_minutes in (
        ("user", identifier, True, policy["login_lock_minutes"]),
        ("ip", ip_address, policy["login_ip_enabled"], policy["login_ip_lock_minutes"]),
    ):
        if not enabled or not value:
            continue
        state = _read_state(db, kind, value)
        attempts = int(state.get("attempts") or 0) + 1
        state = {"attempts": attempts, "last_failure": now.isoformat(timespec="seconds")}
        if attempts >= policy["login_max_attempts"]:
            until = now + timedelta(minutes=lock_minutes)
            state["locked_until"] = until.isoformat(timespec="seconds")
            result = {"locked": True, "remaining_minutes": max(result["remaining_minutes"], lock_minutes)}
        _write_state(db, kind, value, state)
    return result


def clear_login_failures(db: Session, identifier: str, ip_address: str) -> None:
    keys = [_state_key("user", identifier)]
    if ip_address:
        keys.append(_state_key("ip", ip_address))
    db.query(Setting).filter(Setting.key.in_(keys)).delete(synchronize_session=False)
    db.commit()
