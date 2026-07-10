from .common import *

router = APIRouter()

@router.get("/system/settings/departments", response_class=HTMLResponse)
def system_departments(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect

    departments = db.query(Department).order_by(Department.name).all()
    employees = db.query(Employee).filter(Employee.active == True).order_by(Employee.last_name, Employee.first_name).all()

    counts = {}
    for d in departments:
        counts[d.id] = _exclude_fixed_admin(db.query(Employee).filter(Employee.department_id == d.id), Employee).count()

    return templates.TemplateResponse("system_departments.html", {
        "request": request,
        "user": user,
        "departments": departments,
        "employee_number_length": get_employee_number_length(db),
        "employees": employees,
        "counts": counts,
        "error": None
    })

@router.post("/system/settings/departments/add")
def system_department_add(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    manager_employee_id: int = Form(0),
    active: str = Form("off"),
    db: Session = Depends(get_db)
):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect

    name = name.strip()
    if not name:
        return RedirectResponse("/system/settings/departments", status_code=303)

    exists = db.query(Department).filter(Department.name == name).first()
    if exists:
        departments = db.query(Department).order_by(Department.name).all()
        employees = db.query(Employee).filter(Employee.active == True).order_by(Employee.last_name, Employee.first_name).all()
        counts = {d.id: _exclude_fixed_admin(db.query(Employee).filter(Employee.department_id == d.id), Employee).count() for d in departments}
        return templates.TemplateResponse("system_departments.html", {
            "request": request,
            "user": user,
            "departments": departments,
        "employee_number_length": get_employee_number_length(db),
            "employees": employees,
            "counts": counts,
            "error": "Diese Abteilung existiert bereits."
        })

    dept = Department(
        name=name,
        description=description.strip() or None,
        manager_employee_id=manager_employee_id if manager_employee_id and manager_employee_id > 0 else None,
        active=active == "on"
    )
    db.add(dept)
    db.commit()
    log_action(db, user.employee_number, "department_created", "departments", str(dept.id), dept.name)
    return RedirectResponse("/system/settings/departments", status_code=303)

@router.get("/system/settings/departments/{department_id}/edit", response_class=HTMLResponse)
def system_department_edit_form(department_id: int, request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect

    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        return templates.TemplateResponse("message.html", {
            "request": request,
            "title": "Fehler",
            "message": "Abteilung nicht gefunden",
            "return_to": "/system/settings/departments"
        })

    employees = db.query(Employee).filter(Employee.active == True).order_by(Employee.last_name, Employee.first_name).all()
    return templates.TemplateResponse("system_department_edit.html", {
        "request": request,
        "user": user,
        "department": department,
        "employees": employees,
        "error": None
    })

@router.post("/system/settings/departments/{department_id}/edit")
def system_department_edit_save(
    department_id: int,
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    manager_employee_id: int = Form(0),
    active: str = Form("off"),
    db: Session = Depends(get_db)
):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect

    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        return RedirectResponse("/system/settings/departments", status_code=303)

    name = name.strip()
    if not name:
        employees = db.query(Employee).filter(Employee.active == True).order_by(Employee.last_name, Employee.first_name).all()
        return templates.TemplateResponse("system_department_edit.html", {
            "request": request,
            "user": user,
            "department": department,
            "employees": employees,
            "error": "Name darf nicht leer sein."
        })

    duplicate = db.query(Department).filter(Department.name == name, Department.id != department.id).first()
    if duplicate:
        employees = db.query(Employee).filter(Employee.active == True).order_by(Employee.last_name, Employee.first_name).all()
        return templates.TemplateResponse("system_department_edit.html", {
            "request": request,
            "user": user,
            "department": department,
            "employees": employees,
            "error": "Diese Abteilung existiert bereits."
        })

    department.name = name
    department.description = description.strip() or None
    department.manager_employee_id = manager_employee_id if manager_employee_id and manager_employee_id > 0 else None
    department.active = active == "on"

    db.commit()
    log_action(db, user.employee_number, "department_updated", "departments", str(department.id), department.name)
    return RedirectResponse("/system/settings/departments", status_code=303)

@router.post("/system/settings/departments/{department_id}/delete")
def system_department_delete(department_id: int, request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect

    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        return RedirectResponse("/system/settings/departments", status_code=303)

    used = _exclude_fixed_admin(db.query(Employee).filter(Employee.department_id == department.id), Employee).count()
    if used > 0:
        department.active = False
        db.commit()
        log_action(db, user.employee_number, "department_deactivated", "departments", str(department.id), f"{department.name}, verwendet von {used} Mitarbeitern")
    else:
        name = department.name
        db.delete(department)
        db.commit()
        log_action(db, user.employee_number, "department_deleted", "departments", str(department_id), name)

    return RedirectResponse("/system/settings/departments", status_code=303)



# ---------------------------------------------------------------------------
# API-Key Verwaltung
# ---------------------------------------------------------------------------
