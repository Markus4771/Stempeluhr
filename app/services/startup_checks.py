"""Leichtgewichtige Startup-Checks.

Die Pruefungen duerfen den Dienst nicht stoppen. Sie liefern Diagnosewerte fuer
Logs, /health und Selftest. Version 5.2.29 stabilisiert damit Start und Update.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List

from app.version import APP_VERSION, validate_runtime_version, write_version_file


def _check_path(name: str, path: str | Path, should_exist: bool = True) -> Dict[str, Any]:
    p = Path(path)
    exists = p.exists()
    ok = exists if should_exist else True
    return {"name": name, "ok": bool(ok), "path": str(p), "exists": bool(exists)}


def run_startup_checks(app_dir: str | Path | None = None) -> Dict[str, Any]:
    root = Path(app_dir or os.environ.get("STEMPELUHR_APP_DIR", "/opt/stempeluhr"))
    checks: List[Dict[str, Any]] = []

    version_status = validate_runtime_version()
    if not version_status.get("file_version"):
        # Fehlende Datei automatisch nachziehen, aber nicht erzwingen.
        write_version_file(root / "version.txt")
        version_status = validate_runtime_version()
    checks.append({"name": "version", **version_status})
    checks.append({"name": "python", "ok": sys.version_info >= (3, 10), "version": sys.version.split()[0]})
    checks.append(_check_path("app", root / "app"))
    checks.append(_check_path("templates", root / "app" / "templates"))
    checks.append(_check_path("static", root / "app" / "static"))
    checks.append(_check_path("scripts", root / "scripts"))

    ok = all(bool(c.get("ok", False)) for c in checks)
    return {"ok": ok, "version": APP_VERSION, "checks": checks}
