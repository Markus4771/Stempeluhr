"""Eigenständiges RFID-Plugin mit Legacy-Kompatibilität."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from app.models import Employee
from app.services.auth_credentials import EmployeeAuthCredential, credential_identifier_hash
from app.services.rfid_media import resolve_employee_by_rfid
from .base import AuthenticationPlugin, AuthPluginMetadata, AuthResult


class RfidAuthenticationPlugin(AuthenticationPlugin):
    metadata = AuthPluginMetadata(
        key="rfid",
        name="RFID",
        version="1.2.0",
        description="RFID-Karten, RFID-Transponder und kompatible RFID-Medien.",
        credential_types=("rfid",),
        required_capabilities=("rfid",),
        supports_enrollment=True,
        supports_diagnostics=True,
    )

    def authenticate(self, db: Any, credential: str, context: dict[str, Any] | None = None) -> AuthResult:
        identifier_hash = credential_identifier_hash("rfid", credential)
        generic = db.query(EmployeeAuthCredential).filter(
            EmployeeAuthCredential.provider == "rfid",
            EmployeeAuthCredential.identifier_hash == identifier_hash,
            EmployeeAuthCredential.active.is_(True),
        ).first()
        if generic:
            employee = db.query(Employee).filter(Employee.id == generic.employee_id, Employee.active.is_(True)).first()
            if employee:
                generic.last_used_at = datetime.now(); generic.updated_at = datetime.now()
                return AuthResult(True, employee_id=employee.id, credential_id=generic.id, message="RFID-Medium erkannt", metadata={"provider": "rfid", "medium_name": generic.display_name, "credential_type": generic.credential_type, "terminal_id": (context or {}).get("terminal_id")})

        employee, medium = resolve_employee_by_rfid(db, credential)
        if not employee:
            return AuthResult(False, message="RFID-Medium nicht bekannt")
        # Ein im gemeinsamen Altmodell ausdrücklich als NFC gespeichertes Medium
        # darf nicht mehr vom RFID-Plugin übernommen werden.
        if medium and getattr(medium, "media_type", "rfid") in {"nfc_tag", "nfc_ring"}:
            return AuthResult(False, message="Medium gehört zum NFC-Plugin")
        return AuthResult(True, employee_id=employee.id, credential_id=getattr(medium, "id", None), message="RFID-Medium erkannt", metadata={"provider": "rfid", "medium_name": getattr(medium, "name", "Bestehende RFID-Zuordnung"), "terminal_id": (context or {}).get("terminal_id"), "legacy": True})

    def start_enrollment(self, db: Any, employee_id: int, terminal_id: int | None = None) -> dict[str, Any]:
        return {"status": "ready", "provider": "rfid", "employee_id": employee_id, "terminal_id": terminal_id, "message": "RFID-Anlernen kann am ausgewählten Terminal gestartet werden."}

    def diagnostics(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"status": "ok", "provider": "rfid", "required_capabilities": ["rfid"], "message": "RFID-Plugin ist getrennt vom NFC-Plugin aktiv."}


plugin = RfidAuthenticationPlugin()
