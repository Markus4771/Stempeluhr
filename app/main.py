from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import subprocess
import threading
import time
from datetime import datetime, timedelta

from app.init_db import init_db
from app.routes import web, api, api_v1, api_v1_rfid_compat, rfid_legacy_cleanup, roles_rights, rfid_terminal_display, terminal_protocol, terminal_admin, auth_plugin_admin, auth_credentials_admin, dashboard_plausibility, plausibility_assistant, plausibility_auto_repair, employee_plausibility, plausibility_patterns, overtime_reset, plausibility_reconcile, mobile_pairing
from app.version import APP_NAME, APP_VERSION, get_app_version, get_version_info
from app.core.config import SECRET_KEY, STATIC_DIR
from app.database import SessionLocal
from app.services.network_security import access_allowed, https_should_redirect
from app.services.settings_service import get_setting
from app.services.startup_checks import run_startup_checks
from app.services.rfid_media import ensure_rfid_media_schema
from app.services.auth_credentials import ensure_auth_credential_schema
from app.services.terminal_protocol import ensure_terminal_protocol_schema
from app.services.overtime_reset import ensure_overtime_reset_schema
from app.auth_plugins.registry import ensure_auth_plugin_schema, initialize_auth_plugins
from app.modules.loader import load_module_routers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("stempeluhr")

app = FastAPI(title=APP_NAME, version=APP_VERSION)

app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, same_site="lax", https_only=False)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(web.router)
app.include_router(api.router)
# Kompatibilitätsrouten zuerst: gleiche API-v1-URLs verwenden dadurch bereits
# die zentrale employee_rfid_media-Tabelle, bevor Legacy-Routen geprüft werden.
app.include_router(api_v1_rfid_compat.router)
app.include_router(api_v1.router)
# Alte RFID-Lern-URLs werden vor den modularen Web-Routen abgefangen und
# auf die zentrale Medienverwaltung umgeleitet bzw. deaktiviert.
app.include_router(rfid_legacy_cleanup.router)
app.include_router(roles_rights.router)
app.include_router(rfid_terminal_display.router)
app.include_router(terminal_protocol.router)
app.include_router(terminal_admin.router)
app.include_router(auth_plugin_admin.router)
app.include_router(auth_credentials_admin.router)
app.include_router(mobile_pairing.router)
app.include_router(dashboard_plausibility.router)
app.include_router(plausibility_assistant.router)
app.include_router(plausibility_auto_repair.router)
app.include_router(employee_plausibility.router)
app.include_router(plausibility_patterns.router)
app.include_router(overtime_reset.router)
app.include_router(plausibility_reconcile.router)

app.state.module_loader_results = load_module_routers(app, register=False)


def dsgvo_scheduler_loop():
    last_run_date = None
    while True:
        try:
            db = SessionLocal()
            try:
                web.ensure_dsgvo_settings(db)
                enabled = str(get_setting(db, "dsgvo_enabled", "false")).lower() in ["true", "1", "on"]
                run_time = str(get_setting(db, "dsgvo_run_time", "02:00") or "02:00")[:5]
                now = datetime.now()
                if enabled and now.strftime("%H:%M") == run_time and last_run_date != now.date():
                    mode = get_setting(db, "dsgvo_mode", "archive_anonymize")
                    web.run_dsgvo_cleanup(db, "SYSTEM", mode, False)
                    last_run_date = now.date()
            finally:
                db.close()
        except Exception:
            logger.exception("DSGVO scheduler failed")
        time.sleep(60)


def backup_scheduler_loop():
    """Führt das konfigurierte tägliche Backup zuverlässig aus.

    Alle 15 Minuten wird geprüft, ob das für heute vorgesehene Backup bereits
    erfolgreich gelaufen ist. Ist die konfigurierte Backup-Uhrzeit erreicht
    oder überschritten und fehlt das Tagesbackup, wird es einmal nachgeholt.
    Dadurch werden auch ausgeschaltete oder neu gestartete Systeme abgedeckt,
    ohne unnötige minütliche Prüfungen oder Doppelbackups zu erzeugen.
    """
    while True:
        try:
            db = SessionLocal()
            try:
                enabled = str(get_setting(db, "backup_enabled", "true") or "true").lower() in {
                    "true", "1", "on", "ja", "yes"
                }
                run_time = str(get_setting(db, "backup_time", "02:00") or "02:00")[:5]
                now = datetime.now()

                try:
                    hour, minute = [int(value) for value in run_time.split(":", 1)]
                    scheduled = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                except Exception:
                    run_time = "02:00"
                    scheduled = now.replace(hour=2, minute=0, second=0, microsecond=0)

                last_time_raw = str(get_setting(db, "backup_last_time", "") or "").strip()
                last_date = None
                for fmt in ("%d.%m.%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
                    try:
                        last_date = datetime.strptime(last_time_raw, fmt).date()
                        break
                    except (TypeError, ValueError):
                        continue

                should_run = enabled and now >= scheduled and last_date != now.date()
            finally:
                db.close()

            if should_run:
                logger.info("Automatic backup starting (configured time %s)", run_time)
                result = subprocess.run(
                    ["/opt/stempeluhr/.venv/bin/python", "/opt/stempeluhr/scripts/backup_gfs.py", "daily"],
                    capture_output=True,
                    text=True,
                    timeout=1800,
                )
                output = ((result.stdout or "") + (result.stderr or "")).strip()
                if result.returncode == 0:
                    logger.info("Automatic backup completed: %s", output[-1000:])
                else:
                    logger.error("Automatic backup failed (exit %s): %s", result.returncode, output[-2000:])
        except Exception:
            logger.exception("Automatic backup scheduler failed")
        time.sleep(15 * 60)


def caldav_scheduler_loop():
    while True:
        try:
            from app.routes.caldav_accounts import sync_due_caldav_accounts
            db = SessionLocal()
            try:
                sync_due_caldav_accounts(db)
            finally:
                db.close()
        except Exception:
            logger.exception("CalDAV scheduler failed")
        time.sleep(900)


def plausibility_scheduler_loop():
    while True:
        try:
            from app.services.plausibility import plausibility_scheduler_tick
            db = SessionLocal()
            try:
                result = plausibility_scheduler_tick(db)
                if result.get("status") not in {"waiting", "already_done"}:
                    logger.info("Plausibility scheduler: %s", result)
            finally:
                db.close()
        except Exception:
            logger.exception("Plausibility scheduler failed")
        time.sleep(60)


def plausibility_reconcile_loop():
    while True:
        try:
            from app.services.plausibility_reconcile import reconcile_open_plausibility_issues
            db = SessionLocal()
            try:
                result = reconcile_open_plausibility_issues(db)
                if result.get("resolved"):
                    logger.info("Plausibility reconcile: %s", result)
            finally:
                db.close()
        except Exception:
            logger.exception("Plausibility reconcile failed")
        time.sleep(300)


def monthly_reporting_scheduler_loop():
    while True:
        try:
            from app.routes.reports import monthly_reporting_scheduler_tick
            db = SessionLocal()
            try:
                monthly_reporting_scheduler_tick(db)
            finally:
                db.close()
        except Exception:
            logger.exception("Monthly reporting scheduler failed")
        time.sleep(60)


@app.middleware("http")
async def network_security_middleware(request: Request, call_next):
    db = SessionLocal()
    try:
        if https_should_redirect(request, db):
            https_url = request.url.replace(scheme="https")
            return RedirectResponse(str(https_url), status_code=307)
        allowed, reason = access_allowed(request, db)
        if not allowed:
            return PlainTextResponse(f"Zugriff nicht erlaubt: {reason}", status_code=403)
    finally:
        db.close()
    return await call_next(request)


@app.on_event("startup")
def startup():
    app.state.startup_checks = run_startup_checks()
    if not app.state.startup_checks.get("ok"):
        logger.warning("Startup checks reported warnings: %s", app.state.startup_checks)
    init_db()
    ensure_rfid_media_schema()
    ensure_auth_credential_schema()
    mobile_pairing.ensure_mobile_pairing_schema()
    ensure_terminal_protocol_schema()
    ensure_auth_plugin_schema()
    ensure_overtime_reset_schema()
    db = SessionLocal()
    try:
        app.state.authentication_plugins = initialize_auth_plugins(db)
    finally:
        db.close()
    threading.Thread(target=dsgvo_scheduler_loop, daemon=True).start()
    threading.Thread(target=backup_scheduler_loop, daemon=True).start()
    threading.Thread(target=caldav_scheduler_loop, daemon=True).start()
    threading.Thread(target=monthly_reporting_scheduler_loop, daemon=True).start()
    threading.Thread(target=plausibility_scheduler_loop, daemon=True).start()
    threading.Thread(target=plausibility_reconcile_loop, daemon=True).start()


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return HTMLResponse("<h1>Seite nicht gefunden</h1><p><a href='/'>Zurück zum Dashboard</a></p>", status_code=404)
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s", request.url.path)
    return HTMLResponse("<h1>Interner Fehler</h1><p>Der Fehler wurde im Server-Log protokolliert.</p><p><a href='/'>Zurück zum Dashboard</a></p>", status_code=500)


@app.get("/health")
def health():
    checks = getattr(app.state, "startup_checks", None) or run_startup_checks()
    return {"status": "ok" if checks.get("ok") else "warning", "version": get_app_version(), "database": "postgresql", "startup": checks}


@app.get("/version")
def version():
    return get_version_info()


try:
    from app.routes import updates
    app.include_router(updates.router)
except Exception as exc:
    print("Update-Router konnte nicht geladen werden:", exc)

try:
    from app.routes import caldav_accounts
    app.include_router(caldav_accounts.router)
except Exception as exc:
    print("CalDAV-Konten-Router konnte nicht geladen werden:", exc)
