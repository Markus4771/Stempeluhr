"""RFID/NFC-Kompatibilitätsplugin für die bestehende Medienlogik."""
from __future__ import annotations

from typing import Any

from app.services.rfid_media import resolve_employee_by_rfid
from .base import AuthenticationPlugin, AuthPluginMetadata, AuthResult


class RfidAuthenticationPlugin(AuthenticationPlugin):
    metadata = AuthPluginMetadata(
        key="rfid",
        name="RFID / NFC-Tag",
        version="1.0.0",
        description="RFID-Karten, NFC-Tags, Schlüsselanhänger und kompatible Medien.",
        credential_types=("rfid", "nfc_tag", "nfc_ring"),
        required_capabilities=("rfid",),
        supports_enrollment=True,
        supports_diagnostics=True,
    )

    def authenticate(self, db: Any, credential: str, context: dict[str, Any] | None = None) -> AuthResult:
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
            "message": "RFID-Kompatibilitätsplugin ist geladen.",
        }


plugin = RfidAuthenticationPlugin()
