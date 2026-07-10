from .common import *
from app.models import OnboardingToken, PasswordResetToken

router = APIRouter()


def _onboarding_settings(db: Session) -> dict:
    settings = {s.key: s.value for s in db.query(Setting).all()}
    return {
        "enabled": settings.get("onboarding_enabled", "true"),
        "token_hours": settings.get("onboarding_token_hours", "48"),
        "email_subject": settings.get("onboarding_email_subject", "Einladung zur Stempeluhr"),
        "email_body": settings.get("onboarding_email_body", "Hallo {name},\n\nbitte richte dein Stempeluhr-Konto über folgenden Link ein:\n{link}\n\nDer Link ist {hours} Stunden gültig.\n\nViele Grüße\nStempeluhr"),
        "privacy_version": settings.get("onboarding_privacy_version", "1.0"),
        "privacy_text": settings.get("onboarding_privacy_text", "Ich habe die Datenschutzbestimmungen zur Nutzung der Stempeluhr gelesen und stimme der Verarbeitung meiner Daten zur Arbeitszeiterfassung zu."),
    }


def _set_setting(db: Session, key: str, value: str):
    row = db.query(Setting).filter(Setting.key == key).first()
    if row:
        row.value = str(value)
    else:
        db.add(Setting(key=key, value=str(value)))


def _privacy_required(employee: Employee, db: Session) -> bool:
    if not employee or is_fixed_admin_employee(employee):
        return False
    cfg = _onboarding_settings(db)
    required_version = str(cfg.get("privacy_version") or "1.0")
    return not employee.privacy_accepted_at or str(employee.privacy_version_accepted or "") != required_version


@router.get("/system/settings/onboarding", response_class=HTMLResponse)
def onboarding_settings_form(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_admin_response(request, db)
    if redirect:
        return redirect
    tokens = db.query(OnboardingToken).order_by(OnboardingToken.created_at.desc(), OnboardingToken.id.desc()).limit(100).all()
    return templates.TemplateResponse("system_onboarding.html", {
        "request": request,
        "user": user,
        "settings": _onboarding_settings(db),
        "tokens": tokens,
        "message": None,
        "error": None,
    })


@router.post("/system/settings/onboarding", response_class=HTMLResponse)
def onboarding_settings_save(
    request: Request,
    onboarding_enabled: str = Form("off"),
    onboarding_token_hours: str = Form("48"),
    onboarding_email_subject: str = Form(""),
    onboarding_email_body: str = Form(""),
    onboarding_privacy_version: str = Form("1.0"),
    onboarding_privacy_text: str = Form(""),
    db: Session = Depends(get_db),
):
    user, redirect = require_admin_response(request, db)
    if redirect:
        return redirect
    _set_setting(db, "onboarding_enabled", "true" if onboarding_enabled == "on" else "false")
    _set_setting(db, "onboarding_token_hours", onboarding_token_hours or "48")
    _set_setting(db, "onboarding_email_subject", onboarding_email_subject or "Einladung zur Stempeluhr")
    _set_setting(db, "onboarding_email_body", onboarding_email_body or "Hallo {name},\n\nbitte richte dein Stempeluhr-Konto über folgenden Link ein:\n{link}\n\nDer Link ist {hours} Stunden gültig.\n\nViele Grüße\nStempeluhr")
    _set_setting(db, "onboarding_privacy_version", onboarding_privacy_version or "1.0")
    _set_setting(db, "onboarding_privacy_text", onboarding_privacy_text or "Ich habe die Datenschutzbestimmungen gelesen und stimme zu.")
    db.commit()
    log_action(db, user.employee_number, "onboarding_settings_saved", "settings", "onboarding", "Onboarding-Einstellungen geändert")
    tokens = db.query(OnboardingToken).order_by(OnboardingToken.created_at.desc(), OnboardingToken.id.desc()).limit(100).all()
    return templates.TemplateResponse("system_onboarding.html", {
        "request": request,
        "user": user,
        "settings": _onboarding_settings(db),
        "tokens": tokens,
        "message": "Onboarding-Einstellungen gespeichert.",
        "error": None,
    })


@router.post("/admin/employees/{employee_id}/invite", response_class=HTMLResponse)
def send_onboarding_invite(employee_id: int, request: Request, db: Session = Depends(get_db)):
    user, redirect = require_admin_response(request, db)
    if redirect:
        return redirect
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        return templates.TemplateResponse("message.html", {"request": request, "user": user, "title": "Fehler", "message": "Mitarbeiter nicht gefunden.", "return_to": "/admin"})
    if not (employee.email or "").strip():
        return templates.TemplateResponse("message.html", {"request": request, "user": user, "title": "Fehler", "message": "Der Mitarbeiter hat keine E-Mail-Adresse.", "return_to": "/admin"})
    cfg = _onboarding_settings(db)
    if str(cfg.get("enabled", "true")).lower() not in ("true", "1", "on", "ja"):
        return templates.TemplateResponse("message.html", {"request": request, "user": user, "title": "Onboarding deaktiviert", "message": "Der Onboarding-Versand ist in den Systemeinstellungen deaktiviert.", "return_to": "/admin"})
    try:
        hours = max(1, min(int(cfg.get("token_hours") or "48"), 24 * 14))
    except Exception:
        hours = 48
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    now = datetime.now()
    db.query(OnboardingToken).filter(OnboardingToken.employee_id == employee.id, OnboardingToken.used_at.is_(None)).update({"used_at": now, "status": "replaced"})
    token = OnboardingToken(
        employee_id=employee.id,
        token_hash=token_hash,
        expires_at=now + timedelta(hours=hours),
        sent_at=now,
        requested_by=user.employee_number if user else "system",
        requested_ip=request.client.host if request.client else None,
        status="sent",
    )
    db.add(token)
    employee.onboarding_invited_at = now
    db.commit()
    invite_url = str(request.url_for("onboarding_accept_form", token=raw_token))
    name = f"{employee.first_name} {employee.last_name}".strip()
    subject = (cfg.get("email_subject") or "Einladung zur Stempeluhr").format(name=name, link=invite_url, hours=hours)
    body = (cfg.get("email_body") or "Hallo {name},\n\nbitte richte dein Stempeluhr-Konto über folgenden Link ein:\n{link}\n\nDer Link ist {hours} Stunden gültig.").format(name=name, link=invite_url, hours=hours)
    try:
        send_email_from_settings(db, employee.email.strip(), subject, body)
        log_action(db, user.employee_number, "onboarding_invite_sent", "employees", str(employee.id), employee.email)
        return templates.TemplateResponse("message.html", {"request": request, "user": user, "title": "Einladung versendet", "message": f"Die Einladungsmail wurde an {employee.email} versendet.", "return_to": "/admin"})
    except Exception as exc:
        token.status = "mail_failed"
        token.error_message = str(exc)[:1000]
        db.commit()
        log_action(db, user.employee_number, "onboarding_invite_failed", "employees", str(employee.id), str(exc)[:500])
        return templates.TemplateResponse("message.html", {"request": request, "user": user, "title": "E-Mail konnte nicht versendet werden", "message": str(exc), "return_to": "/admin"})


@router.get("/onboarding/{token}", response_class=HTMLResponse, name="onboarding_accept_form")
def onboarding_accept_form(request: Request, token: str, db: Session = Depends(get_db)):
    token_hash = hashlib.sha256((token or "").encode("utf-8")).hexdigest()
    invite = db.query(OnboardingToken).filter(OnboardingToken.token_hash == token_hash, OnboardingToken.used_at.is_(None), OnboardingToken.expires_at >= datetime.now()).first()
    if not invite:
        return templates.TemplateResponse("onboarding_accept.html", {"request": request, "token": "", "employee": None, "privacy_text": "", "privacy_version": "", "error": "Dieser Einladungslink ist ungültig oder abgelaufen.", "message": None})
    employee = db.query(Employee).filter(Employee.id == invite.employee_id, Employee.active == True).first()
    cfg = _onboarding_settings(db)
    return templates.TemplateResponse("onboarding_accept.html", {"request": request, "token": token, "employee": employee, "privacy_text": cfg.get("privacy_text"), "privacy_version": cfg.get("privacy_version"), "error": None, "message": None})


@router.post("/onboarding/{token}", response_class=HTMLResponse)
def onboarding_accept_submit(
    request: Request,
    token: str,
    password: str = Form(...),
    password_repeat: str = Form(...),
    privacy_accept: str = Form("off"),
    db: Session = Depends(get_db),
):
    token_hash = hashlib.sha256((token or "").encode("utf-8")).hexdigest()
    invite = db.query(OnboardingToken).filter(OnboardingToken.token_hash == token_hash, OnboardingToken.used_at.is_(None), OnboardingToken.expires_at >= datetime.now()).first()
    cfg = _onboarding_settings(db)
    if not invite:
        return templates.TemplateResponse("onboarding_accept.html", {"request": request, "token": "", "employee": None, "privacy_text": cfg.get("privacy_text"), "privacy_version": cfg.get("privacy_version"), "error": "Dieser Einladungslink ist ungültig oder abgelaufen.", "message": None})
    employee = db.query(Employee).filter(Employee.id == invite.employee_id, Employee.active == True).first()
    if not employee:
        invite.used_at = datetime.now()
        invite.status = "invalid_employee"
        db.commit()
        return templates.TemplateResponse("onboarding_accept.html", {"request": request, "token": "", "employee": None, "privacy_text": cfg.get("privacy_text"), "privacy_version": cfg.get("privacy_version"), "error": "Dieser Einladungslink ist ungültig oder abgelaufen.", "message": None})
    if password != password_repeat:
        return templates.TemplateResponse("onboarding_accept.html", {"request": request, "token": token, "employee": employee, "privacy_text": cfg.get("privacy_text"), "privacy_version": cfg.get("privacy_version"), "error": "Die Passwörter stimmen nicht überein.", "message": None})
    if len(password or "") < 8:
        return templates.TemplateResponse("onboarding_accept.html", {"request": request, "token": token, "employee": employee, "privacy_text": cfg.get("privacy_text"), "privacy_version": cfg.get("privacy_version"), "error": "Das Passwort muss mindestens 8 Zeichen lang sein.", "message": None})
    if privacy_accept != "on":
        return templates.TemplateResponse("onboarding_accept.html", {"request": request, "token": token, "employee": employee, "privacy_text": cfg.get("privacy_text"), "privacy_version": cfg.get("privacy_version"), "error": "Bitte bestätige die Datenschutzbestimmungen.", "message": None})
    now = datetime.now()
    employee.password_hash = hash_password(password)
    employee.privacy_accepted_at = now
    employee.privacy_version_accepted = str(cfg.get("privacy_version") or "1.0")
    employee.onboarding_completed_at = now
    employee.updated_at = now
    invite.used_at = now
    invite.status = "completed"
    db.commit()
    log_action(db, employee.employee_number, "onboarding_completed", "employees", str(employee.id), "Passwort gesetzt und Datenschutz bestätigt")
    return templates.TemplateResponse("onboarding_accept.html", {"request": request, "token": "", "employee": employee, "privacy_text": cfg.get("privacy_text"), "privacy_version": cfg.get("privacy_version"), "error": None, "message": "Dein Konto wurde eingerichtet. Du kannst dich jetzt anmelden."})


@router.get("/onboarding/privacy", response_class=HTMLResponse)
def privacy_accept_form(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", 303)
    cfg = _onboarding_settings(db)
    return templates.TemplateResponse("privacy_accept.html", {"request": request, "user": user, "privacy_text": cfg.get("privacy_text"), "privacy_version": cfg.get("privacy_version"), "error": None})


@router.post("/onboarding/privacy", response_class=HTMLResponse)
def privacy_accept_submit(request: Request, privacy_accept: str = Form("off"), db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", 303)
    cfg = _onboarding_settings(db)
    if privacy_accept != "on":
        return templates.TemplateResponse("privacy_accept.html", {"request": request, "user": user, "privacy_text": cfg.get("privacy_text"), "privacy_version": cfg.get("privacy_version"), "error": "Bitte bestätige die Datenschutzbestimmungen."})
    user.privacy_accepted_at = datetime.now()
    user.privacy_version_accepted = str(cfg.get("privacy_version") or "1.0")
    db.commit()
    log_action(db, user.employee_number, "privacy_accepted", "employees", str(user.id), user.privacy_version_accepted)
    return RedirectResponse("/dashboard", 303)
