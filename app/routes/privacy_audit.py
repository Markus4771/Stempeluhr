from .common import *

router = APIRouter()

@router.get("/system/privacy", response_class=HTMLResponse)
def system_privacy(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect

    settings = service_settings_dict(db)

    return templates.TemplateResponse("system_privacy.html", {
        "request": request,
        "user": user,
        "settings": settings,
        "saved": False
    })

@router.post("/system/privacy", response_class=HTMLResponse)
def system_privacy_save(
    request: Request,
    privacy_officer_name: str = Form(""),
    privacy_officer_email: str = Form(""),
    privacy_retention_years: int = Form(10),
    privacy_export_enabled: str = Form("off"),
    privacy_delete_enabled: str = Form("off"),
    privacy_processing_purpose: str = Form(""),
    privacy_legal_basis: str = Form(""),
    privacy_notice_text: str = Form(""),
    db: Session = Depends(get_db)
):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect

    privacy_retention_years = max(1, min(30, privacy_retention_years))

    def set_setting(key: str, value: str):
        row = db.query(Setting).filter(Setting.key == key).first()
        if not row:
            db.add(Setting(key=key, value=value))
        else:
            row.value = value

    set_setting("privacy_officer_name", privacy_officer_name.strip())
    set_setting("privacy_officer_email", privacy_officer_email.strip())
    set_setting("privacy_retention_years", str(privacy_retention_years))
    set_setting("privacy_export_enabled", "true" if privacy_export_enabled == "on" else "false")
    set_setting("privacy_delete_enabled", "true" if privacy_delete_enabled == "on" else "false")
    set_setting("privacy_processing_purpose", privacy_processing_purpose.strip())
    set_setting("privacy_legal_basis", privacy_legal_basis.strip())
    set_setting("privacy_notice_text", privacy_notice_text.strip())

    db.commit()

    log_action(
        db,
        user.employee_number,
        "privacy_settings_updated",
        "settings",
        "privacy",
        f"Aufbewahrung={privacy_retention_years} Jahre"
    )

    settings = service_settings_dict(db)

    return templates.TemplateResponse("system_privacy.html", {
        "request": request,
        "user": user,
        "settings": settings,
        "saved": True
    })

@router.get("/system/audit", response_class=HTMLResponse)
def system_audit(
    request: Request,
    actor: str = "",
    action: str = "",
    entity: str = "",
    date_from: str = "",
    date_to: str = "",
    db: Session = Depends(get_db)
):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect

    query = db.query(AuditLog)

    actor = (actor or "").strip()
    action = (action or "").strip()
    entity = (entity or "").strip()

    if actor:
        query = query.filter(AuditLog.actor.ilike(f"%{actor}%"))

    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))

    if entity:
        query = query.filter(AuditLog.entity.ilike(f"%{entity}%"))

    if date_from:
        try:
            dt_from = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(AuditLog.created_at >= dt_from)
        except Exception:
            pass

    if date_to:
        try:
            dt_to = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(AuditLog.created_at < dt_to)
        except Exception:
            pass

    logs = query.order_by(AuditLog.created_at.desc()).limit(1000).all()

    return templates.TemplateResponse("system_audit.html", {
        "request": request,
        "user": user,
        "logs": logs,
        "filters": {
            "actor": actor,
            "action": action,
            "entity": entity,
            "date_from": date_from,
            "date_to": date_to
        }
    })




