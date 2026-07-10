from .common import *

router = APIRouter()

def _terminal_key_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

@router.get("/system/settings/terminals", response_class=HTMLResponse)
def system_settings_terminals(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    terminals = db.query(Terminal).order_by(Terminal.name.asc()).all()
    return templates.TemplateResponse("system_terminals.html", {
        "request": request,
        "user": user,
        "terminals": terminals,
        "new_key": request.query_params.get("new_key", ""),
        "saved": request.query_params.get("saved") == "1",
    })

@router.get("/system/settings/terminals/help", response_class=HTMLResponse)
def system_settings_terminals_help(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    return templates.TemplateResponse("system_terminals_help.html", {"request": request, "user": user})

@router.post("/system/settings/terminals/create", response_class=HTMLResponse)
def system_settings_terminals_create(
    request: Request,
    name: str = Form(...),
    location: str = Form(""),
    description: str = Form(""),
    offline_buffer_enabled: str = Form("0"),
    db: Session = Depends(get_db),
):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    raw_key = "tk_stempeluhr_" + secrets.token_urlsafe(32)
    count = db.query(Terminal).count() + 1
    terminal = Terminal(
        name=(name or "Terminal").strip()[:100],
        location=(location or "").strip()[:255],
        description=(description or "").strip() or None,
        terminal_code=f"TERMINAL-{count:03d}",
        api_key=_terminal_key_hash(raw_key),
        active=True,
        offline_buffer_enabled=str(offline_buffer_enabled).lower() in ["1", "true", "on", "ja"],
    )
    db.add(terminal)
    db.commit()
    log_action(db, user.employee_number, "terminal_created", "terminals", str(terminal.id), terminal.name)
    return templates.TemplateResponse("system_terminals.html", {
        "request": request,
        "user": user,
        "terminals": db.query(Terminal).order_by(Terminal.name.asc()).all(),
        "new_key": raw_key,
        "saved": True,
    })

@router.post("/system/settings/terminals/{terminal_id}/toggle", response_class=HTMLResponse)
def system_settings_terminals_toggle(request: Request, terminal_id: int, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    terminal = db.query(Terminal).filter(Terminal.id == terminal_id).first()
    if terminal:
        terminal.active = not bool(terminal.active)
        db.commit()
        log_action(db, user.employee_number, "terminal_toggled", "terminals", str(terminal.id), f"active={terminal.active}")
    return RedirectResponse("/system/settings/terminals?saved=1", status_code=303)

@router.post("/system/settings/terminals/{terminal_id}/new-key", response_class=HTMLResponse)
def system_settings_terminals_new_key(request: Request, terminal_id: int, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    terminal = db.query(Terminal).filter(Terminal.id == terminal_id).first()
    raw_key = "tk_stempeluhr_" + secrets.token_urlsafe(32)
    if terminal:
        terminal.api_key = _terminal_key_hash(raw_key)
        db.commit()
        log_action(db, user.employee_number, "terminal_key_rotated", "terminals", str(terminal.id), terminal.name)
    return templates.TemplateResponse("system_terminals.html", {
        "request": request,
        "user": user,
        "terminals": db.query(Terminal).order_by(Terminal.name.asc()).all(),
        "new_key": raw_key,
        "saved": True,
    })

@router.post("/system/settings/terminals/{terminal_id}/time-sync-toggle", response_class=HTMLResponse)
def system_settings_terminals_time_sync_toggle(request: Request, terminal_id: int, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    terminal = db.query(Terminal).filter(Terminal.id == terminal_id).first()
    if terminal:
        terminal.time_sync_enabled = not bool(getattr(terminal, "time_sync_enabled", True))
        db.commit()
        log_action(db, user.employee_number, "terminal_time_sync_toggled", "terminals", str(terminal.id), f"time_sync_enabled={terminal.time_sync_enabled}")
    return RedirectResponse("/system/settings/terminals?saved=1", status_code=303)


@router.post("/system/settings/terminals/{terminal_id}/delete", response_class=HTMLResponse)
def system_settings_terminals_delete(request: Request, terminal_id: int, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    terminal = db.query(Terminal).filter(Terminal.id == terminal_id).first()
    if terminal:
        name = terminal.name
        terminal.active = False
        db.commit()
        log_action(db, user.employee_number, "terminal_deactivated", "terminals", str(terminal_id), name)
    return RedirectResponse("/system/settings/terminals?saved=1", status_code=303)



# ---------------------------------------------------------------------------
# Uhrzeit & Zeitserver
# ---------------------------------------------------------------------------
