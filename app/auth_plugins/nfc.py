"""Eigenständiges NFC-Plugin für NFC-Tags, Ringe und kompatible Medien."""
from __future__ import annotations

from typing import Any

from app.services.rfid_media import resolve_employee_by_rfid
from .base import AuthenticationPlugin, AuthPluginMetadata, AuthResult


class NfcAuthenticationPlugin(AuthenticationPlugin):
    metadata = AuthPluginMetadata(
        key="nfc",
        name="NFC",
        version="1.1.0",
        description="NFC-Tags, NFC-Ringe und andere feste NFC-Anmeldemedien.",
        credential_types=("nfc_tag", "nfc_ring"),
        required_capabilities=("nfc",),
        supports_enrollment=True,
        supports_diagnostics=True,
    )

    def authenticate(self, db: Any, credential: str, context: dict[str, Any] | None = None) -> AuthResult:
        """Authentifiziert NFC ausschließlich über employee_rfid_media.

        RFID und NFC sind UID-basierte physische Medien und haben ab Stempeluhr
        6.0 genau eine maßgebliche Datenquelle. Alte generische
        employee_auth_credentials-Zeilen werden bewusst nicht mehr ausgewertet,
        damit veraltete Spiegelungen niemals eine aktuelle Medienzuordnung
        überschreiben können.
        """
        employee, medium = resolve_employee_by_rfid(db, credential)
        if not employee or not medium:
            return AuthResult(False, message="NFC-Medium nicht bekannt")

        media_type = getattr(medium, "media_type", "") or ""
        if media_type not in {"nfc_ring", "nfc_tag"}:
            return AuthResult(False, message="Medium ist nicht als NFC-Medium registriert")

        return AuthResult(
            True,
            employee_id=employee.id,
            credential_id=medium.id,
            message="NFC-Medium erkannt",
            metadata={
                "provider": self.metadata.key,
                "medium_name": medium.name,
                "credential_type": media_type,
                "terminal_id": (context or {}).get("terminal_id"),
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
            "message": "NFC-Plugin verwendet die zentrale RFID-/NFC-Medienverwaltung.",
        }


plugin = NfcAuthenticationPlugin()
