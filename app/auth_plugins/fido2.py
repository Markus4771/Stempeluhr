"""FIDO2/WebAuthn-Plugin für Yubico Security Keys und Passkeys.

Wichtig: FIDO2-Credentials sind keine RFID-UIDs. Die eigentliche WebAuthn-
Challenge/Signatur wird vom Web-Endpunkt geprüft. Dieses Plugin verwaltet die
Zuordnung eines bereits verifizierten WebAuthn-Credentials zum Mitarbeiter.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from app.models import Employee
from app.services.auth_credentials import EmployeeAuthCredential, credential_identifier_hash
from .base import AuthenticationPlugin, AuthPluginMetadata, AuthResult


class Fido2AuthenticationPlugin(AuthenticationPlugin):
    metadata = AuthPluginMetadata(
        key="fido2",
        name="FIDO2 / WebAuthn",
        version="1.0.0",
        description="Yubico Security Keys und Passkeys über FIDO2/WebAuthn.",
        credential_types=("webauthn", "security_key", "passkey"),
        required_capabilities=(),
        supports_enrollment=True,
        supports_diagnostics=True,
    )

    def authenticate(self, db: Any, credential: str, context: dict[str, Any] | None = None) -> AuthResult:
        """Akzeptiert nur Credentials, deren WebAuthn-Prüfung bereits bestätigt wurde."""
        context = context or {}
        if not context.get("webauthn_verified"):
            return AuthResult(False, message="FIDO2 erfordert eine verifizierte WebAuthn-Antwort")

        credential_id = str(credential or "").strip()
        if not credential_id:
            return AuthResult(False, message="Keine FIDO2-Credential-ID übermittelt")

        identifier_hash = credential_identifier_hash(self.metadata.key, credential_id)
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
            return AuthResult(False, message="FIDO2-Sicherheitsschlüssel nicht bekannt")

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
            message="FIDO2-Sicherheitsschlüssel erkannt",
            metadata={
                "provider": self.metadata.key,
                "credential_type": row.credential_type,
                "terminal_id": context.get("terminal_id"),
            },
        )

    def start_enrollment(self, db: Any, employee_id: int, terminal_id: int | None = None) -> dict[str, Any]:
        employee = db.query(Employee).filter(
            Employee.id == employee_id,
            Employee.active.is_(True),
        ).first()
        if not employee:
            raise ValueError("Aktiver Mitarbeiter nicht gefunden")
        return {
            "status": "webauthn_registration_required",
            "provider": self.metadata.key,
            "employee_id": employee.id,
            "terminal_id": terminal_id,
            "mode": "webauthn",
            "message": "FIDO2-Sicherheitsschlüssel im Browser registrieren.",
        }

    def diagnostics(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "status": "ok",
            "provider": self.metadata.key,
            "protocol": "FIDO2/WebAuthn",
            "message": "FIDO2-Plugin installiert; WebAuthn-Challenge/Signatur muss serverseitig verifiziert werden.",
        }


plugin = Fido2AuthenticationPlugin()
