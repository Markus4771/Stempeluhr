from .common import *

router = APIRouter()

def _api_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

@router.get("/system/settings/api", response_class=HTMLResponse)
def system_settings_api(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    tokens = db.query(ApiToken).order_by(ApiToken.created_at.desc(), ApiToken.id.desc()).all()
    settings = service_settings_dict(db)
    return templates.TemplateResponse("system_settings_api.html", {
        "request": request,
        "user": user,
        "tokens": tokens,
        "settings": settings,
        "new_key": request.query_params.get("new_key", ""),
        "saved": request.query_params.get("saved") == "1",
    })


@router.get("/system/settings/api/help", response_class=HTMLResponse)
def system_settings_api_help(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    settings = service_settings_dict(db)
    tokens = db.query(ApiToken).order_by(ApiToken.last_used_at.desc().nullslast(), ApiToken.id.desc()).all()
    active_tokens = sum(1 for token in tokens if token.active)
    last_used_dt = next((token.last_used_at for token in tokens if token.last_used_at), None)
    last_used = last_used_dt.strftime('%d.%m.%Y %H:%M') if last_used_dt else None
    api_enabled = settings.get('api_enabled', 'false') in ['true', '1', 'on', 'ja']
    return templates.TemplateResponse("system_settings_api_help.html", {
        "request": request,
        "user": user,
        "settings": settings,
        "api_enabled": api_enabled,
        "active_tokens": active_tokens,
        "last_used": last_used,
    })

@router.post("/system/settings/api/save", response_class=HTMLResponse)
def system_settings_api_save(
    request: Request,
    api_enabled: str = Form("0"),
    api_logging_enabled: str = Form("0"),
    terminal_api_enabled: str = Form("0"),
    db: Session = Depends(get_db),
):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    service_set_setting(db, "api_enabled", "true" if str(api_enabled).lower() in ["1", "true", "on", "ja"] else "false")
    service_set_setting(db, "api_logging_enabled", "true" if str(api_logging_enabled).lower() in ["1", "true", "on", "ja"] else "false")
    service_set_setting(db, "terminal_api_enabled", "true" if str(terminal_api_enabled).lower() in ["1", "true", "on", "ja"] else "false")
    log_action(db, user.employee_number, "api_settings_updated", "settings", "api", "API-Einstellungen geändert")
    return RedirectResponse("/system/settings/api?saved=1", status_code=303)

@router.post("/system/settings/api/create", response_class=HTMLResponse)
def system_settings_api_create(
    request: Request,
    name: str = Form("api"),
    permissions: str = Form("read"),
    allowed_ips: str = Form(""),
    expires_at: str = Form(""),
    db: Session = Depends(get_db),
):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    raw_key = "sk_stempeluhr_" + secrets.token_urlsafe(32)
    expires_value = None
    if expires_at:
        try:
            expires_value = datetime.fromisoformat(expires_at)
        except Exception:
            expires_value = None
    token = ApiToken(
        name=(name or "api").strip()[:100],
        token=_api_token_hash(raw_key),
        role="api",
        permissions="write" if permissions == "write" else "read",
        allowed_ips=(allowed_ips or "").strip() or None,
        expires_at=expires_value,
        active=True,
    )
    db.add(token)
    service_set_setting(db, "api_enabled", "true")
    db.commit()
    log_action(db, user.employee_number, "api_token_created", "api_tokens", str(token.id), token.name)
    return templates.TemplateResponse("system_settings_api.html", {
        "request": request,
        "user": user,
        "tokens": db.query(ApiToken).order_by(ApiToken.created_at.desc(), ApiToken.id.desc()).all(),
        "settings": service_settings_dict(db),
        "new_key": raw_key,
        "saved": True,
    })

@router.post("/system/settings/api/{token_id}/toggle", response_class=HTMLResponse)
def system_settings_api_toggle(request: Request, token_id: int, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    token = db.query(ApiToken).filter(ApiToken.id == token_id).first()
    if token:
        token.active = not bool(token.active)
        db.commit()
        log_action(db, user.employee_number, "api_token_toggled", "api_tokens", str(token.id), f"active={token.active}")
    return RedirectResponse("/system/settings/api?saved=1", status_code=303)

@router.post("/system/settings/api/{token_id}/delete", response_class=HTMLResponse)
def system_settings_api_delete(request: Request, token_id: int, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    token = db.query(ApiToken).filter(ApiToken.id == token_id).first()
    if token:
        name = token.name
        db.delete(token)
        db.commit()
        log_action(db, user.employee_number, "api_token_deleted", "api_tokens", str(token_id), name)
    return RedirectResponse("/system/settings/api?saved=1", status_code=303)



# ---------------------------------------------------------------------------
# Terminalverwaltung / Multi-Terminal
# ---------------------------------------------------------------------------
