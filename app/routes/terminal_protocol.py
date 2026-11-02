from __future__ import annotations

import json
import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Terminal
from app.services.terminal_protocol import (
    PROTOCOL_VERSION,
    TerminalCapability,
    normalize_capabilities,
    protocol_response,
)

router = APIRouter(prefix="/api/v2/terminals", tags=["terminal-protocol"])


def _terminal_code(data: dict) -> str:
    return str(data.get("terminal_code") or data.get("hostname") or "").strip()[:100]


@router.post("/register")
async def register_terminal(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
    except Exception:
        data = {}

    code = _terminal_code(data)
    if not code:
        return JSONResponse({"status": "error", "message": "terminal_code oder hostname fehlt"}, status_code=400)

    terminal = db.query(Terminal).filter(Terminal.terminal_code == code).first()
    created = terminal is None
    supplied_key = str(data.get("api_key") or "").strip()
    generated_key = False

    if terminal is None:
        terminal = Terminal(
            name=str(data.get("name") or data.get("hostname") or code)[:100],
            terminal_code=code,
            api_key=secrets.token_urlsafe(32),
            active=True,
            created_at=datetime.now(),
        )
        generated_key = True
        db.add(terminal)
        db.flush()
    elif not terminal.api_key:
        terminal.api_key = secrets.token_urlsafe(32)
        generated_key = True
    elif not supplied_key or not secrets.compare_digest(terminal.api_key, supplied_key):
        # Ein bereits bekanntes Terminal kann seinen lokalen State verlieren
        # (Neuinstallation, defekte/gelöschte State-Datei). In diesem Fall
        # wird bei der expliziten Neuregistrierung ein neuer Schlüssel erzeugt.
        # Der alte Schlüssel wird damit sofort ungültig und nicht offengelegt.
        terminal.api_key = secrets.token_urlsafe(32)
        generated_key = True

    terminal.active = True
    terminal.last_seen = datetime.now()
    terminal.last_ip = str(data.get("ip_address") or (request.client.host if request.client else ""))[:100]
    terminal.app_version = str(data.get("agent_version") or data.get("app_version") or "")[:50]

    capabilities = normalize_capabilities(data.get("capabilities"))
    db.query(TerminalCapability).filter(TerminalCapability.terminal_id == terminal.id).delete(synchronize_session=False)
    for item in capabilities:
        db.add(TerminalCapability(
            terminal_id=terminal.id,
            capability=item["name"],
            enabled=item["enabled"],
            details=json.dumps(item.get("details"), ensure_ascii=False) if item.get("details") is not None else None,
            detected_at=datetime.now(),
            updated_at=datetime.now(),
        ))
    db.commit()

    result = protocol_response(terminal_id=terminal.id)
    result.update({
        "created": created,
        "terminal_code": terminal.terminal_code,
        "api_key": terminal.api_key if generated_key else None,
        "capabilities": [item["name"] for item in capabilities if item["enabled"]],
    })
    return result


@router.post("/heartbeat")
async def terminal_heartbeat(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
    except Exception:
        data = {}

    code = _terminal_code(data)
    if not code:
        return JSONResponse({"status": "error", "message": "Terminalkennung fehlt"}, status_code=400)

    terminal = db.query(Terminal).filter(Terminal.terminal_code == code).first()
    if terminal is None:
        return JSONResponse({
            "status": "registration_required",
            "protocol_version": PROTOCOL_VERSION,
            "message": "Terminal ist noch nicht registriert",
        }, status_code=409)

    supplied_key = str(data.get("api_key") or "")
    if not terminal.api_key or not supplied_key or not secrets.compare_digest(terminal.api_key, supplied_key):
        return JSONResponse({"status": "error", "message": "Ungültiger oder fehlender Terminal-Schlüssel"}, status_code=403)

    terminal.last_seen = datetime.now()
    terminal.last_ip = str(data.get("ip_address") or (request.client.host if request.client else ""))[:100]
    terminal.app_version = str(data.get("agent_version") or data.get("app_version") or "")[:50]
    db.commit()

    # In Phase 2 bleibt die bestehende Befehlswarteschlange kompatibel. Die
    # generische Queue wird in Phase 3 auf eigene Command-Datensätze migriert.
    return protocol_response(terminal_id=terminal.id, command=None)


@router.get("/{terminal_id}/capabilities")
def terminal_capabilities(terminal_id: int, db: Session = Depends(get_db)):
    terminal = db.query(Terminal).filter(Terminal.id == terminal_id).first()
    if terminal is None:
        return JSONResponse({"status": "error", "message": "Terminal nicht gefunden"}, status_code=404)
    rows = db.query(TerminalCapability).filter(TerminalCapability.terminal_id == terminal_id).order_by(TerminalCapability.capability).all()
    return {
        "status": "ok",
        "terminal": {
            "id": terminal.id,
            "name": terminal.name,
            "terminal_code": terminal.terminal_code,
            "last_seen": terminal.last_seen.isoformat() if terminal.last_seen else None,
            "online": bool(terminal.last_seen and (datetime.now() - terminal.last_seen).total_seconds() < 90),
        },
        "capabilities": [
            {
                "name": row.capability,
                "enabled": row.enabled,
                "details": json.loads(row.details) if row.details else None,
            }
            for row in rows
        ],
    }
