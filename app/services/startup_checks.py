"""Leichtgewichtige Startup-Checks für Healthcheck und Systemdiagnose.

Die Prüfungen stoppen den Dienst nicht. Kritische Probleme werden verständlich
als Warnungen ausgegeben, statt einen unlesbaren Traceback zu erzeugen.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List

from app.version import APP_VERSION, validate_runtime_version, write_version_file

ENV_FILE = Path("/etc/stempeluhr/stempeluhr.env")
REQUIRED_DATABASE_KEYS = (
    "DATABASE_TYPE", "DATABASE_HOST", "DATABASE_PORT", "DATABASE_NAME",
    "DATABASE_USER", "DATABASE_PASSWORD",
)


def _check_path(name: str, path: str | Path, should_exist: bool = True, writable: bool = False) -> Dict[str, Any]:
    p = Path(path)
    exists = p.exists()
    ok = exists if should_exist else True
    result: Dict[str, Any] = {"name": name, "ok": bool(ok), "path": str(p), "exists": bool(exists)}
    if writable:
        result["writable"] = bool(exists and os.access(p, os.W_OK))
        result["ok"] = bool(result["ok"] and result["writable"])
    return result


def _env_keys(path: Path) -> set[str]:
    keys: set[str] = set()
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].lstrip()
            if "=" in line:
                keys.add(line.split("=", 1)[0].strip())
    except OSError:
        pass
    return keys


def run_startup_checks(app_dir: str | Path | None = None) -> Dict[str, Any]:
    root = Path(app_dir or os.environ.get("STEMPELUHR_APP_DIR", "/opt/stempeluhr"))
    checks: List[Dict[str, Any]] = []

    version_status = validate_runtime_version()
    if not version_status.get("file_version"):
        write_version_file(root / "version.txt")
        version_status = validate_runtime_version()
    checks.append({"name": "version", **version_status})
    checks.append({"name": "python", "ok": sys.version_info >= (3, 10), "version": sys.version.split()[0]})
    checks.append(_check_path("app", root / "app"))
    checks.append(_check_path("templates", root / "app" / "templates"))
    checks.append(_check_path("static", root / "app" / "static"))
    checks.append(_check_path("scripts", root / "scripts"))
    checks.append(_check_path("data", "/var/lib/stempeluhr", writable=True))
    checks.append(_check_path("logs", "/var/log/stempeluhr", writable=True))

    keys = _env_keys(ENV_FILE)
    missing = [key for key in REQUIRED_DATABASE_KEYS if key not in keys]
    checks.append({
        "name": "configuration",
        "ok": ENV_FILE.exists() and not missing,
        "path": str(ENV_FILE),
        "exists": ENV_FILE.exists(),
        "missing_required": missing,
        "message": "OK" if ENV_FILE.exists() and not missing else "Datenbankkonfiguration unvollständig",
    })

    try:
        disk = shutil.disk_usage(root if root.exists() else "/")
        checks.append({
            "name": "storage",
            "ok": disk.free >= 512 * 1024 * 1024,
            "free_bytes": disk.free,
            "total_bytes": disk.total,
            "message": "OK" if disk.free >= 512 * 1024 * 1024 else "Weniger als 512 MiB frei",
        })
    except OSError as exc:
        checks.append({"name": "storage", "ok": False, "message": f"Speicherprüfung fehlgeschlagen: {type(exc).__name__}"})

    ok = all(bool(c.get("ok", False)) for c in checks)
    warnings = [c.get("message", c.get("name", "Prüfung fehlgeschlagen")) for c in checks if not c.get("ok")]
    return {"ok": ok, "version": APP_VERSION, "checks": checks, "warnings": warnings}
