from __future__ import annotations

import json
from datetime import datetime, timedelta
from html import escape

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Terminal
from app.services.terminal_protocol import TerminalCapability
from .common import require_admin_response

router = APIRouter()

CAPABILITY_LABELS = {
    "display": "Display",
    "rfid": "RFID",
    "nfc": "NFC",
    "qr": "QR-Code",
    "barcode": "Barcode",
    "pin": "PIN",
    "fingerprint": "Fingerabdruck",
    "camera": "Kamera",
    "speaker": "Lautsprecher",
    "buzzer": "Summer",
    "led": "LED",
    "relay": "Relais",
    "bluetooth": "Bluetooth",
    "offline_buffer": "Offline-Puffer",
}


def _online(terminal: Terminal) -> bool:
    return bool(terminal.last_seen and terminal.last_seen > datetime.now() - timedelta(seconds=90))


def _capability_badges(rows: list[TerminalCapability]) -> str:
    enabled = [row for row in rows if row.enabled]
    if not enabled:
        return "<span class='muted'>Keine Fähigkeiten gemeldet</span>"
    return "".join(
        f"<span class='cap'>{escape(CAPABILITY_LABELS.get(row.capability, row.capability))}</span>"
        for row in enabled
    )


def _page(terminals: list[Terminal], capability_map: dict[int, list[TerminalCapability]], message: str = "") -> str:
    online_count = sum(1 for item in terminals if _online(item))
    cards = "".join(
        f"""
        <article class='terminal-card'>
          <div class='terminal-head'>
            <div>
              <h2>{escape(item.name)}</h2>
              <div class='muted'>{escape(item.location or 'Kein Standort hinterlegt')}</div>
            </div>
            <span class='state {'online' if _online(item) else 'offline'}'>{'Online' if _online(item) else 'Offline'}</span>
          </div>
          <dl>
            <div><dt>Kennung</dt><dd><code>{escape(item.terminal_code or '—')}</code></dd></div>
            <div><dt>IP-Adresse</dt><dd>{escape(item.last_ip or '—')}</dd></div>
            <div><dt>Agent-Version</dt><dd>{escape(item.app_version or '—')}</dd></div>
            <div><dt>Letzter Kontakt</dt><dd>{item.last_seen.strftime('%d.%m.%Y %H:%M:%S') if item.last_seen else 'Noch nie'}</dd></div>
          </dl>
          <div class='caps'>{_capability_badges(capability_map.get(item.id, []))}</div>
          <div class='actions'>
            <a class='button' href='/system/terminals/{item.id}'>Details & Einstellungen</a>
          </div>
        </article>
        """
        for item in terminals
    ) or "<div class='empty'>Noch kein Terminal registriert. Ein Terminal erscheint automatisch, sobald sein Agent den Server erreicht.</div>"

    return f"""<!doctype html>
<html lang='de'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Terminalverwaltung</title>
<style>
:root{{--bg:#f4f7fb;--card:#fff;--text:#172033;--muted:#667085;--line:#dbe3ee;--blue:#1769e0;--green:#17864b;--red:#bd3434}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font-family:system-ui,-apple-system,Segoe UI,sans-serif}}
.wrap{{max-width:1280px;margin:auto;padding:28px}}a{{color:var(--blue);text-decoration:none}}h1{{margin:.3rem 0}}.subtitle,.muted{{color:var(--muted)}}
.summary{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin:22px 0}}.summary-card,.terminal-card,.empty{{background:var(--card);border:1px solid var(--line);border-radius:14px;box-shadow:0 4px 18px rgba(23,32,51,.06);padding:20px}}
.summary-card strong{{display:block;font-size:1.8rem;margin-top:4px}}.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}}
.terminal-head{{display:flex;justify-content:space-between;gap:16px;align-items:start}}.terminal-head h2{{margin:0 0 4px}}.state{{border-radius:999px;padding:6px 11px;font-weight:700;font-size:.86rem}}.state.online{{background:#eaf8ef;color:var(--green)}}.state.offline{{background:#fff0f0;color:var(--red)}}
dl{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin:20px 0}}dl div{{background:#f8fafc;border-radius:9px;padding:10px}}dt{{font-size:.78rem;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}}dd{{margin:4px 0 0;font-weight:600;overflow-wrap:anywhere}}
.caps{{display:flex;flex-wrap:wrap;gap:7px;min-height:32px}}.cap{{background:#eaf1ff;color:#174f9d;border-radius:999px;padding:5px 9px;font-size:.84rem;font-weight:650}}.actions{{margin-top:18px}}.button{{display:inline-block;background:var(--blue);color:white;padding:10px 14px;border-radius:8px;font-weight:700}}
.msg{{background:#ecfdf3;border:1px solid #a6e3bf;padding:11px 14px;border-radius:9px;margin:16px 0}}@media(max-width:850px){{.grid,.summary{{grid-template-columns:1fr}}dl{{grid-template-columns:1fr}}.wrap{{padding:15px}}}}
</style></head>
<body><main class='wrap'>
<p><a href='/system/monitoring'>← Zurück zur Systemverwaltung</a></p>
<h1>Terminals</h1><p class='subtitle'>Server-, All-in-One- und entfernte Hardware-Terminals zentral verwalten.</p>
{f"<div class='msg'>{escape(message)}</div>" if message else ''}
<section class='summary'>
 <div class='summary-card'><span class='muted'>Terminals insgesamt</span><strong>{len(terminals)}</strong></div>
 <div class='summary-card'><span class='muted'>Online</span><strong>{online_count}</strong></div>
 <div class='summary-card'><span class='muted'>Offline</span><strong>{len(terminals)-online_count}</strong></div>
</section>
<section class='grid'>{cards}</section>
</main></body></html>"""


def _detail_page(terminal: Terminal, capabilities: list[TerminalCapability], message: str = "") -> str:
    rows = "".join(
        f"<tr><td>{escape(CAPABILITY_LABELS.get(row.capability, row.capability))}</td><td>{'Aktiv' if row.enabled else 'Inaktiv'}</td><td><code>{escape(row.details or '—')}</code></td><td>{row.updated_at.strftime('%d.%m.%Y %H:%M:%S') if row.updated_at else '—'}</td></tr>"
        for row in capabilities
    ) or "<tr><td colspan='4'>Keine Fähigkeiten gemeldet.</td></tr>"
    return f"""<!doctype html><html lang='de'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>{escape(terminal.name)}</title><style>
body{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;background:#f4f7fb;color:#172033;margin:0}}.wrap{{max-width:1050px;margin:auto;padding:28px}}.card{{background:white;border:1px solid #dbe3ee;border-radius:14px;padding:22px;margin:18px 0;box-shadow:0 4px 18px rgba(23,32,51,.06)}}a{{color:#1769e0;text-decoration:none}}label{{display:block;font-weight:700;margin:12px 0 6px}}input,textarea{{width:100%;padding:10px;border:1px solid #bec9d8;border-radius:8px;font:inherit}}textarea{{min-height:90px}}button{{background:#1769e0;color:white;border:0;border-radius:8px;padding:11px 16px;font-weight:700;cursor:pointer}}table{{width:100%;border-collapse:collapse}}th,td{{border-bottom:1px solid #dbe3ee;padding:11px;text-align:left}}th{{background:#f8fafc}}.status{{font-weight:750;color:{'#17864b' if _online(terminal) else '#bd3434'}}}.msg{{background:#ecfdf3;border:1px solid #a6e3bf;padding:11px 14px;border-radius:9px}}</style></head>
<body><main class='wrap'><p><a href='/system/terminals'>← Zurück zu allen Terminals</a></p><h1>{escape(terminal.name)}</h1><p class='status'>{'Online' if _online(terminal) else 'Offline'}</p>
{f"<div class='msg'>{escape(message)}</div>" if message else ''}
<section class='card'><h2>Einstellungen</h2><form method='post'>
<label>Name</label><input name='name' value='{escape(terminal.name)}' required maxlength='100'>
<label>Standort</label><input name='location' value='{escape(terminal.location or '')}' maxlength='255' placeholder='z. B. Empfang oder Lager'>
<label>Beschreibung</label><textarea name='description' placeholder='Optionale Hinweise zum Gerät'>{escape(terminal.description or '')}</textarea>
<label><input style='width:auto' type='checkbox' name='active' {'checked' if terminal.active else ''}> Terminal aktiv</label><br><button type='submit'>Einstellungen speichern</button></form></section>
<section class='card'><h2>Verbindung</h2><p><strong>Kennung:</strong> <code>{escape(terminal.terminal_code or '—')}</code></p><p><strong>IP-Adresse:</strong> {escape(terminal.last_ip or '—')}</p><p><strong>Agent-Version:</strong> {escape(terminal.app_version or '—')}</p><p><strong>Letzter Kontakt:</strong> {terminal.last_seen.strftime('%d.%m.%Y %H:%M:%S') if terminal.last_seen else 'Noch nie'}</p></section>
<section class='card'><h2>Gemeldete Fähigkeiten</h2><table><thead><tr><th>Fähigkeit</th><th>Status</th><th>Details</th><th>Aktualisiert</th></tr></thead><tbody>{rows}</tbody></table></section>
</main></body></html>"""


@router.get('/system/terminals', response_class=HTMLResponse)
def terminal_list(request: Request, message: str = '', db: Session = Depends(get_db)):
    user, redirect = require_admin_response(request, db)
    if redirect:
        return redirect
    terminals = db.query(Terminal).order_by(Terminal.name).all()
    rows = db.query(TerminalCapability).order_by(TerminalCapability.capability).all()
    capability_map: dict[int, list[TerminalCapability]] = {}
    for row in rows:
        capability_map.setdefault(row.terminal_id, []).append(row)
    return HTMLResponse(_page(terminals, capability_map, message))


@router.get('/system/terminals/{terminal_id}', response_class=HTMLResponse)
def terminal_detail(terminal_id: int, request: Request, message: str = '', db: Session = Depends(get_db)):
    user, redirect = require_admin_response(request, db)
    if redirect:
        return redirect
    terminal = db.query(Terminal).filter(Terminal.id == terminal_id).first()
    if not terminal:
        return HTMLResponse('<h1>Terminal nicht gefunden</h1>', status_code=404)
    capabilities = db.query(TerminalCapability).filter(TerminalCapability.terminal_id == terminal_id).order_by(TerminalCapability.capability).all()
    return HTMLResponse(_detail_page(terminal, capabilities, message))


@router.post('/system/terminals/{terminal_id}')
def terminal_update(
    terminal_id: int,
    request: Request,
    name: str = Form(...),
    location: str = Form(''),
    description: str = Form(''),
    active: str | None = Form(None),
    db: Session = Depends(get_db),
):
    user, redirect = require_admin_response(request, db)
    if redirect:
        return redirect
    terminal = db.query(Terminal).filter(Terminal.id == terminal_id).first()
    if not terminal:
        return HTMLResponse('<h1>Terminal nicht gefunden</h1>', status_code=404)
    terminal.name = name.strip()[:100] or terminal.name
    terminal.location = location.strip()[:255] or None
    terminal.description = description.strip() or None
    terminal.active = active is not None
    db.commit()
    return RedirectResponse(f'/system/terminals/{terminal_id}?message=Terminal%20wurde%20gespeichert.', status_code=303)
