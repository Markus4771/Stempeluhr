from fastapi import APIRouter

from . import dashboard_privacy, dashboard, dashboard_metrics, employees, reports, report_stamps, corrections, privacy_audit, backup, vacation, plausibility, plausibility_reset, overtime_adjustments, stamp_reasons
from app.modules.developer import routes as developer
from app.modules.updates import github_routes
from app.services.absence_approval import register_absence_approval_events
from . import email_settings, departments, api_settings, terminals, time_settings, https_settings
from . import security_general, security_login, security_policies, roles, offboarding, dsgvo, absence_types, kiosk_settings, monitoring, setup_wizard, raspberry_monitor, onboarding, diagnostics, database_security, additional_programs, help_docs, privacy_notice

register_absence_approval_events()

router = APIRouter()

for module in (
    security_login,
    privacy_notice,
    dashboard_privacy, dashboard, dashboard_metrics, employees, reports, report_stamps, corrections, privacy_audit, backup, vacation, plausibility, plausibility_reset, overtime_adjustments, stamp_reasons,
    email_settings, departments, api_settings, terminals, time_settings, https_settings,
    security_general, security_policies, roles, offboarding, dsgvo, absence_types, kiosk_settings, monitoring, setup_wizard,
    raspberry_monitor, onboarding, diagnostics, database_security, additional_programs, help_docs, developer, github_routes,
):
    router.include_router(module.router)

ensure_dsgvo_settings = dsgvo.ensure_dsgvo_settings
run_dsgvo_cleanup = dsgvo.run_dsgvo_cleanup
