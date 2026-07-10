from .common import *

router = APIRouter()

@router.get("/system/settings/email", response_class=HTMLResponse)
def system_email_settings(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect

    settings = service_settings_dict(db)
    return templates.TemplateResponse("system_email.html", {
        "request": request,
        "user": user,
        "settings": settings,
        "saved": False,
        "message": None,
        "error": None
    })



@router.get("/system/settings/email/help", response_class=HTMLResponse)
def system_email_help(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    settings = service_settings_dict(db)
    return templates.TemplateResponse("system_email_help.html", {
        "request": request,
        "user": user,
        "settings": settings,
    })

@router.post("/system/settings/email", response_class=HTMLResponse)
def system_email_settings_save(
    request: Request,
    email_enabled: str = Form("off"),
    email_smtp_host: str = Form(""),
    email_smtp_port: int = Form(587),
    email_smtp_user: str = Form(""),
    email_smtp_password: str = Form(""),
    email_from_address: str = Form(""),
    email_from_name: str = Form("Stempeluhr"),
    email_use_tls: str = Form("off"),
    email_use_ssl: str = Form("off"),
    email_test_recipient: str = Form(""),
    db: Session = Depends(get_db)
):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect

    def set_setting(key, value):
        row = db.query(Setting).filter(Setting.key == key).first()
        if not row:
            db.add(Setting(key=key, value=str(value)))
        else:
            row.value = str(value)

    email_smtp_port = max(1, min(65535, email_smtp_port))

    set_setting("email_enabled", "true" if email_enabled == "on" else "false")
    set_setting("email_smtp_host", email_smtp_host.strip())
    set_setting("email_smtp_port", email_smtp_port)
    set_setting("email_smtp_user", email_smtp_user.strip())
    if email_smtp_password:
        set_setting("email_smtp_password", email_smtp_password)
    set_setting("email_from_address", email_from_address.strip())
    set_setting("email_from_name", email_from_name.strip() or "Stempeluhr")
    set_setting("email_use_tls", "true" if email_use_tls == "on" else "false")
    set_setting("email_use_ssl", "true" if email_use_ssl == "on" else "false")
    set_setting("email_test_recipient", email_test_recipient.strip())

    db.commit()
    log_action(db, user.employee_number, "email_settings_updated", "settings", "email", f"SMTP={email_smtp_host}:{email_smtp_port}")

    settings = service_settings_dict(db)
    return templates.TemplateResponse("system_email.html", {
        "request": request,
        "user": user,
        "settings": settings,
        "saved": True,
        "message": "E-Mail-Einstellungen gespeichert.",
        "error": None
    })

@router.post("/system/settings/email/test", response_class=HTMLResponse)
def system_email_test(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect

    settings = service_settings_dict(db)
    recipient = settings.get("email_test_recipient", "") or settings.get("email_from_address", "")
    error = None
    message = None

    try:
        send_email_from_settings(
            db,
            recipient,
            "Stempeluhr Test-E-Mail",
            "Dies ist eine Test-E-Mail aus der Stempeluhr."
        )
        message = f"Test-E-Mail wurde an {recipient} gesendet."
        log_action(db, user.employee_number, "email_test_sent", "settings", "email", recipient)
    except Exception as exc:
        error = f"Test-E-Mail fehlgeschlagen: {exc}"
        log_action(db, user.employee_number, "email_test_failed", "settings", "email", str(exc))

    return templates.TemplateResponse("system_email.html", {
        "request": request,
        "user": user,
        "settings": {s.key: s.value for s in db.query(Setting).all()},
        "saved": False,
        "message": message,
        "error": error
    })

