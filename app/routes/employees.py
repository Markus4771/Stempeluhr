from .common import *

router = APIRouter()

def parse_optional_date(value: str):
    value = (value or "").strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        return None


@router.get("/admin", response_class=HTMLResponse)
def admin(request: Request, q: str = "", role_id: int = 0, department_id: int = 0, active: str = "", admin_filter: str = "", db: Session = Depends(get_db)):
    user, redirect = require_admin_response(request, db)
    if redirect: return redirect
    query = db.query(Employee)
    q = (q or "").strip()
    if q:
        search = f"%{q}%"
        query = query.filter((Employee.employee_number.ilike(search)) | (Employee.first_name.ilike(search)) | (Employee.last_name.ilike(search)) | (Employee.email.ilike(search)))
    if role_id: query = query.filter(Employee.role_id == role_id)
    if department_id: query = query.filter(Employee.department_id == department_id)
    if active == "active": query = query.filter(Employee.active == True)
    elif active == "inactive": query = query.filter(Employee.active == False)
    if admin_filter == "admin": query = query.filter(Employee.is_admin == True)
    elif admin_filter == "no_admin": query = query.filter(Employee.is_admin == False)
    try:
        sync_all_vacation_balances(db); db.commit()
    except Exception as exc:
        db.rollback(); log_action(db, user.employee_number, "admin_vacation_balance_sync_failed", "employees", "", str(exc)[:500])
    employees = query.order_by(Employee.employee_number, Employee.last_name, Employee.first_name).all()
    return templates.TemplateResponse("admin.html", {"request": request, "user": user, "employees": employees, "employee_statuses": latest_employee_statuses(db, [e.id for e in employees]), "roles": db.query(Role).order_by(Role.name).all(), "departments": db.query(Department).order_by(Department.name).all(), "employee_number_length": get_employee_number_length(db), "settings": db.query(Setting).all(), "filters": {"q": q, "role_id": role_id, "department_id": department_id, "active": active, "admin_filter": admin_filter}})

@router.post("/admin/employees/{employee_id}/time-entry")
def admin_employee_time_entry_disabled(employee_id: int, request: Request, entry_type: str = Form(None), db: Session = Depends(get_db)):
    user, redirect = require_admin_response(request, db)
    if redirect: return redirect
    log_action(db, user.employee_number if user else "system", "admin_direct_time_entry_blocked", "employees", str(employee_id), "Direkte Kommen-/Gehen-Buchung aus Mitarbeiterliste wurde blockiert.")
    return templates.TemplateResponse("message.html", {"request": request, "user": user, "title": "Direkte Buchung deaktiviert", "message": "Kommen/Gehen kann nicht mehr direkt in der Mitarbeiterliste gesetzt werden. Bitte nutze die Buchungskorrektur mit Pflicht-Begründung.", "return_to": "/admin"})

@router.post("/admin/employees/add")
def add_employee(request: Request, employee_number: str = Form(...), first_name: str = Form(...), last_name: str = Form(...), email: str = Form(""), phone: str = Form(""), birth_date: str = Form(""), entry_date: str = Form(""), rfid_code: str = Form(""), password: str = Form(""), role_id: int = Form(0), department_id: int = Form(0), can_self_correct: str = Form("off"), can_self_manage: str = Form("off"), plausibility_check_enabled: str = Form("off"), auto_break_enabled: str = Form("on"), weekly_hours: float = Form(40.0), daily_hours: float = Form(8.0), monday_hours: float = Form(8.0), tuesday_hours: float = Form(8.0), wednesday_hours: float = Form(8.0), thursday_hours: float = Form(8.0), friday_hours: float = Form(8.0), saturday_hours: float = Form(0.0), sunday_hours: float = Form(0.0), vacation_days_total: float = Form(30.0), db: Session = Depends(get_db)):
    user, redirect = require_admin_response(request, db)
    if redirect: return redirect
    employee_number = normalize_employee_number(employee_number, get_employee_number_length(db))
    valid_emp_no, emp_no_error = validate_employee_number(employee_number, get_employee_number_length(db))
    if not valid_emp_no: return templates.TemplateResponse("message.html", {"request": request, "user": user, "title": "Fehler", "message": emp_no_error, "return_to": "/admin"})
    if db.query(Employee).filter(Employee.employee_number == employee_number).first(): return templates.TemplateResponse("message.html", {"request": request, "user": user, "title": "Fehler", "message": "Diese Mitarbeiternummer ist bereits vergeben.", "return_to": "/admin"})
    e = Employee(employee_number=employee_number, first_name=first_name.strip(), last_name=last_name.strip(), email=email.strip() or None, phone=phone.strip() or None, birth_date=parse_optional_date(birth_date), entry_date=parse_optional_date(entry_date), password_hash=hash_password(password) if password else None, role_id=role_id or None, department_id=department_id or None, can_self_correct=(can_self_correct == "on"), can_self_manage=(can_self_manage == "on"), plausibility_check_enabled=(plausibility_check_enabled == "on"), auto_break_enabled=(auto_break_enabled == "on"), weekly_hours=weekly_hours, daily_hours=daily_hours, monday_hours=monday_hours, tuesday_hours=tuesday_hours, wednesday_hours=wednesday_hours, thursday_hours=thursday_hours, friday_hours=friday_hours, saturday_hours=saturday_hours, sunday_hours=sunday_hours, vacation_days_total=vacation_days_total, vacation_days_used=0.0, vacation_days_remaining=vacation_days_total, active=True)
    db.add(e); db.commit(); sync_emergency_admin(db); log_action(db, user.employee_number, "employee_created", "employees", str(e.id), e.employee_number)
    return RedirectResponse("/admin", 303)

@router.get("/admin/employees/{employee_id}/edit", response_class=HTMLResponse)
def edit_employee_form(employee_id: int, request: Request, db: Session = Depends(get_db)):
    user, redirect = require_admin_response(request, db)
    if redirect: return redirect
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee: return templates.TemplateResponse("message.html", {"request": request, "user": user, "title": "Fehler", "message": "Mitarbeiter nicht gefunden", "return_to": "/admin"})
    sync_employee_vacation_balance(db, employee); db.commit()
    return templates.TemplateResponse("employee_edit.html", {"request": request, "user": user, "employee": employee, "roles": db.query(Role).order_by(Role.name).all(), "departments": db.query(Department).order_by(Department.name).all(), "employee_number_length": get_employee_number_length(db)})

@router.post("/admin/employees/{employee_id}/edit")
def edit_employee_save(employee_id: int, request: Request, employee_number: str = Form(...), first_name: str = Form(...), last_name: str = Form(...), email: str = Form(""), phone: str = Form(""), birth_date: str = Form(""), entry_date: str = Form(""), rfid_code: str = Form(""), password: str = Form(""), role_id: int = Form(0), department_id: int = Form(0), active: str = Form("off"), can_self_correct: str = Form("off"), can_self_manage: str = Form("off"), plausibility_check_enabled: str = Form("off"), auto_break_enabled: str = Form("on"), weekly_hours: float = Form(40.0), daily_hours: float = Form(8.0), monday_hours: float = Form(8.0), tuesday_hours: float = Form(8.0), wednesday_hours: float = Form(8.0), thursday_hours: float = Form(8.0), friday_hours: float = Form(8.0), saturday_hours: float = Form(0.0), sunday_hours: float = Form(0.0), vacation_days_total: float = Form(30.0), sick_days: float = Form(0.0), overtime_balance: float = Form(0.0), db: Session = Depends(get_db)):
    user, redirect = require_admin_response(request, db)
    if redirect: return redirect
    e = db.query(Employee).filter(Employee.id == employee_id).first()
    if not e: return templates.TemplateResponse("message.html", {"request": request, "user": user, "title": "Fehler", "message": "Mitarbeiter nicht gefunden", "return_to": "/admin"})
    employee_number = normalize_employee_number(employee_number, get_employee_number_length(db))
    valid_emp_no, emp_no_error = validate_employee_number(employee_number, get_employee_number_length(db))
    if not valid_emp_no: return templates.TemplateResponse("message.html", {"request": request, "user": user, "title": "Fehler", "message": emp_no_error, "return_to": f"/admin/employees/{employee_id}/edit"})
    if db.query(Employee).filter(Employee.employee_number == employee_number, Employee.id != employee_id).first(): return templates.TemplateResponse("message.html", {"request": request, "user": user, "title": "Fehler", "message": "Diese Mitarbeiternummer ist bereits vergeben.", "return_to": f"/admin/employees/{employee_id}/edit"})
    e.employee_number = employee_number; e.first_name = first_name.strip(); e.last_name = last_name.strip(); e.email = email.strip() or None; e.phone = phone.strip() or None; e.birth_date = parse_optional_date(birth_date); e.entry_date = parse_optional_date(entry_date)
    if password: e.password_hash = hash_password(password)
    e.role_id = role_id or None; e.department_id = department_id or None; e.active = active == "on"; e.can_self_correct = can_self_correct == "on"; e.can_self_manage = can_self_manage == "on"; e.plausibility_check_enabled = plausibility_check_enabled == "on"; e.auto_break_enabled = auto_break_enabled == "on"; e.weekly_hours = weekly_hours; e.daily_hours = daily_hours; e.monday_hours = monday_hours; e.tuesday_hours = tuesday_hours; e.wednesday_hours = wednesday_hours; e.thursday_hours = thursday_hours; e.friday_hours = friday_hours; e.saturday_hours = saturday_hours; e.sunday_hours = sunday_hours; e.vacation_days_total = vacation_days_total; sync_employee_vacation_balance(db, e); e.sick_days = sick_days; e.overtime_balance = overtime_balance; e.updated_at = datetime.now()
    db.commit(); sync_emergency_admin(db); log_action(db, user.employee_number, "employee_updated", "employees", str(e.id), e.employee_number)
    return RedirectResponse("/admin", 303)

@router.post("/admin/employees/{employee_id}/toggle/plausibility")
def toggle_employee_plausibility(employee_id: int, request: Request, db: Session = Depends(get_db)):
    user, redirect = require_admin_response(request, db)
    if redirect: return redirect
    e = db.query(Employee).filter(Employee.id == employee_id).first()
    if not e: return templates.TemplateResponse("message.html", {"request": request, "user": user, "title": "Fehler", "message": "Mitarbeiter nicht gefunden", "return_to": "/admin"})
    e.plausibility_check_enabled = not bool(e.plausibility_check_enabled); e.updated_at = datetime.now(); db.commit(); log_action(db, user.employee_number, "employee_plausibility_toggled", "employees", str(e.id), f"plausibility_check_enabled={e.plausibility_check_enabled}")
    return RedirectResponse("/admin", 303)

@router.post("/admin/employees/{employee_id}/toggle/auto-break")
def toggle_employee_auto_break(employee_id: int, request: Request, db: Session = Depends(get_db)):
    user, redirect = require_admin_response(request, db)
    if redirect: return redirect
    e = db.query(Employee).filter(Employee.id == employee_id).first()
    if not e: return templates.TemplateResponse("message.html", {"request": request, "user": user, "title": "Fehler", "message": "Mitarbeiter nicht gefunden", "return_to": "/admin"})
    e.auto_break_enabled = not bool(e.auto_break_enabled is not False); e.updated_at = datetime.now(); db.commit(); log_action(db, user.employee_number, "employee_auto_break_toggled", "employees", str(e.id), f"auto_break_enabled={e.auto_break_enabled}")
    return RedirectResponse("/admin", 303)
