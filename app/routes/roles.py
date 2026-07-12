from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Employee, Role
from app.routes.common import log_action, require_system_admin_response, templates
from app.services.role_permissions import (
    DEFAULT_ROLE_PERMISSIONS,
    parse_permissions,
    permission_labels,
    serialize_permissions,
)

router = APIRouter()
PROTECTED_ROLES = {"Administrator", "Personal", "Teamleiter", "Mitarbeiter"}


@router.get("/system/settings/roles", response_class=HTMLResponse)
def roles_settings(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    roles = db.query(Role).order_by(Role.name).all()
    role_values = {}
    employee_counts = {}
    for role in roles:
        role_values[role.id] = parse_permissions(role.permissions) or set(DEFAULT_ROLE_PERMISSIONS.get(role.name, set()))
        employee_counts[role.id] = db.query(Employee).filter(Employee.role_id == role.id).count()
    return templates.TemplateResponse("system_roles.html", {
        "request": request,
        "user": user,
        "roles": roles,
        "role_values": role_values,
        "employee_counts": employee_counts,
        "permission_groups": permission_labels(),
        "saved": request.query_params.get("saved") == "1",
        "message": request.query_params.get("message", ""),
        "error": request.query_params.get("error", ""),
        "protected_roles": PROTECTED_ROLES,
    })


@router.post("/system/settings/roles/add")
def add_role(
    request: Request,
    name: str = Form(""),
    description: str = Form(""),
    permissions: list[str] = Form(default=[]),
    db: Session = Depends(get_db),
):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    name = (name or "").strip()
    if len(name) < 2 or len(name) > 100:
        return RedirectResponse("/system/settings/roles?error=" + quote("Der Rollenname muss 2 bis 100 Zeichen lang sein."), 303)
    if db.query(Role).filter(Role.name == name).first():
        return RedirectResponse("/system/settings/roles?error=" + quote("Eine Rolle mit diesem Namen existiert bereits."), 303)
    role = Role(name=name, description=(description or "").strip(), permissions=serialize_permissions(permissions))
    db.add(role)
    db.commit()
    db.refresh(role)
    log_action(db, user.employee_number, "role_created", "roles", str(role.id), role.name)
    return RedirectResponse("/system/settings/roles?saved=1&message=" + quote(f"Rolle {name} wurde angelegt."), 303)


@router.post("/system/settings/roles/{role_id}/save")
def save_role(
    role_id: int,
    request: Request,
    name: str = Form(""),
    description: str = Form(""),
    permissions: list[str] = Form(default=[]),
    db: Session = Depends(get_db),
):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        return RedirectResponse("/system/settings/roles?error=" + quote("Rolle nicht gefunden."), 303)
    old_name = role.name
    new_name = (name or "").strip()
    if role.name in PROTECTED_ROLES:
        new_name = role.name
    elif len(new_name) < 2 or len(new_name) > 100:
        return RedirectResponse("/system/settings/roles?error=" + quote("Der Rollenname muss 2 bis 100 Zeichen lang sein."), 303)
    duplicate = db.query(Role).filter(Role.name == new_name, Role.id != role.id).first()
    if duplicate:
        return RedirectResponse("/system/settings/roles?error=" + quote("Eine Rolle mit diesem Namen existiert bereits."), 303)
    role.name = new_name
    role.description = (description or "").strip()
    role.permissions = '["*"]' if role.name == "Administrator" else serialize_permissions(permissions)
    db.commit()
    log_action(db, user.employee_number, "role_updated", "roles", str(role.id), f"{old_name} -> {role.name}")
    return RedirectResponse("/system/settings/roles?saved=1&message=" + quote(f"Rolle {role.name} wurde gespeichert."), 303)


@router.post("/system/settings/roles/{role_id}/delete")
def delete_role(role_id: int, request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        return RedirectResponse("/system/settings/roles?error=" + quote("Rolle nicht gefunden."), 303)
    if role.name in PROTECTED_ROLES:
        return RedirectResponse("/system/settings/roles?error=" + quote("Standardrollen können nicht gelöscht werden."), 303)
    count = db.query(Employee).filter(Employee.role_id == role.id).count()
    if count:
        return RedirectResponse("/system/settings/roles?error=" + quote(f"Die Rolle ist noch {count} Benutzer(n) zugeordnet."), 303)
    name = role.name
    db.delete(role)
    db.commit()
    log_action(db, user.employee_number, "role_deleted", "roles", str(role_id), name)
    return RedirectResponse("/system/settings/roles?saved=1&message=" + quote(f"Rolle {name} wurde gelöscht."), 303)
