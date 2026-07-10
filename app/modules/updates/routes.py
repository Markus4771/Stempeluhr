import os
import shutil
import subprocess
import re
import json
import hashlib
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Request, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

from app.routes.common import templates
from app.version import get_app_version

router = APIRouter()

UPLOAD_DIR = Path(os.environ.get("STEMPELUHR_UPDATE_UPLOAD_DIR", "/var/lib/stempeluhr/uploads/updates"))
LEGACY_UPLOAD_DIR = Path("/opt/stempeluhr/uploads/updates")
LOG_FILE = Path("/opt/stempeluhr/logs/update.log")
WEB_UPDATE_RUNNER = Path("/usr/local/sbin/stempeluhr-web-update-run")
STATUS_FILE = Path("/opt/stempeluhr/logs/update-status.json")


def _append_log(message: str) -> None:
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(f"[{timestamp}] gui-update: {message}\n")
    except Exception:
        pass


def _write_status(state: str, message: str = "", package: str = "", version: str = "", progress: int = 0, step: str = "") -> None:
    try:
        STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "state": state,
            "message": message,
            "package": package,
            "version": version,
            "progress": int(progress or 0),
            "step": step,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        STATUS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.chmod(STATUS_FILE, 0o664)
    except Exception:
        pass


def _read_status() -> dict:
    try:
        if STATUS_FILE.exists():
            return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"state": "idle", "message": "Bereit", "progress": 0, "step": "Bereit", "time": ""}


def _read_log_tail(lines: int = 180) -> str:
    if not LOG_FILE.exists():
        return ""
    try:
        content = LOG_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
        return "\n".join(content[-lines:])
    except Exception as exc:
        return f"Update-Protokoll konnte nicht gelesen werden: {exc}"


def _current_version() -> str:
    return get_app_version() or "unbekannt"


def _update_running() -> bool:
    # zuerst Statusdatei beachten
    status = _read_status()
    if status.get("state") in {"uploaded", "starting", "running"}:
        return True
    try:
        result = subprocess.run(
            ["systemctl", "list-units", "--all", "--no-legend", "--no-pager", "stempeluhr-update-*"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=3,
        )
        return bool(result.stdout.strip())
    except Exception:
        return False


def _uploaded_debs():
    try:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        files = []
        all_debs = list(UPLOAD_DIR.glob("*.deb"))
        if LEGACY_UPLOAD_DIR != UPLOAD_DIR and LEGACY_UPLOAD_DIR.exists():
            all_debs += list(LEGACY_UPLOAD_DIR.glob("*.deb"))
        seen = set()
        for p in sorted(all_debs, key=lambda x: x.stat().st_mtime, reverse=True):
            if str(p) in seen:
                continue
            seen.add(str(p))
            stat = p.stat()
            meta = _deb_info(p)
            files.append({
                "name": p.name,
                "size": stat.st_size,
                "mtime": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "package": meta.get("Package", ""),
                "version": meta.get("Version", ""),
            })
        return files[:20]
    except Exception:
        return []


def _deb_info(path: Path) -> dict:
    try:
        result = subprocess.run(
            ["dpkg-deb", "-f", str(path), "Package", "Version", "Architecture"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
        if result.returncode != 0:
            return {}
        lines = result.stdout.splitlines()
        data = {}
        for line in lines:
            if ":" in line:
                k, v = line.split(":", 1)
                data[k.strip()] = v.strip()
        return data
    except Exception:
        return {}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _compare_versions(uploaded: str, current: str) -> bool:
    """True, wenn uploaded neuer als current ist. Bei unbekannter aktueller Version erlauben."""
    if not uploaded:
        return False
    if not current or current == "unbekannt":
        return True
    try:
        result = subprocess.run(
            ["dpkg", "--compare-versions", uploaded, "gt", current],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        # Fallback: unklare Vergleichbarkeit nicht blockieren, aber protokollieren.
        _append_log(f"Versionsvergleich konnte nicht sicher durchgeführt werden: upload={uploaded} current={current}")
        return True


def _free_space_ok(path: Path, needed_bytes: int) -> tuple[bool, str]:
    usage = shutil.disk_usage(str(path))
    # Mindestens Paketgröße x3 + 100 MB Reserve.
    required = max(needed_bytes * 3, 100 * 1024 * 1024)
    ok = usage.free >= required
    return ok, f"frei={usage.free} benötigt={required}"


@router.get("/system/settings/updates", response_class=HTMLResponse)
async def updates_page(request: Request):
    return templates.TemplateResponse(
        "system_updates.html",
        {
            "request": request,
            "current_version": _current_version(),
            "log_tail": _read_log_tail(),
            "update_running": _update_running(),
            "upload_dir": str(UPLOAD_DIR),
            "legacy_upload_dir": str(LEGACY_UPLOAD_DIR),
            "uploaded_debs": _uploaded_debs(),
            "update_status": _read_status(),
        },
    )


@router.get("/system/settings/updates/status")
async def updates_status():
    return JSONResponse({
        "running": _update_running(),
        "status": _read_status(),
        "log_tail": _read_log_tail(),
        "current_version": _current_version(),
    })


@router.get("/system/settings/updates/diagnostics")
async def updates_diagnostics():
    checks = []
    def add(name: str, ok: bool, detail: str = ""):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    add("Update-Runner vorhanden", WEB_UPDATE_RUNNER.exists(), str(WEB_UPDATE_RUNNER))
    add("Upload-Verzeichnis beschreibbar", os.access(str(UPLOAD_DIR), os.W_OK) or not UPLOAD_DIR.exists(), str(UPLOAD_DIR))
    add("Kompatibilitäts-Verzeichnis", LEGACY_UPLOAD_DIR.exists(), str(LEGACY_UPLOAD_DIR))
    add("Log-Verzeichnis beschreibbar", os.access(str(LOG_FILE.parent), os.W_OK) or not LOG_FILE.parent.exists(), str(LOG_FILE.parent))
    try:
        r = subprocess.run(["systemctl", "is-enabled", "stempeluhr.service"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
        add("systemd-Service aktiviert", r.returncode == 0, (r.stdout or r.stderr).strip())
    except Exception as exc:
        add("systemd-Service aktiviert", False, str(exc))
    try:
        r = subprocess.run(["sudo", "-n", "-l", str(WEB_UPDATE_RUNNER), str(UPLOAD_DIR / "dummy.deb")], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        add("sudoers für Runner", r.returncode == 0, ((r.stdout or "") + (r.stderr or "")).strip()[-500:])
    except Exception as exc:
        add("sudoers für Runner", False, str(exc))
    return JSONResponse({"checks": checks, "status": _read_status(), "current_version": _current_version()})


@router.post("/system/settings/updates/upload")
async def upload_update(request: Request, update_file: UploadFile = File(...)):
    filename = Path(update_file.filename or "").name
    if not filename.endswith(".deb"):
        _append_log(f"Upload abgelehnt, keine DEB-Datei: {filename}")
        _write_status("failed", f"Keine DEB-Datei: {filename}", progress=0, step="Paketprüfung")
        raise HTTPException(status_code=400, detail="Bitte eine DEB-Datei hochladen.")
    if not re.match(r"^[A-Za-z0-9._+-]+\.deb$", filename):
        _append_log(f"Upload abgelehnt, ungültiger Dateiname: {filename}")
        _write_status("failed", f"Ungültiger Dateiname: {filename}", progress=0, step="Paketprüfung")
        raise HTTPException(status_code=400, detail="Ungültiger Dateiname.")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chown(UPLOAD_DIR, os.getuid(), os.getgid())
    except Exception:
        pass
    target = UPLOAD_DIR / filename
    tmp_target = UPLOAD_DIR / (filename + ".uploading")

    try:
        with tmp_target.open("wb") as f:
            shutil.copyfileobj(update_file.file, f)
        tmp_target.replace(target)
        os.chmod(target, 0o644)
    except Exception as exc:
        _append_log(f"Upload fehlgeschlagen: {filename}: {exc}")
        _write_status("failed", f"Upload fehlgeschlagen: {exc}", progress=0, step="Upload")
        raise HTTPException(status_code=500, detail=f"Upload fehlgeschlagen: {exc}")

    meta = _deb_info(target)
    pkg = meta.get("Package", "")
    ver = meta.get("Version", "")
    arch = meta.get("Architecture", "")
    _append_log(f"DEB hochgeladen: {target} Paket={pkg} Version={ver} Architektur={arch}")
    _write_status("uploaded", "DEB hochgeladen", pkg, ver, progress=10, step="Upload abgeschlossen")

    if pkg != "stempeluhr":
        _append_log(f"Upload abgelehnt, falsches Paket: {pkg}")
        _write_status("failed", f"Falsches Paket: {pkg}. Erwartet: stempeluhr", pkg, ver, progress=15, step="Paketprüfung")
        raise HTTPException(status_code=400, detail=f"Falsches Paket: {pkg}. Erwartet: stempeluhr")
    if not ver:
        _append_log("Upload abgelehnt, Paketversion konnte nicht gelesen werden")
        _write_status("failed", "Paketversion konnte nicht gelesen werden", pkg, ver, progress=15, step="Paketprüfung")
        raise HTTPException(status_code=400, detail="Paketversion konnte nicht gelesen werden.")
    if arch and arch != "all":
        msg = f"Falsche Architektur: {arch}. Erwartet: all"
        _append_log(msg)
        _write_status("failed", msg, pkg, ver, progress=15, step="Paketprüfung")
        raise HTTPException(status_code=400, detail=msg)

    current = _current_version()
    if not _compare_versions(ver, current):
        msg = f"Paketversion {ver} ist nicht neuer als installierte Version {current}."
        _append_log(msg)
        _write_status("failed", msg, pkg, ver, progress=15, step="Versionsprüfung")
        raise HTTPException(status_code=400, detail=msg)

    ok_space, space_msg = _free_space_ok(UPLOAD_DIR, target.stat().st_size)
    if not ok_space:
        msg = f"Nicht genügend freier Speicher für Update: {space_msg}"
        _append_log(msg)
        _write_status("failed", msg, pkg, ver, progress=20, step="Speicherprüfung")
        raise HTTPException(status_code=400, detail=msg)

    checksum = _sha256(target)
    _append_log(f"Paketprüfung OK: Paket={pkg} Version={ver} Architektur={arch or 'unbekannt'} SHA256={checksum} Speicher={space_msg}")
    _write_status("uploaded", "Paket geprüft und bereit zur Installation", pkg, ver, progress=25, step="Paketprüfung OK")

    if not WEB_UPDATE_RUNNER.exists():
        _append_log(f"Update-Starter fehlt: {WEB_UPDATE_RUNNER}")
        _write_status("failed", f"Update-Starter fehlt: {WEB_UPDATE_RUNNER}", pkg, ver, progress=20, step="Voraussetzungen")
        raise HTTPException(status_code=500, detail=f"Update-Starter fehlt: {WEB_UPDATE_RUNNER}")

    try:
        # Direkter sudo-Test für genau diesen Runner. stdout/stderr kommen ins Update-Log.
        _append_log("Prüfe sudo-Rechte für Web-Update-Runner")
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as log_fh:
            sudo_test = subprocess.run(
                ["sudo", "-n", "-l", str(WEB_UPDATE_RUNNER), str(target)],
                stdout=log_fh,
                stderr=log_fh,
                stdin=subprocess.DEVNULL,
                timeout=10,
            )
        if sudo_test.returncode != 0:
            msg = "sudo-Test fehlgeschlagen. Prüfe systemd NoNewPrivileges und /etc/sudoers.d/stempeluhr-web-update. Ab Version 5.1.23 installiert das Paket ein systemd-Override 90-webupdate.conf."
            _append_log(msg)
            _write_status("failed", msg, pkg, ver, progress=25, step="sudo/Runner")
            raise HTTPException(status_code=500, detail=msg)

        _append_log(f"Starte Web-Update über Runner: {WEB_UPDATE_RUNNER} {target}")
        _write_status("starting", "Update wird gestartet", pkg, ver, progress=30, step="Runner startet")
        with LOG_FILE.open("a", encoding="utf-8") as log_fh:
            proc = subprocess.Popen(
                ["sudo", "-n", str(WEB_UPDATE_RUNNER), str(target)],
                stdout=log_fh,
                stderr=log_fh,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
                close_fds=True,
            )
        _append_log(f"Update-Starter aufgerufen, PID={proc.pid}: {target}")
    except HTTPException:
        raise
    except Exception as exc:
        _append_log(f"Update konnte nicht gestartet werden: {exc}")
        _write_status("failed", f"Update konnte nicht gestartet werden: {exc}", pkg, ver, progress=30, step="Runner")
        raise HTTPException(status_code=500, detail=f"Update konnte nicht gestartet werden: {exc}")

    return RedirectResponse("/system/settings/updates?started=1", status_code=303)
