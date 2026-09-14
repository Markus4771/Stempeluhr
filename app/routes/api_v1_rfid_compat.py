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


# Die bestehenden API-v1-Buchungsrouten rufen diese Funktion zur Laufzeit aus
# dem api_v1-Modul auf. Durch den Austausch bleiben ihre Request-Modelle und
# URLs kompatibel, während die alte employees.rfid_code-Abfrage verschwindet.
def _resolve_employee_media_first(
    db: Session,
    employee_number: Optional[str],
    password: Optional[str],
    rfid_code: Optional[str],
) -> tuple[Employee, str]:
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


_original_set_user_fields = api_v1._set_user_fields


def _set_user_fields_without_legacy_rfid(employee, data, db: Session, creating: bool = False):
    """Behält rfid_code im API-Schema, schreibt aber nicht mehr ins Legacy-Feld.

    Bei Create/Update wird ein mitgesendeter RFID-Code nach dem Flush durch die
    jeweilige API-Route verarbeitet. Das direkte RFID-Endpoint unten ist der
    bevorzugte Weg für neue Integrationen.
    """
    payload = data.model_dump(exclude_unset=not creating)
    rfid_supplied = "rfid_code" in payload
    rfid_value = payload.pop("rfid_code", None)

    # Pydantic-Kopie ohne rfid_code erzeugen, damit die bestehende Feldlogik
    # unverändert für alle Nicht-RFID-Felder weiterverwendet werden kann.
    clean_data = data.model_copy(update={"rfid_code": None})
    _original_set_user_fields(employee, clean_data, db, creating=creating)

    # Die Originalfunktion würde bei vorhandenem Feld None ins Legacy-Feld
    # schreiben. Das ist zulässig und verhindert neue Legacy-Zuordnungen.
    if rfid_supplied:
        employee.rfid_code = None
        # UID erst nach vorhandenem employee.id anlegen. Create/Import führen
        # unmittelbar danach flush aus; daher wird der Wert temporär am Objekt
        # abgelegt und von den kompatiblen Create-Routen nicht benötigt. Für
        # Updates empfehlen wir das dedizierte /users/{id}/rfid-Endpoint.
        if rfid_value:
            setattr(employee, "_pending_api_rfid", str(rfid_value).strip())


api_v1._resolve_employee = _resolve_employee_media_first
api_v1._set_user_fields = _set_user_fields_without_legacy_rfid


@router.post("/users/{user_id}/rfid")
def api_set_user_rfid_media(
    user_id: int,
    data: api_v1.UserRfidRequest,
    db: Session = Depends(get_db),
    token: ApiToken = Depends(api_v1.require_api_token),
):
    """Kompatibles RFID-Endpoint mit zentralem Medienspeicher."""
    api_v1.require_api_write(token)
    employee = db.query(Employee).filter(Employee.id == user_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")

    uid = (data.rfid_code or "").strip()
    if not uid:
        raise HTTPException(status_code=400, detail="rfid_code erforderlich")

    try:
        medium = add_rfid_medium(
            db,
            employee.id,
            uid,
            name="API RFID-Medium",
            media_type="rfid",
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

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
