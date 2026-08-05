from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import threading
import time
from datetime import datetime, timedelta

from app.init_db import init_db
from app.routes import web, api, api_v1, roles_rights, rfid_terminal_display, terminal_protocol, terminal_admin, auth_plugin_admin, auth_credentials_admin
from app.version import APP_NAME, APP_VERSION, get_app_version, get_version_info
from app.core.config import SECRET_KEY, STATIC_DIR
from app.database import SessionLocal
from app.services.network_security import access_allowed, https_should_redirect
from app.services.settings_service import get_setting
from app.services.startup_checks import run_startup_checks
from app.services.rfid_media import ensure_rfid_media_schema
from app.services.auth_credentials import ensure_auth_credential_schema
from app.services.terminal_protocol import ensure_terminal_protocol_schema
from app.auth_plugins.registry import ensure_auth_plugin_schema, initialize_auth_plugins
from app.modules.loader import load_module_routers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("stempeluhr")

app = FastAPI(title=APP_NAME, version=APP_VERSION)

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    same_site="lax",
    https_only=False,
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(web.router)
app.include_router(api.router)
app.include_router(api_v1.router)
app.include_router(roles_rights.router)
app.include_router(rfid_terminal_display.router)
app.include_router(terminal_protocol.router)
app.include_router(terminal_admin.router)
app.include_router(auth_plugin_admin.router)
app.include_router(auth_credentials_admin.router)

# 5.2.07: Modul-Lader im sicheren Kompatibilitätsmodus.
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
    ensure_terminal_protocol_schema()
    ensure_auth_plugin_schema()
    db = SessionLocal()
    try:
        app.state.authentication_plugins = initialize_auth_plugins(db)
    finally:
        db.close()
    threading.Thread(target=dsgvo_scheduler_loop, daemon=True).start()
    threading.Thread(target=caldav_scheduler_loop, daemon=True).start()
    threading.Thread(target=monthly_reporting_scheduler_loop, daemon=True).start()
    threading.Thread(target=plausibility_scheduler_loop, daemon=True).start()


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return HTMLResponse("<h1>Seite nicht gefunden</h1><p><a href='/'>Zurück zum Dashboard</a></p>", status_code=404)
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s", request.url.path)
    return HTMLResponse(
        "<h1>Interner Fehler</h1>"
        "<p>Der Fehler wurde im Server-Log protokolliert.</p>"
        "<p><a href='/'>Zurück zum Dashboard</a></p>",
        status_code=500,
    )


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
