from app.version import get_app_version
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.models import Employee, TimeEntry
from app.schemas import ClockRequest
from app.security import verify_password
from app.services.authentication import AuthenticationContext, authenticate_credential


def _exclude_fixed_admin(query, Employee):
    """Festen Notfall-Admin aus Dashboard-Statistiken herausrechnen."""
    for field in ("username", "employee_number", "email"):
        if hasattr(Employee, field):
            query = query.filter(getattr(Employee, field) != "admin")
    if hasattr(Employee, "first_name"):
        query = query.filter(Employee.first_name != "admin")
    if hasattr(Employee, "last_name"):
        query = query.filter(Employee.last_name != "admin")
    return query


router = APIRouter(prefix="/api", tags=["API"])
VALID_ENTRY_TYPES = {"kommen", "gehen", "pause_start", "pause_ende"}


def api_is_duplicate_booking(db: Session, employee_id: int, seconds: int = 8):
    last = db.query(TimeEntry).filter(TimeEntry.employee_id == employee_id).order_by(TimeEntry.timestamp.desc()).first()
    if not last:
        return False, None
    delta = datetime.now() - last.timestamp
    if delta.total_seconds() < seconds:
        return True, last
    return False, last


@router.get("/status")
def status(db: Session = Depends(get_db)):
    return {"success": True, "app": "Stempeluhr", "version": get_app_version()}


@router.get("/employees")
def employees(db: Session = Depends(get_db)):
    return [
        {
            "id": e.id,
            "employee_number": e.employee_number,
            "name": f"{e.first_name} {e.last_name}",
            "active": e.active,
            "birth_date": e.birth_date.isoformat() if e.birth_date else None,
            "entry_date": e.entry_date.isoformat() if e.entry_date else None,
        }
        for e in db.query(Employee).all()
    ]


@router.post("/clock")
def clock(data: ClockRequest, db: Session = Depends(get_db)):
    if data.entry_type not in VALID_ENTRY_TYPES:
        raise HTTPException(400, "Ungültiger Buchungstyp")

    employee = None
    method = "api"
    credential_id = None
    auth_metadata = {}

    # 6.x: generisches Anmeldeverfahren. Für alte Terminals wird rfid_code
    # automatisch auf den Provider rfid abgebildet.
    provider = (data.auth_provider or ("rfid" if data.rfid_code else "")).strip().lower()
    credential = data.auth_credential if data.auth_credential is not None else data.rfid_code
    if provider or credential:
        resolved = authenticate_credential(
            db,
            AuthenticationContext(
                provider=provider,
                credential=credential or "",
                terminal_name=data.terminal,
                terminal_id=data.terminal_id,
            ),
        )
        if not resolved.success:
            message = resolved.result.message or "Anmeldemedium nicht bekannt"
            status_code = 503 if "nicht aktiviert" in message else 404
            raise HTTPException(status_code, message)
        employee = resolved.employee
        method = resolved.provider
        credential_id = resolved.result.credential_id
        auth_metadata = dict(resolved.result.metadata or {})

    # Passwort bleibt während der Migration als kompatibler Kernweg erhalten.
    # Es kann später ohne API-Änderung in ein eigenes Plugin verschoben werden.
    if not employee and data.employee_number and data.password:
        employee_number = data.employee_number.strip()
        employee = (
            db.query(Employee)
            .filter(Employee.employee_number == employee_number, Employee.active.is_(True))
            .first()
        )
        method = "password"
        if not employee or not verify_password(data.password, employee.password_hash):
            raise HTTPException(401, "Mitarbeiter oder Passwort falsch")

    if not employee:
        raise HTTPException(404, "Anmeldemedium oder Mitarbeiter nicht gefunden")

    duplicate, last = api_is_duplicate_booking(db, employee.id, 8)
    if duplicate:
        return {
            "success": False,
            "duplicate": True,
            "message": "Doppelbuchung erkannt",
            "employee": f"{employee.first_name} {employee.last_name}",
            "auth_provider": method,
            "credential_id": credential_id,
            "last_entry_type": last.entry_type,
            "last_timestamp": last.timestamp.isoformat(timespec="seconds"),
        }

    entry = TimeEntry(
        employee_id=employee.id,
        timestamp=datetime.now(),
        entry_type=data.entry_type,
        method=method,
        terminal=data.terminal,
        terminal_id=data.terminal_id,
        note=data.note,
    )
    db.add(entry)
    db.commit()

    return {
        "success": True,
        "employee": f"{employee.first_name} {employee.last_name}",
        "entry_type": data.entry_type,
        "auth_provider": method,
        "credential_id": credential_id,
        "credential_name": auth_metadata.get("medium_name"),
        # Altes Feld bleibt für bestehende Clients erhalten.
        "rfid_medium": auth_metadata.get("medium_name") if method == "rfid" else None,
    }
