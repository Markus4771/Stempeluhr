"""Zentrale Versionsinformationen fuer Stempeluhr Professional."""
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, Tuple
APP_NAME = "Stempeluhr Professional"
APP_VERSION = "5.6.33"
VERSION_FILE_NAME = "version.txt"
def _project_root() -> Path:
    try: return Path(__file__).resolve().parents[1]
    except Exception: return Path("/opt/stempeluhr")
def get_app_version() -> str: return APP_VERSION
def get_app_name() -> str: return APP_NAME
def get_version_file_path() -> Path: return _project_root() / VERSION_FILE_NAME
def read_version_file(default: str = "") -> str:
    try: return get_version_file_path().read_text(encoding="utf-8").strip()
    except Exception: return default
def write_version_file(path: str | Path | None = None) -> bool:
    try:
        (Path(path) if path else get_version_file_path()).write_text(APP_VERSION + "\n", encoding="utf-8")
        return True
    except Exception: return False
def version_tuple(version: str | None = None) -> Tuple[int, ...]:
    return tuple(int("".join(ch for ch in item if ch.isdigit()) or 0) for item in str(version or APP_VERSION).strip().split("."))
def validate_runtime_version() -> Dict[str, Any]:
    file_version = read_version_file("")
    matches = (not file_version) or file_version == APP_VERSION
    return {"ok": True, "matches": matches, "name": APP_NAME, "version": APP_VERSION, "file_version": file_version, "version_file": str(get_version_file_path()), "message": "OK" if matches else f"version.txt={file_version} app.version={APP_VERSION}"}
def get_version_info() -> Dict[str, Any]:
    info = validate_runtime_version()
    info.update({"display": f"{APP_NAME} {APP_VERSION}", "major": version_tuple(APP_VERSION)[0] if version_tuple(APP_VERSION) else 0})
    return info
