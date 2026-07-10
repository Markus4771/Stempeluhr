from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from sqlalchemy import inspect, text

from .database import engine


@dataclass(frozen=True)
class Migration:
    version: str
    name: str
    upgrade: Callable[[object, str], None]


def _table_exists(conn, table: str) -> bool:
    return inspect(conn).has_table(table)


def _column_exists(conn, table: str, column: str) -> bool:
    if not _table_exists(conn, table):
        return False
    return column in {c["name"] for c in inspect(conn).get_columns(table)}


def _add_column(conn, dialect: str, table: str, column: str, definition_pg: str, definition_sqlite: str | None = None) -> None:
    if not _table_exists(conn, table) or _column_exists(conn, table, column):
        return
    definition = definition_sqlite or definition_pg
    if dialect == "postgresql":
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {definition_pg}"))
    else:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))


def _execute_if_table(conn, table: str, sql: str) -> None:
    if _table_exists(conn, table):
        conn.execute(text(sql))


def _m001_soft_delete_time_entries(conn, dialect: str) -> None:
    _add_column(conn, dialect, "time_entries", "deleted", "BOOLEAN DEFAULT FALSE", "BOOLEAN DEFAULT 0")
    _add_column(conn, dialect, "time_entries", "deleted_at", "TIMESTAMP NULL")
    _add_column(conn, dialect, "time_entries", "deleted_by", "VARCHAR(100) NULL")
    _add_column(conn, dialect, "time_entries", "delete_reason", "TEXT NULL")
    if _table_exists(conn, "time_entries"):
        false_value = "FALSE" if dialect == "postgresql" else "0"
        conn.execute(text(f"UPDATE time_entries SET deleted = {false_value} WHERE deleted IS NULL"))


def _m002_employee_permissions(conn, dialect: str) -> None:
    _add_column(conn, dialect, "employees", "can_self_correct", "BOOLEAN DEFAULT FALSE", "BOOLEAN DEFAULT 0")
    _add_column(conn, dialect, "employees", "can_self_manage", "BOOLEAN DEFAULT FALSE", "BOOLEAN DEFAULT 0")
    _add_column(conn, dialect, "employees", "plausibility_check_enabled", "BOOLEAN DEFAULT TRUE", "BOOLEAN DEFAULT 1")


def _m003_terminals_extended(conn, dialect: str) -> None:
    _add_column(conn, dialect, "terminals", "terminal_code", "VARCHAR(100) NULL")
    _add_column(conn, dialect, "terminals", "offline_buffer_enabled", "BOOLEAN DEFAULT TRUE", "BOOLEAN DEFAULT 1")
    _add_column(conn, dialect, "terminals", "description", "TEXT NULL")
    _add_column(conn, dialect, "terminals", "last_ip", "VARCHAR(100) NULL")
    _add_column(conn, dialect, "terminals", "app_version", "VARCHAR(50) NULL")


def _m004_api_tokens_extended(conn, dialect: str) -> None:
    _add_column(conn, dialect, "api_tokens", "permissions", "TEXT DEFAULT 'read'")
    _add_column(conn, dialect, "api_tokens", "allowed_ips", "TEXT NULL")
    _add_column(conn, dialect, "api_tokens", "expires_at", "TIMESTAMP NULL")


def _m005_absence_custom_reason(conn, dialect: str) -> None:
    _add_column(conn, dialect, "vacation_requests", "custom_reason", "TEXT NULL")


def _m006_offboarding(conn, dialect: str) -> None:
    _add_column(conn, dialect, "employees", "status", "VARCHAR(20) DEFAULT 'active'")
    _add_column(conn, dialect, "employees", "exit_date", "DATE NULL")
    _add_column(conn, dialect, "employees", "archived_at", "TIMESTAMP NULL")
    _add_column(conn, dialect, "employees", "offboarding_note", "TEXT NULL")
    _execute_if_table(conn, "employees", "UPDATE employees SET status = 'active' WHERE status IS NULL")


def _m007_dsgvo_log(conn, dialect: str) -> None:
    if dialect == "postgresql":
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dsgvo_logs (
                id SERIAL PRIMARY KEY,
                action VARCHAR(100) NOT NULL,
                data_type VARCHAR(100) NOT NULL,
                record_id VARCHAR(100),
                employee_id INTEGER NULL,
                actor VARCHAR(100) DEFAULT 'SYSTEM',
                details TEXT,
                created_at TIMESTAMP
            )
        """))
    else:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dsgvo_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action VARCHAR(100) NOT NULL,
                data_type VARCHAR(100) NOT NULL,
                record_id VARCHAR(100),
                employee_id INTEGER NULL,
                actor VARCHAR(100) DEFAULT 'SYSTEM',
                details TEXT,
                created_at TIMESTAMP
            )
        """))


def _m008_password_reset_tokens(conn, dialect: str) -> None:
    if dialect == "postgresql":
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id SERIAL PRIMARY KEY,
                employee_id INTEGER NOT NULL REFERENCES employees(id),
                token_hash VARCHAR(128) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                used_at TIMESTAMP NULL,
                requested_ip VARCHAR(100) NULL
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_password_reset_tokens_token_hash ON password_reset_tokens (token_hash)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_password_reset_tokens_employee_id ON password_reset_tokens (employee_id)"))
    else:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                token_hash VARCHAR(128) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                used_at TIMESTAMP NULL,
                requested_ip VARCHAR(100) NULL,
                FOREIGN KEY(employee_id) REFERENCES employees(id)
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_password_reset_tokens_token_hash ON password_reset_tokens (token_hash)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_password_reset_tokens_employee_id ON password_reset_tokens (employee_id)"))


def _m009_absence_types(conn, dialect: str) -> None:
    if dialect == "postgresql":
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS absence_types (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                code VARCHAR(50) UNIQUE NOT NULL,
                active BOOLEAN DEFAULT TRUE,
                requires_approval BOOLEAN DEFAULT TRUE,
                requires_text BOOLEAN DEFAULT FALSE,
                sort_order INTEGER DEFAULT 100,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
    else:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS absence_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                code VARCHAR(50) UNIQUE NOT NULL,
                active BOOLEAN DEFAULT 1,
                requires_approval BOOLEAN DEFAULT 1,
                requires_text BOOLEAN DEFAULT 0,
                sort_order INTEGER DEFAULT 100,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

    defaults = [
        ("Urlaub", "abwesenheit", True, False, 10),
        ("Krank", "krank", False, False, 20),
        ("Homeoffice", "homeoffice", True, False, 30),
        ("Dienstreise", "dienstreise", True, False, 40),
        ("Fortbildung", "fortbildung", True, False, 50),
        ("Berufsschule", "berufsschule", False, False, 60),
        ("Sonstiges", "sonstiges", True, True, 90),
    ]
    existing = {row[0] for row in conn.execute(text("SELECT code FROM absence_types"))}
    for name, code, requires_approval, requires_text, sort_order in defaults:
        if code in existing:
            continue
        conn.execute(
            text("""
                INSERT INTO absence_types (name, code, active, requires_approval, requires_text, sort_order)
                VALUES (:name, :code, :active, :requires_approval, :requires_text, :sort_order)
            """),
            {
                "name": name,
                "code": code,
                "active": True,
                "requires_approval": requires_approval,
                "requires_text": requires_text,
                "sort_order": sort_order,
            },
        )


def _m010_employee_break_rule(conn, dialect: str) -> None:
    _add_column(conn, dialect, "employees", "auto_break_enabled", "BOOLEAN DEFAULT TRUE", "BOOLEAN DEFAULT 1")
    if _table_exists(conn, "employees"):
        true_value = "TRUE" if dialect == "postgresql" else "1"
        conn.execute(text(f"UPDATE employees SET auto_break_enabled = {true_value} WHERE auto_break_enabled IS NULL"))


def _m011_raspberry_monitoring(conn, dialect: str) -> None:
    if dialect == "postgresql":
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS raspberry_clients (
                id SERIAL PRIMARY KEY,
                hostname VARCHAR(150) UNIQUE NOT NULL,
                ip_address VARCHAR(100),
                agent_version VARCHAR(50),
                app_version VARCHAR(50),
                debian_version VARCHAR(200),
                chromium_running BOOLEAN DEFAULT FALSE,
                kiosk_url TEXT,
                fullscreen BOOLEAN DEFAULT FALSE,
                wayland_display VARCHAR(100),
                display_name VARCHAR(100),
                cpu_percent DOUBLE PRECISION DEFAULT 0,
                ram_percent DOUBLE PRECISION DEFAULT 0,
                temperature VARCHAR(50),
                uptime VARCHAR(100),
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_screenshot_path TEXT,
                last_log TEXT,
                pending_command VARCHAR(100),
                command_requested_at TIMESTAMP,
                command_result TEXT,
                command_finished_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
    else:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS raspberry_clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hostname VARCHAR(150) UNIQUE NOT NULL,
                ip_address VARCHAR(100),
                agent_version VARCHAR(50),
                app_version VARCHAR(50),
                debian_version VARCHAR(200),
                chromium_running BOOLEAN DEFAULT 0,
                kiosk_url TEXT,
                fullscreen BOOLEAN DEFAULT 0,
                wayland_display VARCHAR(100),
                display_name VARCHAR(100),
                cpu_percent FLOAT DEFAULT 0,
                ram_percent FLOAT DEFAULT 0,
                temperature VARCHAR(50),
                uptime VARCHAR(100),
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_screenshot_path TEXT,
                last_log TEXT,
                pending_command VARCHAR(100),
                command_requested_at TIMESTAMP,
                command_result TEXT,
                command_finished_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
    for column, pgdef, sqdef in [
        ("ip_address", "VARCHAR(100) NULL", "VARCHAR(100) NULL"),
        ("agent_version", "VARCHAR(50) NULL", "VARCHAR(50) NULL"),
        ("app_version", "VARCHAR(50) NULL", "VARCHAR(50) NULL"),
        ("debian_version", "VARCHAR(200) NULL", "VARCHAR(200) NULL"),
        ("chromium_running", "BOOLEAN DEFAULT FALSE", "BOOLEAN DEFAULT 0"),
        ("kiosk_url", "TEXT NULL", "TEXT NULL"),
        ("fullscreen", "BOOLEAN DEFAULT FALSE", "BOOLEAN DEFAULT 0"),
        ("wayland_display", "VARCHAR(100) NULL", "VARCHAR(100) NULL"),
        ("display_name", "VARCHAR(100) NULL", "VARCHAR(100) NULL"),
        ("cpu_percent", "DOUBLE PRECISION DEFAULT 0", "FLOAT DEFAULT 0"),
        ("ram_percent", "DOUBLE PRECISION DEFAULT 0", "FLOAT DEFAULT 0"),
        ("temperature", "VARCHAR(50) NULL", "VARCHAR(50) NULL"),
        ("uptime", "VARCHAR(100) NULL", "VARCHAR(100) NULL"),
        ("last_seen", "TIMESTAMP NULL", "TIMESTAMP NULL"),
        ("last_screenshot_path", "TEXT NULL", "TEXT NULL"),
        ("last_log", "TEXT NULL", "TEXT NULL"),
        ("pending_command", "VARCHAR(100) NULL", "VARCHAR(100) NULL"),
        ("command_requested_at", "TIMESTAMP NULL", "TIMESTAMP NULL"),
        ("command_result", "TEXT NULL", "TEXT NULL"),
        ("command_finished_at", "TIMESTAMP NULL", "TIMESTAMP NULL"),
        ("created_at", "TIMESTAMP NULL", "TIMESTAMP NULL"),
        ("updated_at", "TIMESTAMP NULL", "TIMESTAMP NULL"),
    ]:
        _add_column(conn, dialect, "raspberry_clients", column, pgdef, sqdef)


def _m012_onboarding(conn, dialect: str) -> None:
    _add_column(conn, dialect, "employees", "onboarding_invited_at", "TIMESTAMP NULL", "TIMESTAMP NULL")
    _add_column(conn, dialect, "employees", "onboarding_completed_at", "TIMESTAMP NULL", "TIMESTAMP NULL")
    _add_column(conn, dialect, "employees", "privacy_accepted_at", "TIMESTAMP NULL", "TIMESTAMP NULL")
    _add_column(conn, dialect, "employees", "privacy_version_accepted", "VARCHAR(50) NULL", "VARCHAR(50) NULL")
    if dialect == "postgresql":
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS onboarding_tokens (
                id SERIAL PRIMARY KEY,
                employee_id INTEGER NOT NULL REFERENCES employees(id),
                token_hash VARCHAR(128) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                used_at TIMESTAMP NULL,
                sent_at TIMESTAMP NULL,
                requested_by VARCHAR(100) NULL,
                requested_ip VARCHAR(100) NULL,
                status VARCHAR(50) DEFAULT 'created',
                error_message TEXT NULL
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_onboarding_tokens_token_hash ON onboarding_tokens (token_hash)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_onboarding_tokens_employee_id ON onboarding_tokens (employee_id)"))
    else:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS onboarding_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                token_hash VARCHAR(128) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                used_at TIMESTAMP NULL,
                sent_at TIMESTAMP NULL,
                requested_by VARCHAR(100) NULL,
                requested_ip VARCHAR(100) NULL,
                status VARCHAR(50) DEFAULT 'created',
                error_message TEXT NULL,
                FOREIGN KEY(employee_id) REFERENCES employees(id)
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_onboarding_tokens_token_hash ON onboarding_tokens (token_hash)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_onboarding_tokens_employee_id ON onboarding_tokens (employee_id)"))


MIGRATIONS: tuple[Migration, ...] = (
    Migration("001", "soft_delete_time_entries", _m001_soft_delete_time_entries),
    Migration("002", "employee_permissions", _m002_employee_permissions),
    Migration("003", "terminals_extended", _m003_terminals_extended),
    Migration("004", "api_tokens_extended", _m004_api_tokens_extended),
    Migration("005", "absence_custom_reason", _m005_absence_custom_reason),
    Migration("006", "offboarding", _m006_offboarding),
    Migration("007", "dsgvo_log", _m007_dsgvo_log),
    Migration("008", "password_reset_tokens", _m008_password_reset_tokens),
    Migration("009", "absence_types", _m009_absence_types),
    Migration("010", "employee_break_rule", _m010_employee_break_rule),
    Migration("011", "raspberry_monitoring", _m011_raspberry_monitoring),
    Migration("012", "onboarding", _m012_onboarding),
)


def ensure_migration_table(conn) -> None:
    dialect = conn.dialect.name
    if dialect == "postgresql":
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(20) PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
    else:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(20) PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))


def applied_versions(conn) -> set[str]:
    ensure_migration_table(conn)
    return {row[0] for row in conn.execute(text("SELECT version FROM schema_migrations"))}


def run_migrations() -> list[str]:
    """Führt alle noch offenen Datenbankmigrationen idempotent aus.

    Die Migrationen sind bewusst defensiv geschrieben: Jede Spalte wird vor dem
    ALTER geprüft. Dadurch kann die Funktion auch auf bestehenden Installationen
    laufen, bei denen einzelne Spalten bereits manuell oder durch ältere Updates
    erzeugt wurden.
    """
    executed: list[str] = []
    with engine.begin() as conn:
        dialect = conn.dialect.name
        done = applied_versions(conn)
        for migration in MIGRATIONS:
            if migration.version in done:
                continue
            migration.upgrade(conn, dialect)
            conn.execute(
                text("INSERT INTO schema_migrations (version, name) VALUES (:version, :name)"),
                {"version": migration.version, "name": migration.name},
            )
            executed.append(f"{migration.version}_{migration.name}")
    return executed


def migration_status() -> dict[str, object]:
    with engine.begin() as conn:
        done = applied_versions(conn)
    return {
        "applied": sorted(done),
        "pending": [f"{m.version}_{m.name}" for m in MIGRATIONS if m.version not in done],
    }
