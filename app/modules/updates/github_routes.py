"""GitHub-Release-Endpunkte für die vorhandene Updateverwaltung."""
from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from app.modules.updates.github_release import download_release_assets, latest_release
from app.modules.updates.routes import _append_log, _compare_versions, _current_version, _write_status, upload_update

router = APIRouter()


@router.get("/system/settings/updates/github/check")
async def github_update_check():
    release = latest_release()
    current = _current_version()
    if not release.get("ok"):
        return JSONResponse({"ok": False, "current_version": current, "error": release.get("error", "Unbekannter Fehler")}, status_code=502)

    release["current_version"] = current
    release["update_available"] = bool(
        release.get("assets_complete")
        and _compare_versions(str(release.get("version") or ""), current)
    )
    return JSONResponse(release)


@router.post("/system/settings/updates/github/install")
async def github_update_install(request: Request):
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
