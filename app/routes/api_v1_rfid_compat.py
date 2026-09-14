"""RFID-Kompatibilität für API v1.

Das öffentliche Feld ``rfid_code`` bleibt für ältere Clients erhalten. Intern
ist ab Stempeluhr 6.0 ausschließlich ``employee_rfid_media`` maßgeblich.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ApiToken, AuditLog, Employee
from app.services.rfid_media import add_rfid_medium, resolve_employee_by_rfid
from . import api_v1

router = APIRouter(prefix="/api/v1", tags=["API v1"])


def _resolve_employee_media_first(
    db: Session,
    employee_number: Optional[str],
    password: Optional[str],
    rfid_code: Optional[str],
) -> tuple[Employee, str]:
    """Kompatibles rfid_code-Feld, aber Auflösung nur über Medienverwaltung."""
    if rfid_code:
        employee, _medium = resolve_employee_by_rfid(db, rfid_code)
        if employee:
            return employee, "api_rfid"
        if not employee_number:
            raise HTTPException(status_code=404, detail="RFID-/NFC-Medium nicht gefunden")

    if employee_number:
        nr = employee_number.strip()
        employee = db.query(Employee).filter(
            Employee.employee_number == nr,
            Employee.active.is_(True),
        ).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Mitarbeiter nicht gefunden")
        if password is not None and not api_v1.verify_password(password, employee.password_hash):
            raise HTTPException(status_code=401, detail="Mitarbeiter oder Passwort falsch")
        return employee, "api_password" if password is not None else "api"

    raise HTTPException(status_code=400, detail="employee_number oder rfid_code erforderlich")


# Bestehende Buchungs-, Terminal- und Offline-Sync-Routen greifen zur Laufzeit
# auf api_v1._resolve_employee zu. Damit werden alle diese Wege zentralisiert,
# ohne das öffentliche API-v1-Protokoll zu brechen.
api_v1._resolve_employee = _resolve_employee_media_first


def _apply_non_rfid_user_fields(employee: Employee, data, db: Session, creating: bool) -> str | None:
    """Wendet bestehende Benutzerlogik an und gibt optionalen RFID-Wert zurück."""
    payload = data.model_dump(exclude_unset=not creating)
    rfid_value = payload.pop("rfid_code", None) if "rfid_code" in payload else None

    # Für die vorhandene Hilfsfunktion ein Modell erzeugen, bei dem rfid_code
    # nicht als gesetzt gilt. So bleibt employees.rfid_code unangetastet.
    model_type = type(data)
    clean = model_type(**payload)
    api_v1._set_user_fields(employee, clean, db, creating=creating)
    employee.rfid_code = None
    return str(rfid_value).strip() if rfid_value else None


def _attach_rfid(db: Session, employee: Employee, uid: str | None):
    if not uid:
        return None
    try:
        return add_rfid_medium(
            db,
            employee.id,
            uid,
            name="API RFID-Medium",
            media_type="rfid",
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/users")
def api_create_user_media(
    data: api_v1.UserCreateRequest,
    db: Session = Depends(get_db),
    token: ApiToken = Depends(api_v1.require_api_token),
):
    api_v1.require_api_write(token)
    employee = Employee()
    uid = _apply_non_rfid_user_fields(employee, data, db, creating=True)
    db.add(employee)
    db.flush()
    _attach_rfid(db, employee, uid)
    db.add(AuditLog(actor=f"api:{token.name}", action="user_create", entity="employee", entity_id=str(employee.id), details=employee.employee_number))
    db.commit()
    db.refresh(employee)
    return {"success": True, "user": api_v1._employee_dict(employee)}


@router.put("/users/{user_id}")
def api_update_user_media(
    user_id: int,
    data: api_v1.UserUpdateRequest,
    db: Session = Depends(get_db),
    token: ApiToken = Depends(api_v1.require_api_token),
):
    api_v1.require_api_write(token)
    employee = db.query(Employee).filter(Employee.id == user_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")
    uid = _apply_non_rfid_user_fields(employee, data, db, creating=False)
    _attach_rfid(db, employee, uid)
    db.add(AuditLog(actor=f"api:{token.name}", action="user_update", entity="employee", entity_id=str(employee.id), details=employee.employee_number))
    db.commit()
    db.refresh(employee)
    return {"success": True, "user": api_v1._employee_dict(employee)}


@router.post("/users/{user_id}/rfid")
def api_set_user_rfid_media(
    user_id: int,
    data: api_v1.UserRfidRequest,
    db: Session = Depends(get_db),
    token: ApiToken = Depends(api_v1.require_api_token),
):
    api_v1.require_api_write(token)
    employee = db.query(Employee).filter(Employee.id == user_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")

    uid = (data.rfid_code or "").strip()
    if not uid:
        raise HTTPException(status_code=400, detail="rfid_code erforderlich")
    medium = _attach_rfid(db, employee, uid)
    employee.rfid_code = None
    employee.updated_at = datetime.now()
    db.add(AuditLog(
        actor=f"api:{token.name}",
        action="user_rfid_update",
        entity="employee_rfid_media",
        entity_id=str(medium.id or ""),
        details=employee.employee_number,
    ))
    db.commit()
    db.refresh(medium)
    return {
        "success": True,
        "user": api_v1._employee_dict(employee),
        "rfid_medium": {
            "id": medium.id,
            "name": medium.name,
            "media_type": medium.media_type,
            "active": medium.active,
        },
    }
