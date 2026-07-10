from .common import *

router = APIRouter()

def ensure_dsgvo_settings(db: Session):
    defaults = {
        "dsgvo_enabled": "false",
        "dsgvo_run_time": "02:00",
        "dsgvo_mode": "archive_anonymize",
        "dsgvo_time_entries_years": "2",
        "dsgvo_vacation_years": "3",
        "dsgvo_audit_years": "3",
        "dsgvo_archived_employee_years": "3",
        "dsgvo_payroll_years": "10",
        "dsgvo_last_run": "",
        "dsgvo_last_status": "noch nicht ausgeführt",
    }
    changed = False
    for key, value in defaults.items():
        if service_get_setting(db, key, None) is None:
            service_set_setting(db, key, value)
            changed = True
    if changed:
        db.commit()


def _dsgvo_int(db: Session, key: str, default: int) -> int:
    try:
        return max(1, min(30, int(service_get_setting(db, key, str(default)))))
    except Exception:
        return default


def _dsgvo_cutoff(years: int):
    return datetime.now() - timedelta(days=365 * years)


def dsgvo_preview_counts(db: Session):
    ensure_dsgvo_settings(db)
    te_cut = _dsgvo_cutoff(_dsgvo_int(db, "dsgvo_time_entries_years", 2))
    vac_cut = _dsgvo_cutoff(_dsgvo_int(db, "dsgvo_vacation_years", 3))
    audit_cut = _dsgvo_cutoff(_dsgvo_int(db, "dsgvo_audit_years", 3))
    emp_cut = _dsgvo_cutoff(_dsgvo_int(db, "dsgvo_archived_employee_years", 3))
    time_entries = db.query(TimeEntry).filter(TimeEntry.timestamp < te_cut, or_(TimeEntry.deleted == False, TimeEntry.deleted.is_(None))).count()
    vacations = db.query(VacationRequest).filter(VacationRequest.requested_at < vac_cut).count()
    audit_logs = db.query(AuditLog).filter(AuditLog.created_at < audit_cut).count()
    employees = db.query(Employee).filter(Employee.employee_number != "admin", Employee.status.in_(["archived", "inactive", "anonymized"]), Employee.archived_at != None, Employee.archived_at < emp_cut).count()
    return {"time_entries": time_entries, "vacations": vacations, "audit_logs": audit_logs, "employees": employees}


def _dsgvo_log(db: Session, action: str, data_type: str, record_id: str = "", employee_id=None, actor: str = "SYSTEM", details: str = ""):
    db.add(DsgvoLog(action=action, data_type=data_type, record_id=str(record_id or ""), employee_id=employee_id, actor=actor or "SYSTEM", details=details or ""))


def run_dsgvo_cleanup(db: Session, actor: str, mode: str, execute_delete: bool = False):
    ensure_dsgvo_settings(db)
    counts = {"archived": 0, "anonymized": 0, "deleted": 0}
    now = datetime.now()
    te_cut = _dsgvo_cutoff(_dsgvo_int(db, "dsgvo_time_entries_years", 2))
    vac_cut = _dsgvo_cutoff(_dsgvo_int(db, "dsgvo_vacation_years", 3))
    audit_cut = _dsgvo_cutoff(_dsgvo_int(db, "dsgvo_audit_years", 3))
    emp_cut = _dsgvo_cutoff(_dsgvo_int(db, "dsgvo_archived_employee_years", 3))

    # Arbeitszeitbuchungen: zunächst logisch archivieren/löschen markieren.
    entries = db.query(TimeEntry).filter(TimeEntry.timestamp < te_cut, or_(TimeEntry.deleted == False, TimeEntry.deleted.is_(None))).limit(10000).all()
    for entry in entries:
        entry.deleted = True
        entry.deleted_at = now
        entry.deleted_by = actor
        entry.delete_reason = "DSGVO-Frist abgelaufen - archiviert/aus aktiver Anzeige entfernt"
        _dsgvo_log(db, "ARCHIVIERT", "Arbeitszeitbuchung", entry.id, entry.employee_id, actor, "Zeitbuchung logisch archiviert")
        counts["archived"] += 1

    # Abwesenheits-/Urlaubsanträge: personenbezogene Freitexte anonymisieren, optional löschen.
    vacations = db.query(VacationRequest).filter(VacationRequest.requested_at < vac_cut).limit(10000).all()
    for req in vacations:
        if execute_delete or mode == "archive_anonymize_delete":
            _dsgvo_log(db, "GELÖSCHT", "Abwesenheitsantrag", req.id, req.employee_id, actor, "Frist abgelaufen")
            db.delete(req)
            counts["deleted"] += 1
        else:
            req.comment = None
            req.decision_comment = None
            req.custom_reason = None
            _dsgvo_log(db, "ANONYMISIERT", "Abwesenheitsantrag", req.id, req.employee_id, actor, "Freitexte entfernt")
            counts["anonymized"] += 1

    # Archivierte ausgeschiedene Mitarbeiter anonymisieren.
    employees = db.query(Employee).filter(Employee.employee_number != "admin", Employee.status.in_(["archived", "inactive", "anonymized"]), Employee.archived_at != None, Employee.archived_at < emp_cut).limit(1000).all()
    for emp in employees:
        emp.first_name = "Mitarbeiter"
        emp.last_name = f"#{emp.id}"
        emp.email = None
        emp.phone = None
        emp.rfid_code = None
        emp.password_hash = None
        emp.pin_code_hash = None
        emp.offboarding_note = "DSGVO-anonymisiert"
        emp.status = "anonymized"
        emp.active = False
        _dsgvo_log(db, "ANONYMISIERT", "Mitarbeiter", emp.id, emp.id, actor, "Stammdaten anonymisiert")
        counts["anonymized"] += 1

    # Audit-Protokoll nur bei Löschmodus bereinigen; DSGVO-Log bleibt erhalten.
    if execute_delete or mode == "archive_anonymize_delete":
        old_audit = db.query(AuditLog).filter(AuditLog.created_at < audit_cut).limit(10000).all()
        for row in old_audit:
            _dsgvo_log(db, "GELÖSCHT", "Audit-Protokoll", row.id, None, actor, "Audit-Frist abgelaufen")
            db.delete(row)
            counts["deleted"] += 1

    service_set_setting(db, "dsgvo_last_run", now.strftime("%d.%m.%Y %H:%M"))
    service_set_setting(db, "dsgvo_last_status", f"Archiviert: {counts['archived']}, anonymisiert: {counts['anonymized']}, gelöscht: {counts['deleted']}")
    db.commit()
    return counts


@router.get("/system/settings/dsgvo", response_class=HTMLResponse)
def system_settings_dsgvo(request: Request, message: str = "", db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    ensure_dsgvo_settings(db)
    settings = service_settings_dict(db)
    preview = dsgvo_preview_counts(db)
    logs = db.query(DsgvoLog).order_by(DsgvoLog.created_at.desc()).limit(100).all()
    return templates.TemplateResponse("system_settings_dsgvo.html", {"request": request, "user": user, "settings": settings, "preview": preview, "logs": logs, "message": message})


@router.post("/system/settings/dsgvo", response_class=HTMLResponse)
def system_settings_dsgvo_save(
    request: Request,
    dsgvo_enabled: str = Form("off"),
    dsgvo_run_time: str = Form("02:00"),
    dsgvo_mode: str = Form("archive_anonymize"),
    dsgvo_time_entries_years: int = Form(2),
    dsgvo_vacation_years: int = Form(3),
    dsgvo_audit_years: int = Form(3),
    dsgvo_archived_employee_years: int = Form(3),
    dsgvo_payroll_years: int = Form(10),
    db: Session = Depends(get_db),
):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    ensure_dsgvo_settings(db)
    if dsgvo_mode not in ["archive", "archive_anonymize", "archive_anonymize_delete"]:
        dsgvo_mode = "archive_anonymize"
    service_set_setting(db, "dsgvo_enabled", "true" if dsgvo_enabled == "on" else "false")
    service_set_setting(db, "dsgvo_run_time", (dsgvo_run_time or "02:00")[:5])
    service_set_setting(db, "dsgvo_mode", dsgvo_mode)
    for key, value, default in [
        ("dsgvo_time_entries_years", dsgvo_time_entries_years, 2),
        ("dsgvo_vacation_years", dsgvo_vacation_years, 3),
        ("dsgvo_audit_years", dsgvo_audit_years, 3),
        ("dsgvo_archived_employee_years", dsgvo_archived_employee_years, 3),
        ("dsgvo_payroll_years", dsgvo_payroll_years, 10),
    ]:
        try:
            value = max(1, min(30, int(value)))
        except Exception:
            value = default
        service_set_setting(db, key, str(value))
    _dsgvo_log(db, "KONFIGURATION", "DSGVO-Manager", "settings", getattr(user, "id", None), user.employee_number, "DSGVO-Fristen gespeichert")
    db.commit()
    return RedirectResponse("/system/settings/dsgvo?message=" + quote("DSGVO-Einstellungen gespeichert."), status_code=303)


@router.post("/system/settings/dsgvo/run", response_class=HTMLResponse)
def system_settings_dsgvo_run(
    request: Request,
    confirm_password: str = Form(""),
    confirm_text: str = Form(""),
    execute_delete: str = Form("off"),
    db: Session = Depends(get_db),
):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    ensure_dsgvo_settings(db)
    if not verify_password(confirm_password or "", user.password_hash or ""):
        return RedirectResponse("/system/settings/dsgvo?message=" + quote("Passwort falsch. DSGVO-Lauf wurde nicht ausgeführt."), status_code=303)
    if (confirm_text or "").strip() != "DSGVO AUSFÜHREN":
        return RedirectResponse("/system/settings/dsgvo?message=" + quote("Bestätigungstext falsch. Bitte exakt DSGVO AUSFÜHREN eingeben."), status_code=303)
    mode = service_get_setting(db, "dsgvo_mode", "archive_anonymize")
    counts = run_dsgvo_cleanup(db, user.employee_number, mode, execute_delete == "on")
    msg = f"DSGVO-Lauf abgeschlossen: {counts['archived']} archiviert, {counts['anonymized']} anonymisiert, {counts['deleted']} gelöscht."
    return RedirectResponse("/system/settings/dsgvo?message=" + quote(msg), status_code=303)
