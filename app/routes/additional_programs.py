from __future__ import annotations

import ipaddress
import json
import re
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth import current_user
from app.database import get_db
from app.models import Role, Setting
from app.routes.common import log_action, require_system_admin_response, templates
from app.services.role_permissions import has_permission

router = APIRouter()
SETTING_KEY = "additional_programs"
_HOST_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]{0,252}[A-Za-z0-9]$|^[A-Za-z0-9]$")
STANDARD_ROLES_WITH_PROGRAM_ACCESS = {"Administrator", "Personal", "Teamleiter", "Mitarbeiter"}


def _load_programs(db: Session) -> list[dict]:
    row = db.query(Setting).filter(Setting.key == SETTING_KEY).first()
    try:
        data = json.loads(row.value or "[]") if row else []
    except Exception:
        data = []
    programs = data if isinstance(data, list) else []
    # Bestehende Einträge ohne Rollenangabe bleiben für die bisherigen Standardrollen sichtbar.
    for program in programs:
        if not isinstance(program.get("allowed_roles"), list):
            program["allowed_roles"] = sorted(STANDARD_ROLES_WITH_PROGRAM_ACCESS)
    return programs


def _save_programs(db: Session, programs: list[dict]) -> None:
    row = db.query(Setting).filter(Setting.key == SETTING_KEY).first()
    payload = json.dumps(programs, ensure_ascii=False, separators=(",", ":"))
    if row:
        row.value = payload
    else:
        db.add(Setting(key=SETTING_KEY, value=payload))
    db.commit()


def _valid_host(host: str) -> bool:
    host = (host or "").strip()
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return bool(_HOST_RE.fullmatch(host)) and ".." not in host


def _build_url(protocol: str, host: str, port: int, path: str) -> str:
    protocol = "https" if protocol == "https" else "http"
    path = "/" + (path or "").strip().lstrip("/") if (path or "").strip() else ""
    return f"{protocol}://{host}:{port}{path}"


def _clean_roles(allowed_roles: list[str] | None, valid_roles: set[str]) -> list[str]:
    selected = {str(role or "").strip() for role in (allowed_roles or [])}
    return sorted(role for role in selected if role in valid_roles)


def _normalize_program(name: str, description: str, protocol: str, host: str, port: int, path: str, enabled: str, allowed_roles: list[str], valid_roles: set[str]) -> dict:
    host = (host or "").strip()
    port = int(port)
    return {
        "name": (name or "").strip()[:100],
        "description": (description or "").strip()[:300],
        "protocol": "https" if protocol == "https" else "http",
        "host": host,
        "port": port,
        "path": (path or "").strip()[:300],
        "enabled": str(enabled).lower() in {"1", "true", "on", "yes", "ja"},
        "allowed_roles": _clean_roles(allowed_roles, valid_roles),
        "url": _build_url(protocol, host, port, path),
    }


def _validate_program(name: str, host: str, port: int) -> str | None:
    try:
        port = int(port)
    except (TypeError, ValueError):
        return "Der Port ist ungültig."
    if not (name or "").strip():
        return "Der Name darf nicht leer sein."
    if not _valid_host(host):
        return "Die IP-Adresse oder der Hostname ist ungültig."
    if not 1 <= port <= 65535:
        return "Der Port muss zwischen 1 und 65535 liegen."
    return None


def _user_role_name(user) -> str:
    return str(getattr(getattr(user, "role", None), "name", "") or "").strip()


def _can_open_additional_programs(user) -> bool:
    if not user:
        return False
    employee_number = str(getattr(user, "employee_number", "") or "").strip().lower()
    return employee_number == "admin" or has_permission(user, "nav.additional_programs") or bool(_user_role_name(user))


def _program_visible_for_user(program: dict, user) -> bool:
    if not user or not program.get("enabled", True):
        return False
    if str(getattr(user, "employee_number", "") or "").strip().lower() == "admin":
        return True
    allowed_roles = program.get("allowed_roles")
    if not isinstance(allowed_roles, list):
        allowed_roles = sorted(STANDARD_ROLES_WITH_PROGRAM_ACCESS)
    return _user_role_name(user) in allowed_roles


def _visible_programs(db: Session, user) -> list[dict]:
    if not _can_open_additional_programs(user):
        return []
    return [program for program in _load_programs(db) if _program_visible_for_user(program, user)]


@router.get("/api/additional-programs/menu-visible")
def additional_programs_menu_visible(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    return JSONResponse({"visible": bool(_visible_programs(db, user))})


@router.get("/additional-programs", response_class=HTMLResponse)
@router.get("/additional-programs/", response_class=HTMLResponse, include_in_schema=False)
def additional_programs_overview(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if not _can_open_additional_programs(user):
        return RedirectResponse("/?error=" + quote("Für Zusatz-Programme fehlt die Berechtigung."), status_code=303)
    programs = _visible_programs(db, user)
    return templates.TemplateResponse("additional_programs.html", {
        "request": request,
        "user": user,
        "programs": programs,
    })


@router.get("/system/settings/general/additional-programs", response_class=HTMLResponse)
def additional_programs_settings(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    roles = db.query(Role).order_by(Role.name).all()
    return templates.TemplateResponse("system_additional_programs.html", {
        "request": request,
        "user": user,
        "roles": roles,
        "programs": _load_programs(db),
        "message": request.query_params.get("message", ""),
        "error": request.query_params.get("error", ""),
    })


@router.post("/system/settings/general/additional-programs/add")
def additional_program_add(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    protocol: str = Form("http"),
    host: str = Form(...),
    port: int = Form(...),
    path: str = Form(""),
    enabled: str = Form("0"),
    allowed_roles: list[str] = Form(default=[]),
    db: Session = Depends(get_db),
):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    error = _validate_program(name, host, port)
    if error:
        return RedirectResponse("/system/settings/general/additional-programs?error=" + quote(error), status_code=303)
    valid_roles = {role.name for role in db.query(Role).all()}
    programs = _load_programs(db)
    next_id = max([int(p.get("id", 0)) for p in programs] + [0]) + 1
    program = _normalize_program(name, description, protocol, host, port, path, enabled, allowed_roles, valid_roles)
    program["id"] = next_id
    programs.append(program)
    _save_programs(db, programs)
    log_action(db, user.employee_number, "additional_program_created", "settings", str(next_id), f"{program['name']}; Rollen: {', '.join(program['allowed_roles']) or 'keine'}")
    return RedirectResponse("/system/settings/general/additional-programs?message=" + quote("Zusatz-Programm gespeichert."), status_code=303)


@router.post("/system/settings/general/additional-programs/{program_id}/save")
def additional_program_save(
    program_id: int,
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    protocol: str = Form("http"),
    host: str = Form(...),
    port: int = Form(...),
    path: str = Form(""),
    enabled: str = Form("0"),
    allowed_roles: list[str] = Form(default=[]),
    db: Session = Depends(get_db),
):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    error = _validate_program(name, host, port)
    if error:
        return RedirectResponse("/system/settings/general/additional-programs?error=" + quote(error), status_code=303)
    programs = _load_programs(db)
    program = next((p for p in programs if int(p.get("id", 0)) == program_id), None)
    if not program:
        return RedirectResponse("/system/settings/general/additional-programs?error=" + quote("Zusatz-Programm nicht gefunden."), status_code=303)
    valid_roles = {role.name for role in db.query(Role).all()}
    updated = _normalize_program(name, description, protocol, host, port, path, enabled, allowed_roles, valid_roles)
    updated["id"] = program_id
    programs = [updated if int(p.get("id", 0)) == program_id else p for p in programs]
    _save_programs(db, programs)
    log_action(db, user.employee_number, "additional_program_updated", "settings", str(program_id), f"{updated['name']}; Rollen: {', '.join(updated['allowed_roles']) or 'keine'}")
    return RedirectResponse("/system/settings/general/additional-programs?message=" + quote("Zusatz-Programm aktualisiert."), status_code=303)


@router.post("/system/settings/general/additional-programs/{program_id}/delete")
def additional_program_delete(program_id: int, request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    programs = _load_programs(db)
    removed = next((p for p in programs if int(p.get("id", 0)) == program_id), None)
    programs = [p for p in programs if int(p.get("id", 0)) != program_id]
    _save_programs(db, programs)
    log_action(db, user.employee_number, "additional_program_deleted", "settings", str(program_id), (removed or {}).get("name", ""))
    return RedirectResponse("/system/settings/general/additional-programs?message=" + quote("Zusatz-Programm gelöscht."), status_code=303)
