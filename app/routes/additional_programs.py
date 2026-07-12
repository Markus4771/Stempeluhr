from __future__ import annotations

import ipaddress
import json
import re
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth import current_user
from app.database import get_db
from app.models import Setting
from app.routes.common import log_action, require_system_admin_response, templates
from app.services.role_permissions import has_permission

router = APIRouter()
SETTING_KEY = "additional_programs"
_HOST_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]{0,252}[A-Za-z0-9]$|^[A-Za-z0-9]$")


def _load_programs(db: Session) -> list[dict]:
    row = db.query(Setting).filter(Setting.key == SETTING_KEY).first()
    try:
        data = json.loads(row.value or "[]") if row else []
    except Exception:
        data = []
    return data if isinstance(data, list) else []


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


def _normalize_program(name: str, description: str, protocol: str, host: str, port: int, path: str, enabled: str) -> dict:
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


@router.get("/additional-programs", response_class=HTMLResponse)
def additional_programs_overview(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if not has_permission(user, "nav.additional_programs"):
        return RedirectResponse("/", status_code=303)
    programs = [p for p in _load_programs(db) if p.get("enabled", True)]
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
    return templates.TemplateResponse("system_additional_programs.html", {
        "request": request,
        "user": user,
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
    db: Session = Depends(get_db),
):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    error = _validate_program(name, host, port)
    if error:
        return RedirectResponse("/system/settings/general/additional-programs?error=" + quote(error), status_code=303)
    programs = _load_programs(db)
    next_id = max([int(p.get("id", 0)) for p in programs] + [0]) + 1
    program = _normalize_program(name, description, protocol, host, port, path, enabled)
    program["id"] = next_id
    programs.append(program)
    _save_programs(db, programs)
    log_action(db, user.employee_number, "additional_program_created", "settings", str(next_id), program["name"])
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
    updated = _normalize_program(name, description, protocol, host, port, path, enabled)
    updated["id"] = program_id
    programs = [updated if int(p.get("id", 0)) == program_id else p for p in programs]
    _save_programs(db, programs)
    log_action(db, user.employee_number, "additional_program_updated", "settings", str(program_id), updated["name"])
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
