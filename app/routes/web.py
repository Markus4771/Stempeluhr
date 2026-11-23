from fastapi import APIRouter

# Muss vor den übrigen Web-Routen geladen werden: korrigiert den gemeinsamen
# NULL-sicheren Ausschluss des festen Systemadmins.
from . import fixed_admin_filter_fix
from . import dashboard_privacy, dashboard, dashboard_metrics_corrected, dashboard_metrics, dashboard_self_booking_extended, dashboard_self_booking, employees, report_stamps, reports, corrections, corrections_restore, privacy_audit, backup, vacation, vacation_management, plausibility, plausibility_reset, plausibility_exceptions, overtime_adjustments, stamp_reasons, terminal_hardware
from app.modules.developer import routes as developer
from app.modules.updates import github_routes
from app.services.absence_approval import register_absence_approval_events
from app.services.vacation_work_schedule import register_vacation_work_schedule_events
from . import email_settings, departments, api_settings, terminals, time_settings, https_settings
from . import security_general, security_login, security_policies, roles, offboarding, dsgvo, absence_types, kiosk_settings, monitoring, setup_wizard, raspberry_monitor, onboarding, diagnostics, database_security, additional_programs, help_docs, privacy_notice, rfid_media_admin, legacy_rfid_redirect

register_absence_approval_events()
register_vacation_work_schedule_events()

router = APIRouter()

for module in (
    security_login,
    privacy_notice,
    # Kompatibilitätsrouten müssen vor employees registriert werden. FastAPI/
    # Starlette verwendet bei identischen Pfaden die zuerst registrierte Route.
    # Alte RFID-Lern-URLs landen dadurch sicher in der zentralen Medienverwaltung.
    legacy_rfid_redirect,
    dashboard_privacy, dashboard, dashboard_metrics_corrected, dashboard_metrics, dashboard_self_booking_extended, dashboard_self_booking, employees, rfid_media_admin, report_stamps, reports, corrections, corrections_restore, privacy_audit, backup, vacation, vacation_management, plausibility, plausibility_reset, plausibility_exceptions, overtime_adjustments, stamp_reasons, terminal_hardware,
    email_settings, departments, api_settings, terminals, time_settings, https_settings,
    security_general, security_policies, roles, offboarding, dsgvo, absence_types, kiosk_settings, monitoring, setup_wizard,
    raspberry_monitor, onboarding, diagnostics, database_security, additional_programs, help_docs, developer, github_routes,
):
    router.include_router(module.router)

ensure_dsgvo_settings = dsgvo.ensure_dsgvo_settings
run_dsgvo_cleanup = dsgvo.run_dsgvo_cleanup