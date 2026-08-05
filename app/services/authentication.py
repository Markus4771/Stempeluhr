"""Zentraler Dispatcher für alle Anmeldeverfahren der Stempeluhr 6.x."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.auth_plugins.base import AuthResult
from app.auth_plugins.registry import enabled_plugin
from app.models import Employee


@dataclass
class AuthenticationContext:
    provider: str
    credential: str
    terminal_name: str | None = None
    terminal_id: int | None = None
    remote_ip: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "terminal_name": self.terminal_name,
            "terminal_id": self.terminal_id,
            "remote_ip": self.remote_ip,
            **self.metadata,
        }


@dataclass
class ResolvedAuthentication:
    result: AuthResult
    employee: Employee | None
    provider: str

    @property
    def success(self) -> bool:
        return bool(self.result.success and self.employee)


def authenticate_credential(db: Session, context: AuthenticationContext) -> ResolvedAuthentication:
    """Authentifiziert ein Credential ausschließlich über ein aktiviertes Plugin.

    Der Anwendungskern kennt dadurch keine RFID-, QR-, Fingerprint- oder
    sonstige medienspezifische Suchlogik mehr.
    """
    provider = str(context.provider or "").strip().lower()
    credential = str(context.credential or "").strip()
    if not provider:
        return ResolvedAuthentication(AuthResult(False, message="Anmeldeverfahren fehlt"), None, provider)
    if not credential:
        return ResolvedAuthentication(AuthResult(False, message="Anmeldemedium fehlt"), None, provider)

    plugin = enabled_plugin(provider)
    if plugin is None:
        return ResolvedAuthentication(
            AuthResult(False, message=f"Anmelde-Plugin '{provider}' ist nicht aktiviert oder nicht installiert"),
            None,
            provider,
        )

    result = plugin.authenticate(db, credential, context.as_dict())
    employee = None
    if result.success and result.employee_id is not None:
        employee = (
            db.query(Employee)
            .filter(Employee.id == result.employee_id, Employee.active.is_(True))
            .first()
        )
        if employee is None:
            result = AuthResult(
                False,
                message="Zugeordneter Mitarbeiter ist nicht vorhanden oder inaktiv",
                metadata=dict(result.metadata or {}),
            )
    return ResolvedAuthentication(result, employee, provider)
