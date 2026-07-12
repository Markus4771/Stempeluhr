"""Zentrale, rückwärtskompatible Rollen- und Berechtigungslogik."""
from __future__ import annotations

import json
from typing import Any

PERMISSIONS: dict[str, dict[str, str]] = {
    "navigation": {
        "nav.dashboard": "Dashboard anzeigen",
        "nav.timeclock": "Zeiterfassung anzeigen",
        "nav.absence": "Abwesenheiten anzeigen",
        "nav.employees": "Mitarbeiterverwaltung anzeigen",
        "nav.corrections": "Korrekturen anzeigen",
        "nav.reports": "Auswertungen anzeigen",
        "nav.plausibility": "Plausibilitätsprüfung anzeigen",
        "nav.settings": "Systemeinstellungen anzeigen",
        "nav.audit": "Audit-Protokoll anzeigen",
        "nav.monitoring": "Monitoring anzeigen",
    },
    "employees": {
        "employees.view": "Mitarbeiter ansehen",
        "employees.manage": "Mitarbeiter anlegen und bearbeiten",
        "employees.invite": "Onboarding-Einladungen versenden",
    },
    "worktime": {
        "corrections.manage": "Alle Korrekturen bearbeiten",
        "reports.all": "Auswertungen aller Mitarbeiter ansehen",
        "absence.approve": "Abwesenheiten genehmigen",
        "plausibility.manage": "Plausibilitätsfälle bearbeiten",
    },
    "system": {
        "system.settings": "Allgemeine Systemeinstellungen verwalten",
        "system.backup": "Backup und Restore verwalten",
        "system.updates": "Updates installieren",
        "system.diagnostics": "Systemdiagnose öffnen",
        "system.audit": "Audit-Protokoll ansehen",
        "system.monitoring": "Monitoring öffnen",
    },
}

DEFAULT_ROLE_PERMISSIONS: dict[str, set[str]] = {
    "Administrator": {"*"},
    "Personal": {
        "nav.dashboard", "nav.timeclock", "nav.absence", "nav.employees", "nav.corrections",
        "nav.reports", "nav.plausibility", "employees.view", "employees.manage", "employees.invite",
        "corrections.manage", "reports.all", "absence.approve", "plausibility.manage",
    },
    "Teamleiter": {
        "nav.dashboard", "nav.timeclock", "nav.absence", "nav.corrections", "nav.reports",
        "nav.plausibility", "plausibility.manage",
    },
    "Mitarbeiter": {"nav.dashboard", "nav.timeclock", "nav.absence", "nav.reports"},
}


def all_permission_keys() -> set[str]:
    return {key for group in PERMISSIONS.values() for key in group}


def parse_permissions(raw: Any) -> set[str]:
    if isinstance(raw, set):
        return set(raw)
    if isinstance(raw, (list, tuple)):
        return {str(item) for item in raw if str(item)}
    text = str(raw or "").strip()
    if not text:
        return set()
    try:
        value = json.loads(text)
        if isinstance(value, list):
            return {str(item) for item in value if str(item)}
        if isinstance(value, dict):
            return {str(key) for key, enabled in value.items() if enabled}
    except Exception:
        pass
    return {item.strip() for item in text.split(",") if item.strip()}


def role_permissions(role: Any) -> set[str]:
    if not role:
        return set()
    name = str(getattr(role, "name", "") or "")
    if name == "Administrator":
        return {"*"}
    parsed = parse_permissions(getattr(role, "permissions", ""))
    return parsed or set(DEFAULT_ROLE_PERMISSIONS.get(name, set()))


def has_permission(user: Any, permission: str) -> bool:
    if not user:
        return False
    role = getattr(user, "role", None)
    permissions = role_permissions(role)
    return "*" in permissions or permission in permissions


def serialize_permissions(values: list[str] | set[str]) -> str:
    allowed = all_permission_keys()
    cleaned = sorted({str(value) for value in values if str(value) in allowed})
    return json.dumps(cleaned, ensure_ascii=False, separators=(",", ":"))


def permission_labels() -> dict[str, dict[str, str]]:
    return PERMISSIONS
