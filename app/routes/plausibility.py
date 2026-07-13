from .common import *
from urllib.parse import urlencode

router = APIRouter()


def _plausibility_return_url(employee_id: int = 0, status: str = "offen", date_from: str = "", date_to: str = "") -> str:
    query = urlencode({
        "employee_id": int(employee_id or 0),
        "status": status or "offen",
        "date_from": date_from or "",
        "date_to": date_to or "",
    })
    return f"/plausibility?{query}"


@router.get("/plausibility", response_class=HTMLResponse)
def plausibility_view(
    request: Request,
    employee_id: int = 0,
    status: str = "offen",
    date_from: str = "",
    date_to: str = "",
    db: Session = Depends(get_db),
):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    visible_ids = report_visible_employee_ids(db, user)
    if employee_id and employee_id not in visible_ids:
        employee_id = user.id
    today = date.today()
    try:
        start_day = datetime.strptime(date_from, "%Y-%m-%d").date() if date_from else today - timedelta(days=7)
        end_day = datetime.strptime(date_to, "%Y-%m-%d").date() if date_to else today
    except Exception:
        start_day = today - timedelta(days=7)
        end_day = today
    q = db.query(PlausibilityIssue).join(Employee, PlausibilityIssue.employee_id == Employee.id)
    if visible_ids:
        q = q.filter(PlausibilityIssue.employee_id.in_(visible_ids))
    else:
        q = q.filter(PlausibilityIssue.id == -1)
    if employee_id:
        q = q.filter(PlausibilityIssue.employee_id == employee_id)
    if status and status != "alle":
        q = q.filter(PlausibilityIssue.status == status)
    q = q.filter(PlausibilityIssue.issue_date >= start_day, PlausibilityIssue.issue_date <= end_day)
    employees = db.query(Employee).filter(Employee.id.in_(visible_ids)).order_by(Employee.last_name, Employee.first_name).all() if visible_ids else []
    return templates.TemplateResponse("plausibility.html", {
        "request": request,
        "user": user,
        "issues": q.order_by(PlausibilityIssue.issue_date.desc(), Employee.last_name).all(),
        "employees": employees,
        "filters": {"employee_id": employee_id, "status": status, "date_from": start_day.isoformat(), "date_to": end_day.isoformat()},
    })


@router.post("/plausibility/run", response_class=HTMLResponse)
def plausibility_run(request: Request, day: str = Form(""), db: Session = Depends(get_db)):
    user, redirect = require_admin_response(request, db)
    if redirect:
        return redirect
    try:
        scan_day_value = datetime.strptime(day, "%Y-%m-%d").date() if day else date.today()
    except Exception:
        scan_day_value = date.today()
    issues = scan_day(db, scan_day_value, send_employee_mail=False)
    log_action(db, user.employee_number, "plausibility_manual_run", "plausibility", scan_day_value.isoformat(), f"{len(issues)} Auffälligkeiten")
    return templates.TemplateResponse("message.html", {"request": request, "user": user, "title": "Plausibilitätsprüfung", "message": f"Prüfung für {scan_day_value.strftime('%d.%m.%Y')} ausgeführt. Auffälligkeiten: {len(issues)}", "return_to": "/plausibility"})


@router.post("/plausibility/teamlead-summary", response_class=HTMLResponse)
def plausibility_teamlead_summary(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_admin_response(request, db)
    if redirect:
        return redirect
    count = teamlead_summary(db, date.today())
    log_action(db, user.employee_number, "plausibility_teamlead_summary_manual", "plausibility", "today", f"{count} E-Mails")
    return templates.TemplateResponse("message.html", {"request": request, "user": user, "title": "Teamleiter-Mail", "message": f"Teamleiter-Zusammenfassung gesendet: {count} E-Mail(s).", "return_to": "/plausibility"})


@router.post("/plausibility/daily-mail-test", response_class=HTMLResponse)
def plausibility_daily_mail_test(request: Request, day: str = Form(""), db: Session = Depends(get_db)):
    user, redirect = require_admin_response(request, db)
    if redirect:
        return redirect
    try:
        run_day = datetime.strptime(day, "%Y-%m-%d").date() if day else date.today()
    except Exception:
        run_day = date.today()
    result = dispatch_daily_plausibility_mails(db, run_day)
    log_action(db, user.employee_number, "plausibility_daily_mail_test", "plausibility", run_day.isoformat(), str(result))
    return templates.TemplateResponse("message.html", {"request": request, "user": user, "title": "Plausibilitäts-Mail", "message": f"Tagesversand ausgeführt: {result}", "return_to": "/plausibility/mail-history"})


@router.get("/plausibility/mail-history", response_class=HTMLResponse)
def plausibility_mail_history(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_admin_response(request, db)
    if redirect:
        return redirect
    rows = db.query(MailDispatchLog).filter(MailDispatchLog.dispatch_type.like("plausibility%"))
    rows = rows.order_by(MailDispatchLog.created_at.desc()).limit(200).all()
    return templates.TemplateResponse("plausibility_mail_history.html", {"request": request, "user": user, "rows": rows})


@router.post("/plausibility/{issue_id}/status", response_class=HTMLResponse)
def plausibility_status(
    issue_id: int,
    request: Request,
    new_status: str = Form(...),
    comment: str = Form(""),
    filter_employee_id: int = Form(0),
    filter_status: str = Form("offen"),
    filter_date_from: str = Form(""),
    filter_date_to: str = Form(""),
    db: Session = Depends(get_db),
):
    user = current_user(request, db)
    return_to = _plausibility_return_url(filter_employee_id, filter_status, filter_date_from, filter_date_to)
    if not user:
        return RedirectResponse("/login", status_code=303)
    issue = db.query(PlausibilityIssue).filter(PlausibilityIssue.id == issue_id).first()
    if not issue or issue.employee_id not in report_visible_employee_ids(db, user):
        return templates.TemplateResponse("message.html", {"request": request, "user": user, "title": "Keine Berechtigung", "message": "Diese Auffälligkeit kann nicht bearbeitet werden.", "return_to": return_to})
    if new_status not in ["offen", "geprueft", "erledigt", "ignoriert"]:
        new_status = "geprueft"
    issue.status = new_status
    issue.comment = comment.strip() or issue.comment
    issue.updated_at = datetime.now()
    if new_status in ["erledigt", "ignoriert"]:
        issue.resolved_at = datetime.now()
        issue.resolved_by = user.employee_number
    else:
        issue.resolved_at = None
        issue.resolved_by = None
    db.commit()
    log_action(db, user.employee_number, "plausibility_status_changed", "plausibility", str(issue.id), f"{new_status}: {comment}")
    return RedirectResponse(return_to, status_code=303)


@router.get("/system/settings/plausibility", response_class=HTMLResponse)
def system_plausibility_settings(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    ensure_plausibility_settings(db)
    return templates.TemplateResponse("system_settings_plausibility.html", {"request": request, "user": user, "settings": service_settings_dict(db), "saved": False})


@router.post("/system/settings/plausibility", response_class=HTMLResponse)
def system_plausibility_settings_save(
    request: Request,
    plausibility_enabled: str = Form("off"),
    plausibility_daily_time: str = Form("18:30"),
    plausibility_email_enabled: str = Form("off"),
    plausibility_employee_email_enabled: str = Form("off"),
    plausibility_teamlead_email_enabled: str = Form("off"),
    plausibility_max_daily_hours: str = Form("10"),
    plausibility_warn_daily_hours: str = Form("9"),
    plausibility_earliest_come: str = Form("05:00"),
    plausibility_latest_leave: str = Form("22:00"),
    plausibility_duplicate_minutes: str = Form("5"),
    plausibility_check_missing_leave: str = Form("off"),
    plausibility_check_missing_workday: str = Form("off"),
    plausibility_check_absence_booking: str = Form("off"),
    plausibility_check_duplicates: str = Form("off"),
    plausibility_check_boundaries: str = Form("off"),
    plausibility_check_breaks_if_auto_disabled: str = Form("off"),
    plausibility_break_min_6h_minutes: str = Form("30"),
    plausibility_break_min_9h_minutes: str = Form("45"),
    db: Session = Depends(get_db),
):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    bools = {
        "plausibility_enabled": plausibility_enabled,
        "plausibility_email_enabled": plausibility_email_enabled,
        "plausibility_employee_email_enabled": plausibility_employee_email_enabled,
        "plausibility_teamlead_email_enabled": plausibility_teamlead_email_enabled,
        "plausibility_check_missing_leave": plausibility_check_missing_leave,
        "plausibility_check_missing_workday": plausibility_check_missing_workday,
        "plausibility_check_absence_booking": plausibility_check_absence_booking,
        "plausibility_check_duplicates": plausibility_check_duplicates,
        "plausibility_check_boundaries": plausibility_check_boundaries,
        "plausibility_check_breaks_if_auto_disabled": plausibility_check_breaks_if_auto_disabled,
    }
    for key, value in bools.items():
        service_set_setting(db, key, "true" if value == "on" else "false")
    for key, value in {
        "plausibility_daily_time": plausibility_daily_time,
        "plausibility_max_daily_hours": plausibility_max_daily_hours,
        "plausibility_warn_daily_hours": plausibility_warn_daily_hours,
        "plausibility_earliest_come": plausibility_earliest_come,
        "plausibility_latest_leave": plausibility_latest_leave,
        "plausibility_duplicate_minutes": plausibility_duplicate_minutes,
        "plausibility_break_min_6h_minutes": plausibility_break_min_6h_minutes,
        "plausibility_break_min_9h_minutes": plausibility_break_min_9h_minutes,
    }.items():
        service_set_setting(db, key, value.strip())
    db.commit()
    log_action(db, user.employee_number, "plausibility_settings_updated", "settings", "plausibility", "gespeichert")
    return templates.TemplateResponse("system_settings_plausibility.html", {"request": request, "user": user, "settings": service_settings_dict(db), "saved": True})