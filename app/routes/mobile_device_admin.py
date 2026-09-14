"""Admin-API für gekoppelte Smartphones.

Die API verwaltet ausschließlich provider='mobile_app'. RFID-/NFC-UID-Medien
bleiben vollständig in employee_rfid_media und werden hier nicht verändert.
"""
from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Employee
from app.services.auth_credentials import (
    EmployeeAuthCredential,
    activate_auth_credential,
    revoke_auth_credential,
)
from .common import log_action, require_admin_response

router = APIRouter(prefix="/api/admin/mobile-devices", tags=["Mobile devices"])
PROVIDER = "mobile_app"


def _authorized(request: Request, db: Session):
    user, redirect = require_admin_response(request, db)
    if redirect:
        return None, JSONResponse({"status": "error", "message": "Admin-Anmeldung erforderlich"}, status_code=401)
    return user, None


def _row_json(row: EmployeeAuthCredential) -> dict:
    try:
        metadata = json.loads(row.metadata_json or "{}")
    except Exception:
        metadata = {}
    return {
        "id": row.id,
        "employee_id": row.employee_id,
        "provider": row.provider,
        "credential_type": row.credential_type,
        "display_name": row.display_name,
        "active": bool(row.active),
        "identifier_hint": row.identifier_hint,
        "created_at": row.created_at.isoformat(timespec="seconds") if row.created_at else None,
        "updated_at": row.updated_at.isoformat(timespec="seconds") if row.updated_at else None,
        "last_used_at": row.last_used_at.isoformat(timespec="seconds") if row.last_used_at else None,
        "revoked_at": row.revoked_at.isoformat(timespec="seconds") if row.revoked_at else None,
        "revoked_reason": row.revoked_reason,
        "metadata": metadata,
    }


@router.get("/employees/{employee_id}")
def list_mobile_devices(employee_id: int, request: Request, db: Session = Depends(get_db)):
    user, error = _authorized(request, db)
    if error:
        return error
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        return JSONResponse({"status": "error", "message": "Mitarbeiter nicht gefunden"}, status_code=404)
    rows = (
        db.query(EmployeeAuthCredential)
        .filter(
            EmployeeAuthCredential.employee_id == employee_id,
            EmployeeAuthCredential.provider == PROVIDER,
        )
        .order_by(EmployeeAuthCredential.id.desc())
        .all()
    )
    return {
        "status": "ok",
        "employee_id": employee.id,
        "employee": f"{employee.first_name} {employee.last_name}",
        "devices": [_row_json(row) for row in rows],
    }


@router.post("/{credential_id}/revoke")
def revoke_mobile_device(credential_id: int, request: Request, db: Session = Depends(get_db)):
    user, error = _authorized(request, db)
    if error:
        return error
    row = db.query(EmployeeAuthCredential).filter(
        EmployeeAuthCredential.id == credential_id,
        EmployeeAuthCredential.provider == PROVIDER,
    ).first()
    if not row:
        return JSONResponse({"status": "error", "message": "Smartphone nicht gefunden"}, status_code=404)
    try:
        revoke_auth_credential(db, row.id, "Smartphone durch Administrator gesperrt")
        db.commit()
        log_action(db, user.employee_number, "mobile_device_revoked", "employee_auth_credentials", str(row.id), f"employee={row.employee_id}; name={row.display_name}")
        return {"status": "ok", "message": "Smartphone wurde gesperrt", "device": _row_json(row)}
    except ValueError as exc:
        db.rollback()
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=400)


@router.post("/{credential_id}/activate")
def activate_mobile_device(credential_id: int, request: Request, db: Session = Depends(get_db)):
    user, error = _authorized(request, db)
    if error:
        return error
    row = db.query(EmployeeAuthCredential).filter(
        EmployeeAuthCredential.id == credential_id,
        EmployeeAuthCredential.provider == PROVIDER,
    ).first()
    if not row:
        return JSONResponse({"status": "error", "message": "Smartphone nicht gefunden"}, status_code=404)
    try:
        activate_auth_credential(db, row.id)
        db.commit()
        log_action(db, user.employee_number, "mobile_device_activated", "employee_auth_credentials", str(row.id), f"employee={row.employee_id}; name={row.display_name}")
        return {"status": "ok", "message": "Smartphone wurde wieder aktiviert", "device": _row_json(row)}
    except ValueError as exc:
        db.rollback()
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=400)


@router.delete("/{credential_id}")
def delete_mobile_device(credential_id: int, request: Request, db: Session = Depends(get_db)):
    user, error = _authorized(request, db)
    if error:
        return error
    row = db.query(EmployeeAuthCredential).filter(
        EmployeeAuthCredential.id == credential_id,
        EmployeeAuthCredential.provider == PROVIDER,
    ).first()
    if not row:
        return JSONResponse({"status": "error", "message": "Smartphone nicht gefunden"}, status_code=404)
    employee_id = row.employee_id
    name = row.display_name
    db.delete(row)
    db.commit()
    log_action(db, user.employee_number, "mobile_device_deleted", "employee_auth_credentials", str(credential_id), f"employee={employee_id}; name={name}")
    return {"status": "ok", "message": "Smartphone wurde gelöscht", "credential_id": credential_id}
