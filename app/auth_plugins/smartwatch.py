"""Smartwatch-Plugin für stabile, tokenbasierte Geräteanmeldung."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from app.models import Employee
from app.services.auth_credentials import EmployeeAuthCredential, credential_identifier_hash
from .base import AuthenticationPlugin, AuthPluginMetadata, AuthResult


class SmartwatchAuthenticationPlugin(AuthenticationPlugin):
    metadata = AuthPluginMetadata(
        key="smartwatch",
        name="Smartwatch",
        version="1.0.0",
        description="Smartwatch-Anmeldung über einen stabilen Geräte-Token statt wechselnder NFC-UID.",
        credential_types=("smartwatch_device",),
        required_capabilities=(),
        supports_enrollment=True,
        supports_diagnostics=True,
    )

    def authenticate(self, db: Any, credential: str, context: dict[str, Any] | None = None) -> AuthResult:
        identifier_hash = credential_identifier_hash(self.metadata.key, credential)
        row = (
            db.query(EmployeeAuthCredential)
            .filter(
                EmployeeAuthCredential.provider == self.metadata.key,
                EmployeeAuthCredential.identifier_hash == identifier_hash,
                EmployeeAuthCredential.active.is_(True),
            )
            .first()
        )
        if not row:
            return AuthResult(False, message="Smartwatch ist nicht gekoppelt")
        employee = db.query(Employee).filter(Employee.id == row.employee_id, Employee.active.is_(True)).first()
        if not employee:
            return AuthResult(False, message="Mitarbeiter ist nicht aktiv")
        row.last_used_at = datetime.now()
        row.updated_at = datetime.now()
        return AuthResult(
            True,
            employee_id=employee.id,
            credential_id=row.id,
            message="Smartwatch erkannt",
            metadata={"provider": self.metadata.key, "terminal_id": (context or {}).get("terminal_id")},
        )

    def start_enrollment(self, db: Any, employee_id: int, terminal_id: int | None = None) -> dict[str, Any]:
        return {
            "status": "pairing_required",
            "provider": self.metadata.key,
            "employee_id": employee_id,
            "terminal_id": terminal_id,
            "mode": "device_pairing",
            "message": "Smartwatches werden über einen stabilen Geräte-Token gekoppelt. Eine wechselnde NFC-UID wird nicht gespeichert.",
        }

    def diagnostics(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "status": "ok",
            "provider": self.metadata.key,
            "message": "Tokenbasierte Smartwatch-Anmeldung aktiv.",
        }


plugin = SmartwatchAuthenticationPlugin()
