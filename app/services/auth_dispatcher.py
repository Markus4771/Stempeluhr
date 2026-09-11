"""Zentraler Dispatcher für alle Anmeldeverfahren der Stempeluhr 6.x."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.auth_plugins.registry import installed_plugin
from app.models import Employee


@dataclass
class AuthenticationMatch:
    success: bool
    employee: Employee | None = None
    provider: str | None = None
    credential_id: int | None = None
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


# Passive Medien kommen am aktuellen Keyboard-Wedge-Leser nur als Kennung an.
# Deshalb werden genau diese Provider in definierter Reihenfolge geprüft.
PASSIVE_MEDIA_PROVIDERS = ("rfid", "nfc")


def authenticate_credential(
    db: Session,
    credential: str,
    *,
    provider: str | None = None,
    providers: Iterable[str] | None = None,
    context: dict[str, Any] | None = None,
) -> AuthenticationMatch:
    """Authentifiziert eine Kennung über ein oder mehrere Plugins.

    Wird ``provider`` angegeben, wird nur dieses Plugin verwendet. Ohne Provider
    werden die passiven Terminal-Medien RFID und NFC geprüft. Das Ergebnis ist
    immer ein Mitarbeiter plus Provider; die Buchungslogik bleibt davon getrennt.
    """
    value = str(credential or "").strip().replace("\\r", "").replace("\\n", "")
    if not value:
        return AuthenticationMatch(False, message="Keine Anmeldekennung erkannt")

    candidates = (provider,) if provider else tuple(providers or PASSIVE_MEDIA_PROVIDERS)
    matches: list[AuthenticationMatch] = []
    errors: list[str] = []

    for key in candidates:
        plugin = installed_plugin(key)
        if not plugin:
            errors.append(f"Plugin {key} ist nicht installiert")
            continue
        result = plugin.authenticate(db, value, context=context)
        if not result.success or not result.employee_id:
            continue
        employee = db.query(Employee).filter(
            Employee.id == result.employee_id,
            Employee.active.is_(True),
        ).first()
        if not employee:
            continue
        metadata = dict(result.metadata or {})
        metadata.setdefault("provider", key)
        matches.append(AuthenticationMatch(
            True,
            employee=employee,
            provider=key,
            credential_id=result.credential_id,
            message=result.message,
            metadata=metadata,
        ))

    if not matches:
        return AuthenticationMatch(False, message="Anmeldemedium nicht bekannt" if not errors else "; ".join(errors))

    employee_ids = {match.employee.id for match in matches if match.employee}
    if len(employee_ids) > 1:
        return AuthenticationMatch(False, message="Anmeldemedium ist mehreren Mitarbeitern zugeordnet")

    # Bei Übergangsdaten kann dieselbe RFID-Kennung von beiden Legacy-Pfaden
    # gefunden werden. Dann gewinnt ein typgenauer Treffer vor einem Fallback.
    matches.sort(key=lambda match: bool(match.metadata.get("legacy")))
    return matches[0]
