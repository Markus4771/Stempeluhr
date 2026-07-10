from __future__ import annotations

import hashlib
from datetime import date, datetime, time, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ApiToken, AuditLog, Employee, PlausibilityIssue, Setting, TimeEntry, Terminal, Role, Department
from app.security import verify_password, hash_password
from app.version import APP_NAME, APP_VERSION
from app.services.booking_state import (
    normalize_entry_type as state_normalize_entry_type,
    determine_auto_entry_type as state_determine_auto_entry_type,
    is_valid_transition_for_employee as state_is_valid_transition_for_employee,
    latest_entry as state_latest_entry,
)

router = APIRouter(prefix="/api/v1", tags=["API v1"])

VALID_ENTRY_TYPES = {"kommen", "gehen", "pause_start", "pause_ende"}
ENTRY_ALIASES = {
    "kommend": "kommen",
    "kommen": "kommen",
    "in": "kommen",
    "gehend": "gehen",
    "gehen": "gehen",
    "out": "gehen",
    "pause": "pause_start",
    "pause_start": "pause_start",
    "pause_ende": "pause_ende",
    "pause_ende_": "pause_ende",
    "pause_end": "pause_ende",
}


def _get_setting(db: Session, key: str, default: str = "") -> str:
    row = db.query(Setting).filter(Setting.key == key).first()
    return row.value if row and row.value is not None else default


def _setting_bool(db: Session, key: str, default: bool = False) -> bool:
    val = _get_setting(db, key, "true" if default else "false")
    return str(val).strip().lower() in {"1", "true", "yes", "ja", "on"}


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _extract_api_key(authorization: Optional[str], x_api_key: Optional[str]) -> Optional[str]:
    if x_api_key:
        return x_api_key.strip()
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    return None


def require_api_token(
    request: Request,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None),
) -> ApiToken:
    if not _setting_bool(db, "api_enabled", False):
        raise HTTPException(status_code=403, detail="API ist deaktiviert")

    raw_token = _extract_api_key(authorization, x_api_key)
    if not raw_token:
        raise HTTPException(status_code=401, detail="API-Key fehlt")

    token_hash = _hash_token(raw_token)
    token = db.query(ApiToken).filter(ApiToken.active == True, ApiToken.token == token_hash).first()

    # Kompatibilität für ältere Installationen, falls dort ein Token im Klartext gespeichert wurde.
    if not token:
        token = db.query(ApiToken).filter(ApiToken.active == True, ApiToken.token == raw_token).first()

    if not token:
        raise HTTPException(status_code=401, detail="API-Key ungültig")

    if getattr(token, "expires_at", None) and token.expires_at < datetime.now():
        raise HTTPException(status_code=401, detail="API-Key abgelaufen")

    client_ip = request.client.host if request.client else ""
    allowed_ips = (getattr(token, "allowed_ips", None) or "").strip()
    if allowed_ips:
        allowed = [x.strip() for x in allowed_ips.replace(";", ",").split(",") if x.strip()]
        if client_ip not in allowed:
            raise HTTPException(status_code=403, detail="IP-Adresse für diesen API-Key nicht erlaubt")

    token.last_used_at = datetime.now()
    if _setting_bool(db, "api_logging_enabled", True):
        db.add(AuditLog(
            actor=f"api:{token.name}",
            action="api_access",
            entity="api",
            entity_id=request.url.path,
            details=request.method,
            ip_address=client_ip,
        ))
    db.commit()
    return token


def require_api_write(token: ApiToken):
    perms = (getattr(token, "permissions", "read") or "read").lower()
    if "write" not in perms and "admin" not in perms:
        raise HTTPException(status_code=403, detail="API-Key hat keine Schreibrechte")


class ApiClockRequest(BaseModel):
    employee_number: Optional[str] = None
    password: Optional[str] = None
    rfid_code: Optional[str] = None
    entry_type: str = Field(..., description="kommen, gehen, pause_start oder pause_ende")
    terminal: Optional[str] = "api"
    note: Optional[str] = None


class ApiClockAutoRequest(BaseModel):
    employee_number: Optional[str] = None
    password: Optional[str] = None
    rfid_code: Optional[str] = None
    terminal: Optional[str] = "api"
    note: Optional[str] = None


class UserCreateRequest(BaseModel):
    employee_number: str = Field(..., description="Eindeutige Personal-/Mitarbeiternummer")
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    rfid_code: Optional[str] = None
    password: Optional[str] = None
    role_id: Optional[int] = None
    department_id: Optional[int] = None
    active: bool = True
    can_self_correct: bool = False
    can_self_manage: bool = False
    plausibility_check_enabled: bool = True
    auto_break_enabled: bool = True
    weekly_hours: Optional[float] = 40.0
    daily_hours: Optional[float] = 8.0


class UserUpdateRequest(BaseModel):
    employee_number: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    rfid_code: Optional[str] = None
    password: Optional[str] = None
    role_id: Optional[int] = None
    department_id: Optional[int] = None
    active: Optional[bool] = None
    can_self_correct: Optional[bool] = None
    can_self_manage: Optional[bool] = None
    plausibility_check_enabled: Optional[bool] = None
    auto_break_enabled: Optional[bool] = None
    weekly_hours: Optional[float] = None
    daily_hours: Optional[float] = None


class UserRfidRequest(BaseModel):
    rfid_code: str


def _validate_user_refs(db: Session, role_id: Optional[int], department_id: Optional[int]):
    if role_id:
        if not db.query(Role).filter(Role.id == role_id).first():
            raise HTTPException(status_code=400, detail="Rolle nicht gefunden")
    if department_id:
        if not db.query(Department).filter(Department.id == department_id).first():
            raise HTTPException(status_code=400, detail="Abteilung nicht gefunden")


def _set_user_fields(employee: Employee, data: UserUpdateRequest | UserCreateRequest, db: Session, creating: bool = False):
    payload = data.model_dump(exclude_unset=not creating)
    if "employee_number" in payload and payload["employee_number"]:
        nr = str(payload["employee_number"]).strip()
        other = db.query(Employee).filter(Employee.employee_number == nr).first()
        if other and other.id != getattr(employee, "id", None):
            raise HTTPException(status_code=409, detail="Mitarbeiternummer ist bereits vergeben")
        employee.employee_number = nr
    if "rfid_code" in payload:
        rfid = (payload.get("rfid_code") or "").strip() or None
        if rfid:
            other = db.query(Employee).filter(Employee.rfid_code == rfid).first()
            if other and other.id != getattr(employee, "id", None):
                raise HTTPException(status_code=409, detail="RFID-Code ist bereits vergeben")
        employee.rfid_code = rfid
    for field in ["first_name", "last_name", "email", "phone"]:
        if field in payload:
            value = payload.get(field)
            setattr(employee, field, value.strip() if isinstance(value, str) else value)
    if "password" in payload and payload.get("password"):
        employee.password_hash = hash_password(payload["password"])
    _validate_user_refs(db, payload.get("role_id"), payload.get("department_id"))
    for field in ["role_id", "department_id", "active", "can_self_correct", "can_self_manage", "plausibility_check_enabled", "auto_break_enabled", "weekly_hours", "daily_hours"]:
        if field in payload:
            setattr(employee, field, payload.get(field))
    employee.updated_at = datetime.now()



class ResolvePlausibilityRequest(BaseModel):
    status: str = Field(..., description="geprüft, erledigt oder ignoriert")
    comment: Optional[str] = None


def _employee_dict(e: Employee) -> dict:
    role = e.role.name if getattr(e, "role", None) else None
    department = e.department.name if getattr(e, "department", None) else None
    return {
        "id": e.id,
        "employee_number": e.employee_number,
        "first_name": e.first_name,
        "last_name": e.last_name,
        "name": f"{e.first_name} {e.last_name}",
        "email": e.email,
        "active": e.active,
        "role": role,
        "department": department,
        "can_self_correct": getattr(e, "can_self_correct", False),
            "can_self_manage": getattr(e, "can_self_manage", False),
        "plausibility_check_enabled": getattr(e, "plausibility_check_enabled", True),
        "auto_break_enabled": getattr(e, "auto_break_enabled", True),
        "role_id": getattr(e, "role_id", None),
        "department_id": getattr(e, "department_id", None),
        "phone": getattr(e, "phone", None),
        "weekly_hours": getattr(e, "weekly_hours", None),
        "daily_hours": getattr(e, "daily_hours", None),
    }


def _entry_dict(entry: TimeEntry) -> dict:
    employee = entry.employee
    return {
        "id": entry.id,
        "employee_id": entry.employee_id,
        "employee_number": employee.employee_number if employee else None,
        "employee_name": f"{employee.first_name} {employee.last_name}" if employee else None,
        "timestamp": entry.timestamp.isoformat(timespec="seconds") if entry.timestamp else None,
        "entry_type": entry.entry_type,
        "method": entry.method,
        "terminal": entry.terminal,
        "note": entry.note,
        "corrected": entry.corrected,
        "deleted": getattr(entry, "deleted", False),
    }


def _normalize_entry_type(value: str) -> str:
    key = (value or "").strip().lower().replace("-", "_").replace(" ", "_")
    normalized = ENTRY_ALIASES.get(key, key)
    if normalized not in VALID_ENTRY_TYPES:
        raise HTTPException(status_code=400, detail="Ungültiger Buchungstyp")
    return normalized


def _resolve_employee(db: Session, employee_number: Optional[str], password: Optional[str], rfid_code: Optional[str]) -> tuple[Employee, str]:
    if rfid_code:
        rfid = rfid_code.strip().replace("\r", "").replace("\n", "")
        employee = db.query(Employee).filter(Employee.rfid_code == rfid, Employee.active == True).first()
        if employee:
            return employee, "api_rfid"

    if employee_number:
        nr = employee_number.strip()
        employee = db.query(Employee).filter(Employee.employee_number == nr, Employee.active == True).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Mitarbeiter nicht gefunden")
        if password is not None and not verify_password(password, employee.password_hash):
            raise HTTPException(status_code=401, detail="Mitarbeiter oder Passwort falsch")
        return employee, "api_password" if password is not None else "api"

    raise HTTPException(status_code=400, detail="employee_number oder rfid_code erforderlich")


def _last_active_entry(db: Session, employee_id: int) -> Optional[TimeEntry]:
    return db.query(TimeEntry).filter(
        TimeEntry.employee_id == employee_id,
        TimeEntry.deleted == False,
    ).order_by(TimeEntry.timestamp.desc(), TimeEntry.id.desc()).first()


def _next_entry_type(db: Session, employee_id: int) -> str:
    return state_determine_auto_entry_type(db, employee_id)


def _create_entry(db: Session, employee: Employee, entry_type: str, method: str, terminal: Optional[str], note: Optional[str]) -> TimeEntry:
    entry_type = state_normalize_entry_type(entry_type)
    last = state_latest_entry(db, employee.id)
    if last:
        delta = datetime.now() - last.timestamp
        if delta.total_seconds() < 8:
            raise HTTPException(status_code=409, detail="Doppelbuchung erkannt")
    if not state_is_valid_transition_for_employee(db, employee.id, entry_type):
        raise HTTPException(status_code=409, detail="Ungültiger Buchungswechsel")

    entry = TimeEntry(
        employee_id=employee.id,
        timestamp=datetime.now(),
        entry_type=entry_type,
        method=method,
        terminal=terminal or "api",
        note=note,
    )
    db.add(entry)
    db.add(AuditLog(
        actor="api",
        action="booking_create",
        entity="time_entry",
        details=f"{employee.employee_number} {entry_type}",
    ))
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/info")
def api_info(db: Session = Depends(get_db)):
    return {
        "app": APP_NAME,
        "version": APP_VERSION,
        "api_version": "v1",
        "api_enabled": _setting_bool(db, "api_enabled", False),
        "docs": "/docs",
    }


@router.get("/health")
def api_health():
    return {"status": "ok", "version": APP_VERSION, "api_version": "v1"}


@router.get("/employees")
def api_employees(
    active_only: bool = True,
    db: Session = Depends(get_db),
    token: ApiToken = Depends(require_api_token),
):
    query = db.query(Employee)
    if active_only:
        query = query.filter(Employee.active == True)
    query = query.filter(Employee.employee_number != "admin")
    return [_employee_dict(e) for e in query.order_by(Employee.last_name, Employee.first_name).all()]


@router.get("/employees/{employee_id}")
def api_employee(employee_id: int, db: Session = Depends(get_db), token: ApiToken = Depends(require_api_token)):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Mitarbeiter nicht gefunden")
    return _employee_dict(employee)


# ---------------------------------------------------------------------------
# Benutzer-API (neue REST-Endpunkte; /employees bleibt als Lesekompatibilität)
# ---------------------------------------------------------------------------
@router.get("/users")
def api_users(
    active_only: bool = True,
    db: Session = Depends(get_db),
    token: ApiToken = Depends(require_api_token),
):
    query = db.query(Employee)
    if active_only:
        query = query.filter(Employee.active == True)
    query = query.filter(Employee.employee_number != "admin")
    return [_employee_dict(e) for e in query.order_by(Employee.last_name, Employee.first_name).all()]


@router.post("/users")
def api_create_user(data: UserCreateRequest, db: Session = Depends(get_db), token: ApiToken = Depends(require_api_token)):
    require_api_write(token)
    employee = Employee()
    _set_user_fields(employee, data, db, creating=True)
    db.add(employee)
    db.flush()
    db.add(AuditLog(actor=f"api:{token.name}", action="user_create", entity="employee", entity_id=str(employee.id), details=employee.employee_number))
    db.commit()
    db.refresh(employee)
    return {"success": True, "user": _employee_dict(employee)}


@router.get("/users/changes")
def api_users_changes(
    since: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    token: ApiToken = Depends(require_api_token),
):
    query = db.query(Employee).filter(Employee.employee_number != "admin")
    if since:
        query = query.filter(Employee.updated_at >= since)
    return [_employee_dict(e) for e in query.order_by(Employee.updated_at.desc(), Employee.id.desc()).limit(1000).all()]


@router.get("/users/{user_id}")
def api_get_user(user_id: int, db: Session = Depends(get_db), token: ApiToken = Depends(require_api_token)):
    employee = db.query(Employee).filter(Employee.id == user_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")
    return _employee_dict(employee)


@router.put("/users/{user_id}")
def api_update_user(user_id: int, data: UserUpdateRequest, db: Session = Depends(get_db), token: ApiToken = Depends(require_api_token)):
    require_api_write(token)
    employee = db.query(Employee).filter(Employee.id == user_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")
    _set_user_fields(employee, data, db, creating=False)
    db.add(AuditLog(actor=f"api:{token.name}", action="user_update", entity="employee", entity_id=str(employee.id), details=employee.employee_number))
    db.commit()
    db.refresh(employee)
    return {"success": True, "user": _employee_dict(employee)}


@router.delete("/users/{user_id}")
def api_delete_user(user_id: int, hard_delete: bool = False, db: Session = Depends(get_db), token: ApiToken = Depends(require_api_token)):
    require_api_write(token)
    employee = db.query(Employee).filter(Employee.id == user_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")
    if employee.employee_number == "admin":
        raise HTTPException(status_code=400, detail="Admin-Benutzer kann nicht über die API gelöscht werden")
    if hard_delete:
        db.delete(employee)
        action = "user_delete"
    else:
        employee.active = False
        employee.status = "inactive"
        employee.updated_at = datetime.now()
        action = "user_deactivate"
    db.add(AuditLog(actor=f"api:{token.name}", action=action, entity="employee", entity_id=str(user_id), details=employee.employee_number))
    db.commit()
    return {"success": True, "id": user_id, "deleted": hard_delete, "active": False if not hard_delete else None}


@router.post("/users/{user_id}/rfid")
def api_set_user_rfid(user_id: int, data: UserRfidRequest, db: Session = Depends(get_db), token: ApiToken = Depends(require_api_token)):
    require_api_write(token)
    employee = db.query(Employee).filter(Employee.id == user_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")
    other = db.query(Employee).filter(Employee.rfid_code == data.rfid_code).first()
    if other and other.id != employee.id:
        raise HTTPException(status_code=409, detail="RFID-Code ist bereits vergeben")
    employee.rfid_code = data.rfid_code.strip()
    employee.updated_at = datetime.now()
    db.add(AuditLog(actor=f"api:{token.name}", action="user_rfid_update", entity="employee", entity_id=str(employee.id), details=employee.employee_number))
    db.commit()
    return {"success": True, "user": _employee_dict(employee)}


@router.post("/users/{user_id}/photo")
def api_user_photo_placeholder(user_id: int, db: Session = Depends(get_db), token: ApiToken = Depends(require_api_token)):
    require_api_write(token)
    if not db.query(Employee).filter(Employee.id == user_id).first():
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")
    raise HTTPException(status_code=501, detail="Foto-Upload ist vorbereitet, aber noch nicht produktiv aktiviert")


@router.post("/users/import")
def api_users_import(users: list[UserCreateRequest], db: Session = Depends(get_db), token: ApiToken = Depends(require_api_token)):
    require_api_write(token)
    created = 0
    updated = 0
    results = []
    for item in users:
        employee = db.query(Employee).filter(Employee.employee_number == item.employee_number).first()
        if employee:
            _set_user_fields(employee, UserUpdateRequest(**item.model_dump(exclude_unset=True)), db, creating=False)
            updated += 1
            action = "updated"
        else:
            employee = Employee()
            _set_user_fields(employee, item, db, creating=True)
            db.add(employee)
            db.flush()
            created += 1
            action = "created"
        results.append({"employee_number": employee.employee_number, "id": employee.id, "action": action})
    db.add(AuditLog(actor=f"api:{token.name}", action="users_import", entity="employees", details=f"created={created}; updated={updated}"))
    db.commit()
    return {"success": True, "created": created, "updated": updated, "results": results}



@router.get("/bookings")
def api_bookings(
    employee_id: Optional[int] = None,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    include_deleted: bool = False,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    token: ApiToken = Depends(require_api_token),
):
    query = db.query(TimeEntry).join(Employee)
    if employee_id:
        query = query.filter(TimeEntry.employee_id == employee_id)
    if date_from:
        query = query.filter(TimeEntry.timestamp >= datetime.combine(date_from, time.min))
    if date_to:
        query = query.filter(TimeEntry.timestamp <= datetime.combine(date_to, time.max))
    if not include_deleted:
        query = query.filter(TimeEntry.deleted == False)
    entries = query.order_by(TimeEntry.timestamp.desc(), TimeEntry.id.desc()).limit(limit).all()
    return [_entry_dict(e) for e in entries]


@router.post("/bookings")
def api_create_booking(data: ApiClockRequest, db: Session = Depends(get_db), token: ApiToken = Depends(require_api_token)):
    require_api_write(token)
    entry_type = _normalize_entry_type(data.entry_type)
    employee, method = _resolve_employee(db, data.employee_number, data.password, data.rfid_code)
    entry = _create_entry(db, employee, entry_type, method, data.terminal, data.note)
    return {"success": True, "booking": _entry_dict(entry)}


@router.post("/bookings/auto")
def api_auto_booking(data: ApiClockAutoRequest, db: Session = Depends(get_db), token: ApiToken = Depends(require_api_token)):
    require_api_write(token)
    employee, method = _resolve_employee(db, data.employee_number, data.password, data.rfid_code)
    entry_type = _next_entry_type(db, employee.id)
    entry = _create_entry(db, employee, entry_type, method + "_auto", data.terminal, data.note)
    return {"success": True, "auto_entry_type": entry_type, "booking": _entry_dict(entry)}


@router.post("/rfid/book")
def api_rfid_book(data: ApiClockAutoRequest, db: Session = Depends(get_db), token: ApiToken = Depends(require_api_token)):
    require_api_write(token)
    if not data.rfid_code:
        raise HTTPException(status_code=400, detail="rfid_code erforderlich")
    employee, method = _resolve_employee(db, None, None, data.rfid_code)
    entry_type = _next_entry_type(db, employee.id)
    entry = _create_entry(db, employee, entry_type, method + "_auto", data.terminal or "api_rfid", data.note)
    return {"success": True, "auto_entry_type": entry_type, "booking": _entry_dict(entry)}


@router.get("/dashboard")
def api_dashboard(db: Session = Depends(get_db), token: ApiToken = Depends(require_api_token)):
    employees = db.query(Employee).filter(Employee.active == True, Employee.employee_number != "admin").all()
    present = 0
    pause = 0
    absent = 0
    for employee in employees:
        last = _last_active_entry(db, employee.id)
        if not last:
            absent += 1
            continue
        typ = _normalize_entry_type(last.entry_type)
        if typ == "kommen" or typ == "pause_ende":
            present += 1
        elif typ == "pause_start":
            pause += 1
        else:
            absent += 1
    open_issues = db.query(PlausibilityIssue).filter(PlausibilityIssue.status == "offen").count() if PlausibilityIssue else 0
    return {
        "employees_total": len(employees),
        "present": present,
        "pause": pause,
        "absent": absent,
        "plausibility_open": open_issues,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }


@router.get("/plausibility/open")
def api_plausibility_open(
    employee_id: Optional[int] = None,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    token: ApiToken = Depends(require_api_token),
):
    query = db.query(PlausibilityIssue).filter(PlausibilityIssue.status == "offen")
    if employee_id:
        query = query.filter(PlausibilityIssue.employee_id == employee_id)
    issues = query.order_by(PlausibilityIssue.issue_date.desc(), PlausibilityIssue.id.desc()).limit(limit).all()
    return [{
        "id": i.id,
        "employee_id": i.employee_id,
        "employee_name": f"{i.employee.first_name} {i.employee.last_name}" if i.employee else None,
        "issue_date": i.issue_date.isoformat() if i.issue_date else None,
        "check_type": i.check_type,
        "severity": i.severity,
        "message": i.message,
        "status": i.status,
        "comment": i.comment,
    } for i in issues]


@router.post("/plausibility/{issue_id}/status")
def api_plausibility_status(issue_id: int, data: ResolvePlausibilityRequest, db: Session = Depends(get_db), token: ApiToken = Depends(require_api_token)):
    require_api_write(token)
    status = data.status.strip().lower()
    if status not in {"geprüft", "erledigt", "ignoriert"}:
        raise HTTPException(status_code=400, detail="Ungültiger Status")
    issue = db.query(PlausibilityIssue).filter(PlausibilityIssue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Plausibilitätsfall nicht gefunden")
    issue.status = status
    issue.comment = data.comment
    issue.resolved_at = datetime.now() if status in {"erledigt", "ignoriert"} else issue.resolved_at
    issue.resolved_by = f"api:{token.name}"
    db.add(AuditLog(actor=f"api:{token.name}", action="plausibility_status", entity="plausibility_issue", entity_id=str(issue.id), details=status))
    db.commit()
    return {"success": True, "id": issue.id, "status": issue.status}

# ---------------------------------------------------------------------------
# Multi-Terminal API
# ---------------------------------------------------------------------------
class TerminalHeartbeatRequest(BaseModel):
    terminal_code: Optional[str] = None
    name: Optional[str] = None
    app_version: Optional[str] = None

class TerminalRfidBookingRequest(BaseModel):
    rfid_code: str
    note: Optional[str] = None
    offline_timestamp: Optional[datetime] = None

class TerminalOfflineBooking(BaseModel):
    rfid_code: str
    timestamp: datetime
    note: Optional[str] = None

class TerminalSyncRequest(BaseModel):
    bookings: list[TerminalOfflineBooking] = []


class TerminalTimeReportRequest(BaseModel):
    terminal_time: Optional[datetime] = None
    offset_seconds: Optional[float] = None
    status: Optional[str] = None
    message: Optional[str] = None


def _extract_terminal_key(authorization: Optional[str], x_terminal_key: Optional[str]) -> Optional[str]:
    if x_terminal_key:
        return x_terminal_key.strip()
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    return None


def require_terminal(
    request: Request,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
    x_terminal_key: Optional[str] = Header(None),
) -> Terminal:
    from app.models import Terminal
    if not _setting_bool(db, "terminal_api_enabled", True):
        raise HTTPException(status_code=403, detail="Terminal-API ist deaktiviert")
    raw_key = _extract_terminal_key(authorization, x_terminal_key)
    if not raw_key:
        raise HTTPException(status_code=401, detail="Terminal-Key fehlt")
    key_hash = _hash_token(raw_key)
    terminal = db.query(Terminal).filter(Terminal.active == True, Terminal.api_key == key_hash).first()
    if not terminal:
        terminal = db.query(Terminal).filter(Terminal.active == True, Terminal.api_key == raw_key).first()
    if not terminal:
        raise HTTPException(status_code=401, detail="Terminal-Key ungültig")
    terminal.last_seen = datetime.now()
    terminal.last_ip = request.client.host if request.client else None
    db.commit()
    return terminal


@router.get("/terminals/me")
def api_terminal_me(terminal: Terminal = Depends(require_terminal)):
    return {
        "id": terminal.id,
        "terminal_code": terminal.terminal_code,
        "name": terminal.name,
        "location": terminal.location,
        "active": terminal.active,
        "offline_buffer_enabled": getattr(terminal, "offline_buffer_enabled", True),
        "last_seen": terminal.last_seen.isoformat(timespec="seconds") if terminal.last_seen else None,
        "time_sync_enabled": bool(getattr(terminal, "time_sync_enabled", True)),
        "last_time_sync": terminal.last_time_sync.isoformat(timespec="seconds") if getattr(terminal, "last_time_sync", None) else None,
        "time_offset_seconds": getattr(terminal, "time_offset_seconds", None),
        "time_status": getattr(terminal, "time_status", None),
    }


@router.get("/terminals/time")
def api_terminal_time(db: Session = Depends(get_db), terminal: Terminal = Depends(require_terminal)):
    """Referenzzeit für Raspberry-Terminals.

    Terminals können diesen Endpunkt regelmäßig abfragen und damit ihre lokale Uhr prüfen.
    Das tatsächliche Setzen der Systemzeit muss auf dem Raspberry mit passenden sudo-Rechten erfolgen.
    """
    server_now = datetime.now()
    enabled = _setting_bool(db, "time_sync_terminals", False) and bool(getattr(terminal, "time_sync_enabled", True))
    return {
        "success": True,
        "sync_enabled": enabled,
        "server_time": server_now.isoformat(timespec="seconds"),
        "server_unix": int(server_now.timestamp()),
        "timezone": _get_setting(db, "time_timezone", "Europe/Berlin"),
        "max_allowed_offset_seconds": int(_get_setting(db, "terminal_time_max_offset_seconds", "5") or 5),
        "recommended_command": "sudo timedatectl set-time '@%s'" % int(server_now.timestamp()),
    }


@router.post("/terminals/time/report")
def api_terminal_time_report(
    data: TerminalTimeReportRequest,
    db: Session = Depends(get_db),
    terminal: Terminal = Depends(require_terminal),
):
    terminal.last_time_sync = datetime.now()
    terminal.time_offset_seconds = data.offset_seconds
    terminal.time_status = (data.status or "reported")[:50]
    terminal.time_message = (data.message or "")[:500]
    db.add(AuditLog(actor=f"terminal:{terminal.name}", action="terminal_time_report", entity="terminal", entity_id=str(terminal.id), details=f"offset={data.offset_seconds}; status={terminal.time_status}"))
    db.commit()
    return {"success": True, "terminal": terminal.name, "saved": True}


@router.post("/terminals/heartbeat")
def api_terminal_heartbeat(
    data: TerminalHeartbeatRequest,
    request: Request,
    db: Session = Depends(get_db),
    terminal: Terminal = Depends(require_terminal),
):
    if data.app_version:
        terminal.app_version = data.app_version[:50]
    if data.name:
        terminal.name = data.name[:100]
    terminal.last_seen = datetime.now()
    terminal.last_ip = request.client.host if request.client else None
    db.commit()
    server_now = datetime.now()
    return {
        "success": True,
        "server_time": server_now.isoformat(timespec="seconds"),
        "server_unix": int(server_now.timestamp()),
        "time_sync_enabled": _setting_bool(db, "time_sync_terminals", False) and bool(getattr(terminal, "time_sync_enabled", True)),
        "timezone": _get_setting(db, "time_timezone", "Europe/Berlin"),
        "terminal": terminal.name,
    }


@router.post("/terminals/rfid/book")
def api_terminal_rfid_book(
    data: TerminalRfidBookingRequest,
    db: Session = Depends(get_db),
    terminal: Terminal = Depends(require_terminal),
):
    if not data.rfid_code:
        raise HTTPException(status_code=400, detail="rfid_code erforderlich")
    employee, method = _resolve_employee(db, None, None, data.rfid_code)
    entry_type = _next_entry_type(db, employee.id)
    entry = TimeEntry(
        employee_id=employee.id,
        timestamp=data.offline_timestamp or datetime.now(),
        entry_type=entry_type,
        method="terminal_rfid_auto",
        terminal=terminal.name,
        terminal_id=terminal.id,
        note=data.note,
    )
    db.add(entry)
    db.add(AuditLog(actor=f"terminal:{terminal.name}", action="terminal_booking", entity="time_entry", details=f"{employee.employee_number} {entry_type}"))
    db.commit()
    db.refresh(entry)
    return {"success": True, "auto_entry_type": entry_type, "booking": _entry_dict(entry), "terminal": terminal.name}


@router.post("/terminals/offline/sync")
def api_terminal_offline_sync(
    data: TerminalSyncRequest,
    db: Session = Depends(get_db),
    terminal: Terminal = Depends(require_terminal),
):
    results = []
    for item in data.bookings:
        try:
            employee, method = _resolve_employee(db, None, None, item.rfid_code)
            # Bei Offline-Buchungen wird nach Zeitstempel einsortiert; doppelte identische Buchungen werden übersprungen.
            existing = db.query(TimeEntry).filter(
                TimeEntry.employee_id == employee.id,
                TimeEntry.timestamp == item.timestamp,
                TimeEntry.terminal_id == terminal.id,
            ).first()
            if existing:
                results.append({"success": True, "duplicate": True, "timestamp": item.timestamp.isoformat()})
                continue
            entry_type = _next_entry_type(db, employee.id)
            entry = TimeEntry(employee_id=employee.id, timestamp=item.timestamp, entry_type=entry_type, method="terminal_offline_sync", terminal=terminal.name, terminal_id=terminal.id, note=item.note)
            db.add(entry)
            db.commit()
            results.append({"success": True, "entry_type": entry_type, "timestamp": item.timestamp.isoformat()})
        except Exception as exc:
            db.rollback()
            results.append({"success": False, "timestamp": item.timestamp.isoformat(), "error": str(exc)})
    return {"success": True, "count": len(results), "results": results}


@router.get("/terminals/status")
def api_terminals_status(db: Session = Depends(get_db), token: ApiToken = Depends(require_api_token)):
    from app.models import Terminal
    terminals = db.query(Terminal).order_by(Terminal.name.asc()).all()
    now = datetime.now()
    return [{
        "id": t.id,
        "terminal_code": t.terminal_code,
        "name": t.name,
        "location": t.location,
        "active": t.active,
        "online": bool(t.last_seen and (now - t.last_seen).total_seconds() < 300),
        "last_seen": t.last_seen.isoformat(timespec="seconds") if t.last_seen else None,
        "last_ip": getattr(t, "last_ip", None),
        "app_version": getattr(t, "app_version", None),
        "time_sync_enabled": bool(getattr(t, "time_sync_enabled", True)),
        "last_time_sync": t.last_time_sync.isoformat(timespec="seconds") if getattr(t, "last_time_sync", None) else None,
        "time_offset_seconds": getattr(t, "time_offset_seconds", None),
        "time_status": getattr(t, "time_status", None),
    } for t in terminals]
