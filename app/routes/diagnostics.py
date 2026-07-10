from __future__ import annotations

import io
import json
import subprocess
import zipfile
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from .common import templates, require_system_admin_response
from app.auth import current_user, is_system_admin
from app.database import get_db
from app.services.diagnostics import collect_diagnostics

router = APIRouter()


def _admin_or_403(request: Request, db: Session):
    user = current_user(request, db)
    if not user or not is_system_admin(user):
        return None, JSONResponse({"detail": "Administratorrechte erforderlich"}, status_code=403)
    return user, None


@router.get("/system/diagnostics", response_class=HTMLResponse)
def diagnostics_page(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    return templates.TemplateResponse(
        "system_diagnostics.html",
        {"request": request, "user": user, "diagnostics": collect_diagnostics(db)},
    )


@router.get("/diagnostics")
def diagnostics_api(request: Request, db: Session = Depends(get_db)):
    _, error = _admin_or_403(request, db)
    if error:
        return error
    return collect_diagnostics(db)


@router.get("/api/v1/diagnostics")
def diagnostics_api_v1(request: Request, db: Session = Depends(get_db)):
    _, error = _admin_or_403(request, db)
    if error:
        return error
    return collect_diagnostics(db)


def _service_status() -> str:
    try:
        result = subprocess.run(
            ["systemctl", "status", "stempeluhr.service", "--no-pager", "-l"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        return (result.stdout + result.stderr)[-20000:]
    except Exception as exc:
        return f"Service-Status nicht verfügbar: {type(exc).__name__}\n"


@router.get("/system/diagnostics/report")
def diagnostics_report(request: Request, db: Session = Depends(get_db)):
    _, error = _admin_or_403(request, db)
    if error:
        return error

    diagnostics = collect_diagnostics(db)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "diagnostics.json",
            json.dumps(diagnostics, ensure_ascii=False, indent=2, default=str),
        )
        archive.writestr(
            "configuration.txt",
            "Konfigurationsdatei: {file}\nVorhanden: {exists}\n"
            "Fehlende Pflichtwerte: {required}\nFehlende empfohlene Werte: {recommended}\n"
            "Passwörter, Tokens und Secrets werden nicht exportiert.\n".format(
                file=diagnostics["configuration"]["file"],
                exists=diagnostics["configuration"]["exists"],
                required=", ".join(diagnostics["configuration"]["missing_required"]) or "keine",
                recommended=", ".join(diagnostics["configuration"]["missing_recommended"]) or "keine",
            ),
        )
        archive.writestr("stempeluhr-service.txt", _service_status())
        archive.writestr(
            "README.txt",
            "Stempeluhr Professional Diagnosebericht\n"
            "Dieser Bericht enthält keine Passwörter, Tokens oder vollständigen Konfigurationswerte.\n",
        )
    buffer.seek(0)
    headers = {"Content-Disposition": f'attachment; filename="stempeluhr-diagnose-{timestamp}.zip"'}
    return StreamingResponse(buffer, media_type="application/zip", headers=headers)
