from fastapi import APIRouter, Depends, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Role, Employee
from app.routes.common import templates, require_admin_response

router = APIRouter()

DEFAULT_PERMISSIONS = {
    "dashboard.view": "Dashboard anzeigen",
    "employee.view": "Mitarbeiter anzeigen",
    "employee.edit": "Mitarbeiter bearbeiten",
    "employee.delete": "Mitarbeiter löschen",
    "time.book": "Zeiten buchen",
    "time.correct": "Zeitkorrekturen bearbeiten",
    "time.history": "Zeithistorie anzeigen",
    "absence.manage": "Abwesenheiten verwalten",
    "vacation.request": "Urlaub beantragen",
    "vacation.approve": "Urlaub genehmigen",
    "reports.view": "Auswertungen ansehen",
    "reports.export": "Auswertungen exportieren",
    "settings.view": "Systemeinstellungen anzeigen",
    "settings.edit": "Systemeinstellungen bearbeiten",
    "roles.manage": "Rollen & Rechte verwalten",
    "backup.manage": "Backup & Restore verwalten",
    "updates.install": "Updates installieren",
    "api.manage": "API verwalten",
    "dsgvo.manage": "DSGVO verwalten",
    "offboarding.manage": "Offboarding verwalten",
    "terminals.manage": "Terminals verwalten",
}

SYSTEM_ROLE_DEFAULTS = {
    "Administrator": set(DEFAULT_PERMISSIONS.keys()),
    "Personal": {
        "dashboard.view", "employee.view", "employee.edit", "time.correct", "time.history",
        "absence.manage", "vacation.approve", "reports.view", "reports.export",
        "settings.view", "dsgvo.manage", "offboarding.manage",
    },
    "Teamleiter": {
        "dashboard.view", "employee.view", "time.history", "time.correct",
        "vacation.approve", "reports.view",
    },
    "Mitarbeiter": {
        "dashboard.view", "time.book", "vacation.request",
    },
}

SYSTEM_ROLES = set(SYSTEM_ROLE_DEFAULTS.keys())


def _split_permissions(value: str | None) -> set[str]:
    if not value:
        return set()
    return {p.strip() for p in value.split(",") if p.strip()}


def _join_permissions(values) -> str:
    return ",".join(sorted(set(values)))


def ensure_default_roles(db: Session):
    for name, perms in SYSTEM_ROLE_DEFAULTS.items():
        role = db.query(Role).filter(Role.name == name).first()
        if not role:
            role = Role(name=name, description="Systemrolle", permissions=_join_permissions(perms))
            db.add(role)
    db.commit()


@router.get("/system/settings/roles", response_class=HTMLResponse)
@router.get("/system/settings/rights", response_class=HTMLResponse)
@router.get("/system/settings/roles-rights", response_class=HTMLResponse)
def roles_rights_page(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_admin_response(request, db)
    if redirect:
        return redirect
    ensure_default_roles(db)
    roles = db.query(Role).order_by(Role.name).all()
    counts = dict(db.query(Employee.role_id, Employee.id).filter(Employee.role_id.isnot(None)).all())
    # oben nur ein Mitarbeiter pro Rolle möglich wegen dict, deshalb separat zählen
    counts = {r.id: db.query(Employee).filter(Employee.role_id == r.id).count() for r in roles}
    selected_id = int(request.query_params.get("role_id") or (roles[0].id if roles else 0))
    selected_role = db.query(Role).filter(Role.id == selected_id).first() if selected_id else None
    selected_permissions = _split_permissions(selected_role.permissions if selected_role else "")
    return templates.TemplateResponse("system_roles_rights.html", {
        "request": request,
        "user": user,
        "roles": roles,
        "counts": counts,
        "permissions": DEFAULT_PERMISSIONS,
        "selected_role": selected_role,
        "selected_permissions": selected_permissions,
        "system_roles": SYSTEM_ROLES,
    })


@router.post("/system/settings/roles/create")
def create_role(
    request: Request,
    name: str = Form(...),
    copy_from_role_id: int = Form(0),
    db: Session = Depends(get_db),
):
    user, redirect = require_admin_response(request, db)
    if redirect:
        return redirect
    ensure_default_roles(db)
    name = (name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Rollenname fehlt.")
    if db.query(Role).filter(Role.name == name).first():
        raise HTTPException(status_code=400, detail="Diese Rolle gibt es bereits.")
    permissions = ""
    if copy_from_role_id:
        source = db.query(Role).filter(Role.id == copy_from_role_id).first()
        if source:
            permissions = source.permissions or ""
    role = Role(name=name, description="Benutzerdefinierte Rolle", permissions=permissions)
    db.add(role)
    db.commit()
    return RedirectResponse(f"/system/settings/roles?role_id={role.id}", status_code=303)


@router.post("/system/settings/roles/{role_id}/permissions")
def save_permissions(
    role_id: int,
    request: Request,
    permissions: list[str] = Form(default=[]),
    db: Session = Depends(get_db),
):
    user, redirect = require_admin_response(request, db)
    if redirect:
        return redirect
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Rolle nicht gefunden.")
    allowed = set(DEFAULT_PERMISSIONS.keys())
    role.permissions = _join_permissions([p for p in permissions if p in allowed])
    db.commit()
    return RedirectResponse(f"/system/settings/roles?role_id={role.id}", status_code=303)


@router.post("/system/settings/roles/{role_id}/rename")
def rename_role(
    role_id: int,
    request: Request,
    name: str = Form(...),
    db: Session = Depends(get_db),
):
    user, redirect = require_admin_response(request, db)
    if redirect:
        return redirect
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Rolle nicht gefunden.")
    if role.name in SYSTEM_ROLES:
        raise HTTPException(status_code=400, detail="Systemrollen können nicht umbenannt werden.")
    name = (name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Rollenname fehlt.")
    role.name = name
    db.commit()
    return RedirectResponse(f"/system/settings/roles?role_id={role.id}", status_code=303)


@router.post("/system/settings/roles/{role_id}/delete")
def delete_role(role_id: int, request: Request, db: Session = Depends(get_db)):
    user, redirect = require_admin_response(request, db)
    if redirect:
        return redirect
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Rolle nicht gefunden.")
    if role.name in SYSTEM_ROLES:
        raise HTTPException(status_code=400, detail="Systemrollen können nicht gelöscht werden.")
    if db.query(Employee).filter(Employee.role_id == role.id).count() > 0:
        raise HTTPException(status_code=400, detail="Rolle ist noch Mitarbeitern zugewiesen.")
    db.delete(role)
    db.commit()
    return RedirectResponse("/system/settings/roles", status_code=303)


@router.post("/system/settings/roles/defaults")
def restore_defaults(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_admin_response(request, db)
    if redirect:
        return redirect
    for name, perms in SYSTEM_ROLE_DEFAULTS.items():
        role = db.query(Role).filter(Role.name == name).first()
        if role:
            role.permissions = _join_permissions(perms)
        else:
            db.add(Role(name=name, description="Systemrolle", permissions=_join_permissions(perms)))
    db.commit()
    return RedirectResponse("/system/settings/roles", status_code=303)
