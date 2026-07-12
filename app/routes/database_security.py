from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.routes.common import templates, require_system_admin_response, log_action
from app.security import verify_password

router = APIRouter()
HELPER = Path("/usr/local/sbin/stempeluhr-database-secret-helper")
TMP_DIR = Path("/var/lib/stempeluhr/tmp")
SECRET_FILE = Path("/etc/stempeluhr/secrets/database.conf")


def _database_status(db: Session) -> dict:
    status = {
        "host": os.getenv("DATABASE_HOST", "127.0.0.1"),
        "port": os.getenv("DATABASE_PORT", "5432"),
        "name": os.getenv("DATABASE_NAME", "stempeluhr"),
        "user": os.getenv("DATABASE_USER", "stempeluhr"),
        "connected": False,
        "server_version": "unbekannt",
        "secret_exists": SECRET_FILE.exists(),
        "secret_mode": "-",
    }
    try:
        status["server_version"] = str(db.execute(text("SHOW server_version")).scalar() or "unbekannt")
        status["connected"] = True
    except Exception:
        db.rollback()
    try:
        status["secret_mode"] = oct(SECRET_FILE.stat().st_mode & 0o777)
    except OSError:
        pass
    return status


@router.get("/system/settings/database-security", response_class=HTMLResponse)
def database_security_page(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    return templates.TemplateResponse("system_database_security.html", {
        "request": request,
        "user": user,
        "status": _database_status(db),
        "message": request.query_params.get("message", ""),
        "error": request.query_params.get("error", ""),
    })


@router.post("/system/settings/database-security/change")
def database_security_change(
    request: Request,
    admin_password: str = Form(""),
    new_password: str = Form(""),
    new_password_repeat: str = Form(""),
    db: Session = Depends(get_db),
):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    if not user.password_hash or not verify_password(admin_password, user.password_hash):
        return RedirectResponse("/system/settings/database-security?error=Administratorpasswort+ist+falsch", status_code=303)
    if new_password != new_password_repeat:
        return RedirectResponse("/system/settings/database-security?error=Passwörter+stimmen+nicht+überein", status_code=303)
    if len(new_password) < 16 or not any(c.islower() for c in new_password) or not any(c.isupper() for c in new_password) or not any(c.isdigit() for c in new_password):
        return RedirectResponse("/system/settings/database-security?error=Passwort+muss+mindestens+16+Zeichen,+Groß-/Kleinbuchstaben+und+Zahlen+enthalten", status_code=303)
    if not HELPER.exists():
        return RedirectResponse("/system/settings/database-security?error=Sicherheits-Helfer+fehlt", status_code=303)

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix="database-secret-", suffix=".json", dir=str(TMP_DIR))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump({
                "host": os.getenv("DATABASE_HOST", "127.0.0.1"),
                "port": os.getenv("DATABASE_PORT", "5432"),
                "database": os.getenv("DATABASE_NAME", "stempeluhr"),
                "user": os.getenv("DATABASE_USER", "stempeluhr"),
                "password": new_password,
            }, handle)
        os.chmod(temp_name, 0o600)
        result = subprocess.run(["sudo", "-n", str(HELPER), temp_name], capture_output=True, text=True, timeout=45)
        if result.returncode != 0:
            return RedirectResponse("/system/settings/database-security?error=Datenbankpasswort+konnte+nicht+geändert+werden", status_code=303)
        log_action(db, user.employee_number, "database_password_changed", "security", "database", "Datenbankpasswort sicher geändert; Secret-Datei aktualisiert")
        return RedirectResponse("/system/settings/database-security?message=Passwort+geändert.+Dienst+wird+neu+gestartet", status_code=303)
    finally:
        Path(temp_name).unlink(missing_ok=True)
