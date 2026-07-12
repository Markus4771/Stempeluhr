from fastapi import Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.models import Employee
from app.services.security_policy import default_admin_password_active
from app.services.role_permissions import has_permission, role_permissions

SESSION_KEY_EMPLOYEE_ID = "employee_id"


def _sync_user_session_flags(request: Request, employee: Employee):
    """Aktualisiert Rechte- und Sicherheitsflags in der Session."""
    permissions = role_permissions(employee.role)
    request.session[SESSION_KEY_EMPLOYEE_ID] = employee.id
    request.session["employee_number"] = employee.employee_number
    request.session["employee_name"] = f"{employee.first_name} {employee.last_name}"
    request.session["is_admin"] = bool(employee.is_admin)
    request.session["role"] = employee.role.name if employee.role else ""
    request.session["permissions"] = sorted(permissions)
    request.session["can_self_correct"] = bool(getattr(employee, "can_self_correct", False))
    request.session["can_self_manage"] = bool(getattr(employee, "can_self_manage", False))
    request.session["default_admin_password_active"] = default_admin_password_active(employee)


def login_user(request: Request, employee: Employee):
    _sync_user_session_flags(request, employee)


def logout_user(request: Request):
    request.session.clear()


def current_user(request: Request, db: Session):
    employee_id = request.session.get(SESSION_KEY_EMPLOYEE_ID)
    if not employee_id:
        return None
    employee = db.query(Employee).filter(Employee.id == employee_id, Employee.active == True).first()
    if employee:
        _sync_user_session_flags(request, employee)
    return employee


def require_login(request: Request, db: Session):
    user = current_user(request, db)
    if not user:
        return None
    return user


def is_admin_user(user: Employee | None) -> bool:
    if not user:
        return False
    return bool(
        has_permission(user, "employees.view")
        or has_permission(user, "employees.manage")
        or (user.role and user.role.name in ["Administrator", "Personal", "Teamleiter"])
    )


def is_system_admin(user: Employee | None) -> bool:
    if not user:
        return False
    return bool(user.role and user.role.name == "Administrator")


def redirect_to_login():
    return RedirectResponse("/login", status_code=303)
