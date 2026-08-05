"""RFID/NFC-Plugin mit 6.x-Anmeldemedien und Legacy-Kompatibilität."""
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
        name="RFID / NFC-Tag",
        version="1.1.0",
        description="RFID-Karten, NFC-Tags, Schlüsselanhänger und kompatible Medien.",
        credential_types=("rfid", "nfc_tag", "nfc_ring"),
        required_capabilities=("rfid",),
        supports_enrollment=True,
        supports_diagnostics=True,
    )

    def authenticate(self, db: Any, credential: str, context: dict[str, Any] | None = None) -> AuthResult:
        identifier_hash = credential_identifier_hash("rfid", credential)
        generic = (
            db.query(EmployeeAuthCredential)
            .filter(
                EmployeeAuthCredential.provider == "rfid",
                EmployeeAuthCredential.identifier_hash == identifier_hash,
                EmployeeAuthCredential.active.is_(True),
            )
            .first()
        )
        if generic:
            employee = db.query(Employee).filter(
                Employee.id == generic.employee_id,
                Employee.active.is_(True),
            ).first()
            if employee:
                generic.last_used_at = datetime.now()
                generic.updated_at = datetime.now()
                return AuthResult(
                    True,
                    employee_id=employee.id,
                    credential_id=generic.id,
                    message="Medium erkannt",
                    metadata={
                        "provider": self.metadata.key,
                        "medium_name": generic.display_name,
                        "credential_type": generic.credential_type,
                        "terminal_id": (context or {}).get("terminal_id"),
                    },
                )

        # Übergangsweg für bestehende 5.x-Daten und noch nicht migrierte Installationen.
        employee, medium = resolve_employee_by_rfid(db, credential)
        if not employee:
            return AuthResult(False, message="RFID-/NFC-Medium nicht bekannt")
        return AuthResult(
            True,
            employee_id=employee.id,
            credential_id=getattr(medium, "id", None),
            message="Medium erkannt",
            metadata={
                "provider": self.metadata.key,
                "medium_name": getattr(medium, "name", "Bestehende RFID-Zuordnung"),
                "terminal_id": (context or {}).get("terminal_id"),
                "legacy": True,
            },
        )

    def start_enrollment(self, db: Any, employee_id: int, terminal_id: int | None = None) -> dict[str, Any]:
        return {
            "status": "ready",
            "provider": self.metadata.key,
            "employee_id": employee_id,
            "terminal_id": terminal_id,
            "message": "RFID-/NFC-Anlernen kann am ausgewählten Terminal gestartet werden.",
        }

    def diagnostics(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "status": "ok",
            "provider": self.metadata.key,
            "required_capabilities": list(self.metadata.required_capabilities),
            "message": "RFID-Plugin verwendet das allgemeine 6.x-Anmeldemedienmodell.",
        }


plugin = RfidAuthenticationPlugin()
