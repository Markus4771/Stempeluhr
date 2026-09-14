"""Handy-Plugin für stabile, tokenbasierte Geräteanmeldung.

Smartphones werden absichtlich nicht über ihre NFC-UID identifiziert, da diese
je nach Gerät und Betriebsart wechseln kann. Stattdessen erhält jedes gekoppelte
Gerät einen zufälligen, dauerhaft gespeicherten Geräte-Token.
"""
from __future__ import annotations

import secrets
from datetime import datetime
from typing import Any

from app.models import Employee
from app.services.auth_credentials import (
    EmployeeAuthCredential,
    add_auth_credential,
    credential_identifier_hash,
)
from .base import AuthenticationPlugin, AuthPluginMetadata, AuthResult


class MobileAppAuthenticationPlugin(AuthenticationPlugin):
    metadata = AuthPluginMetadata(
        key="mobile_app",
        name="Handy",
        version="1.1.0",
        description="Sichere Handy-Anmeldung über einen stabilen Geräte-Token statt wechselnder NFC-UID.",
        credential_types=("mobile_device",),
        required_capabilities=(),
        supports_enrollment=True,
        supports_diagnostics=True,
    )

    def authenticate(self, db: Any, credential: str, context: dict[str, Any] | None = None) -> AuthResult:
        token = str(credential or "").strip()
        if not token:
            return AuthResult(False, message="Kein Handy-Token übermittelt")

        identifier_hash = credential_identifier_hash(self.metadata.key, token)
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
            return AuthResult(False, message="Handy ist nicht gekoppelt")

        employee = db.query(Employee).filter(
            Employee.id == row.employee_id,
            Employee.active.is_(True),
        ).first()
        if not employee:
            return AuthResult(False, message="Mitarbeiter ist nicht aktiv")

        row.last_used_at = datetime.now()
        row.updated_at = datetime.now()
        return AuthResult(
            True,
            employee_id=employee.id,
            credential_id=row.id,
            message="Handy erkannt",
            metadata={
                "provider": self.metadata.key,
                "credential_type": row.credential_type,
                "terminal_id": (context or {}).get("terminal_id"),
            },
        )

    def enroll_device(
        self,
        db: Any,
        employee_id: int,
        *,
        display_name: str = "Smartphone",
        device_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Erzeugt ein neues Smartphone-Credential.

        Der Klartext-Token wird ausschließlich in dieser Antwort zurückgegeben.
        In der Datenbank speichert ``add_auth_credential`` nur seinen Hash. Der
        mobile Client muss den Token anschließend sicher auf dem Gerät ablegen.
        """
        employee = db.query(Employee).filter(
            Employee.id == employee_id,
            Employee.active.is_(True),
        ).first()
        if not employee:
            raise ValueError("Aktiver Mitarbeiter nicht gefunden")

        token = secrets.token_urlsafe(32)
        row = add_auth_credential(
            db,
            employee_id=employee.id,
            provider=self.metadata.key,
            credential_type="mobile_device",
            identifier=token,
            display_name=str(display_name or "Smartphone").strip() or "Smartphone",
            metadata=device_metadata or {},
        )
        db.flush()
        return {
            "status": "enrolled",
            "provider": self.metadata.key,
            "employee_id": employee.id,
            "credential_id": row.id,
            "credential_type": row.credential_type,
            "display_name": row.display_name,
            "token": token,
        }

    def start_enrollment(self, db: Any, employee_id: int, terminal_id: int | None = None) -> dict[str, Any]:
        employee = db.query(Employee).filter(
            Employee.id == employee_id,
            Employee.active.is_(True),
        ).first()
        if not employee:
            raise ValueError("Aktiver Mitarbeiter nicht gefunden")
        return {
            "status": "pairing_required",
            "provider": self.metadata.key,
            "employee_id": employee.id,
            "terminal_id": terminal_id,
            "mode": "device_pairing",
            "message": "Smartphone koppeln; die NFC-UID wird nicht als Identität gespeichert.",
        }

    def diagnostics(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "status": "ok",
            "provider": self.metadata.key,
            "credential_type": "mobile_device",
            "token_storage": "sha256",
            "message": "Tokenbasierte Handy-Anmeldung aktiv; NFC-UID-Randomisierung wird nicht als Identität verwendet.",
        }


plugin = MobileAppAuthenticationPlugin()
