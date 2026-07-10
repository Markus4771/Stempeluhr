"""System-Modul-Registry.

In 5.2.04 wird die System-Modularisierung vorbereitet, ohne produktive Routen
riskant zu verschieben. Diese Registry dokumentiert und bündelt die bestehenden
System-Router. Spätere Versionen können die einzelnen Dateien schrittweise aus
``app.routes`` nach ``app.modules.system`` übernehmen.
"""
from app.routes import (
    time_settings,
    security_general,
    backup,
    dsgvo,
    https_settings,
    email_settings,
    api_settings,
    departments,
    terminals,
    offboarding,
    privacy_audit,
)

ROUTERS = [
    time_settings.router,
    security_general.router,
    backup.router,
    dsgvo.router,
    https_settings.router,
    email_settings.router,
    api_settings.router,
    departments.router,
    terminals.router,
    offboarding.router,
    privacy_audit.router,
]


def get_routers():
    """Liefert die aktuell zusammengehörigen System-Router."""
    return list(ROUTERS)
