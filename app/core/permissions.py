"""Zentrale Rollen- und Rechtebasis.

5.2.07 führt diese Datei als gemeinsame Quelle ein. Bestehende Routen bleiben
zunächst kompatibel und können schrittweise auf diese Funktionen umgestellt
werden.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Any

ROLE_ADMIN = "admin"
ROLE_PERSONAL = "personal"
ROLE_TEAMLEAD = "teamleiter"
ROLE_EMPLOYEE = "mitarbeiter"
ROLE_GUEST = "gast"

ROLE_ORDER = [ROLE_GUEST, ROLE_EMPLOYEE, ROLE_TEAMLEAD, ROLE_PERSONAL, ROLE_ADMIN]


@dataclass(frozen=True)
class PermissionRule:
    key: str
    title: str
    allowed_roles: tuple[str, ...]


PERMISSIONS: dict[str, PermissionRule] = {
    "developer.view": PermissionRule("developer.view", "Entwicklerkonsole anzeigen", (ROLE_ADMIN,)),
    "system.manage": PermissionRule("system.manage", "Systemeinstellungen verwalten", (ROLE_ADMIN,)),
    "updates.manage": PermissionRule("updates.manage", "Updates installieren", (ROLE_ADMIN,)),
    "employees.manage": PermissionRule("employees.manage", "Mitarbeiter verwalten", (ROLE_ADMIN, ROLE_PERSONAL)),
    "attendance.manage": PermissionRule("attendance.manage", "Zeiten verwalten", (ROLE_ADMIN, ROLE_PERSONAL, ROLE_TEAMLEAD)),
    "reports.view": PermissionRule("reports.view", "Auswertungen anzeigen", (ROLE_ADMIN, ROLE_PERSONAL, ROLE_TEAMLEAD)),
}


def normalize_role(role: str | None) -> str:
    value = (role or "").strip().lower()
    aliases = {
        "administrator": ROLE_ADMIN,
        "admin": ROLE_ADMIN,
        "personal": ROLE_PERSONAL,
        "hr": ROLE_PERSONAL,
        "teamleiter": ROLE_TEAMLEAD,
        "teamlead": ROLE_TEAMLEAD,
        "mitarbeiter": ROLE_EMPLOYEE,
        "employee": ROLE_EMPLOYEE,
    }
    return aliases.get(value, value or ROLE_GUEST)


def user_role(user: Any) -> str:
    if user is None:
        return ROLE_GUEST
    for attr in ("role", "rolle", "role_name"):
        if hasattr(user, attr):
            return normalize_role(getattr(user, attr))
    if isinstance(user, dict):
        return normalize_role(user.get("role") or user.get("rolle"))
    return ROLE_GUEST


def has_role(user: Any, roles: Iterable[str]) -> bool:
    allowed = {normalize_role(role) for role in roles}
    return user_role(user) in allowed


def has_permission(user: Any, permission_key: str) -> bool:
    rule = PERMISSIONS.get(permission_key)
    if not rule:
        return False
    return has_role(user, rule.allowed_roles)


def permissions_as_dicts() -> list[dict[str, object]]:
    return [
        {"key": rule.key, "title": rule.title, "allowed_roles": list(rule.allowed_roles)}
        for rule in PERMISSIONS.values()
    ]
