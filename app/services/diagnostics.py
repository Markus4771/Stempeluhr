"""Sichere Systemdiagnose ohne Ausgabe von Passwörtern oder Tokens."""
from __future__ import annotations

import os
import platform
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import Employee, TimeEntry
from app.version import get_app_version, validate_runtime_version

APP_STARTED_MONOTONIC = time.monotonic()
APP_STARTED_AT = datetime.now(timezone.utc)
ENV_FILE = Path("/etc/stempeluhr/stempeluhr.env")
REQUIRED_DATABASE_KEYS = (
    "DATABASE_TYPE", "DATABASE_HOST", "DATABASE_PORT", "DATABASE_NAME",
    "DATABASE_USER", "DATABASE_PASSWORD",
)
RECOMMENDED_KEYS = ("HOST", "PORT")


def _read_env_keys(path: Path = ENV_FILE) -> set[str]:
    keys: set[str] = set()
    try:
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].lstrip()
            if "=" in line:
                key = line.split("=", 1)[0].strip()
                if key:
                    keys.add(key)
    except OSError:
        pass
    return keys


def _path_check(name: str, path: str | Path, writable: bool = False) -> dict[str, Any]:
    target = Path(path)
    exists = target.exists()
    result: dict[str, Any] = {"name": name, "path": str(target), "exists": exists, "ok": exists}
    if writable:
        result["writable"] = bool(exists and os.access(target, os.W_OK))
        result["ok"] = bool(result["ok"] and result["writable"])
    return result


def collect_diagnostics(db: Session, app_dir: str | Path = "/opt/stempeluhr") -> dict[str, Any]:
    started = time.monotonic()
    root = Path(app_dir)
    warnings: list[str] = []

    env_keys = _read_env_keys()
    missing_required = [key for key in REQUIRED_DATABASE_KEYS if key not in env_keys]
    missing_recommended = [key for key in RECOMMENDED_KEYS if key not in env_keys]
    config_ok = ENV_FILE.exists() and not missing_required
    if not ENV_FILE.exists():
        warnings.append(f"Konfigurationsdatei fehlt: {ENV_FILE}")
    if missing_required:
        warnings.append("Fehlende Datenbankvariablen: " + ", ".join(missing_required))
    if missing_recommended:
        warnings.append("Empfohlene Variablen fehlen: " + ", ".join(missing_recommended))

    database: dict[str, Any] = {
        "ok": False,
        "type": os.getenv("DATABASE_TYPE", "postgresql"),
        "host": os.getenv("DATABASE_HOST", "127.0.0.1"),
        "port": os.getenv("DATABASE_PORT", "5432"),
        "name": os.getenv("DATABASE_NAME", "stempeluhr"),
        "user": os.getenv("DATABASE_USER", "stempeluhr"),
    }
    db_started = time.perf_counter()
    try:
        database["server_version"] = str(db.execute(text("SHOW server_version")).scalar() or "unbekannt")
        database["latency_ms"] = round((time.perf_counter() - db_started) * 1000, 2)
        database["employees"] = db.query(Employee).count()
        database["time_entries"] = db.query(TimeEntry).count()
        database["ok"] = True
    except Exception as exc:
        database["error"] = f"{type(exc).__name__}: Datenbankverbindung fehlgeschlagen"
        warnings.append("PostgreSQL-Verbindung fehlgeschlagen")
        try:
            db.rollback()
        except Exception:
            pass

    disk = shutil.disk_usage(root if root.exists() else "/")
    storage = {
        "ok": disk.free >= 512 * 1024 * 1024,
        "path": str(root if root.exists() else Path("/")),
        "total_bytes": disk.total,
        "free_bytes": disk.free,
        "free_percent": round((disk.free / disk.total) * 100, 1) if disk.total else 0,
    }
    if not storage["ok"]:
        warnings.append("Weniger als 512 MiB freier Speicherplatz")

    paths = [
        _path_check("app", root / "app"),
        _path_check("templates", root / "app" / "templates"),
        _path_check("static", root / "app" / "static"),
        _path_check("data", "/var/lib/stempeluhr", writable=True),
        _path_check("logs", "/var/log/stempeluhr", writable=True),
    ]
    for item in paths:
        if not item["ok"]:
            warnings.append(f"Pfadprüfung fehlgeschlagen: {item['name']}")

    version = validate_runtime_version()
    overall_ok = bool(version.get("matches") and config_ok and database["ok"] and storage["ok"] and all(p["ok"] for p in paths))
    return {
        "status": "ok" if overall_ok else ("warning" if database["ok"] else "error"),
        "ok": overall_ok,
        "version": get_app_version(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "application": {
            "name": "Stempeluhr Professional",
            "version": get_app_version(),
            "version_matches": bool(version.get("matches")),
            "app_dir": str(root),
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "uptime_seconds": int(time.monotonic() - APP_STARTED_MONOTONIC),
            "started_at": APP_STARTED_AT.isoformat(),
        },
        "configuration": {
            "ok": config_ok,
            "file": str(ENV_FILE),
            "exists": ENV_FILE.exists(),
            "missing_required": missing_required,
            "missing_recommended": missing_recommended,
        },
        "database": database,
        "storage": storage,
        "paths": paths,
        "warnings": warnings,
        "duration_ms": round((time.monotonic() - started) * 1000, 2),
    }
