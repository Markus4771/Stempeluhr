"""Eigenständiges NFC-Plugin für NFC-Tags, Ringe und kompatible Medien."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from app.models import Employee
from app.services.auth_credentials import EmployeeAuthCredential, credential_identifier_hash
from app.services.rfid_media import resolve_employee_by_rfid
from .base import AuthenticationPlugin, AuthPluginMetadata, AuthResult


class NfcAuthenticationPlugin(AuthenticationPlugin):
    metadata = AuthPluginMetadata(
        key="nfc",
        name="NFC",
        version="1.0.0",
        description="NFC-Tags, NFC-Ringe und andere feste NFC-Anmeldemedien.",
        credential_types=("nfc_tag", "nfc_ring"),
        required_capabilities=("nfc",),
        supports_enrollment=True,
        supports_diagnostics=True,
    )

    def authenticate(self, db: Any, credential: str, context: dict[str, Any] | None = None) -> AuthResult:
        identifier_hash = credential_identifier_hash("nfc", credential)
        generic = (
            db.query(EmployeeAuthCredential)
            .filter(
                EmployeeAuthCredential.provider == "nfc",
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
                    message="NFC-Medium erkannt",
                    metadata={
                        "provider": self.metadata.key,
                        "medium_name": generic.display_name,
                        "credential_type": generic.credential_type,
                        "terminal_id": (context or {}).get("terminal_id"),
                    },
                )

        # Übergang: bestehende NFC-Medien liegen in 5.x/6.0 noch im gemeinsamen RFID-Medienmodell.
        employee, medium = resolve_employee_by_rfid(db, credential)
        if not employee:
            return AuthResult(False, message="NFC-Medium nicht bekannt")
        media_type = getattr(medium, "media_type", "") if medium else ""
        if media_type not in {"nfc_ring", "nfc_tag"}:
            return AuthResult(False, message="Medium ist nicht als NFC-Medium registriert")
        return AuthResult(
            True,
            employee_id=employee.id,
            credential_id=getattr(medium, "id", None),
            message="NFC-Medium erkannt",
            metadata={
                "provider": self.metadata.key,
                "medium_name": getattr(medium, "name", "Bestehende NFC-Zuordnung"),
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
            "message": "NFC-Anlernen kann am ausgewählten Terminal gestartet werden.",
        }

    def diagnostics(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "status": "ok",
            "provider": self.metadata.key,
            "required_capabilities": list(self.metadata.required_capabilities),
            "message": "NFC-Plugin ist getrennt vom RFID-Plugin aktiv.",
        }


plugin = NfcAuthenticationPlugin()
