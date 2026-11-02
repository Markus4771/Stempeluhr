"""Sammelt die gemeinsam genutzten Routen-Module.

Dieses Paket exportiert die Route-Module, damit ``from app.routes import
...`` weiterhin funktioniert.

Hinweis zu doppelten Routen: Der hier gebaute ``router`` wird in
``app/main.py`` nicht eingebunden. Die produktiven Router kommen aus
``app/routes/web.py``, ``api.py``, ``api_v1.py`` und ``roles_rights.py``.
Die doppelt registrierten Routen entstehen nicht durch diesen Router,
sondern dadurch, dass verschiedene Module denselben Pfad bedienen
(zum Beispiel ``dashboard.py`` und ``security_login.py`` beide ``/login``).
Details in ``docs/OPTIMIERUNG.md``, Abschnitt 2.1.
"""
from fastapi import APIRouter

from . import dashboard, employees, reports, corrections, privacy_audit, backup, vacation, plausibility, stamp_reasons
from app.modules.developer import routes as developer
from app.modules.updates import github_routes
from . import email_settings, departments, api_settings, terminals, time_settings, https_settings
from . import security_general, security_login, security_policies, offboarding, dsgvo, absence_types, kiosk_settings, monitoring, setup_wizard, raspberry_monitor, onboarding, diagnostics, database_security, roles, additional_programs

router = APIRouter()

for module in (
    security_login,
    dashboard, employees, reports, corrections, privacy_audit, backup, vacation, plausibility, stamp_reasons,
    email_settings, departments, api_settings, terminals, time_settings, https_settings,
    security_general, security_policies, offboarding, dsgvo, absence_types, kiosk_settings, monitoring, setup_wizard,
    raspberry_monitor, onboarding, diagnostics, database_security, roles, additional_programs, developer, github_routes,
):
    router.include_router(module.router)

ensure_dsgvo_settings = dsgvo.ensure_dsgvo_settings
run_dsgvo_cleanup = dsgvo.run_dsgvo_cleanup
