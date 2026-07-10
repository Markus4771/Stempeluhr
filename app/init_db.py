from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import Base, engine, SessionLocal
from .models import Employee, Setting, Role, Department
from .security import hash_password
from .db_migrations import run_migrations
from app.core.config import BACKUP_DIR


def model_has(model, field: str) -> bool:
    return hasattr(model, field)


def safe_add_setting(db: Session, key: str, value: str):
    existing = db.query(Setting).filter(Setting.key == key).first()
    if existing:
        return existing
    row = Setting(key=key, value=str(value))
    db.add(row)
    try:
        db.flush()
        return row
    except IntegrityError:
        db.rollback()
        return db.query(Setting).filter(Setting.key == key).first()


def safe_add_role(db: Session, name: str, description: str = "", permissions: str = "{}"):
    role = db.query(Role).filter(Role.name == name).first()
    if role:
        return role

    kwargs = {"name": name}
    if model_has(Role, "description"):
        kwargs["description"] = description
    if model_has(Role, "permissions"):
        kwargs["permissions"] = permissions

    role = Role(**kwargs)
    db.add(role)
    try:
        db.flush()
        return role
    except IntegrityError:
        db.rollback()
        return db.query(Role).filter(Role.name == name).first()


def safe_add_department(db: Session, name: str, description: str = "Standard-Abteilung"):
    if not hasattr(Department, "name"):
        return None
    dept = db.query(Department).filter(Department.name == name).first()
    if dept:
        return dept

    kwargs = {"name": name}
    if model_has(Department, "description"):
        kwargs["description"] = description
    if model_has(Department, "active"):
        kwargs["active"] = True

    dept = Department(**kwargs)
    db.add(dept)
    try:
        db.flush()
        return dept
    except IntegrityError:
        db.rollback()
        return db.query(Department).filter(Department.name == name).first()


def create_or_update_fixed_admin(db: Session, admin_role):
    fixed_admin = db.query(Employee).filter(Employee.employee_number == "admin").first()
    if fixed_admin:
        if admin_role and model_has(Employee, "role_id") and not fixed_admin.role_id:
            fixed_admin.role_id = admin_role.id
        return fixed_admin

    kwargs = {}

    # Nur Felder setzen, die das aktuelle Employee-Modell wirklich besitzt.
    possible = {
        "employee_number": "admin",
        "first_name": "Fester",
        "last_name": "Admin",
        "email": "",
        "password_hash": hash_password("admin123"),
        "active": True,
        "is_admin": True,
        "weekly_hours": 40,
        "vacation_days_total": 30,
        "vacation_days_used": 0,
        "overtime_balance": 0,
    }

    for field, value in possible.items():
        if model_has(Employee, field):
            kwargs[field] = value

    if admin_role and model_has(Employee, "role_id"):
        kwargs["role_id"] = admin_role.id

    fixed_admin = Employee(**kwargs)
    db.add(fixed_admin)
    db.flush()
    return fixed_admin


def sync_emergency_admin(db: Session):
    if not model_has(Employee, "active"):
        return

    admin_role = db.query(Role).filter(Role.name == "Administrator").first()
    fixed_admin = db.query(Employee).filter(Employee.employee_number == "admin").first()
    if not fixed_admin:
        return

    real_admin_count = 0

    if admin_role and model_has(Employee, "role_id"):
        real_admin_count = db.query(Employee).filter(
            Employee.employee_number != "admin",
            Employee.active == True,
            Employee.role_id == admin_role.id
        ).count()
    elif model_has(Employee, "is_admin"):
        real_admin_count = db.query(Employee).filter(
            Employee.employee_number != "admin",
            Employee.active == True,
            Employee.is_admin == True
        ).count()

    fixed_admin.active = False if real_admin_count > 0 else True



def ensure_schema_columns():
    """Kompatibilitätsfunktion für ältere Aufrufe.

    Seit Version 4.7.07 werden Schemaänderungen über app.db_migrations
    mit Versionsprotokoll in schema_migrations ausgeführt.
    """
    run_migrations()

def init_db():
    Base.metadata.create_all(bind=engine)
    run_migrations()

    db = SessionLocal()
    try:
        for name, desc in [
            ("Administrator", "Vollzugriff"),
            ("Personal", "Personalverwaltung"),
            ("Teamleiter", "Teamverwaltung"),
            ("Mitarbeiter", "Eigene Zeiten"),
        ]:
            safe_add_role(db, name, desc)

        admin_role = db.query(Role).filter(Role.name == "Administrator").first()
        create_or_update_fixed_admin(db, admin_role)

        try:
            for dept_name in ["IT", "Verwaltung", "Geschäftsleitung"]:
                safe_add_department(db, dept_name)
        except Exception:
            db.rollback()

        defaults = {
            "logo_path": "",
            "correction_days_back": "14",
            "system_settings_enabled": "true",

            "privacy_officer_name": "",
            "privacy_officer_email": "",
            "privacy_retention_years": "10",
            "privacy_export_enabled": "true",
            "privacy_delete_enabled": "false",
            "privacy_processing_purpose": "Arbeitszeiterfassung, Pausen, Korrekturen und gesetzliche Nachweispflichten",
            "privacy_legal_basis": "Art. 6 Abs. 1 lit. c DSGVO / arbeitsrechtliche Nachweispflichten",
            "privacy_notice_text": "Die Stempeluhr verarbeitet personenbezogene Daten zur Arbeitszeiterfassung. Zugriff erhalten nur berechtigte Rollen.",

            "dsgvo_enabled": "false",
            "dsgvo_run_time": "02:00",
            "dsgvo_mode": "archive_anonymize",
            "dsgvo_time_entries_years": "2",
            "dsgvo_vacation_years": "3",
            "dsgvo_audit_years": "3",
            "dsgvo_archived_employee_years": "3",
            "dsgvo_payroll_years": "10",
            "dsgvo_last_run": "",
            "dsgvo_last_status": "noch nicht ausgeführt",

            "backup_enabled": "true",
            "backup_time": "02:00",
            "backup_daily_keep": "30",
            "backup_weekly_keep": "4",
            "backup_monthly_keep": "12",
            "backup_yearly_keep": "10",
            "backup_target": "local",
            "backup_path": str(BACKUP_DIR),
            "backup_include_database": "true",
            "backup_include_config": "true",
            "backup_include_uploads": "true",
            "backup_before_update": "true",
            "backup_before_restore": "true",
            "backup_log_audit": "true",
            "backup_last_status": "noch nicht ausgeführt",
            "backup_last_time": "",
            "backup_last_file": "",

            "backup_smb_server": "",
            "backup_smb_share": "",
            "backup_smb_path": "",
            "backup_smb_username": "",
            "backup_smb_password": "",
            "backup_smb_domain": "",
            "backup_smb_mountpoint": "/mnt/stempeluhr_backup",

            "email_enabled": "false",
            "email_smtp_host": "",
            "email_smtp_port": "587",
            "email_smtp_user": "",
            "email_smtp_password": "",
            "email_from_address": "",
            "email_from_name": "Stempeluhr",
            "email_use_tls": "true",
            "email_use_ssl": "false",
            "email_test_recipient": "",

            "onboarding_enabled": "true",
            "onboarding_token_hours": "48",
            "onboarding_email_subject": "Einladung zur Stempeluhr",
            "onboarding_email_body": "Hallo {name},\n\nbitte richte dein Stempeluhr-Konto über folgenden Link ein:\n{link}\n\nDer Link ist {hours} Stunden gültig.\n\nViele Grüße\nStempeluhr",
            "onboarding_privacy_version": "1.0",
            "onboarding_privacy_text": "Ich habe die Datenschutzbestimmungen zur Nutzung der Stempeluhr gelesen und stimme der Verarbeitung meiner Daten zur Arbeitszeiterfassung zu.",

            "caldav_enabled": "false",
            "caldav_url": "",
            "caldav_username": "",
            "caldav_password": "",
            "caldav_holiday_calendar_url": "",
            "absence_calendar_name": "Abwesenheit",
            "absence_calendar_slug": "abwesenheit",
            "absence_calendar_username": "",
            "absence_calendar_password": "",
            "absence_calendar_auth_enabled": "0",
            "caldav_vacation_calendar_url": "",
            "caldav_vacation_feed_token": "change-me",
            "caldav_last_import": "",
            "caldav_last_status": "noch nicht ausgeführt",
            "caldav_holidays_enabled": "true",
            "caldav_holiday_sync_interval_hours": "24",
            "caldav_holidays_affect_target_hours": "true",
            "caldav_half_day_factor": "0.5",
            "caldav_auto_sync_on_start": "false",

            "api_enabled": "false",
            "api_logging_enabled": "true",
            "api_require_ip_filter": "false",

            "plausibility_enabled": "true",
            "plausibility_daily_time": "18:30",
            "plausibility_email_enabled": "true",
            "plausibility_employee_email_enabled": "true",
            "plausibility_teamlead_email_enabled": "true",
            "plausibility_max_daily_hours": "10",
            "plausibility_warn_daily_hours": "9",
            "plausibility_earliest_come": "05:00",
            "plausibility_latest_leave": "22:00",
            "plausibility_duplicate_minutes": "5",
            "plausibility_check_missing_leave": "true",
            "plausibility_check_missing_workday": "true",
            "plausibility_check_absence_booking": "true",
            "plausibility_check_duplicates": "true",
            "plausibility_check_boundaries": "true",
            "plausibility_check_breaks_if_auto_disabled": "true",
            "plausibility_break_min_6h_minutes": "30",
            "plausibility_break_min_9h_minutes": "45",
            "plausibility_teamlead_summary_days": "1",

            "api_enabled": "false",
            "api_require_key": "true",
            "terminal_api_enabled": "true",

            "security_network_filter_enabled": "false",
            "security_allowed_networks": "192.168.132.0/24,192.168.130.0/24,10.4.81.0/24",
            "security_admin_network_filter_enabled": "false",
            "security_admin_allowed_networks": "192.168.132.0/24",
            "security_api_network_filter_enabled": "false",
            "security_api_allowed_networks": "192.168.130.0/24,10.4.81.0/24",
            "security_force_https": "false",

            "setup_completed": "false",
            "odoo_plugin_enabled": "false",
            "odoo_url": "",
            "odoo_db": "",
            "odoo_username": "",
            "odoo_password": "",
            "monitoring_enabled": "true",
            "rollback_enabled": "true",
        }

        for key, value in defaults.items():
            safe_add_setting(db, key, value)

        sync_emergency_admin(db)
        db.commit()

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# Standardwert für Mitarbeiternummer-Länge wird durch init_db gesetzt, wenn Setting-Modell verfügbar ist.
def ensure_employee_number_length_default(db):
    try:
        from app.models import Setting
        row = db.query(Setting).filter(Setting.key == "employee_number_length").first()
        if not row:
            db.add(Setting(key="employee_number_length", value="4"))
            db.commit()
    except Exception:
        pass
