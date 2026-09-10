from .common import *
from app.models import PasswordResetToken
from app.services.rfid_media import resolve_employee_by_rfid
from .common import _dashboard_stats, _get_pending_rfid_employee, _get_pending_rfid_status, _save_pending_rfid_from_terminal

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    stats = _dashboard_stats(db)
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user, "stats": stats, "auto_delay_seconds": auto_delay_seconds_setting(db)})

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    return index(request, db)

@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@router.post("/login")
def login_submit(request: Request, employee_number: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    raw_employee_number = (employee_number or "").strip()
    if raw_employee_number.lower() == "admin": employee_number = "admin"
    else:
        employee_number = normalize_employee_number(raw_employee_number, get_employee_number_length(db))
        valid_emp_no, emp_no_error = validate_employee_number(employee_number, get_employee_number_length(db))
        if not valid_emp_no: return templates.TemplateResponse("message.html", {"request": request, "title": "Fehler", "message": emp_no_error, "return_to": "/login"})
    employee = db.query(Employee).filter(Employee.employee_number == employee_number, Employee.active == True).first()
    if not employee or not verify_password(password, employee.password_hash): return templates.TemplateResponse("login.html", {"request": request, "error": "Mitarbeiternummer oder Passwort falsch."})
    login_user(request, employee); log_action(db, employee.employee_number, "login", "employees", str(employee.id), "Login")
    try:
        from app.routes.onboarding import _privacy_required
        if _privacy_required(employee, db): return RedirectResponse("/onboarding/privacy", status_code=303)
    except Exception: pass
    return RedirectResponse("/dashboard", status_code=303)

@router.get("/logout")
def logout(request: Request):
    logout_user(request); return RedirectResponse("/login", status_code=303)

@router.get("/password-forgot", response_class=HTMLResponse)
def password_forgot_form(request: Request):
    return templates.TemplateResponse("password_forgot.html", {"request": request, "message": None, "error": None})

@router.post("/password-forgot", response_class=HTMLResponse)
def password_forgot_submit(request: Request, identifier: str = Form(...), db: Session = Depends(get_db)):
    neutral_message = "Falls ein passender aktiver Mitarbeiter mit E-Mail-Adresse gefunden wurde, wurde ein Link zum Zurücksetzen des Passworts versendet."
    identifier = (identifier or "").strip(); employee = None
    if identifier: employee = db.query(Employee).filter(Employee.active == True, or_(Employee.email == identifier, Employee.employee_number == identifier)).first()
    if employee and not is_fixed_admin_employee(employee) and (employee.email or "").strip():
        raw_token = secrets.token_urlsafe(32); token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest(); expires_at = datetime.now() + timedelta(minutes=60)
        db.query(PasswordResetToken).filter(PasswordResetToken.employee_id == employee.id, PasswordResetToken.used_at.is_(None)).update({"used_at": datetime.now()})
        reset_token = PasswordResetToken(employee_id=employee.id, token_hash=token_hash, expires_at=expires_at, requested_ip=request.client.host if request.client else None); db.add(reset_token); db.commit()
        reset_url = str(request.url_for("password_reset_form", token=raw_token)); body = f"Hallo {employee.first_name} {employee.last_name},\n\nfür dein Stempeluhr-Konto wurde ein Zurücksetzen des Passworts angefordert.\n\nBitte öffne diesen Link, um ein neues Passwort zu vergeben:\n{reset_url}\n\nDer Link ist 60 Minuten gültig und kann nur einmal verwendet werden.\nFalls du diese Anfrage nicht gestellt hast, kannst du diese E-Mail ignorieren.\n\nViele Grüße\nStempeluhr"
        try: send_email_from_settings(db, employee.email.strip(), "Stempeluhr Passwort zurücksetzen", body); log_action(db, employee.employee_number, "password_reset_requested", "employees", str(employee.id), "Reset-Link per E-Mail versendet")
        except Exception as exc: reset_token.used_at = datetime.now(); db.commit(); log_action(db, employee.employee_number, "password_reset_mail_failed", "employees", str(employee.id), str(exc))
    return templates.TemplateResponse("password_forgot.html", {"request": request, "message": neutral_message, "error": None})

@router.get("/password-reset/{token}", response_class=HTMLResponse)
def password_reset_form(request: Request, token: str, db: Session = Depends(get_db)):
    token_hash = hashlib.sha256((token or "").encode("utf-8")).hexdigest(); reset_token = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == token_hash, PasswordResetToken.used_at.is_(None), PasswordResetToken.expires_at >= datetime.now()).first()
    if not reset_token: return templates.TemplateResponse("password_reset.html", {"request": request, "token": "", "error": "Dieser Link ist ungültig oder abgelaufen.", "message": None})
    return templates.TemplateResponse("password_reset.html", {"request": request, "token": token, "error": None, "message": None})

@router.post("/password-reset/{token}", response_class=HTMLResponse)
def password_reset_submit(request: Request, token: str, password: str = Form(...), password_repeat: str = Form(...), db: Session = Depends(get_db)):
    token_hash = hashlib.sha256((token or "").encode("utf-8")).hexdigest(); reset_token = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == token_hash, PasswordResetToken.used_at.is_(None), PasswordResetToken.expires_at >= datetime.now()).first()
    if not reset_token: return templates.TemplateResponse("password_reset.html", {"request": request, "token": "", "error": "Dieser Link ist ungültig oder abgelaufen.", "message": None})
    employee = db.query(Employee).filter(Employee.id == reset_token.employee_id, Employee.active == True).first()
    if not employee or is_fixed_admin_employee(employee): reset_token.used_at = datetime.now(); db.commit(); return templates.TemplateResponse("password_reset.html", {"request": request, "token": "", "error": "Dieser Link ist ungültig oder abgelaufen.", "message": None})
    password = password or ""; password_repeat = password_repeat or ""
    if password != password_repeat: return templates.TemplateResponse("password_reset.html", {"request": request, "token": token, "error": "Die Passwörter stimmen nicht überein.", "message": None})
    if len(password) < 8: return templates.TemplateResponse("password_reset.html", {"request": request, "token": token, "error": "Das Passwort muss mindestens 8 Zeichen lang sein.", "message": None})
    employee.password_hash = hash_password(password); employee.updated_at = datetime.now(); reset_token.used_at = datetime.now(); db.commit(); log_action(db, employee.employee_number, "password_reset_completed", "employees", str(employee.id), "Passwort per E-Mail-Reset geändert")
    return templates.TemplateResponse("password_reset.html", {"request": request, "token": "", "error": None, "message": "Dein Passwort wurde geändert. Du kannst dich jetzt anmelden."})

@router.get("/api/rfid-learn/status")
def rfid_learn_status(db: Session = Depends(get_db)): return JSONResponse(_get_pending_rfid_status(db))

def _rfid_employee(db, rfid_code):
    employee, medium = resolve_employee_by_rfid(db, rfid_code)
    return employee

@router.post("/raspberry/rfid-scan", response_class=HTMLResponse)
def raspberry_rfid_scan(request: Request, rfid_code: str = Form(""), db: Session = Depends(get_db)):
    rfid_code = (rfid_code or "").strip().replace("\r", "").replace("\n", "")
    if not rfid_code: return templates.TemplateResponse("message.html", {"request": request, "title": "Fehler", "message": "Kein RFID-Code erkannt.", "return_to": "/raspberry"})
    learn_response = _save_pending_rfid_from_terminal(request, db, rfid_code)
    if learn_response: return learn_response
    employee = _rfid_employee(db, rfid_code)
    if not employee or is_fixed_admin_employee(employee): return templates.TemplateResponse("rfid_unknown.html", {"request": request, "rfid_code": rfid_code, "message": "RFID unbekannt! Bitte Administrator informieren.", "return_to": "/raspberry"})
    entry_type = determine_auto_entry_type(db, employee.id); entry, duplicate_last = create_time_entry(db, employee, entry_type, "rfid_auto", "raspberry", "Automatische Buchung über Raspberry-Scan", duplicate_seconds=8)
    if duplicate_last: return templates.TemplateResponse("duplicate_booking.html", {"request": request, "employee": employee, "last": duplicate_last, "seconds": 8, "return_to": "/raspberry"})
    return templates.TemplateResponse("message.html", {"request": request, "title": "Automatisch gebucht", "message": f"{entry_type} für {employee.first_name} {employee.last_name} automatisch gebucht.", "return_to": "/raspberry", "status_display_seconds": status_display_seconds(db)})

@router.get("/raspberry", response_class=HTMLResponse)
def raspberry(request: Request, db: Session = Depends(get_db)):
    pending_rfid_employee = _get_pending_rfid_employee(db); settings = service_settings_dict(db)
    try: auto_delay_seconds = int(settings.get("booking_auto_delay_seconds", "3"))
    except Exception: auto_delay_seconds = 3
    auto_delay_seconds = max(1, min(auto_delay_seconds, 30))
    return templates.TemplateResponse("raspberry.html", {"request": request, "pending_rfid_employee": pending_rfid_employee, "auto_delay_seconds": auto_delay_seconds})

@router.post("/book_auto", response_class=HTMLResponse)
def book_auto(request: Request, rfid_code: str = Form(""), return_to: str = Form("/raspberry"), db: Session = Depends(get_db)):
    return_to = "/raspberry" if return_to == "/raspberry" else "/"; rfid_code = (rfid_code or "").strip().replace("\r", "").replace("\n", "")
    if not rfid_code: return templates.TemplateResponse("message.html", {"request": request, "title": "Fehler", "message": "Kein RFID-Code erkannt.", "return_to": return_to})
    if return_to == "/raspberry":
        learn_response = _save_pending_rfid_from_terminal(request, db, rfid_code)
        if learn_response: return learn_response
    employee = _rfid_employee(db, rfid_code)
    if not employee or is_fixed_admin_employee(employee): return templates.TemplateResponse("rfid_unknown.html", {"request": request, "rfid_code": rfid_code, "message": "RFID unbekannt! Bitte Administrator informieren.", "return_to": return_to})
    entry_type = determine_auto_entry_type(db, employee.id); terminal_name = "raspberry" if return_to == "/raspberry" else "dashboard"; entry, duplicate_last = create_time_entry(db, employee, entry_type, "rfid_auto", terminal_name, "Automatische Buchung nach 3 Sekunden ohne Auswahl", duplicate_seconds=8)
    if duplicate_last: return templates.TemplateResponse("duplicate_booking.html", {"request": request, "employee": employee, "last": duplicate_last, "seconds": 8, "return_to": return_to})
    return templates.TemplateResponse("message.html", {"request": request, "title": "Automatisch gebucht", "message": f"{entry_type} für {employee.first_name} {employee.last_name} automatisch gebucht.", "return_to": return_to, "status_display_seconds": status_display_seconds(db)})

@router.post("/book_auto_password", response_class=HTMLResponse)
def book_auto_password(request: Request, employee_number: str = Form(""), password: str = Form(""), return_to: str = Form("/dashboard"), db: Session = Depends(get_db)):
    return_to = return_to if return_to in ["/dashboard", "/"] else "/dashboard"; employee_number = normalize_employee_number(employee_number, get_employee_number_length(db)) if employee_number else ""
    if not employee_number or not password: return templates.TemplateResponse("message.html", {"request": request, "title": "Fehler", "message": "Mitarbeiternummer und Passwort sind erforderlich.", "return_to": return_to})
    employee = db.query(Employee).filter(Employee.employee_number == employee_number, Employee.active == True).first()
    if not employee or is_fixed_admin_employee(employee) or not verify_password(password, employee.password_hash): return templates.TemplateResponse("message.html", {"request": request, "title": "Fehler", "message": "Mitarbeiter oder Passwort falsch", "return_to": return_to})
    entry_type = determine_auto_entry_type(db, employee.id); entry, duplicate_last = create_time_entry(db, employee, entry_type, "password_auto", "quick_booking", "Automatische Schnellbuchung nach 3 Sekunden ohne manuelle Auswahl", duplicate_seconds=8)
    if duplicate_last: return templates.TemplateResponse("duplicate_booking.html", {"request": request, "employee": employee, "last": duplicate_last, "seconds": 8, "return_to": return_to})
    return templates.TemplateResponse("message.html", {"request": request, "title": "Automatisch gebucht", "message": f"{entry_type} für {employee.first_name} {employee.last_name} automatisch gebucht.", "return_to": return_to, "status_display_seconds": status_display_seconds(db)})

@router.post("/book", response_class=HTMLResponse)
def book(request: Request, entry_type: str = Form(...), rfid_code: str = Form(""), employee_number: str = Form(""), password: str = Form(""), return_to: str = Form("/"), manual_booking: str = Form("0"), db: Session = Depends(get_db)):
    rfid_code = (rfid_code or "").strip().replace("\r", "").replace("\n", ""); employee_number = normalize_employee_number(employee_number, get_employee_number_length(db)) if employee_number else ""; return_to = return_to if return_to in ["/raspberry", "/dashboard", "/"] else "/"
    if return_to == "/raspberry" and rfid_code:
        learn_response = _save_pending_rfid_from_terminal(request, db, rfid_code)
        if learn_response: return learn_response
    if entry_type not in VALID_ENTRY_TYPES: return templates.TemplateResponse("message.html", {"request": request, "title": "Fehler", "message": "Ungültiger Buchungstyp", "return_to": return_to})
    employee = None; method = "web"
    if rfid_code: employee = _rfid_employee(db, rfid_code); method = "rfid"
    if not employee and employee_number and password:
        employee = db.query(Employee).filter(Employee.employee_number == employee_number, Employee.active == True).first(); method = "password"
        if not employee or not verify_password(password, employee.password_hash): return templates.TemplateResponse("message.html", {"request": request, "title": "Fehler", "message": "Mitarbeiter oder Passwort falsch", "return_to": return_to})
        if return_to == "/dashboard" and str(manual_booking).lower() not in ["1", "true", "on", "ja"]: entry_type = determine_auto_entry_type(db, employee.id)
    if not employee and rfid_code: return templates.TemplateResponse("rfid_unknown.html", {"request": request, "rfid_code": rfid_code, "message": "RFID unbekannt! Bitte Administrator informieren.", "return_to": return_to})
    if not employee: return templates.TemplateResponse("message.html", {"request": request, "title": "Fehler", "message": "Mitarbeiter nicht gefunden", "return_to": return_to})
    entry, duplicate_last = create_time_entry(db, employee, entry_type, method, "web", duplicate_seconds=8)
    if duplicate_last: return templates.TemplateResponse("duplicate_booking.html", {"request": request, "employee": employee, "last": duplicate_last, "seconds": 8, "return_to": return_to})
    return templates.TemplateResponse("message.html", {"request": request, "title": "Gebucht", "message": f"{entry_type} für {employee.first_name} {employee.last_name} gebucht.", "return_to": return_to, "status_display_seconds": status_display_seconds(db)})
