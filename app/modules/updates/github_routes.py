"""GitHub-Release-Endpunkte für die vorhandene Updateverwaltung."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from app.modules.updates.github_release import TOKEN_FILE, download_release_assets, latest_release
from app.modules.updates.routes import _append_log, _compare_versions, _current_version, _write_status, upload_update

router = APIRouter()


def _is_admin_request(request: Request) -> bool:
    session = request.scope.get("session", {}) or {}
    return session.get("role") == "Administrator" or session.get("employee_number") == "admin" or "*" in (session.get("permissions") or [])


def _token_configured() -> bool:
    if (os.environ.get("STEMPELUHR_GITHUB_TOKEN") or "").strip():
        return True
    try:
        return TOKEN_FILE.is_file() and bool(TOKEN_FILE.read_text(encoding="utf-8").strip())
    except Exception:
        return False


@router.post("/system/settings/updates/github/token")
async def github_token_save(request: Request, token: str = Form(...)):
    if not _is_admin_request(request):
        raise HTTPException(status_code=403, detail="Nur Administratoren dürfen den GitHub-Token speichern.")
    cleaned = (token or "").strip()
    if len(cleaned) < 20 or any(ch.isspace() for ch in cleaned):
        raise HTTPException(status_code=400, detail="Der GitHub-Token ist ungültig.")
    try:
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        temp_file = TOKEN_FILE.with_suffix(".tmp")
        temp_file.write_text(cleaned + "\n", encoding="utf-8")
        os.chmod(temp_file, 0o600)
        temp_file.replace(TOKEN_FILE)
        os.chmod(TOKEN_FILE, 0o600)
    except PermissionError:
        raise HTTPException(status_code=500, detail="Der Dienst darf /etc/stempeluhr/secrets nicht beschreiben. Bitte Version 5.6.21 installieren oder die Verzeichnisrechte prüfen.")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Token konnte nicht gespeichert werden: {exc}")
    _append_log("GitHub-Lesetoken wurde über die Updateverwaltung hinterlegt.")
    return JSONResponse({"ok": True, "token_configured": True})


@router.get("/system/settings/updates/github/check")
async def github_update_check(request: Request):
    if not _is_admin_request(request):
        raise HTTPException(status_code=403, detail="Keine Berechtigung.")
    configured = _token_configured()
    release = latest_release()
    current = _current_version()
    if not release.get("ok"):
        return JSONResponse({
            "ok": False,
            "current_version": current,
            "token_configured": configured,
            "token_required": not configured,
            "error": release.get("error", "Unbekannter Fehler"),
        }, status_code=502)
    release["current_version"] = current
    release["token_configured"] = configured
    release["token_required"] = False
    release["update_available"] = bool(release.get("assets_complete") and _compare_versions(str(release.get("version") or ""), current))
    return JSONResponse(release)


@router.post("/system/settings/updates/github/install")
async def github_update_install(request: Request):
    if not _is_admin_request(request):
        raise HTTPException(status_code=403, detail="Keine Berechtigung.")
    release = latest_release()
    current = _current_version()
    if not release.get("ok"):
        message = str(release.get("error") or "GitHub Release konnte nicht gelesen werden.")
        _append_log(message)
        _write_status("failed", message, progress=0, step="GitHub-Prüfung")
        raise HTTPException(status_code=502, detail=message)
    version = str(release.get("version") or "")
    if not release.get("assets_complete"):
        message = f"GitHub Release {version or '?'} enthält kein vollständiges DEB/SHA256-Paar."
        _append_log(message)
        _write_status("failed", message, version=version, progress=5, step="GitHub-Prüfung")
        raise HTTPException(status_code=400, detail=message)
    if not _compare_versions(version, current):
        message = f"GitHub-Version {version} ist nicht neuer als installierte Version {current}."
        _append_log(message)
        _write_status("failed", message, version=version, progress=5, step="Versionsprüfung")
        raise HTTPException(status_code=400, detail=message)
    _append_log(f"Lade GitHub Release {release.get('tag')} herunter")
    _write_status("starting", "GitHub-Paket wird heruntergeladen", "stempeluhr", version, progress=5, step="GitHub-Download")
    try:
        with tempfile.TemporaryDirectory(prefix="stempeluhr-github-update-") as temp_dir:
            deb_path, checksum = download_release_assets(release, Path(temp_dir))
            _append_log(f"GitHub-Download geprüft: {deb_path.name} SHA256={checksum}")
            _write_status("uploaded", "GitHub-Paket heruntergeladen und SHA256 geprüft", "stempeluhr", version, progress=20, step="GitHub-Download OK")
            with deb_path.open("rb") as package_file:
                upload = UploadFile(filename=deb_path.name, file=package_file)
                return await upload_update(request, upload)
    except HTTPException:
        raise
    except Exception as exc:
        message = f"GitHub-Update konnte nicht vorbereitet werden: {exc}"
        _append_log(message)
        _write_status("failed", message, "stempeluhr", version, progress=10, step="GitHub-Download")
        raise HTTPException(status_code=500, detail=message)
