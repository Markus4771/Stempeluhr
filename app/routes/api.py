from app.version import get_app_version
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.models import Employee, TimeEntry, Setting
from app.schemas import ClockRequest
from app.security import verify_password
from app.services.rfid_media import normalize_rfid_uid, resolve_employee_by_rfid


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
VALID_ENTRY_TYPES = {"kommen","gehen","pause_start","pause_ende"}

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
    return {"success": True, "app":"Stempeluhr", "version": get_app_version()}

@router.get("/employees")
def employees(db: Session = Depends(get_db)):
    return [{"id":e.id,"employee_number":e.employee_number,"name":f"{e.first_name} {e.last_name}","active":e.active,"birth_date": e.birth_date.isoformat() if e.birth_date else None, "entry_date": e.entry_date.isoformat() if e.entry_date else None} for e in db.query(Employee).all()]

@router.post("/clock")
def clock(data: ClockRequest, db: Session = Depends(get_db)):
    if data.entry_type not in VALID_ENTRY_TYPES:
        raise HTTPException(400, "Ungültiger Buchungstyp")
    if data.rfid_code:
        data.rfid_code = normalize_rfid_uid(data.rfid_code)
    if data.employee_number:
        data.employee_number=data.employee_number.strip()
    employee=None; method="api"; medium=None
    if data.rfid_code:
        employee, medium = resolve_employee_by_rfid(db, data.rfid_code)
        method="rfid"
    if not employee and data.employee_number and data.password:
        employee=db.query(Employee).filter(Employee.employee_number==data.employee_number, Employee.active==True).first(); method="password"
        if not employee or not verify_password(data.password, employee.password_hash):
            raise HTTPException(401, "Mitarbeiter oder Passwort falsch")
    if not employee:
        raise HTTPException(404, "RFID/Mitarbeiter nicht gefunden")
    duplicate, last = api_is_duplicate_booking(db, employee.id, 8)
    if duplicate:
        return {
            "success": False,
            "duplicate": True,
            "message": "Doppelbuchung erkannt",
            "employee": f"{employee.first_name} {employee.last_name}",
            "last_entry_type": last.entry_type,
            "last_timestamp": last.timestamp.isoformat(timespec="seconds")
        }

    entry=TimeEntry(employee_id=employee.id,timestamp=datetime.now(),entry_type=data.entry_type,method=method,terminal=data.terminal,note=data.note)
    db.add(entry)
    db.commit()
    return {
        "success":True,
        "employee":f"{employee.first_name} {employee.last_name}",
        "entry_type":data.entry_type,
        "rfid_medium": medium.name if medium else None,
    }
