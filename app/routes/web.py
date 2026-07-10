from fastapi import APIRouter

from . import dashboard, employees, reports, corrections, privacy_audit, backup, vacation, plausibility
from app.modules.developer import routes as developer
from . import email_settings, departments, api_settings, terminals, time_settings, https_settings
from . import security_general, offboarding, dsgvo, absence_types, kiosk_settings, monitoring, setup_wizard, raspberry_monitor, onboarding

router = APIRouter()

for module in (
    dashboard, employees, reports, corrections, privacy_audit, backup, vacation, plausibility,
    email_settings, departments, api_settings, terminals, time_settings, https_settings,
    security_general, offboarding, dsgvo, absence_types, kiosk_settings, monitoring, setup_wizard, raspberry_monitor, onboarding, developer,
):
    router.include_router(module.router)

# Re-Exports für bestehende main.py / Scheduler-Kompatibilität
ensure_dsgvo_settings = dsgvo.ensure_dsgvo_settings
run_dsgvo_cleanup = dsgvo.run_dsgvo_cleanup
