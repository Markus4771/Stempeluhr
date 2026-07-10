from .common import *
import base64
import secrets
import re
import unicodedata

router = APIRouter()

def absence_calendar_slug_from_name(name: str) -> str:
    text = (name or "Abwesenheit").strip() or "Abwesenheit"
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().replace("ß", "ss")
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "abwesenheit"

def configured_absence_calendar_slug(settings: dict) -> str:
    saved = (settings.get("absence_calendar_slug") or "").strip()
    return saved or absence_calendar_slug_from_name(settings.get("absence_calendar_name") or "Abwesenheit")

def _check_absence_calendar_access(request: Request, settings: dict, token: str):
    expected = settings.get("caldav_vacation_feed_token", "")
    configured_user = (settings.get("absence_calendar_username", "") or "").strip()
    configured_password = settings.get("absence_calendar_password", "") or ""
    auth_enabled = str(settings.get("absence_calendar_auth_enabled", "0") or "0").lower() in ["1", "true", "on", "yes", "ja"]
    # 5.2.21: Wenn Benutzer und Passwort konfiguriert sind, wird Basic Auth auch ohne extra Haken verlangt.
    auth_enabled = auth_enabled or bool(configured_user and configured_password)
    if auth_enabled:
        header = request.headers.get("authorization", "")
        ok = False
        if header.lower().startswith("basic ") and configured_user and configured_password:
            try:
                decoded = base64.b64decode(header.split(" ", 1)[1]).decode("utf-8")
                supplied_user, supplied_password = decoded.split(":", 1)
                ok = secrets.compare_digest(supplied_user, configured_user) and secrets.compare_digest(supplied_password, configured_password)
            except Exception:
                ok = False
        if not ok and (not expected or token != expected):
            return PlainTextResponse("Unauthorized", status_code=401, headers={"WWW-Authenticate": 'Basic realm="Stempeluhr Abwesenheitskalender"'})
        return None
    if not expected or token != expected:
        return PlainTextResponse("Unauthorized", status_code=401)
    return None


def vacation_days_between(start_date, end_date, half_day=False):
    if end_date < start_date:
        return 0
    if half_day:
        return 0.5
    return float((end_date - start_date).days + 1)

def vacation_role_name(user):
    return user.role.name if user and user.role else ""

def is_vacation_admin(user):
    return vacation_role_name(user) in ["Administrator", "Personal"]

def is_teamleader(user):
    return vacation_role_name(user) == "Teamleiter"

def can_approve_vacation(user):
    return bool(user and vacation_role_name(user) in ["Administrator", "Personal", "Teamleiter"])

def teamleader_department_ids(db: Session, user):
    if not user:
        return []
    return [d.id for d in db.query(Department).filter(Department.manager_employee_id == user.id, Department.active == True).all()]

def vacation_request_query_for_user(db: Session, user, status: str = "offen"):
    query = db.query(VacationRequest).join(Employee, VacationRequest.employee_id == Employee.id)
    # 5.1.10: "offen" bedeutet alle Vorgänge, die eine Entscheidung benötigen.
    # Dadurch erscheinen Löschanträge direkt in der Genehmigungsliste.
    if status in (None, "", "alle"):
        pass
    elif status == "offen":
        query = query.filter(VacationRequest.status.in_(["beantragt", "offen", "Offen", "loeschung_beantragt"]))
    else:
        query = query.filter(VacationRequest.status == status)

    if is_vacation_admin(user):
        return query

    if is_teamleader(user):
        dept_ids = teamleader_department_ids(db, user)
        if not dept_ids:
            return query.filter(VacationRequest.id == -1)
        return query.filter(Employee.department_id.in_(dept_ids), Employee.id != user.id)

    return query.filter(VacationRequest.id == -1)

def can_decide_vacation_request(db: Session, user, vacation_request):
    if not user or not vacation_request:
        return False
    if is_vacation_admin(user):
        return True
    if is_teamleader(user):
        dept_ids = teamleader_department_ids(db, user)
        return bool(vacation_request.employee and vacation_request.employee.department_id in dept_ids and vacation_request.employee_id != user.id)
    return False

def notify_vacation(db: Session, subject: str, body: str, to_email: str | None):
    if not to_email:
        return
    try:
        send_email_from_settings(db, to_email, subject, body)
    except Exception:
        pass


def admin_teamlead_recipients(db: Session):
    """Empfänger für Systemwarnungen: Administrator, Personal und Teamleiter."""
    try:
        return (
            db.query(Employee)
            .join(Role, Employee.role_id == Role.id)
            .filter(Role.name.in_(["Administrator", "Personal", "Teamleiter"]), Employee.active == True)
            .all()
        )
    except Exception:
        return []


def notify_holiday_calendar_expiry(db: Session, latest_date, imported_count: int, actor: str = "system"):
    """Sendet optional eine Warnmail, wenn ein importierter Feiertagskalender bald abläuft."""
    settings = service_settings_dict(db)
    if settings.get("holiday_ics_expiry_warning_enabled", "0") not in ["1", "true", "on"]:
        return
    try:
        warn_days = int(settings.get("holiday_ics_warn_days", settings.get("holiday_ics_expiry_warn_days", "45")) or 45)
    except Exception:
        warn_days = 45
    warn_days = max(1, min(warn_days, 365))
    if latest_date and latest_date >= (datetime.now().date() + timedelta(days=warn_days)):
        return
    subject = "Stempeluhr: Feiertagskalender läuft ab"
    if latest_date:
        body = f"Der importierte Feiertagskalender enthält nur Termine bis {latest_date}. Bitte eine neue ICS-Datei importieren. Importierte Termine: {imported_count}."
    else:
        body = "Beim Feiertagskalender-Import wurden keine zukünftigen Termine gefunden. Bitte die ICS-Datei prüfen."
    sent = 0
    for emp in admin_teamlead_recipients(db):
        if not emp.email:
            continue
        notify_vacation(db, subject, body, emp.email)
        sent += 1
    log_action(db, actor, "holiday_ics_expiry_warning", "holidays", "ics", f"Warnung gesendet an {sent} Empfänger; letzter Termin: {latest_date}")


def import_holidays_from_ics_content(db: Session, content: bytes, source_name: str = "ICS", actor: str = "system"):
    """Importiert Feiertage aus einer ICS-Datei in die Holiday-Tabelle.

    5.2.12: Wiederkehrende ICS-Termine werden für das aktuelle und nächste Jahr
    expandiert. Dadurch funktionieren exportierte Kalender aus Nextcloud,
    Thunderbird und vielen Bundesland-ICS-Quellen zuverlässiger.
    """
    from icalendar import Calendar
    import recurring_ical_events
    cal = Calendar.from_ical(content)
    imported = 0
    updated = 0
    latest_date = None
    start = date(datetime.now().year, 1, 1)
    end = date(datetime.now().year + 2, 1, 1)
    try:
        components = recurring_ical_events.of(cal).between(start, end)
    except Exception:
        components = []
    if not components:
        components = [c for c in cal.walk() if c.name == "VEVENT"]
    for component in components:
        if component.name != "VEVENT":
            continue
        summary = str(component.get("summary") or component.get("SUMMARY") or "Feiertag").strip() or "Feiertag"
        dtstart = component.get("dtstart") or component.get("DTSTART")
        if not dtstart:
            continue
        value = dtstart.dt
        holiday_date = value.date() if isinstance(value, datetime) else value
        if not isinstance(holiday_date, date):
            continue
        latest_date = holiday_date if latest_date is None or holiday_date > latest_date else latest_date
        summary_lower = summary.lower()
        half_day = any(token in summary_lower for token in ["halb", "1/2", "halber"])
        exists = db.query(Holiday).filter(Holiday.date == holiday_date, Holiday.name == summary).first()
        if exists:
            exists.active = True
            exists.federal_state = source_name[:50] or "ICS"
            exists.half_day = half_day
            updated += 1
            continue
        db.add(Holiday(name=summary[:100], date=holiday_date, federal_state=source_name[:50] or "ICS", half_day=half_day, active=True))
        imported += 1
    service_set_setting(db, "holiday_ics_last_import", datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
    service_set_setting(db, "holiday_ics_last_status", f"{imported} neu, {updated} aktualisiert; letzter Termin: {latest_date or '-'}")
    db.commit()
    notify_holiday_calendar_expiry(db, latest_date, imported, actor)
    return imported, latest_date


def get_active_absence_types(db: Session):
    types = db.query(AbsenceType).filter(AbsenceType.active == True).order_by(AbsenceType.sort_order, AbsenceType.name).all()
    if not types:
        defaults = [
            ("Urlaub", "abwesenheit", True, False, 10),
            ("Krank", "krank", False, False, 20),
            ("Homeoffice", "homeoffice", True, False, 30),
            ("Dienstreise", "dienstreise", True, False, 40),
            ("Fortbildung", "fortbildung", True, False, 50),
            ("Berufsschule", "berufsschule", False, False, 60),
            ("Sonstiges", "sonstiges", True, True, 90),
        ]
        for name, code, requires_approval, requires_text, sort_order in defaults:
            db.add(AbsenceType(name=name, code=code, active=True, requires_approval=requires_approval, requires_text=requires_text, sort_order=sort_order))
        db.commit()
        types = db.query(AbsenceType).filter(AbsenceType.active == True).order_by(AbsenceType.sort_order, AbsenceType.name).all()
    return types

def vacation_form_context(request, user, db, error=None, vacation_request=None):
    return {
        "request": request,
        "user": user,
        "error": error,
        "absence_types": get_active_absence_types(db),
        "vacation_request": vacation_request,
    }


def can_employee_correct_absence(user, vacation_request):
    """Mitarbeiter duerfen eigene Abwesenheiten korrigieren, solange sie nicht storniert sind."""
    return bool(user and vacation_request and vacation_request.employee_id == user.id and vacation_request.status != "storniert")


def describe_vacation_change(old_values: dict, req) -> str:
    new_values = {
        "start_date": str(req.start_date),
        "end_date": str(req.end_date),
        "half_day": bool(req.half_day),
        "request_type": req.request_type,
        "custom_reason": req.custom_reason or "",
        "comment": req.comment or "",
        "days": req.days,
        "status": req.status,
    }
    changes = []
    labels = {
        "start_date": "Von",
        "end_date": "Bis",
        "half_day": "Halber Tag",
        "request_type": "Art",
        "custom_reason": "Beschreibung",
        "comment": "Kommentar",
        "days": "Tage",
        "status": "Status",
    }
    for key, old in old_values.items():
        new = new_values.get(key)
        if str(old) != str(new):
            changes.append(f"{labels.get(key, key)}: {old} -> {new}")
    return "; ".join(changes) or "Keine inhaltliche Aenderung"


def absence_calendar_name(db: Session) -> str:
    name = (service_get_setting(db, "absence_calendar_name", "Abwesenheit") or "").strip()
    return name or "Abwesenheit"


def absence_type_requires_approval(db: Session, code: str) -> bool:
    absence_type = db.query(AbsenceType).filter(AbsenceType.code == code).first()
    if absence_type is None:
        return True
    return bool(absence_type.requires_approval)


def absence_type_label_map(db: Session):
    """Liefert sprechende Namen fuer Abwesenheitsarten anhand des Codes."""
    labels = {
        "abwesenheit": "Urlaub",
        "urlaub": "Urlaub",
        "krank": "Krank",
        "homeoffice": "Homeoffice",
        "dienstreise": "Dienstreise",
        "fortbildung": "Fortbildung",
        "berufsschule": "Berufsschule",
        "sonstiges": "Sonstiges",
    }
    try:
        for absence_type in db.query(AbsenceType).all():
            if absence_type.code:
                labels[absence_type.code] = absence_type.name
    except Exception:
        pass
    return labels

def absence_reason_for_request(vacation_request, labels):
    base = labels.get(vacation_request.request_type, vacation_request.request_type or "Abwesenheit")
    if vacation_request.request_type == "sonstiges" and vacation_request.custom_reason:
        return f"{base}: {vacation_request.custom_reason}"
    return base

def employee_display_name(employee):
    if not employee:
        return "Unbekannt"
    return f"{employee.first_name or ''} {employee.last_name or ''}".strip() or getattr(employee, "employee_number", "Unbekannt")

def build_absence_calendar_days(start, end, requests, labels):
    days = []
    current = start
    while current < end:
        entries = []
        for req in requests:
            if req.start_date <= current <= req.end_date:
                employee_name = employee_display_name(req.employee)
                reason = absence_reason_for_request(req, labels)
                entries.append({
                    "employee_name": employee_name,
                    "reason": reason,
                    "start_date": req.start_date,
                    "end_date": req.end_date,
                    "days": req.days,
                    "half_day": req.half_day,
                    "comment": req.comment or "",
                    "decision_comment": req.decision_comment or "",
                    "status": req.status,
                })
        days.append({
            "date": current,
            "day": current.day,
            "weekday": current.weekday(),
            "entries": entries,
        })
        current += timedelta(days=1)
    # auf Wochen mit Montag als Wochenbeginn auffuellen
    leading = start.weekday()
    trailing = (7 - ((leading + len(days)) % 7)) % 7
    padded = ([None] * leading) + days + ([None] * trailing)
    return [padded[i:i+7] for i in range(0, len(padded), 7)]

@router.get("/vacation", response_class=HTMLResponse)
def vacation_home(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    my_requests = db.query(VacationRequest).filter(VacationRequest.employee_id == user.id).order_by(VacationRequest.id.desc()).limit(10).all()
    open_count = 0
    if can_approve_vacation(user):
        open_count = vacation_request_query_for_user(db, user, "beantragt").count()
        open_count += vacation_request_query_for_user(db, user, "loeschung_beantragt").count()

    return templates.TemplateResponse("vacation_home.html", {
        "request": request,
        "user": user,
        "my_requests": my_requests,
        "open_count": open_count,
        "can_approve": can_approve_vacation(user)
    })

@router.get("/vacation/request", response_class=HTMLResponse)
def vacation_request_form(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse("vacation_request.html", vacation_form_context(request, user, db))

@router.post("/vacation/request", response_class=HTMLResponse)
def vacation_request_save(
    request: Request,
    start_date: str = Form(...),
    end_date: str = Form(...),
    half_day: str = Form("off"),
    request_type: str = Form("abwesenheit"),
    custom_reason: str = Form(""),
    comment: str = Form(""),
    db: Session = Depends(get_db)
):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except Exception:
        return templates.TemplateResponse("vacation_request.html", vacation_form_context(request, user, db, "Datum ist ungültig."))

    if end < start:
        return templates.TemplateResponse("vacation_request.html", vacation_form_context(request, user, db, "Bis-Datum darf nicht vor Von-Datum liegen."))

    absence_type = db.query(AbsenceType).filter(AbsenceType.code == request_type, AbsenceType.active == True).first()
    if not absence_type:
        return templates.TemplateResponse("vacation_request.html", vacation_form_context(request, user, db, "Bitte eine gültige Abwesenheitsart auswählen."))

    custom_reason_clean = custom_reason.strip()
    if absence_type.requires_text:
        if len(custom_reason_clean) < 5:
            return templates.TemplateResponse("vacation_request.html", vacation_form_context(request, user, db, "Bitte eine Beschreibung mit mindestens 5 Zeichen angeben."))
        if len(custom_reason_clean) > 500:
            return templates.TemplateResponse("vacation_request.html", vacation_form_context(request, user, db, "Die Beschreibung darf maximal 500 Zeichen lang sein."))
    else:
        custom_reason_clean = ""

    days = vacation_days_between(start, end, half_day == "on")

    req = VacationRequest(
        employee_id=user.id,
        start_date=start,
        end_date=end,
        days=days,
        half_day=half_day == "on",
        request_type=request_type,
        custom_reason=custom_reason_clean or None,
        status="beantragt",
        comment=comment.strip() or None
    )
    db.add(req)
    db.commit()
    log_details = f"{start} bis {end}, Art: {request_type}"
    if custom_reason_clean:
        log_details += f", Sonstiges: {custom_reason_clean[:120]}"
    log_action(db, user.employee_number, "vacation_requested", "vacation_requests", str(req.id), log_details)

    try:
        recipients = db.query(Employee).join(Role, Employee.role_id == Role.id).filter(Role.name.in_(["Administrator", "Personal"]), Employee.active == True).all()
        if user.department_id:
            dept = db.query(Department).filter(Department.id == user.department_id).first()
            if dept and dept.manager_employee_id:
                manager = db.query(Employee).filter(Employee.id == dept.manager_employee_id, Employee.active == True).first()
                if manager:
                    recipients.append(manager)
        seen = set()
        for r in recipients:
            if not r.email or r.id in seen:
                continue
            seen.add(r.id)
            mail_body = f"{user.first_name} {user.last_name} hat Abwesenheit beantragt: {start} bis {end}. Art: {request_type}"
            if custom_reason_clean:
                mail_body += f". Beschreibung: {custom_reason_clean}"
            notify_vacation(db, "Neuer Abwesenheitsantrag", mail_body, r.email)
    except Exception:
        pass

    return RedirectResponse("/vacation/my", status_code=303)

@router.get("/vacation/my", response_class=HTMLResponse)
def vacation_my(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    requests = db.query(VacationRequest).filter(VacationRequest.employee_id == user.id).order_by(VacationRequest.id.desc()).all()
    return templates.TemplateResponse("vacation_my.html", {"request": request, "user": user, "requests": requests, "absence_labels": absence_type_label_map(db)})


@router.get("/vacation/{request_id}/edit", response_class=HTMLResponse)
def vacation_edit_form(request_id: int, request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    req = db.query(VacationRequest).filter(VacationRequest.id == request_id).first()
    if not can_employee_correct_absence(user, req):
        log_action(db, getattr(user, "employee_number", ""), "vacation_correction_denied", "vacation_requests", str(request_id), "Keine Berechtigung oder Antrag storniert")
        return RedirectResponse("/vacation/my", status_code=303)
    return templates.TemplateResponse("vacation_edit.html", vacation_form_context(request, user, db, vacation_request=req))


@router.post("/vacation/{request_id}/edit", response_class=HTMLResponse)
def vacation_edit_save(
    request_id: int,
    request: Request,
    start_date: str = Form(...),
    end_date: str = Form(...),
    half_day: str = Form("off"),
    request_type: str = Form("abwesenheit"),
    custom_reason: str = Form(""),
    comment: str = Form(""),
    correction_reason: str = Form(""),
    db: Session = Depends(get_db),
):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    req = db.query(VacationRequest).filter(VacationRequest.id == request_id).first()
    if not can_employee_correct_absence(user, req):
        log_action(db, getattr(user, "employee_number", ""), "vacation_correction_denied", "vacation_requests", str(request_id), "Keine Berechtigung oder Antrag storniert")
        return RedirectResponse("/vacation/my", status_code=303)

    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except Exception:
        return templates.TemplateResponse("vacation_edit.html", vacation_form_context(request, user, db, "Datum ist ungültig.", req))
    if end < start:
        return templates.TemplateResponse("vacation_edit.html", vacation_form_context(request, user, db, "Bis-Datum darf nicht vor Von-Datum liegen.", req))

    absence_type = db.query(AbsenceType).filter(AbsenceType.code == request_type, AbsenceType.active == True).first()
    if not absence_type:
        return templates.TemplateResponse("vacation_edit.html", vacation_form_context(request, user, db, "Bitte eine gültige Abwesenheitsart auswählen.", req))

    custom_reason_clean = custom_reason.strip()
    if absence_type.requires_text:
        if len(custom_reason_clean) < 5:
            return templates.TemplateResponse("vacation_edit.html", vacation_form_context(request, user, db, "Bitte eine Beschreibung mit mindestens 5 Zeichen angeben.", req))
        if len(custom_reason_clean) > 500:
            return templates.TemplateResponse("vacation_edit.html", vacation_form_context(request, user, db, "Die Beschreibung darf maximal 500 Zeichen lang sein.", req))
    else:
        custom_reason_clean = ""

    old_values = {
        "start_date": str(req.start_date),
        "end_date": str(req.end_date),
        "half_day": bool(req.half_day),
        "request_type": req.request_type,
        "custom_reason": req.custom_reason or "",
        "comment": req.comment or "",
        "days": req.days,
        "status": req.status,
    }
    old_status = req.status

    req.start_date = start
    req.end_date = end
    req.half_day = half_day == "on"
    req.days = vacation_days_between(start, end, req.half_day)
    req.request_type = request_type
    req.custom_reason = custom_reason_clean or None
    req.comment = comment.strip() or None

    # Wenn eine bereits genehmigte Abwesenheit korrigiert wird und die Art eine Genehmigung braucht,
    # wird sie wieder zur Freigabe vorgelegt. Nicht genehmigungspflichtige Arten bleiben genehmigt.
    if old_status == "genehmigt" and absence_type.requires_approval:
        req.status = "beantragt"
        req.decision_comment = None
        req.decided_at = None
        req.decided_by = None

    db.commit()
    details = describe_vacation_change(old_values, req)
    reason = (correction_reason or "").strip()
    if reason:
        details += f"; Korrekturgrund: {reason[:500]}"
    log_action(db, user.employee_number, "vacation_corrected_by_employee", "vacation_requests", str(req.id), details)

    try:
        recipients = db.query(Employee).join(Role, Employee.role_id == Role.id).filter(Role.name.in_(["Administrator", "Personal"]), Employee.active == True).all()
        if user.department_id:
            dept = db.query(Department).filter(Department.id == user.department_id).first()
            if dept and dept.manager_employee_id:
                manager = db.query(Employee).filter(Employee.id == dept.manager_employee_id, Employee.active == True).first()
                if manager:
                    recipients.append(manager)
        seen = set()
        for r in recipients:
            if r.email and r.email not in seen:
                seen.add(r.email)
                notify_vacation(db, "Abwesenheit korrigiert", f"{employee_display_name(user)} hat eine Abwesenheit korrigiert: {details}", r.email)
    except Exception:
        pass

    return RedirectResponse("/vacation/my", status_code=303)


@router.get("/vacation/{request_id}/delete", response_class=HTMLResponse)
def vacation_delete_form(request_id: int, request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    req = db.query(VacationRequest).filter(VacationRequest.id == request_id).first()
    if not can_employee_correct_absence(user, req):
        log_action(db, getattr(user, "employee_number", ""), "vacation_delete_denied", "vacation_requests", str(request_id), "Keine Berechtigung oder Antrag storniert")
        return RedirectResponse("/vacation/my", status_code=303)
    return templates.TemplateResponse("vacation_delete.html", {
        "request": request,
        "user": user,
        "vacation_request": req,
        "absence_labels": absence_type_label_map(db),
        "requires_approval": req.status == "genehmigt",
        "error": None,
    })


@router.post("/vacation/{request_id}/delete", response_class=HTMLResponse)
def vacation_delete_save(
    request_id: int,
    request: Request,
    delete_reason: str = Form(""),
    db: Session = Depends(get_db),
):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    req = db.query(VacationRequest).filter(VacationRequest.id == request_id).first()
    if not can_employee_correct_absence(user, req):
        log_action(db, getattr(user, "employee_number", ""), "vacation_delete_denied", "vacation_requests", str(request_id), "Keine Berechtigung oder Antrag storniert")
        return RedirectResponse("/vacation/my", status_code=303)
    reason = (delete_reason or "").strip()
    if req.status == "genehmigt" and len(reason) < 5:
        return templates.TemplateResponse("vacation_delete.html", {
            "request": request,
            "user": user,
            "vacation_request": req,
            "absence_labels": absence_type_label_map(db),
            "requires_approval": True,
            "error": "Bitte einen Löschgrund mit mindestens 5 Zeichen angeben.",
        })
    before = f"{req.start_date} bis {req.end_date}, Art={req.request_type}, Status={req.status}, Tage={req.days}"
    if req.status == "genehmigt":
        req.status = "loeschung_beantragt"
        req.decision_comment = f"Löschantrag Mitarbeiter: {reason}"
        details = f"Löschung beantragt; Vorher: {before}; Grund: {reason}"
        log_action(db, user.employee_number, "vacation_delete_requested", "vacation_requests", str(req.id), details)
        try:
            for emp in admin_teamlead_recipients(db):
                notify_vacation(db, "Löschantrag Abwesenheit", f"{employee_display_name(user)} hat die Löschung einer genehmigten Abwesenheit beantragt.\n{before}\nGrund: {reason}", emp.email)
        except Exception:
            pass
    else:
        req.status = "storniert"
        req.decision_comment = f"Vom Mitarbeiter gelöscht: {reason or 'ohne Angabe'}"
        req.decided_at = datetime.now()
        req.decided_by = user.employee_number
        details = f"Direkt gelöscht/storniert; Vorher: {before}; Grund: {reason or 'ohne Angabe'}"
        log_action(db, user.employee_number, "vacation_deleted_by_employee", "vacation_requests", str(req.id), details)
    db.commit()
    return RedirectResponse("/vacation/my", status_code=303)


@router.get("/vacation/approvals", response_class=HTMLResponse)
def vacation_approvals(request: Request, status: str = "offen", db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not can_approve_vacation(user):
        return RedirectResponse("/login", status_code=303)
    query = vacation_request_query_for_user(db, user, status)
    requests = query.order_by(VacationRequest.id.desc()).all()
    return templates.TemplateResponse("vacation_approvals.html", {
        "request": request,
        "user": user,
        "requests": requests,
        "status": status,
        "is_teamleader_view": is_teamleader(user) and not is_vacation_admin(user)
    })

@router.post("/vacation/approvals/{request_id}/decide")
def vacation_decide(
    request_id: int,
    request: Request,
    decision: str = Form(...),
    decision_comment: str = Form(""),
    db: Session = Depends(get_db)
):
    user = current_user(request, db)
    if not can_approve_vacation(user):
        return RedirectResponse("/login", status_code=303)

    req = db.query(VacationRequest).filter(VacationRequest.id == request_id).first()
    if not req:
        return RedirectResponse("/vacation/approvals?status=offen", status_code=303)

    if not can_decide_vacation_request(db, user, req):
        log_action(db, user.employee_number, "vacation_decision_denied", "vacation_requests", str(req.id), "Keine Berechtigung für diesen Mitarbeiter")
        return RedirectResponse("/vacation/approvals?status=offen", status_code=303)

    if decision not in ["genehmigt", "abgelehnt", "storniert"]:
        return RedirectResponse("/vacation/approvals?status=offen", status_code=303)

    old_status = req.status
    clean_comment = decision_comment.strip() or None

    if old_status == "loeschung_beantragt":
        if decision == "genehmigt":
            req.status = "storniert"
            req.decision_comment = f"Löschung genehmigt: {clean_comment or ''}".strip()
            action = "vacation_delete_approved"
            mail_subject = "Löschung der Abwesenheit genehmigt"
            mail_body = f"Dein Löschantrag für die Abwesenheit vom {req.start_date} bis {req.end_date} wurde genehmigt.\n{clean_comment or ''}"
        elif decision == "abgelehnt":
            req.status = "genehmigt"
            req.decision_comment = f"Löschung abgelehnt: {clean_comment or ''}".strip()
            action = "vacation_delete_rejected"
            mail_subject = "Löschung der Abwesenheit abgelehnt"
            mail_body = f"Dein Löschantrag für die Abwesenheit vom {req.start_date} bis {req.end_date} wurde abgelehnt.\n{clean_comment or ''}"
        else:
            return RedirectResponse("/vacation/approvals?status=offen", status_code=303)
        req.decided_at = datetime.now()
        req.decided_by = user.employee_number
        db.commit()
        log_action(db, user.employee_number, action, "vacation_requests", str(req.id), f"Vorher: {old_status}; Neu: {req.status}; Kommentar: {clean_comment or ''}")
        notify_vacation(db, mail_subject, mail_body, req.employee.email)
        return RedirectResponse("/vacation/approvals?status=offen", status_code=303)

    req.status = decision
    req.decision_comment = clean_comment
    req.decided_at = datetime.now()
    req.decided_by = user.employee_number

    if req.request_type == "abwesenheit":
        sync_employee_vacation_balance(db, req.employee)

    db.commit()
    log_action(db, user.employee_number, f"vacation_{decision}", "vacation_requests", str(req.id), clean_comment or "")

    notify_vacation(db, f"Abwesenheitsantrag {decision}", f"Dein Antrag vom {req.start_date} bis {req.end_date} wurde {decision}.\n{clean_comment or ''}", req.employee.email)

    return RedirectResponse("/vacation/approvals?status=offen", status_code=303)

@router.get("/vacation/calendar", response_class=HTMLResponse)
def vacation_calendar(request: Request, year: int = 0, month: int = 0, department_id: int = 0, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    today = datetime.now().date()
    year = year or today.year
    month = month or today.month
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)

    query = db.query(VacationRequest).filter(VacationRequest.status == "genehmigt", VacationRequest.start_date < end, VacationRequest.end_date >= start)

    if department_id:
        query = query.join(Employee, VacationRequest.employee_id == Employee.id).filter(Employee.department_id == department_id)

    requests = query.order_by(VacationRequest.start_date).all()
    holidays = db.query(Holiday).filter(Holiday.date >= start, Holiday.date < end, Holiday.active == True).order_by(Holiday.date).all()
    departments = db.query(Department).order_by(Department.name).all() if "Department" in globals() else []
    absence_labels = absence_type_label_map(db)
    calendar_weeks = build_absence_calendar_days(start, end, requests, absence_labels)

    return templates.TemplateResponse("vacation_calendar.html", {
        "request": request,
        "user": user,
        "requests": requests,
        "holidays": holidays,
        "departments": departments,
        "employee_number_length": get_employee_number_length(db),
        "year": year,
        "month": month,
        "department_id": department_id,
        "absence_labels": absence_labels,
        "calendar_weeks": calendar_weeks,
        "absence_calendar_name": absence_calendar_name(db)
    })

@router.get("/vacation/balance", response_class=HTMLResponse)
def vacation_balance(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    employees = db.query(Employee).filter(Employee.active == True).order_by(Employee.last_name, Employee.first_name).all() if can_approve_vacation(user) else [user]
    for employee in employees:
        sync_employee_vacation_balance(db, employee)
    db.commit()
    return templates.TemplateResponse("vacation_balance.html", {"request": request, "user": user, "employees": employees})

@router.get("/system/settings/caldav", response_class=HTMLResponse)
def system_caldav_settings(request: Request, db: Session = Depends(get_db)):
    # 5.2.17: Die aktive CalDAV-Konfiguration liegt in der getrennten
    # Kontenverwaltung. Der alte Dialog bleibt intern für bestehende POST-
    # Kompatibilität erhalten, wird aber nicht mehr direkt geöffnet.
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    return RedirectResponse("/system/settings/caldav/accounts", status_code=303)



@router.get("/system/settings/caldav/help", response_class=HTMLResponse)
def system_caldav_help(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    settings = service_settings_dict(db)
    feed_token = settings.get("caldav_vacation_feed_token", "")
    feed_url = f"/calendar/vacation.ics?token={feed_token}" if feed_token else "/calendar/vacation.ics?token=..."
    return templates.TemplateResponse("system_caldav_help.html", {
        "request": request,
        "user": user,
        "settings": settings,
        "feed_url": feed_url,
    })

@router.post("/system/settings/caldav", response_class=HTMLResponse)
def system_caldav_settings_save(
    request: Request,
    caldav_enabled: str = Form("off"),
    caldav_url: str = Form(""),
    caldav_username: str = Form(""),
    caldav_password: str = Form(""),
    caldav_holiday_calendar_url: str = Form(""),
    caldav_holidays_enabled: str = Form("off"),
    caldav_holiday_sync_interval_hours: int = Form(24),
    caldav_holidays_affect_target_hours: str = Form("off"),
    caldav_half_day_factor: str = Form("0.5"),
    caldav_vacation_calendar_url: str = Form(""),
    absence_calendar_name: str = Form("Abwesenheit"),
    caldav_vacation_feed_token: str = Form(""),
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

    token = caldav_vacation_feed_token.strip() or str(uuid4())

    set_setting("caldav_enabled", "true" if caldav_enabled == "on" else "false")
    set_setting("caldav_url", caldav_url.strip())
    set_setting("caldav_username", caldav_username.strip())
    if caldav_password:
        set_setting("caldav_password", caldav_password)
    set_setting("caldav_holiday_calendar_url", caldav_holiday_calendar_url.strip())
    set_setting("caldav_holidays_enabled", "true" if caldav_holidays_enabled == "on" else "false")
    set_setting("caldav_holiday_sync_interval_hours", max(1, int(caldav_holiday_sync_interval_hours or 24)))
    set_setting("caldav_holidays_affect_target_hours", "true" if caldav_holidays_affect_target_hours == "on" else "false")
    set_setting("caldav_half_day_factor", caldav_half_day_factor.strip() or "0.5")
    set_setting("caldav_vacation_calendar_url", caldav_vacation_calendar_url.strip())
    clean_absence_name = absence_calendar_name.strip() or "Abwesenheit"
    set_setting("absence_calendar_name", clean_absence_name)
    set_setting("absence_calendar_slug", absence_calendar_slug_from_name(clean_absence_name))
    set_setting("caldav_vacation_feed_token", token)

    db.commit()
    log_action(db, user.employee_number, "caldav_settings_updated", "settings", "caldav", caldav_url)

    settings = service_settings_dict(db)
    return templates.TemplateResponse("system_caldav.html", {
        "request": request,
        "user": user,
        "settings": settings,
        "saved": True,
        "message": "CalDAV-Einstellungen gespeichert.",
        "error": None
    })

@router.post("/system/settings/caldav/import-holidays", response_class=HTMLResponse)
def system_caldav_import_holidays(
    request: Request,
    import_year: int = Form(0),
    db: Session = Depends(get_db)
):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect

    year = import_year or datetime.now().year
    message = None
    error = None

    try:
        count = import_holidays_from_caldav(db, year)
        message = f"{count} Feiertage für {year} importiert."
        log_action(db, user.employee_number, "caldav_holidays_imported", "holidays", str(year), message)
    except Exception as exc:
        error = f"Feiertagsimport fehlgeschlagen: {exc}"
        log_action(db, user.employee_number, "caldav_holidays_import_failed", "holidays", str(year), str(exc))

    settings = service_settings_dict(db)
    return templates.TemplateResponse("system_caldav.html", {
        "request": request,
        "user": user,
        "settings": settings,
        "saved": False,
        "message": message,
        "error": error
    })

@router.post("/system/settings/caldav/import-holidays-ics", response_class=HTMLResponse)
async def system_caldav_import_holidays_ics(
    request: Request,
    ics_file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    settings = service_settings_dict(db)
    if settings.get("holiday_ics_import_enabled", "1") not in ["1", "true", "on"]:
        return templates.TemplateResponse("system_caldav.html", {
            "request": request, "user": user, "settings": settings, "saved": False, "message": None,
            "error": "ICS-Feiertagsimport ist in den Allgemeinen Einstellungen deaktiviert."
        })
    filename = (ics_file.filename or "feiertage.ics").lower()
    if not filename.endswith(".ics"):
        return templates.TemplateResponse("system_caldav.html", {
            "request": request, "user": user, "settings": settings, "saved": False, "message": None,
            "error": "Bitte eine .ics-Datei auswählen."
        })
    try:
        content = await ics_file.read()
        count, latest = import_holidays_from_ics_content(db, content, source_name="ICS", actor=user.employee_number)
        msg = f"{count} Feiertage aus ICS importiert."
        if latest:
            msg += f" Letzter Termin: {latest}."
        log_action(db, user.employee_number, "holiday_ics_imported", "holidays", filename, msg)
        settings = service_settings_dict(db)
        return templates.TemplateResponse("system_caldav.html", {
            "request": request, "user": user, "settings": settings, "saved": False, "message": msg, "error": None
        })
    except Exception as exc:
        log_action(db, user.employee_number, "holiday_ics_import_failed", "holidays", filename, str(exc))
        return templates.TemplateResponse("system_caldav.html", {
            "request": request, "user": user, "settings": settings, "saved": False, "message": None,
            "error": f"ICS-Import fehlgeschlagen: {exc}"
        })


@router.api_route("/calendar/{calendar_slug}.ics", methods=["POST", "PUT", "PATCH", "DELETE"])
def absence_calendar_feed_write_disabled(calendar_slug: str, token: str = "", db: Session = Depends(get_db)):
    # Dieser Kalender ist ein Nur-Lese-Export. Schreibversuche sollen keine sichtbare Fehlermeldung erzeugen.
    try:
        log_action(db, "system", "absence_calendar_write_ignored", "calendar", f"{calendar_slug}.ics", "Schreibversuch auf Nur-Lese-Abwesenheit still ignoriert")
    except Exception:
        pass
    return PlainTextResponse("", status_code=204)


@router.get("/calendar/{calendar_slug}.ics")
def absence_calendar_feed(calendar_slug: str, request: Request, token: str = "", db: Session = Depends(get_db)):
    settings = service_settings_dict(db)
    configured_slug = configured_absence_calendar_slug(settings)
    # 5.2.21: /calendar/vacation.ics bleibt nur als Altlink kompatibel, die Konfiguration zeigt den freien Namen.
    if calendar_slug not in [configured_slug, "vacation"]:
        return PlainTextResponse("Kalender nicht gefunden", status_code=404)
    denied = _check_absence_calendar_access(request, settings, token)
    if denied:
        return denied
    ics = build_vacation_ical(db)
    return PlainTextResponse(
        ics,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f"inline; filename={configured_slug}.ics"},
    )


@router.get("/system/settings/caldav/test-vacation-ics", response_class=HTMLResponse)
def system_caldav_test_vacation_ics(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    settings = service_settings_dict(db)
    try:
        ics = build_vacation_ical(db)
        ok = "BEGIN:VCALENDAR" in ics and "END:VCALENDAR" in ics
        message = "ICS-Test erfolgreich. Thunderbird-Link ist gültig." if ok else "ICS-Test fehlgeschlagen: Kalenderstruktur unvollständig."
        error = None if ok else message
        if ok:
            service_set_setting(db, "caldav_vacation_ics_last_status", "OK")
        else:
            service_set_setting(db, "caldav_vacation_ics_last_status", message)
        db.commit()
        settings = service_settings_dict(db)
        return templates.TemplateResponse("system_caldav.html", {"request": request, "user": user, "settings": settings, "saved": False, "message": message if ok else None, "error": error})
    except Exception as exc:
        service_set_setting(db, "caldav_vacation_ics_last_status", f"Fehler: {exc}")
        db.commit()
        settings = service_settings_dict(db)
        return templates.TemplateResponse("system_caldav.html", {"request": request, "user": user, "settings": settings, "saved": False, "message": None, "error": f"ICS-Test fehlgeschlagen: {exc}"})


# ---------------------------------------------------------------------------
# Plausibilitätsprüfung
# ---------------------------------------------------------------------------
