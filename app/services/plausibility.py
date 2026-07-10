from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Iterable

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.mailer import send_email_from_settings
from app.models import AuditLog, Department, Employee, PlausibilityIssue, Setting, TimeEntry, VacationRequest, MailDispatchLog
from app.services.settings_service import get_setting, set_setting
from app.services.worktime import calculate_day, get_break_settings, target_hours_for_date


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "ja", "on", "aktiv"}


def _float(value: str | None, default: float) -> float:
    try:
        return float(str(value).replace(",", "."))
    except Exception:
        return default


def _int(value: str | None, default: int) -> int:
    try:
        return int(float(str(value).replace(",", ".")))
    except Exception:
        return default


def _parse_hhmm(value: str, default: time) -> time:
    try:
        h, m = str(value).split(":", 1)
        return time(int(h), int(m))
    except Exception:
        return default


def ensure_plausibility_settings(db: Session) -> None:
    defaults = {
        "plausibility_enabled": "true",
        "plausibility_daily_time": "18:30",
        "plausibility_email_enabled": "true",
        "plausibility_employee_email_enabled": "true",
        "plausibility_teamlead_email_enabled": "true",
        "plausibility_max_daily_hours": "10",
        "plausibility_warn_daily_hours": "9",
        "plausibility_earliest_come": "05:00",
        "plausibility_latest_leave": "22:00",
        "plausibility_duplicate_minutes": "5",
        "plausibility_check_missing_leave": "true",
        "plausibility_check_missing_workday": "true",
        "plausibility_check_absence_booking": "true",
        "plausibility_check_duplicates": "true",
        "plausibility_check_boundaries": "true",
        "plausibility_check_breaks_if_auto_disabled": "true",
        "plausibility_break_min_6h_minutes": "30",
        "plausibility_break_min_9h_minutes": "45",
        "plausibility_teamlead_summary_days": "1",
        "plausibility_last_daily_mail_date": "",
        "plausibility_last_daily_mail_status": "noch nicht ausgeführt",
        "plausibility_last_daily_mail_counts": "",
    }
    for key, value in defaults.items():
        if get_setting(db, key, "") == "":
            set_setting(db, key, value)
    db.commit()


def get_plausibility_settings(db: Session) -> dict:
    ensure_plausibility_settings(db)
    return {s.key: s.value for s in db.query(Setting).filter(Setting.key.like("plausibility_%")).all()}


def _open_or_create_issue(db: Session, employee: Employee, day: date, check_type: str, severity: str, message: str) -> PlausibilityIssue:
    existing = db.query(PlausibilityIssue).filter(
        PlausibilityIssue.employee_id == employee.id,
        PlausibilityIssue.issue_date == day,
        PlausibilityIssue.check_type == check_type,
        PlausibilityIssue.status.in_(["offen", "geprueft"]),
    ).first()
    if existing:
        existing.severity = severity
        existing.message = message
        existing.updated_at = datetime.now()
        return existing
    issue = PlausibilityIssue(
        employee_id=employee.id,
        issue_date=day,
        check_type=check_type,
        severity=severity,
        message=message,
        status="offen",
    )
    db.add(issue)
    return issue


def _absence_on_day(db: Session, employee_id: int, day: date) -> VacationRequest | None:
    return db.query(VacationRequest).filter(
        VacationRequest.employee_id == employee_id,
        VacationRequest.status.in_(["genehmigt", "approved", "freigegeben"]),
        VacationRequest.start_date <= day,
        VacationRequest.end_date >= day,
    ).first()


def scan_day(db: Session, day: date, employee_ids: list[int] | None = None, send_employee_mail: bool = True) -> list[PlausibilityIssue]:
    settings = get_plausibility_settings(db)
    if not _bool(settings.get("plausibility_enabled"), True):
        return []

    q = db.query(Employee).filter(Employee.active == True, Employee.employee_number != "admin")
    if hasattr(Employee, "plausibility_check_enabled"):
        q = q.filter(Employee.plausibility_check_enabled == True)
    if employee_ids:
        q = q.filter(Employee.id.in_(employee_ids))
    employees = q.order_by(Employee.last_name, Employee.first_name).all()

    start_dt = datetime.combine(day, time.min)
    end_dt = datetime.combine(day + timedelta(days=1), time.min)
    break_settings = get_break_settings(db)
    auto_break_enabled = bool(break_settings.get("enabled"))
    created: list[PlausibilityIssue] = []

    max_hours = _float(settings.get("plausibility_max_daily_hours"), 10.0)
    warn_hours = _float(settings.get("plausibility_warn_daily_hours"), 9.0)
    earliest = _parse_hhmm(settings.get("plausibility_earliest_come", "05:00"), time(5, 0))
    latest = _parse_hhmm(settings.get("plausibility_latest_leave", "22:00"), time(22, 0))
    duplicate_minutes = _int(settings.get("plausibility_duplicate_minutes"), 5)
    min6 = _float(settings.get("plausibility_break_min_6h_minutes"), 30.0) / 60.0
    min9 = _float(settings.get("plausibility_break_min_9h_minutes"), 45.0) / 60.0

    for emp in employees:
        entries = db.query(TimeEntry).filter(
            TimeEntry.employee_id == emp.id,
            TimeEntry.timestamp >= start_dt,
            TimeEntry.timestamp < end_dt,
            or_(TimeEntry.deleted == False, TimeEntry.deleted.is_(None)),
        ).order_by(TimeEntry.timestamp.asc()).all()
        workday_target = target_hours_for_date(emp, day)
        absence = _absence_on_day(db, emp.id, day)
        calc = calculate_day(emp, entries, day, break_settings)

        if _bool(settings.get("plausibility_check_missing_workday"), True) and workday_target > 0 and not entries and not absence:
            created.append(_open_or_create_issue(db, emp, day, "missing_workday", "rot", "Soll-Arbeitstag ohne Buchung und ohne Abwesenheit."))

        if _bool(settings.get("plausibility_check_absence_booking"), True) and absence and entries:
            created.append(_open_or_create_issue(db, emp, day, "absence_and_booking", "gelb", f"Abwesenheit ({absence.request_type}) und Arbeitsbuchung am selben Tag."))

        types = [e.entry_type for e in entries]
        if _bool(settings.get("plausibility_check_missing_leave"), True):
            if types.count("kommen") > types.count("gehen"):
                created.append(_open_or_create_issue(db, emp, day, "come_without_leave", "rot", "Kommen-Buchung ohne passende Gehen-Buchung."))
            if types.count("gehen") > types.count("kommen"):
                created.append(_open_or_create_issue(db, emp, day, "leave_without_come", "rot", "Gehen-Buchung ohne passende Kommen-Buchung."))
            if calc.incomplete and entries:
                created.append(_open_or_create_issue(db, emp, day, "incomplete_day", "gelb", "Unvollständige Buchungsfolge an diesem Tag."))

        if calc.net_hours >= max_hours and max_hours > 0:
            created.append(_open_or_create_issue(db, emp, day, "daily_hours_max", "rot", f"Nettoarbeitszeit {calc.net_hours:.2f} h überschreitet Grenzwert {max_hours:.2f} h."))
        elif calc.net_hours >= warn_hours and warn_hours > 0:
            created.append(_open_or_create_issue(db, emp, day, "daily_hours_warning", "gelb", f"Nettoarbeitszeit {calc.net_hours:.2f} h überschreitet Warnwert {warn_hours:.2f} h."))

        if _bool(settings.get("plausibility_check_boundaries"), True):
            for e in entries:
                if e.entry_type == "kommen" and e.timestamp.time() < earliest:
                    created.append(_open_or_create_issue(db, emp, day, "early_come", "gelb", f"Kommen vor erlaubter Zeit: {e.timestamp.strftime('%H:%M')} Uhr."))
                if e.entry_type == "gehen" and e.timestamp.time() > latest:
                    created.append(_open_or_create_issue(db, emp, day, "late_leave", "gelb", f"Gehen nach erlaubter Zeit: {e.timestamp.strftime('%H:%M')} Uhr."))

        if _bool(settings.get("plausibility_check_duplicates"), True) and duplicate_minutes > 0:
            for prev, cur in zip(entries, entries[1:]):
                if prev.entry_type == cur.entry_type and (cur.timestamp - prev.timestamp) <= timedelta(minutes=duplicate_minutes):
                    created.append(_open_or_create_issue(db, emp, day, "duplicate_booking", "gelb", f"Doppelte {cur.entry_type}-Buchung innerhalb von {duplicate_minutes} Minuten."))
                    break

        if (not auto_break_enabled) and _bool(settings.get("plausibility_check_breaks_if_auto_disabled"), True):
            required = 0.0
            if calc.gross_hours > 9:
                required = min9
            elif calc.gross_hours > 6:
                required = min6
            if required and calc.manual_break_hours < required:
                created.append(_open_or_create_issue(db, emp, day, "missing_break", "rot", f"Pause fehlt oder zu kurz: {calc.manual_break_hours:.2f} h statt mindestens {required:.2f} h."))

    db.commit()

    # Ab 5.2.31 versendet der automatische Tageslauf die Mails gebündelt
    # über dispatch_daily_plausibility_mails(). Die direkte Einzelmail bleibt
    # nur für manuelle Alt-Aufrufe erhalten.
    if send_employee_mail and _bool(settings.get("plausibility_email_enabled"), True) and _bool(settings.get("plausibility_employee_email_enabled"), True):
        notify_employees_grouped(db, day)
    db.add(AuditLog(actor="system", action="plausibility_scan", entity="plausibility", entity_id=day.isoformat(), details=f"{len(created)} Auffälligkeiten"))
    db.commit()
    return created


def notify_employees(db: Session, issues: Iterable[PlausibilityIssue]) -> int:
    sent = 0
    for issue in issues:
        if issue.notified_employee_at or not issue.employee or not issue.employee.email:
            continue
        subject = "Stempeluhr – Bitte Buchung prüfen"
        body = (
            f"Hallo {issue.employee.first_name} {issue.employee.last_name},\n\n"
            "bei Ihrer Zeiterfassung wurde eine Auffälligkeit festgestellt.\n\n"
            f"Datum: {issue.issue_date.strftime('%d.%m.%Y')}\n"
            f"Prüfung: {issue.check_type}\n"
            f"Hinweis: {issue.message}\n\n"
            "Bitte prüfen Sie Ihre Buchung und melden Sie sich gegebenenfalls bei Ihrem Teamleiter.\n\n"
            "Mit freundlichen Grüßen\nStempeluhr-System"
        )
        try:
            send_email_from_settings(db, issue.employee.email, subject, body)
            issue.notified_employee_at = datetime.now()
            sent += 1
        except Exception as exc:
            db.add(AuditLog(actor="system", action="plausibility_employee_mail_failed", entity="plausibility", entity_id=str(issue.id), details=str(exc)))
    db.commit()
    return sent


def teamlead_summary(db: Session, day: date | None = None) -> int:
    settings = get_plausibility_settings(db)
    if not (_bool(settings.get("plausibility_email_enabled"), True) and _bool(settings.get("plausibility_teamlead_email_enabled"), True)):
        return 0
    day = day or date.today()
    start = day - timedelta(days=max(0, _int(settings.get("plausibility_teamlead_summary_days"), 1) - 1))
    issues = db.query(PlausibilityIssue).join(Employee, PlausibilityIssue.employee_id == Employee.id).filter(
        PlausibilityIssue.issue_date >= start,
        PlausibilityIssue.issue_date <= day,
        PlausibilityIssue.status.in_(["offen", "geprueft"]),
    ).order_by(Employee.last_name, Employee.first_name, PlausibilityIssue.issue_date).all()

    by_manager: dict[int, list[PlausibilityIssue]] = defaultdict(list)
    for issue in issues:
        emp = issue.employee
        if not emp or not emp.department_id:
            continue
        dept = db.query(Department).filter(Department.id == emp.department_id, Department.active == True).first()
        if dept and dept.manager_employee_id:
            by_manager[dept.manager_employee_id].append(issue)

    sent = 0
    for manager_id, rows in by_manager.items():
        manager = db.query(Employee).filter(Employee.id == manager_id, Employee.active == True).first()
        if not manager or not manager.email:
            continue
        lines = [f"Hallo {manager.first_name} {manager.last_name},", "", "folgende Auffälligkeiten wurden in Ihrem Team festgestellt:", ""]
        for issue in rows:
            emp = issue.employee
            lines.append(f"{emp.first_name} {emp.last_name} – {issue.issue_date.strftime('%d.%m.%Y')} – {issue.severity.upper()}")
            lines.append(f"- {issue.message}")
        lines += ["", f"Anzahl Auffälligkeiten: {len(rows)}", "", "Stempeluhr-System"]
        try:
            send_email_from_settings(db, manager.email, "Stempeluhr – Teamübersicht Plausibilitätsprüfung", "\n".join(lines))
            for issue in rows:
                issue.notified_teamlead_at = datetime.now()
            sent += 1
        except Exception as exc:
            db.add(AuditLog(actor="system", action="plausibility_teamlead_mail_failed", entity="plausibility", entity_id=str(manager_id), details=str(exc)))
    db.commit()
    return sent


# ---------------------------------------------------------------------------
# Version 5.2.31: täglicher Plausibilitäts-Mailversand
# ---------------------------------------------------------------------------

def _mail_log(db: Session, day: date, dispatch_type: str, recipient: str | None, status: str,
              issues_count: int = 0, details: str = "", error_message: str = "",
              recipient_employee_id: int | None = None) -> MailDispatchLog:
    row = MailDispatchLog(
        dispatch_date=day,
        dispatch_type=dispatch_type,
        recipient=recipient,
        recipient_employee_id=recipient_employee_id,
        status=status,
        issues_count=issues_count,
        details=details,
        error_message=error_message,
    )
    db.add(row)
    db.flush()
    return row


def daily_plausibility_mail_already_done(db: Session, day: date) -> bool:
    """True, wenn der Tageslauf fuer das Datum schon abgeschlossen wurde.

    Dadurch wird nach einem Neustart oder Update nicht mehrfach versendet.
    Einzelne Empfaenger-Logs blockieren den Lauf nicht; massgeblich ist der
    Sammel-Status plausibility_daily.
    """
    return db.query(MailDispatchLog).filter(
        MailDispatchLog.dispatch_date == day,
        MailDispatchLog.dispatch_type == "plausibility_daily",
        MailDispatchLog.status.in_(["success", "no_issues", "partial", "failed"]),
    ).first() is not None


def _issues_for_day(db: Session, day: date) -> list[PlausibilityIssue]:
    return db.query(PlausibilityIssue).join(Employee, PlausibilityIssue.employee_id == Employee.id).filter(
        PlausibilityIssue.issue_date == day,
        PlausibilityIssue.status.in_(["offen", "geprueft"]),
        Employee.active == True,
        Employee.employee_number != "admin",
    ).order_by(Employee.last_name, Employee.first_name, PlausibilityIssue.issue_date, PlausibilityIssue.severity).all()


def notify_employees_grouped(db: Session, day: date) -> int:
    """Sendet pro Mitarbeiter genau eine Mail mit allen eigenen Verstoessen."""
    settings = get_plausibility_settings(db)
    if not (_bool(settings.get("plausibility_email_enabled"), True) and _bool(settings.get("plausibility_employee_email_enabled"), True)):
        return 0

    grouped: dict[int, list[PlausibilityIssue]] = defaultdict(list)
    for issue in _issues_for_day(db, day):
        grouped[issue.employee_id].append(issue)

    sent = 0
    for employee_id, rows in grouped.items():
        emp = rows[0].employee
        if not emp:
            continue
        if not emp.email:
            _mail_log(db, day, "plausibility_employee", None, "skipped_no_email", len(rows),
                      f"Keine E-Mail-Adresse fuer {emp.first_name} {emp.last_name}", recipient_employee_id=emp.id)
            continue
        lines = [
            f"Hallo {emp.first_name} {emp.last_name},",
            "",
            f"bei der Plausibilitätsprüfung vom {day.strftime('%d.%m.%Y')} wurden folgende Auffälligkeiten festgestellt:",
            "",
        ]
        for issue in rows:
            lines.append(f"- {issue.issue_date.strftime('%d.%m.%Y')}: {issue.message}")
        lines += ["", "Bitte prüfen Sie Ihre Buchungen und korrigieren Sie diese bei Bedarf.", "", "Mit freundlichen Grüßen", "Stempeluhr-System"]
        try:
            send_email_from_settings(db, emp.email, f"Stempeluhr – Plausibilitätsprüfung {day.strftime('%d.%m.%Y')}", "\n".join(lines))
            now = datetime.now()
            for issue in rows:
                issue.notified_employee_at = now
            _mail_log(db, day, "plausibility_employee", emp.email, "success", len(rows),
                      f"Mitarbeiter-Mail an {emp.first_name} {emp.last_name}", recipient_employee_id=emp.id)
            sent += 1
        except Exception as exc:
            _mail_log(db, day, "plausibility_employee", emp.email, "failed", len(rows),
                      f"Mitarbeiter-Mail an {emp.first_name} {emp.last_name}", str(exc), emp.id)
            db.add(AuditLog(actor="system", action="plausibility_employee_mail_failed", entity="plausibility", entity_id=str(emp.id), details=str(exc)))
    db.commit()
    return sent


def teamlead_summary_grouped(db: Session, day: date) -> int:
    """Sendet pro Vorgesetztem genau eine Sammelmail fuer sein Team."""
    settings = get_plausibility_settings(db)
    if not (_bool(settings.get("plausibility_email_enabled"), True) and _bool(settings.get("plausibility_teamlead_email_enabled"), True)):
        return 0

    by_manager: dict[int, list[PlausibilityIssue]] = defaultdict(list)
    for issue in _issues_for_day(db, day):
        emp = issue.employee
        if not emp or not emp.department_id:
            continue
        dept = db.query(Department).filter(Department.id == emp.department_id, Department.active == True).first()
        if dept and dept.manager_employee_id:
            by_manager[dept.manager_employee_id].append(issue)

    sent = 0
    for manager_id, rows in by_manager.items():
        manager = db.query(Employee).filter(Employee.id == manager_id, Employee.active == True).first()
        if not manager:
            continue
        if not manager.email:
            _mail_log(db, day, "plausibility_teamlead", None, "skipped_no_email", len(rows),
                      f"Keine E-Mail-Adresse fuer Teamleiter ID {manager_id}", recipient_employee_id=manager_id)
            continue
        by_employee: dict[int, list[PlausibilityIssue]] = defaultdict(list)
        for issue in rows:
            by_employee[issue.employee_id].append(issue)
        lines = [
            f"Hallo {manager.first_name} {manager.last_name},",
            "",
            f"bei der Plausibilitätsprüfung vom {day.strftime('%d.%m.%Y')} wurden in Ihrem Team folgende Auffälligkeiten festgestellt:",
            "",
        ]
        for emp_id, emp_issues in by_employee.items():
            emp = emp_issues[0].employee
            lines.append(f"{emp.first_name} {emp.last_name}")
            for issue in emp_issues:
                lines.append(f"- {issue.issue_date.strftime('%d.%m.%Y')}: {issue.message}")
            lines.append("")
        lines += [f"Anzahl Auffälligkeiten: {len(rows)}", "", "Stempeluhr-System"]
        try:
            send_email_from_settings(db, manager.email, f"Stempeluhr – Sammelmail Plausibilitätsprüfung {day.strftime('%d.%m.%Y')}", "\n".join(lines))
            now = datetime.now()
            for issue in rows:
                issue.notified_teamlead_at = now
            _mail_log(db, day, "plausibility_teamlead", manager.email, "success", len(rows),
                      f"Teamleiter-Sammelmail an {manager.first_name} {manager.last_name}", recipient_employee_id=manager.id)
            sent += 1
        except Exception as exc:
            _mail_log(db, day, "plausibility_teamlead", manager.email, "failed", len(rows),
                      f"Teamleiter-Sammelmail an {manager.first_name} {manager.last_name}", str(exc), manager.id)
            db.add(AuditLog(actor="system", action="plausibility_teamlead_mail_failed", entity="plausibility", entity_id=str(manager.id), details=str(exc)))
    db.commit()
    return sent


def dispatch_daily_plausibility_mails(db: Session, day: date | None = None) -> dict:
    """Fuehrt den taeglichen Plausibilitaetslauf aus.

    Regeln 5.2.31:
    - genau einmal taeglich
    - nur zur eingestellten Uhrzeit durch Scheduler aufgerufen
    - Mitarbeiter: eine Mail mit eigenen Verstoessen
    - Vorgesetzter: eine Sammelmail fuer sein Team
    - keine Verstoesse: keine Mail, aber Logeintrag
    """
    day = day or date.today()
    ensure_plausibility_settings(db)
    settings = get_plausibility_settings(db)

    if daily_plausibility_mail_already_done(db, day):
        return {"status": "already_done", "date": day.isoformat()}

    if not _bool(settings.get("plausibility_enabled"), True):
        _mail_log(db, day, "plausibility_daily", None, "disabled", 0, "Plausibilitätsprüfung ist deaktiviert")
        db.commit()
        return {"status": "disabled", "date": day.isoformat()}

    scan_day(db, day, send_employee_mail=False)
    issues = _issues_for_day(db, day)
    if not issues:
        _mail_log(db, day, "plausibility_daily", None, "no_issues", 0, "Keine Verstöße vorhanden, keine E-Mail versendet")
        set_setting(db, "plausibility_last_daily_mail_date", day.isoformat())
        set_setting(db, "plausibility_last_daily_mail_status", "Keine Verstöße vorhanden")
        set_setting(db, "plausibility_last_daily_mail_counts", "0 Verstöße, 0 Mitarbeiter-Mails, 0 Teamleiter-Mails")
        db.add(AuditLog(actor="system", action="plausibility_daily_mail", entity="plausibility", entity_id=day.isoformat(), details="Keine Verstöße vorhanden"))
        db.commit()
        return {"status": "no_issues", "date": day.isoformat(), "issues": 0, "employee_mails": 0, "teamlead_mails": 0}

    employee_mails = notify_employees_grouped(db, day)
    teamlead_mails = teamlead_summary_grouped(db, day)
    failed = db.query(MailDispatchLog).filter(
        MailDispatchLog.dispatch_date == day,
        MailDispatchLog.dispatch_type.in_(["plausibility_employee", "plausibility_teamlead"]),
        MailDispatchLog.status == "failed",
    ).count()
    status = "partial" if failed else "success"
    details = f"{len(issues)} Verstöße, {employee_mails} Mitarbeiter-Mails, {teamlead_mails} Teamleiter-Mails, {failed} Fehler"
    _mail_log(db, day, "plausibility_daily", None, status, len(issues), details)
    set_setting(db, "plausibility_last_daily_mail_date", day.isoformat())
    set_setting(db, "plausibility_last_daily_mail_status", details)
    set_setting(db, "plausibility_last_daily_mail_counts", details)
    db.add(AuditLog(actor="system", action="plausibility_daily_mail", entity="plausibility", entity_id=day.isoformat(), details=details))
    db.commit()
    return {"status": status, "date": day.isoformat(), "issues": len(issues), "employee_mails": employee_mails, "teamlead_mails": teamlead_mails, "failed": failed}


def plausibility_scheduler_tick(db: Session, now: datetime | None = None) -> dict:
    """Eine Scheduler-Iteration. Kann gefahrlos jede Minute aufgerufen werden."""
    now = now or datetime.now()
    ensure_plausibility_settings(db)
    settings = get_plausibility_settings(db)
    run_time = _parse_hhmm(settings.get("plausibility_daily_time", "18:30"), time(18, 30))
    due = now.time().replace(second=0, microsecond=0) >= run_time
    if not due:
        return {"status": "waiting", "next_time": run_time.strftime("%H:%M")}
    if daily_plausibility_mail_already_done(db, now.date()):
        return {"status": "already_done", "date": now.date().isoformat()}
    return dispatch_daily_plausibility_mails(db, now.date())
