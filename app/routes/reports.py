from .common import *
from fastapi.responses import Response
from fastapi import Form
import csv
import io
import calendar
import json

router = APIRouter()


def _setting(db: Session, key: str, default: str = "") -> str:
    row = db.query(Setting).filter(Setting.key == key).first()
    return str(row.value) if row and row.value is not None else default


def _set_setting(db: Session, key: str, value: str):
    row = db.query(Setting).filter(Setting.key == key).first()
    if row:
        row.value = str(value)
    else:
        db.add(Setting(key=key, value=str(value)))


def _month_range(year: int, month: int):
    last = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last)


def _previous_month(year: int, month: int):
    return (year - 1, 12) if month == 1 else (year, month - 1)


def _resolve_report_range(period: str, date_from: str = "", date_to: str = ""):
    today = date.today()
    if period == "week":
        start_day = today - timedelta(days=today.weekday())
        end_day = start_day + timedelta(days=6)
    elif period == "year":
        start_day, end_day = date(today.year, 1, 1), date(today.year, 12, 31)
    elif period == "custom":
        start_day = today.replace(day=1)
        end_day = date(today.year, 12, 31) if today.month == 12 else date(today.year, today.month + 1, 1) - timedelta(days=1)
        try:
            if date_from:
                start_day = datetime.strptime(date_from, "%Y-%m-%d").date()
            if date_to:
                end_day = datetime.strptime(date_to, "%Y-%m-%d").date()
        except Exception:
            pass
    else:
        period = "month"
        start_day = today.replace(day=1)
        end_day = date(today.year, 12, 31) if today.month == 12 else date(today.year, today.month + 1, 1) - timedelta(days=1)
    if end_day < start_day:
        end_day = start_day
    return period, start_day, end_day


def _resolve_report_context(request: Request, db: Session, employee_id: int, period: str, date_from: str, date_to: str):
    user = current_user(request, db)
    if not user:
        return None
    visible_ids = report_visible_employee_ids(db, user)
    visible_employees = db.query(Employee).filter(Employee.id.in_(visible_ids)).order_by(Employee.last_name, Employee.first_name).all() if visible_ids else []
    if employee_id and int(employee_id) not in visible_ids:
        employee_id = user.id
    if not is_hr_or_admin(user) and role_name(user) != "Teamleiter":
        employee_id = user.id
    period, start_day, end_day = _resolve_report_range(period, date_from, date_to)
    result = calculate_period(db, start_day, end_day, employee_id or None, visible_ids)
    return user, visible_ids, visible_employees, employee_id, period, start_day, end_day, result


def _stamp_entries(db: Session, selected_ids: list[int], start_day: date, end_day: date):
    if not selected_ids:
        return []
    start_dt = datetime.combine(start_day, datetime.min.time())
    end_dt = datetime.combine(end_day + timedelta(days=1), datetime.min.time())
    return db.query(TimeEntry).join(Employee, TimeEntry.employee_id == Employee.id).filter(
        TimeEntry.employee_id.in_(selected_ids),
        TimeEntry.timestamp >= start_dt,
        TimeEntry.timestamp < end_dt,
        not_deleted_filter(),
    ).order_by(TimeEntry.timestamp.asc(), TimeEntry.id.asc()).all()


def _absence_summary(db: Session, start_day: date, end_day: date, employee_ids: list[int]) -> list[dict]:
    if not employee_ids:
        return []
    rows = db.query(VacationRequest).join(Employee, VacationRequest.employee_id == Employee.id).filter(
        VacationRequest.employee_id.in_(employee_ids),
        VacationRequest.start_date <= end_day,
        VacationRequest.end_date >= start_day,
    ).all()
    summary = {}
    for item in rows:
        emp = getattr(item, "employee", None)
        name = f"{getattr(emp, 'last_name', '')}, {getattr(emp, 'first_name', '')}".strip(", ") if emp else str(item.employee_id)
        typ, status = item.request_type or "abwesenheit", item.status or ""
        key = (item.employee_id, typ, status)
        row = summary.setdefault(key, {"employee_name": name, "type": typ, "status": status, "days": 0.0, "count": 0})
        row["days"] += float(item.days or 0.0)
        row["count"] += 1
    result = list(summary.values())
    result.sort(key=lambda x: (x["employee_name"], x["type"], x["status"]))
    return result


def _team_statistics(worktime_rows: list) -> list[dict]:
    stats = {}
    for row in worktime_rows:
        item = stats.setdefault(row.employee_id, {"employee_name": row.employee_name, "target_hours": 0.0, "net_hours": 0.0, "break_hours": 0.0, "overtime_hours": 0.0, "incomplete_days": 0})
        item["target_hours"] += float(row.target_hours or 0.0)
        item["net_hours"] += float(row.net_hours or 0.0)
        item["break_hours"] += float(row.break_hours or 0.0)
        item["overtime_hours"] += float(row.overtime_hours or 0.0)
        if getattr(row, "incomplete", False):
            item["incomplete_days"] += 1
    result = []
    for item in stats.values():
        for key in ("target_hours", "net_hours", "break_hours", "overtime_hours"):
            item[key] = round(item[key], 2)
        result.append(item)
    result.sort(key=lambda x: x["employee_name"])
    return result


def _report_csv_bytes(result: dict, entries: list | None = None) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["Datum", "Mitarbeiter", "Soll", "Brutto", "Pause gesamt", "Netto", "Tag +/-", "Status"])
    for row in result.get("rows", []):
        writer.writerow([row.date.strftime("%d.%m.%Y"), row.employee_name, f"{row.target_hours:.2f}".replace(".", ","), f"{row.gross_hours:.2f}".replace(".", ","), f"{row.break_hours:.2f}".replace(".", ","), f"{row.net_hours:.2f}".replace(".", ","), f"{row.overtime_hours:.2f}".replace(".", ","), "unvollständig" if row.incomplete else "OK"])
    writer.writerow([])
    writer.writerow(["Stempelzeiten"])
    writer.writerow(["Datum", "Uhrzeit", "Mitarbeiter", "Buchung", "Methode", "Terminal"])
    for entry in entries or []:
        typ = (entry.entry_type or "").lower()
        label = "Kommen" if typ in ["kommen", "come", "in"] else "Gehen" if typ in ["gehen", "leave", "out"] else entry.entry_type
        writer.writerow([entry.timestamp.strftime("%d.%m.%Y"), entry.timestamp.strftime("%H:%M:%S"), f"{entry.employee.first_name} {entry.employee.last_name}", label, entry.method or "", entry.terminal or ""])
    return ("\ufeff" + output.getvalue()).encode("utf-8")


def _log_month_report(db: Session, employee_id: int, year: int, month: int, status: str, recipient: str, message: str):
    try:
        details = json.dumps({"year": year, "month": month, "recipient": recipient, "status": status, "message": message}, ensure_ascii=False)
        db.add(AuditLog(actor="SYSTEM", action="employee_month_report", entity="employee", entity_id=str(employee_id), details=details))
        db.commit()
    except Exception:
        db.rollback()


def build_employee_month_report(db: Session, employee: Employee, year: int, month: int, avg_months: int = 6):
    start_day, end_day = _month_range(year, month)
    result = calculate_period(db, start_day, end_day, employee.id, [employee.id])
    totals = result.get("totals") or {}
    entries = _stamp_entries(db, [employee.id], start_day, end_day)
    name = f"{employee.first_name} {employee.last_name}".strip()
    subject = f"Arbeitszeitreport {month:02d}/{year} - {name}"
    body = (
        f"Arbeitszeitreport {month:02d}/{year}\n\nMitarbeiter: {name}\n"
        f"Zeitraum: {start_day.strftime('%d.%m.%Y')} bis {end_day.strftime('%d.%m.%Y')}\n\n"
        f"Sollzeit: {float(totals.get('target_hours') or 0):.2f} Stunden\n"
        f"Istzeit/Netto: {float(totals.get('net_hours') or 0):.2f} Stunden\n"
        f"Saldo: {float(totals.get('overtime_hours') or 0):.2f} Stunden\n\n"
        "Arbeitszeitübersicht und Kommen-/Gehen-Buchungen befinden sich im CSV-Anhang.\n"
    )
    filename = f"arbeitszeitreport_{employee.employee_number}_{year}_{month:02d}.csv"
    return subject, body, [(filename, _report_csv_bytes(result, entries), "text/csv")]


def send_employee_month_report(db: Session, employee: Employee, year: int, month: int, avg_months: int = 6):
    from app.mailer import send_email_with_attachments_from_settings
    if not (employee.email or "").strip():
        raise RuntimeError("Beim Mitarbeiter ist keine E-Mail-Adresse hinterlegt.")
    subject, body, attachments = build_employee_month_report(db, employee, year, month, avg_months)
    send_email_with_attachments_from_settings(db, employee.email.strip(), subject, body, attachments)
    _log_month_report(db, employee.id, year, month, "sent", employee.email.strip(), "")


def monthly_reporting_scheduler_tick(db: Session):
    if _setting(db, "monthly_reporting_enabled", "0").lower() not in ["1", "true", "on", "ja", "yes"]:
        return {"enabled": False, "sent": 0, "failed": 0}
    now = datetime.now()
    day = max(1, min(int(_setting(db, "monthly_reporting_day", "1") or "1"), 28))
    run_time = (_setting(db, "monthly_reporting_time", "06:00") or "06:00")[:5]
    if now.day != day or now.strftime("%H:%M") != run_time:
        return {"enabled": True, "sent": 0, "failed": 0, "due": False}
    year, month = _previous_month(now.year, now.month)
    marker = f"monthly_reporting_last_run_{year}_{month:02d}"
    if _setting(db, marker, ""):
        return {"enabled": True, "sent": 0, "failed": 0, "already_done": True}
    sent = failed = 0
    for emp in db.query(Employee).filter(Employee.active == True).all():
        if is_fixed_admin_employee(emp) or not (emp.email or "").strip():
            continue
        try:
            send_employee_month_report(db, emp, year, month, int(_setting(db, "monthly_reporting_average_months", "6") or "6"))
            sent += 1
        except Exception as exc:
            failed += 1
            _log_month_report(db, emp.id, year, month, "failed", emp.email or "", str(exc))
    _set_setting(db, marker, datetime.now().isoformat(timespec="seconds"))
    db.commit()
    return {"enabled": True, "sent": sent, "failed": failed, "year": year, "month": month}


@router.get("/reports", response_class=HTMLResponse)
def reports(request: Request, employee_id: int = 0, period: str = "month", date_from: str = "", date_to: str = "", db: Session = Depends(get_db)):
    ctx = _resolve_report_context(request, db, employee_id, period, date_from, date_to)
    if not ctx:
        return RedirectResponse("/login", status_code=303)
    user, visible_ids, visible_employees, employee_id, period, start_day, end_day, result = ctx
    selected_ids = [employee_id] if employee_id else visible_ids
    return templates.TemplateResponse("reports.html", {
        "request": request, "user": user, "entries": _stamp_entries(db, selected_ids, start_day, end_day),
        "employees": visible_employees, "worktime_rows": result["rows"], "worktime_totals": result["totals"],
        "team_stats": _team_statistics(result["rows"]), "absence_summary": _absence_summary(db, start_day, end_day, selected_ids),
        "break_settings": result["break_settings"], "report_scope": role_name(user),
        "can_select_all": is_hr_or_admin(user) or role_name(user) == "Teamleiter",
        "filters": {"employee_id": employee_id, "period": period, "date_from": start_day.isoformat(), "date_to": end_day.isoformat()},
        "mail_status": request.query_params.get("mail", ""),
        "monthly_reporting": {"enabled": _setting(db, "monthly_reporting_enabled", "0") in ["1", "true"], "day": int(_setting(db, "monthly_reporting_day", "1") or "1"), "time": _setting(db, "monthly_reporting_time", "06:00"), "average_months": int(_setting(db, "monthly_reporting_average_months", "6") or "6")}
    })


@router.get("/reports/export.csv")
def reports_export_csv(request: Request, employee_id: int = 0, period: str = "month", date_from: str = "", date_to: str = "", db: Session = Depends(get_db)):
    ctx = _resolve_report_context(request, db, employee_id, period, date_from, date_to)
    if not ctx:
        return RedirectResponse("/login", status_code=303)
    user, visible_ids, visible_employees, employee_id, period, start_day, end_day, result = ctx
    selected_ids = [employee_id] if employee_id else visible_ids
    filename = f"stempeluhr_report_{start_day.isoformat()}_{end_day.isoformat()}.csv"
    return Response(content=_report_csv_bytes(result, _stamp_entries(db, selected_ids, start_day, end_day)), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f"attachment; filename={filename}"})


@router.get("/reports/print", response_class=HTMLResponse)
def reports_print(request: Request, employee_id: int = 0, period: str = "month", date_from: str = "", date_to: str = "", db: Session = Depends(get_db)):
    ctx = _resolve_report_context(request, db, employee_id, period, date_from, date_to)
    if not ctx:
        return RedirectResponse("/login", status_code=303)
    user, visible_ids, visible_employees, employee_id, period, start_day, end_day, result = ctx
    selected_ids = [employee_id] if employee_id else visible_ids
    return templates.TemplateResponse("reports_print.html", {"request": request, "user": user, "entries": _stamp_entries(db, selected_ids, start_day, end_day), "worktime_rows": result["rows"], "worktime_totals": result["totals"], "team_stats": _team_statistics(result["rows"]), "absence_summary": _absence_summary(db, start_day, end_day, selected_ids), "filters": {"date_from": start_day.isoformat(), "date_to": end_day.isoformat(), "period": period}})


@router.get("/worktime-account", response_class=HTMLResponse)
def worktime_account(request: Request, employee_id: int = 0, period: str = "month", date_from: str = "", date_to: str = "", db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    visible_ids = report_visible_employee_ids(db, user)
    visible_employees = db.query(Employee).filter(Employee.id.in_(visible_ids)).order_by(Employee.last_name, Employee.first_name).all() if visible_ids else []
    if employee_id and int(employee_id) not in visible_ids:
        employee_id = user.id
    if not is_hr_or_admin(user) and role_name(user) != "Teamleiter":
        employee_id = user.id
    period, start_day, end_day = _resolve_report_range(period, date_from, date_to)
    result = calculate_worktime_account(db, start_day, end_day, employee_id or None, visible_ids)
    return templates.TemplateResponse("worktime_account.html", {"request": request, "user": user, "employees": visible_employees, "account_rows": result["employees"], "monthly_rows": result["monthly"], "account_totals": result["totals"], "can_select_all": is_hr_or_admin(user) or role_name(user) == "Teamleiter", "filters": {"employee_id": employee_id, "period": period, "date_from": start_day.isoformat(), "date_to": end_day.isoformat()}})


@router.post("/reports/email")
def reports_send_email(request: Request, employee_id: int = Form(0), period: str = Form("month"), date_from: str = Form(""), date_to: str = Form(""), db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    target_id = user.id
    if (is_hr_or_admin(user) or role_name(user) == "Teamleiter") and employee_id in report_visible_employee_ids(db, user):
        target_id = employee_id
    period, start_day, end_day = _resolve_report_range(period, date_from, date_to)
    target = db.query(Employee).filter(Employee.id == target_id).first()
    if not target:
        return RedirectResponse("/reports?mail=employee_missing", status_code=303)
    try:
        send_employee_month_report(db, target, start_day.year, start_day.month, int(_setting(db, "monthly_reporting_average_months", "6") or "6"))
        return RedirectResponse(f"/reports?employee_id={target_id}&period={period}&date_from={start_day.isoformat()}&date_to={end_day.isoformat()}&mail=sent", status_code=303)
    except Exception as exc:
        _log_month_report(db, target.id, start_day.year, start_day.month, "failed", target.email or "", str(exc))
        return RedirectResponse(f"/reports?employee_id={target_id}&period={period}&date_from={start_day.isoformat()}&date_to={end_day.isoformat()}&mail=failed", status_code=303)


@router.post("/reports/monthly-settings")
def reports_monthly_settings(request: Request, enabled: str = Form("0"), day: int = Form(1), run_time: str = Form("06:00"), average_months: int = Form(6), db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user or not is_hr_or_admin(user):
        return RedirectResponse("/reports", status_code=303)
    _set_setting(db, "monthly_reporting_enabled", "1" if enabled == "1" else "0")
    _set_setting(db, "monthly_reporting_day", str(max(1, min(int(day), 28))))
    _set_setting(db, "monthly_reporting_time", (run_time or "06:00")[:5])
    _set_setting(db, "monthly_reporting_average_months", str(max(1, min(int(average_months), 24))))
    db.commit()
    return RedirectResponse("/reports?settings=saved", status_code=303)


@router.post("/reports/monthly-send-all")
def reports_monthly_send_all(request: Request, year: int = Form(0), month: int = Form(0), db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user or not is_hr_or_admin(user):
        return RedirectResponse("/reports", status_code=303)
    if not year or not month:
        year, month = _previous_month(date.today().year, date.today().month)
    for emp in db.query(Employee).filter(Employee.active == True).all():
        if is_fixed_admin_employee(emp) or not (emp.email or "").strip():
            continue
        try:
            send_employee_month_report(db, emp, int(year), int(month), int(_setting(db, "monthly_reporting_average_months", "6") or "6"))
        except Exception as exc:
            _log_month_report(db, emp.id, int(year), int(month), "failed", emp.email or "", str(exc))
    return RedirectResponse("/reports?bulkmail=done", status_code=303)
