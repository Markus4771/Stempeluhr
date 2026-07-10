from .common import *

router = APIRouter()

def ensure_offboarding_schema(db: Session):
    """Erweitert ältere Installationen um Offboarding-Spalten."""
    try:
        bind = db.get_bind()
        dialect = bind.dialect.name
        if dialect == "sqlite":
            rows = db.execute(text("PRAGMA table_info(employees)")).fetchall()
            cols = {row[1] for row in rows}
            if "status" not in cols:
                db.execute(text("ALTER TABLE employees ADD COLUMN status VARCHAR(20) DEFAULT 'active'"))
            if "exit_date" not in cols:
                db.execute(text("ALTER TABLE employees ADD COLUMN exit_date DATE NULL"))
            if "archived_at" not in cols:
                db.execute(text("ALTER TABLE employees ADD COLUMN archived_at TIMESTAMP NULL"))
            if "offboarding_note" not in cols:
                db.execute(text("ALTER TABLE employees ADD COLUMN offboarding_note TEXT NULL"))
        elif dialect == "postgresql":
            db.execute(text("ALTER TABLE employees ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active'"))
            db.execute(text("ALTER TABLE employees ADD COLUMN IF NOT EXISTS exit_date DATE NULL"))
            db.execute(text("ALTER TABLE employees ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP NULL"))
            db.execute(text("ALTER TABLE employees ADD COLUMN IF NOT EXISTS offboarding_note TEXT NULL"))
        db.commit()
    except Exception:
        db.rollback()


def _offboarding_employee_query(db: Session):
    q = db.query(Employee)
    q = _exclude_fixed_admin(q, Employee)
    return q


@router.get("/system/settings/offboarding", response_class=HTMLResponse)
def system_settings_offboarding(request: Request, employee_id: int = 0, status: str = "active", message: str = "", db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    ensure_module_visibility_settings(db)
    ensure_offboarding_schema(db)
    selected = _offboarding_employee_query(db).filter(Employee.id == employee_id).first() if employee_id else None
    employees_query = _offboarding_employee_query(db)
    if status == "active":
        employees_query = employees_query.filter(Employee.active == True)
    elif status == "inactive":
        employees_query = employees_query.filter(Employee.active == False)
    elif status == "archived":
        employees_query = employees_query.filter(getattr(Employee, "status") == "archived")
    employees = employees_query.order_by(Employee.last_name, Employee.first_name, Employee.employee_number).all()

    stats = None
    if selected:
        try:
            year = date.today().year
            accs = db.query(WorkTimeAccount).filter(WorkTimeAccount.employee_id == selected.id, WorkTimeAccount.year == year).all()
            overtime = sum(float(a.overtime_hours or 0) for a in accs)
            actual = sum(float(a.actual_hours or 0) for a in accs)
        except Exception:
            overtime = float(getattr(selected, "overtime_balance", 0) or 0)
            actual = 0.0
        stats = {
            "resturlaub": float(getattr(selected, "vacation_days_remaining", 0) or 0),
            "ueberstunden": overtime,
            "zeitkonto": actual,
            "letzte_buchung": db.query(TimeEntry).filter(TimeEntry.employee_id == selected.id).order_by(TimeEntry.timestamp.desc()).first(),
        }
    return templates.TemplateResponse("system_offboarding.html", {
        "request": request,
        "user": user,
        "employees": employees,
        "selected": selected,
        "stats": stats,
        "status_filter": status,
        "message": message or request.query_params.get("message", ""),
    })


@router.post("/system/settings/offboarding/select", response_class=HTMLResponse)
def system_settings_offboarding_select(employee_id: int = Form(0), db: Session = Depends(get_db)):
    return RedirectResponse(f"/system/settings/offboarding?employee_id={employee_id}", status_code=303)


@router.post("/system/settings/offboarding/save", response_class=HTMLResponse)
def system_settings_offboarding_save(
    request: Request,
    employee_id: int = Form(...),
    exit_date: str = Form(""),
    status: str = Form("inactive"),
    block_login: str = Form("0"),
    block_rfid: str = Form("0"),
    release_rfid: str = Form("0"),
    vacation_handling: str = Form("noted"),
    overtime_handling: str = Form("noted"),
    offboarding_note: str = Form(""),
    db: Session = Depends(get_db),
):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    ensure_offboarding_schema(db)
    emp = _offboarding_employee_query(db).filter(Employee.id == employee_id).first()
    if not emp:
        return RedirectResponse("/system/settings/offboarding?message=" + quote("Mitarbeiter nicht gefunden oder fester Admin ist gesperrt."), status_code=303)
    try:
        emp.exit_date = datetime.strptime(exit_date, "%Y-%m-%d").date() if exit_date else None
    except Exception:
        emp.exit_date = None
    emp.status = status if status in ["active", "inactive", "archived"] else "inactive"
    emp.active = emp.status == "active"
    if emp.status == "archived" and not getattr(emp, "archived_at", None):
        emp.archived_at = datetime.now()
    if block_login == "1":
        emp.password_hash = None
        emp.pin_code_hash = None
    if block_rfid == "1" or release_rfid == "1":
        emp.rfid_code = None
    emp.offboarding_note = (offboarding_note or "").strip() or None
    emp.updated_at = datetime.now()
    db.add(AuditLog(actor=user.employee_number, action="employee_offboarding_saved", entity="employees", entity_id=str(emp.id), details=f"Status={emp.status}, Austritt={emp.exit_date}, Urlaub={vacation_handling}, Überstunden={overtime_handling}"))
    db.commit()
    return RedirectResponse(f"/system/settings/offboarding?employee_id={emp.id}&message=" + quote("Offboarding gespeichert."), status_code=303)


@router.post("/system/settings/offboarding/reset-employee", response_class=HTMLResponse)
def system_settings_offboarding_reset_employee(
    request: Request,
    employee_id: int = Form(...),
    confirm_password: str = Form(""),
    reset_overtime: str = Form("0"),
    reset_vacation: str = Form("0"),
    delete_bookings: str = Form("0"),
    db: Session = Depends(get_db),
):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    ensure_offboarding_schema(db)
    if not verify_password(confirm_password or "", user.password_hash or ""):
        return RedirectResponse(f"/system/settings/offboarding?employee_id={employee_id}&message=" + quote("Passwort falsch. Keine Änderung durchgeführt."), status_code=303)
    emp = _offboarding_employee_query(db).filter(Employee.id == employee_id).first()
    if not emp:
        return RedirectResponse("/system/settings/offboarding?message=" + quote("Mitarbeiter nicht gefunden oder fester Admin ist gesperrt."), status_code=303)
    changes = []
    if reset_overtime == "1":
        emp.overtime_balance = 0
        try:
            db.query(WorkTimeAccount).filter(WorkTimeAccount.employee_id == emp.id).delete(synchronize_session=False)
        except Exception:
            pass
        changes.append("Überstunden/Zeitkonto zurückgesetzt")
    if reset_vacation == "1":
        emp.vacation_days_used = 0
        emp.vacation_days_remaining = emp.vacation_days_total or 0
        changes.append("Resturlaub auf Standard gesetzt")
    if delete_bookings == "1":
        db.query(Correction).filter(Correction.employee_id == emp.id).delete(synchronize_session=False)
        db.query(TimeEntry).filter(TimeEntry.employee_id == emp.id).delete(synchronize_session=False)
        changes.append("Buchungen/Korrekturen gelöscht")
    emp.updated_at = datetime.now()
    db.add(AuditLog(actor=user.employee_number, action="employee_offboarding_reset", entity="employees", entity_id=str(emp.id), details=", ".join(changes) or "keine Auswahl"))
    db.commit()
    return RedirectResponse(f"/system/settings/offboarding?employee_id={emp.id}&message=" + quote("Mitarbeiter-Neuanfang durchgeführt: " + (", ".join(changes) or "keine Auswahl")), status_code=303)


@router.get("/system/settings/offboarding/report/{employee_id}", response_class=HTMLResponse)
def system_settings_offboarding_report(request: Request, employee_id: int, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    ensure_offboarding_schema(db)
    emp = _offboarding_employee_query(db).filter(Employee.id == employee_id).first()
    if not emp:
        return RedirectResponse("/system/settings/offboarding?message=" + quote("Mitarbeiter nicht gefunden."), status_code=303)
    last_entry = db.query(TimeEntry).filter(TimeEntry.employee_id == emp.id).order_by(TimeEntry.timestamp.desc()).first()
    return templates.TemplateResponse("system_offboarding_report.html", {"request": request, "user": user, "employee": emp, "last_entry": last_entry, "now": datetime.now()})


