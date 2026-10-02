from __future__ import annotations

import json
from datetime import datetime, timedelta
from html import escape

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Terminal
from app.services.terminal_protocol import TerminalCapability
from .common import require_admin_response

router = APIRouter()

LABELS = {
    "display": "Display",
    "rfid": "RFID-Leser",
    "nfc": "NFC-Leser",
    "qr": "QR-Code",
    "barcode": "Barcode",
    "pin": "PIN-Eingabe",
    "fingerprint": "Fingerabdrucksensor",
    "camera": "Kamera",
    "speaker": "Lautsprecher",
    "buzzer": "Summer",
    "led": "LED",
    "relay": "Relais",
    "bluetooth": "Bluetooth",
    "offline_buffer": "Offline-Puffer",
}

DESCRIPTIONS = {
    "display": "Anzeige, Kiosk-Bildschirm und Statusmeldungen des Terminals.",
    "rfid": "RFID-Karten, Transponder, Handy und Smartwatch einlesen.",
    "nfc": "NFC-fähige Medien und Mobilgeräte erkennen.",
    "qr": "QR-Codes über Kamera oder Scanner erfassen.",
    "barcode": "Barcodes über angeschlossene Scanner erfassen.",
    "pin": "Anmeldung und Buchung über eine PIN-Eingabe.",
    "fingerprint": "Fingerabdrucksensor und zugehörigen Treiber prüfen.",
    "camera": "Kameraerkennung und Geräteverfügbarkeit prüfen.",
    "speaker": "Audioausgabe des Terminals prüfen.",
    "buzzer": "Akustischen Summer des Terminals prüfen.",
    "led": "Status-LEDs des Terminals prüfen.",
    "relay": "Angeschlossenes Relais, beispielsweise für Türfreigaben.",
    "bluetooth": "Bluetooth-Adapter und erreichbare Geräte.",
    "offline_buffer": "Zwischenspeicherung bei unterbrochener Serververbindung.",
}


def _online(terminal: Terminal) -> bool:
    return bool(terminal.last_seen and terminal.last_seen > datetime.now() - timedelta(seconds=90))


def _details(row: TerminalCapability) -> str:
    if not row.details:
        return "Keine zusätzlichen Gerätedetails gemeldet."
    try:
        value = json.loads(row.details)
        return json.dumps(value, ensure_ascii=False, indent=2)
    except Exception:
        return str(row.details)


def _layout(title: str, body: str) -> str:
    return f"""<!doctype html><html lang='de'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>{escape(title)}</title><style>
body{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;background:#f4f7fb;color:#172033;margin:0}}.wrap{{max-width:1180px;margin:auto;padding:28px}}a{{color:#1769e0;text-decoration:none}}.grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}}.card{{background:#fff;border:1px solid #dbe3ee;border-radius:14px;padding:19px;box-shadow:0 4px 18px #1720330f}}.card h2{{margin:.1rem 0 .5rem}}.state{{display:inline-block;border-radius:999px;padding:5px 9px;font-weight:700;font-size:.82rem}}.ok{{background:#eaf8ef;color:#17864b}}.off{{background:#fff0f0;color:#bd3434}}.muted{{color:#667085}}.button{{display:inline-block;background:#1769e0;color:#fff;padding:9px 13px;border-radius:8px;font-weight:700;margin-top:10px}}pre{{white-space:pre-wrap;background:#f8fafc;border:1px solid #dbe3ee;padding:13px;border-radius:9px}}.notice{{background:#fff8e7;border:1px solid #e7c76b;padding:13px;border-radius:9px}}@media(max-width:900px){{.grid{{grid-template-columns:1fr}}.wrap{{padding:15px}}}}
</style></head><body><main class='wrap'>{body}</main></body></html>"""


@router.get('/system/hardware', response_class=HTMLResponse)
def hardware_overview(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_admin_response(request, db)
    if redirect:
        return redirect
    terminals = db.query(Terminal).order_by(Terminal.name).all()
    cards = []
    for terminal in terminals:
        count = db.query(TerminalCapability).filter(
            TerminalCapability.terminal_id == terminal.id,
            TerminalCapability.enabled == True,
        ).count()
        cards.append(f"""<article class='card'><h2>{escape(terminal.name)}</h2>
        <p class='muted'>{escape(terminal.location or 'Kein Standort')}</p>
        <span class='state {'ok' if _online(terminal) else 'off'}'>{'Online' if _online(terminal) else 'Offline'}</span>
        <p><strong>{count}</strong> aktive Hardware-Fähigkeiten</p>
        <a class='button' href='/system/terminals/{terminal.id}/hardware'>Hardware öffnen</a></article>""")
    body = "<p><a href='/system/settings'>← Systemeinstellungen</a></p><h1>Hardware</h1><p class='muted'>Hardware aller registrierten Terminals anzeigen und diagnostizieren.</p><section class='grid'>" + ("".join(cards) or "<div class='card'>Noch kein Terminal registriert.</div>") + "</section>"
    return HTMLResponse(_layout("Hardware", body))


@router.get('/system/terminals/{terminal_id}/hardware', response_class=HTMLResponse)
def terminal_hardware(terminal_id: int, request: Request, db: Session = Depends(get_db)):
    user, redirect = require_admin_response(request, db)
    if redirect:
        return redirect
    terminal = db.query(Terminal).filter(Terminal.id == terminal_id).first()
    if not terminal:
        return HTMLResponse(_layout("Terminal nicht gefunden", "<h1>Terminal nicht gefunden</h1>"), status_code=404)
    rows = db.query(TerminalCapability).filter(TerminalCapability.terminal_id == terminal_id).order_by(TerminalCapability.capability).all()
    cards = []
    for row in rows:
        name = LABELS.get(row.capability, row.capability)
        cards.append(f"""<article class='card'><h2>{escape(name)}</h2>
        <span class='state {'ok' if row.enabled else 'off'}'>{'Aktiv' if row.enabled else 'Inaktiv'}</span>
        <p>{escape(DESCRIPTIONS.get(row.capability, 'Vom Terminal gemeldete Hardware-Fähigkeit.'))}</p>
        <a class='button' href='/system/terminals/{terminal.id}/hardware/{escape(row.capability)}'>Details & Diagnose</a></article>""")
    body = f"<p><a href='/system/hardware'>← Hardwareübersicht</a></p><h1>Hardware – {escape(terminal.name)}</h1><p class='muted'>{escape(terminal.location or 'Kein Standort')} · {'Online' if _online(terminal) else 'Offline'}</p><section class='grid'>" + ("".join(cards) or "<div class='card'>Das Terminal hat noch keine Fähigkeiten gemeldet.</div>") + "</section>"
    return HTMLResponse(_layout(f"Hardware – {terminal.name}", body))


@router.get('/system/terminals/{terminal_id}/hardware/{capability}', response_class=HTMLResponse)
def terminal_hardware_detail(terminal_id: int, capability: str, request: Request, db: Session = Depends(get_db)):
    user, redirect = require_admin_response(request, db)
    if redirect:
        return redirect
    terminal = db.query(Terminal).filter(Terminal.id == terminal_id).first()
    row = db.query(TerminalCapability).filter(
        TerminalCapability.terminal_id == terminal_id,
        TerminalCapability.capability == capability,
    ).first()
    if not terminal or not row:
        return HTMLResponse(_layout("Hardware nicht gefunden", "<h1>Hardware nicht gefunden</h1>"), status_code=404)
    name = LABELS.get(capability, capability)
    status = "Aktiv und vom Terminal gemeldet" if row.enabled else "Vom Terminal als inaktiv gemeldet"
    body = f"""<p><a href='/system/terminals/{terminal.id}/hardware'>← Hardware von {escape(terminal.name)}</a></p>
    <h1>{escape(name)}</h1><section class='card'><h2>Status</h2><p><strong>{escape(status)}</strong></p>
    <p>Terminal: {escape(terminal.name)} · {'Online' if _online(terminal) else 'Offline'}</p>
    <p>Zuletzt aktualisiert: {row.updated_at.strftime('%d.%m.%Y %H:%M:%S') if row.updated_at else 'unbekannt'}</p></section>
    <section class='card'><h2>Vom Agent gemeldete Details</h2><pre>{escape(_details(row))}</pre></section>
    <section class='notice'><strong>Fern-Hardwaretest:</strong> Die Seite ist jetzt vollständig bedienbar. Aktive Testbefehle werden im nächsten Schritt an die Befehlswarteschlange des Terminal-Agenten angebunden. Bis dahin zeigt diese Seite zuverlässig Erkennung, Status und Agentdetails an.</section>"""
    return HTMLResponse(_layout(name, body))
