"""Zentrale Modul-Registry für Stempeluhr Professional.

Ab 5.2.07 verwendet die Registry eine einheitliche Modul-Spezifikation. Die
produktiven Legacy-Routen bleiben weiterhin aktiv; die Registry beschreibt den
Zielzustand für automatische Navigation, Modul-Lader und Plugin-Framework.
"""
from __future__ import annotations

from typing import Dict, List

from app.modules.spec import NavigationEntry, StempeluhrModule


_MODULES: List[StempeluhrModule] = [
    StempeluhrModule("auth", "Anmeldung & Sitzungen", "1.0", "prepared", "app.routes.web", "app.modules.auth", None, note="Login bleibt zunächst im Legacy-Webrouter."),
    StempeluhrModule("dashboard", "Dashboard", "1.0", "prepared", "app.routes.dashboard", "app.modules.dashboard", None, (NavigationEntry("Dashboard", "/", ("admin","personal","teamleiter","mitarbeiter"), 10),)),
    StempeluhrModule("employees", "Mitarbeiter", "1.0", "prepared", "app.routes.employees", "app.modules.employees", None, (NavigationEntry("Mitarbeiter", "/employees", ("admin","personal"), 30),)),
    StempeluhrModule("attendance", "Zeiterfassung", "1.0", "prepared", "app.routes.web / app.routes.corrections", "app.modules.attendance", None, (NavigationEntry("Zeiterfassung", "/", ("admin","personal","teamleiter","mitarbeiter"), 20),)),
    StempeluhrModule("absences", "Abwesenheiten", "1.0", "prepared", "app.routes.vacation", "app.modules.absences", None, (NavigationEntry("Abwesenheiten", "/vacation", ("admin","personal","teamleiter","mitarbeiter"), 40),)),
    StempeluhrModule("calendar", "Kalender & CalDAV", "1.0", "prepared", "app.routes.caldav_accounts / app.caldav_service", "app.modules.calendar", None, (NavigationEntry("Kalender", "/system/caldav", ("admin",), 70),)),
    StempeluhrModule("updates", "Updateverwaltung", "1.1", "migrated", "app.routes.updates", "app.modules.updates", "app.modules.updates.routes", (NavigationEntry("Updates", "/system/settings/updates", ("admin",), 85),), note="Produktive Route liegt im Modul; alter Pfad ist Wrapper."),
    StempeluhrModule("system", "Systemeinstellungen", "1.0", "registry", "app.routes.*settings", "app.modules.system", "app.modules.system.routes", (NavigationEntry("System", "/system/settings", ("admin",), 80),), note="System-Router werden über eine Registry gebündelt."),
    StempeluhrModule("reports", "Auswertungen", "1.0", "prepared", "app.routes.reports", "app.modules.reports", None, (NavigationEntry("Berichte", "/reports", ("admin","personal","teamleiter"), 50),)),
    StempeluhrModule("api", "API", "1.0", "prepared", "app.routes.api / app.routes.api_v1", "app.modules.api", None, (NavigationEntry("API", "/docs", ("admin",), 90),)),
    StempeluhrModule("rfid", "RFID & Terminals", "1.0", "prepared", "app.routes.terminals", "app.modules.rfid", None, (NavigationEntry("Terminals", "/system/terminals", ("admin",), 75),)),
    StempeluhrModule("developer", "Entwicklerkonsole", "1.1", "migrated", "-", "app.modules.developer", "app.modules.developer.routes", (NavigationEntry("Entwickler", "/system/developer", ("admin",), 95),), note="Diagnose- und Entwicklerwerkzeuge ab 5.2.06, erweitert in 5.2.07."),
]


def get_modules() -> List[StempeluhrModule]:
    """Gibt alle bekannten Module in stabiler Reihenfolge zurück."""
    return list(_MODULES)


def get_modules_as_dicts() -> List[Dict[str, object]]:
    """JSON-/Template-freundliche Variante der Modulübersicht."""
    return [module.as_dict() for module in _MODULES]


def get_module_status() -> Dict[str, int]:
    """Zählt Module nach Status."""
    result: Dict[str, int] = {}
    for module in _MODULES:
        result[module.status] = result.get(module.status, 0) + 1
    return result


def find_module(key: str) -> StempeluhrModule | None:
    """Sucht ein Modul anhand seines technischen Schlüssels."""
    for module in _MODULES:
        if module.key == key:
            return module
    return None


def get_navigation_as_dicts() -> list[dict[str, object]]:
    """Erzeugt eine spätere automatische Navigation aus Moduldaten."""
    entries: list[dict[str, object]] = []
    for module in _MODULES:
        for nav in module.navigation:
            data = nav.as_dict()
            data["module"] = module.key
            data["module_title"] = module.title
            entries.append(data)
    return sorted(entries, key=lambda item: int(item.get("order", 100)))
