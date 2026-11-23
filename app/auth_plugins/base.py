"""Einheitliche Schnittstelle für Anmelde-Plugins der Stempeluhr 6.x."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class AuthPluginMetadata:
    key: str
    name: str
    version: str
    description: str
    credential_types: tuple[str, ...]
    required_capabilities: tuple[str, ...] = ()
    supports_enrollment: bool = True
    supports_diagnostics: bool = False
    builtin: bool = True
    settings_schema: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["credential_types"] = list(self.credential_types)
        data["required_capabilities"] = list(self.required_capabilities)
        return data


@dataclass
class AuthResult:
    success: bool
    employee_id: int | None = None
    credential_id: int | None = None
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class AuthenticationPlugin(ABC):
    """Vertrag, den jedes Anmeldeverfahren implementieren muss."""

    metadata: AuthPluginMetadata

    def initialize(self) -> None:
        """Optionale Initialisierung beim Serverstart."""

    def shutdown(self) -> None:
        """Optionale Freigabe von Ressourcen beim Herunterfahren."""

    @abstractmethod
    def authenticate(self, db: Any, credential: str, context: dict[str, Any] | None = None) -> AuthResult:
        """Prüft ein Anmeldemedium und liefert ein einheitliches Ergebnis."""

    def start_enrollment(self, db: Any, employee_id: int, terminal_id: int | None = None) -> dict[str, Any]:
        raise NotImplementedError("Dieses Plugin unterstützt kein Anlernen")

    def cancel_enrollment(self, db: Any, enrollment_id: str) -> None:
        return None

    def diagnostics(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"status": "ok", "message": "Keine Diagnoseinformationen vorhanden"}
