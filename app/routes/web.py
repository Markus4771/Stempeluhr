from fastapi import APIRouter

from . import dashboard, employees, reports, corrections, privacy_audit, backup, vacation, plausibility
from app.modules.developer import routes as developer
from app.modules.updates import github_routes
from . import email_settings, departments, api_settings, terminals, time_settings, https_settings
from . import security_general, security_login, security_policies, roles, offboarding, dsgvo, absence_types, kiosk_settings, monitoring, setup_wizard, raspberry_monitor, onboarding, diagnostics, database_security, additional_programs

router = APIRouter()

for module in (
    security_login,
    dashboard, employees, reports, corrections, privacy_audit, backup, vacation, plausibility,
    email_settings, departments, api_settings, terminals, time_settings, https_settings,
    security_general, security_policies, roles, offboarding, dsgvo, absence_types, kiosk_settings, monitoring, setup_wizard,
    raspberry_monitor, onboarding, diagnostics, database_security, additional_programs, developer, github_routes,
):
    router.include_router(module.router)

ensure_dsgvo_settings = dsgvo.ensure_dsgvo_settings
run_dsgvo_cleanup = dsgvo.run_dsgvo_cleanup
