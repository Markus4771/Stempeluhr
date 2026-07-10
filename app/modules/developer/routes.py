from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.registry import get_modules_as_dicts, get_module_status, get_navigation_as_dicts
from app.modules.loader import inspect_modules
from app.plugins import plugins_as_dicts
from app.core.permissions import permissions_as_dicts
from app.routes.common import templates, require_system_admin_response
from app.version import get_version_info, get_app_version

router = APIRouter()

APP_DIR = Path("/opt/stempeluhr")
LOG_DIRS = [Path("/var/log/stempeluhr"), APP_DIR / "logs"]


def _safe_cmd(cmd: list[str], timeout: int = 5) -> str:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = (result.stdout or result.stderr or "").strip()
        return out[:4000]
    except Exception as exc:
        return f"nicht verfügbar: {exc}"


def _disk_info() -> dict:
    usage = shutil.disk_usage("/")
    return {
        "total_gb": round(usage.total / 1024 / 1024 / 1024, 2),
        "used_gb": round(usage.used / 1024 / 1024 / 1024, 2),
        "free_gb": round(usage.free / 1024 / 1024 / 1024, 2),
        "percent": round((usage.used / usage.total) * 100, 1) if usage.total else 0,
    }


def _package_info() -> dict:
    version = _safe_cmd(["dpkg-query", "-W", "-f=${Version}", "stempeluhr"])
    status = _safe_cmd(["dpkg-query", "-W", "-f=${Status}", "stempeluhr"])
    return {"package": "stempeluhr", "version": version or "unbekannt", "status": status or "unbekannt"}


def _routes(request: Request) -> list[dict]:
    rows = []
    for route in request.app.routes:
        methods = sorted([m for m in getattr(route, "methods", []) if m not in {"HEAD", "OPTIONS"}])
        rows.append({
            "path": getattr(route, "path", ""),
            "name": getattr(route, "name", ""),
            "methods": ", ".join(methods) if methods else "-",
        })
    return sorted(rows, key=lambda r: (r["path"], r["methods"]))


def _log_files() -> list[dict]:
    found = []
    seen = set()
    for log_dir in LOG_DIRS:
        if not log_dir.exists():
            continue
        for path in sorted(log_dir.glob("*.log")):
            if path in seen:
                continue
            seen.add(path)
            try:
                stat = path.stat()
                found.append({
                    "name": path.name,
                    "path": str(path),
                    "size_kb": round(stat.st_size / 1024, 1),
                    "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%d.%m.%Y %H:%M"),
                })
            except Exception:
                pass
    return found


def _tail_file(path: Path, lines: int = 120) -> str:
    if not path.exists() or not path.is_file():
        return "Logdatei nicht gefunden."
    try:
        data = path.read_text(encoding="utf-8", errors="ignore").splitlines()[-lines:]
        return "\n".join(data)
    except Exception as exc:
        return f"Logdatei konnte nicht gelesen werden: {exc}"


def _selftest(db: Session) -> list[dict]:
    checks: list[dict] = []

    def add(name: str, ok: bool, detail: str = ""):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    try:
        db.execute(text("SELECT 1"))
        add("Datenbank", True, "Verbindung erfolgreich")
    except Exception as exc:
        add("Datenbank", False, str(exc))

    for rel in ["app/templates/dashboard.html", "app/templates/system_settings.html", "app/main.py", "version.json"]:
        p = APP_DIR / rel
        add(f"Datei {rel}", p.exists(), str(p))

    for p in [APP_DIR / "uploads", APP_DIR / "logs", APP_DIR / "backups"]:
        add(f"Schreibpfad {p.name}", p.exists(), str(p))

    runner = Path("/usr/local/sbin/stempeluhr-web-update-run")
    add("Webupdate-Runner", runner.exists() and os.access(runner, os.X_OK), str(runner))

    plugin_dir = APP_DIR / "plugins"
    add("Plugin-Verzeichnis", plugin_dir.exists(), str(plugin_dir))

    try:
        loader_results = inspect_modules()
        failed = [item.key for item in loader_results if not item.loaded]
        add("Modul-Lader", not failed, "OK" if not failed else ", ".join(failed))
    except Exception as exc:
        add("Modul-Lader", False, str(exc))

    service_state = _safe_cmd(["systemctl", "is-active", "stempeluhr.service"])
    add("systemd Dienst", service_state == "active", service_state)

    return checks


@router.get("/system/developer", response_class=HTMLResponse)
def developer_console(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect

    return templates.TemplateResponse("system_developer.html", {
        "request": request,
        "user": user,
        "version": get_version_info(),
        "package": _package_info(),
        "system": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "machine": platform.machine(),
            "hostname": platform.node(),
            "disk": _disk_info(),
            "service": _safe_cmd(["systemctl", "is-active", "stempeluhr.service"]),
        },
        "modules": get_modules_as_dicts(),
        "module_status": get_module_status(),
        "module_loader": [item.as_dict() for item in inspect_modules()],
        "plugins": plugins_as_dicts(),
        "navigation": get_navigation_as_dicts(),
        "permissions": permissions_as_dicts(),
        "routes": _routes(request),
        "checks": _selftest(db),
        "logs": _log_files(),
    })


@router.get("/system/developer/routes", response_class=JSONResponse)
def developer_routes(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return JSONResponse({"error": "not authorized"}, status_code=403)
    return {"routes": _routes(request), "version": get_app_version()}


@router.get("/system/developer/selftest", response_class=JSONResponse)
def developer_selftest(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return JSONResponse({"error": "not authorized"}, status_code=403)
    return {"checks": _selftest(db), "version": get_app_version()}


@router.get("/system/developer/log/{name}", response_class=PlainTextResponse)
def developer_log(name: str, request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return PlainTextResponse("not authorized", status_code=403)
    safe_name = Path(name).name
    for log_dir in LOG_DIRS:
        path = log_dir / safe_name
        if path.exists():
            return PlainTextResponse(_tail_file(path))
    return PlainTextResponse("Logdatei nicht gefunden.", status_code=404)
