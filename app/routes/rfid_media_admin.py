from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta
from html import escape
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth_plugins.registry import installed_plugin
from app.database import get_db
from app.models import Employee, RaspberryClient
from app.services.rfid_media import EmployeeRfidMedia, add_rfid_medium
from .common import require_admin_response, log_action

router = APIRouter()


MEDIA_PLUGIN = {
    "rfid": "rfid",
    "nfc_ring": "rfid",
    "other": "rfid",
    "nfc_phone": "mobile_app",
    "nfc_watch": "smartwatch",
}


def _online(client: RaspberryClient) -> bool:
    return bool(client.last_seen and client.last_seen > datetime.now() - timedelta(seconds=90))


def _type_label(value: str) -> str:
    return {
        "rfid": "RFID-Karte",
        "nfc_phone": "Handy",
        "nfc_watch": "Smartwatch",
        "nfc_ring": "NFC-Ring",
        "other": "Sonstiges",
    }.get(value, value or "RFID/NFC")


def _page(employee: Employee, media: list[EmployeeRfidMedia], clients: list[RaspberryClient], message: str = "") -> str:
    rows = "".join(
        f"<tr><td><strong>{escape(m.name)}</strong></td>"
        f"<td><span class='type'>{escape(_type_label(m.media_type))}</span></td>"
        f"<td><code>{escape(m.uid_raw or m.uid)}</code></td>"
        f"<td><span class='status {'ok' if m.active else 'off'}'>{'Aktiv' if m.active else 'Inaktiv'}</span></td>"
        f"<td>{m.last_used_at.strftime('%d.%m.%Y %H:%M:%S') if m.last_used_at else 'Noch nie'}</td>"
        f"<td><form method='post' action='/admin/employees/{employee.id}/rfid-media/{m.id}/delete' "
        f"onsubmit=\"return confirm('Medium wirklich löschen?')\"><button class='danger' type='submit'>Löschen</button></form></td></tr>"
        for m in media
    ) or "<tr><td colspan='6' class='empty'>Noch keine RFID-/NFC-Medien vorhanden.</td></tr>"

    client_options = "".join(
        f"<option value='{c.id}' {'selected' if index == 0 and _online(c) else ''}>"
        f"{escape(c.hostname)} ({escape(c.ip_address or 'keine IP')}) – {'online' if _online(c) else 'offline'}</option>"
        for index, c in enumerate(sorted(clients, key=lambda item: (not _online(item), item.hostname.lower())))
    )
    if not client_options:
        client_options = "<option value=''>Kein Raspberry-Terminal registriert</option>"

    return f"""<!doctype html>
<html lang='de'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Anmeldemedien</title>
<style>
:root{{--bg:#f3f6fa;--card:#fff;--text:#172033;--muted:#667085;--line:#dbe3ee;--blue:#1769e0;--green:#18864b;--red:#c93434}}
*{{box-sizing:border-box}}body{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;background:var(--bg);color:var(--text);margin:0}}
.wrap{{max-width:1250px;margin:0 auto;padding:28px}}a{{color:var(--blue)}}h1{{margin:.5rem 0 .2rem;font-size:2rem}}.subtitle{{color:var(--muted);margin-top:0}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:14px;box-shadow:0 4px 18px rgba(23,32,51,.06);padding:22px;margin:18px 0}}
.info{{background:#eef6ff;border-color:#b7d5ff;display:flex;justify-content:space-between;gap:18px;align-items:center}}
.msg{{padding:12px 15px;background:#ecfdf3;border:1px solid #a6e3bf;border-radius:9px;margin:14px 0}}
table{{width:100%;border-collapse:collapse;margin-top:12px}}th,td{{border-bottom:1px solid var(--line);padding:13px;text-align:left}}th{{background:#f8fafc}}code{{font-size:.95rem}}
.type{{background:#e8eef8;padding:4px 9px;border-radius:8px}}.status{{display:inline-flex;align-items:center;gap:6px}}.status:before{{content:'';width:9px;height:9px;border-radius:50%;background:#999}}.status.ok:before{{background:#55bd66}}.status.off:before{{background:#aaa}}
.grid{{display:grid;grid-template-columns:1.2fr 1fr 1.2fr;gap:16px}}label{{display:block;font-weight:650;margin-bottom:6px}}input,select{{width:100%;padding:11px;border:1px solid #bfcada;border-radius:8px;font:inherit}}
button,.button{{border:0;border-radius:8px;padding:11px 16px;font:inherit;font-weight:650;cursor:pointer;background:var(--blue);color:white}}button:disabled{{opacity:.5;cursor:not-allowed}}button.secondary{{background:white;color:var(--blue);border:1px solid var(--blue)}}button.danger{{background:white;color:var(--red);border:1px solid #e48b8b;padding:7px 11px}}
.scanbox{{display:flex;gap:12px;align-items:end;margin-top:15px}}.scan-status{{padding:12px;border-radius:9px;background:#f2f4f7;color:var(--muted);margin-top:14px}}.scan-status.ready{{background:#ecfdf3;color:#116a3b}}.scan-status.error{{background:#fff1f1;color:#9f2424}}.scan-status.info{{background:#eef6ff;color:#175ca8}}
.actions{{display:flex;gap:10px;margin-top:18px}}.empty{{color:var(--muted);text-align:center}}@media(max-width:800px){{.grid{{grid-template-columns:1fr}}.info,.scanbox{{display:block}}table{{font-size:.85rem}}.wrap{{padding:14px}}}}
</style></head>
<body><main class='wrap'>
<a href='/admin/employees/{employee.id}/edit'>← Zurück zum Mitarbeiter</a>
<h1>Anmeldemedien: {escape(employee.first_name)} {escape(employee.last_name)}</h1>
<p class='subtitle'>Das ausgewählte Medium bestimmt automatisch das zuständige Anmelde-Plugin.</p>
{f"<div class='msg'>{escape(message)}</div>" if message else ''}
<section class='card info'><div><strong>Pluginbasierter Anlernmodus</strong><br><span class='subtitle'>RFID/Tags verwenden eine feste UID. Handy und Smartwatch verwenden keine wechselnde NFC-UID, sondern ein separates Geräte-Pairing.</span></div><button type='button' class='secondary' onclick='testTerminal()'>Terminal prüfen</button></section>
<section class='card'><h2>Vorhandene RFID-/NFC-Medien ({len(media)})</h2><table><thead><tr><th>Bezeichnung</th><th>Typ</th><th>UID</th><th>Status</th><th>Letzte Nutzung</th><th>Aktion</th></tr></thead><tbody>{rows}</tbody></table></section>
<section class='card'><h2>Neues Anmeldemedium</h2>
<form method='post' id='media-form'>
<div class='grid'>
<div><label>Bezeichnung</label><input name='name' placeholder='z. B. Mitarbeiterkarte' required></div>
<div><label>Typ</label><select name='media_type' id='media-type' onchange='mediaTypeChanged()'><option value='rfid'>RFID-Karte</option><option value='nfc_ring'>NFC-Ring / NFC-Tag</option><option value='nfc_phone'>Handy</option><option value='nfc_watch'>Smartwatch</option><option value='other'>Sonstiges RFID/NFC</option></select></div>
<div><label>Raspberry-Terminal</label><select id='client-id'>{client_options}</select></div>
</div>
<div class='scanbox'><div style='flex:1'><label id='identifier-label'>UID</label><input id='uid' name='uid' readonly required placeholder='Noch nicht erfasst'></div><button type='button' id='scan-button' onclick='startScan()'>Scan am Raspberry starten</button></div>
<div id='scan-status' class='scan-status'>Terminal auswählen und den Scan starten.</div>
<div class='actions'><button type='submit' id='save-button'>Medium speichern</button></div>
</form></section>
</main>
<script>
let pollTimer = null; let scanToken = null; let activePlugin = 'rfid';
const employeeId = {employee.id};
function setStatus(text, kind=''){{const el=document.getElementById('scan-status');el.textContent=text;el.className='scan-status '+kind}}
function pluginForType(type){{return type==='nfc_phone'?'mobile_app':(type==='nfc_watch'?'smartwatch':'rfid')}}
function mediaTypeChanged(){{
 const type=document.getElementById('media-type').value; activePlugin=pluginForType(type);
 const devicePairing=activePlugin!=='rfid';
 document.getElementById('identifier-label').textContent=devicePairing?'Geräte-Pairing':'UID';
 document.getElementById('uid').placeholder=devicePairing?'Keine NFC-UID verwenden':'Noch nicht erfasst';
 document.getElementById('uid').required=!devicePairing;
 document.getElementById('save-button').style.display=devicePairing?'none':'';
 document.getElementById('scan-button').textContent=devicePairing?'Pairing am Terminal starten':'Scan am Raspberry starten';
 if(devicePairing) setStatus('Handy/Smartwatch werden über ihr eigenes Plugin gekoppelt. Zufällige NFC-Nummern werden nicht gespeichert.','info');
 else setStatus('Terminal auswählen und den RFID-/NFC-Scan starten.');
}}
async function startScan(){{
 const clientId=document.getElementById('client-id').value; const mediaType=document.getElementById('media-type').value;
 if(!clientId){{setStatus('Kein Raspberry-Terminal ausgewählt.','error');return}}
 document.getElementById('scan-button').disabled=true; document.getElementById('uid').value='';
 setStatus('Anlernauftrag wird an das passende Plugin gesendet …');
 try{{
  const res=await fetch(`/admin/employees/${{employeeId}}/rfid-media/scan/start`,{{method:'POST',headers:{{'Content-Type':'application/x-www-form-urlencoded'}},body:new URLSearchParams({{client_id:clientId,media_type:mediaType}})}});
  const data=await res.json(); if(!res.ok) throw new Error(data.message||'Start fehlgeschlagen');
  scanToken=data.token; activePlugin=data.plugin||pluginForType(mediaType);
  setStatus(data.message||'Anlernmodus gestartet.','ready');
  pollTimer=setInterval(()=>pollScan(clientId),1000);
 }}catch(err){{setStatus(err.message,'error');document.getElementById('scan-button').disabled=false}}
}}
async function pollScan(clientId){{
 try{{const res=await fetch(`/admin/employees/${{employeeId}}/rfid-media/scan/status?client_id=${{clientId}}&token=${{encodeURIComponent(scanToken)}}`);const data=await res.json();
 if(data.status==='complete'){{clearInterval(pollTimer);document.getElementById('uid').value=data.uid||'';setStatus(`UID ${{data.uid}} wurde erfasst. Jetzt Medium speichern.`,'ready');document.getElementById('scan-button').disabled=false}}
 else if(data.status==='pairing_required'){{clearInterval(pollTimer);setStatus(data.message||'Geräte-Pairing erforderlich. Die NFC-UID wird nicht gespeichert.','info');document.getElementById('scan-button').disabled=false}}
 else if(data.status==='error'||data.status==='timeout'){{clearInterval(pollTimer);setStatus(data.message||'Anlernen fehlgeschlagen.','error');document.getElementById('scan-button').disabled=false}}
 }}catch(err){{clearInterval(pollTimer);setStatus('Verbindung zum Server unterbrochen.','error');document.getElementById('scan-button').disabled=false}}
}}
async function testTerminal(){{const id=document.getElementById('client-id').value;if(!id){{setStatus('Kein Terminal vorhanden.','error');return}};const r=await fetch(`/admin/employees/${{employeeId}}/rfid-media/terminal/${{id}}`);const d=await r.json();setStatus(d.message,d.online?'ready':'error')}}
mediaTypeChanged();
</script></body></html>"""


@router.get('/admin/employees/{employee_id}/rfid-media', response_class=HTMLResponse)
def list_media(employee_id: int, request: Request, message: str = '', db: Session = Depends(get_db)):
    user, redirect = require_admin_response(request, db)
    if redirect:
        return redirect
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        return HTMLResponse('<h1>Mitarbeiter nicht gefunden</h1>', status_code=404)
    media = db.query(EmployeeRfidMedia).filter(EmployeeRfidMedia.employee_id == employee_id).order_by(EmployeeRfidMedia.id).all()
    clients = db.query(RaspberryClient).order_by(RaspberryClient.hostname).all()
    return HTMLResponse(_page(employee, media, clients, message))


@router.post('/admin/employees/{employee_id}/rfid-media')
def create_medium(employee_id: int, request: Request, uid: str = Form(''), name: str = Form('RFID/NFC-Medium'), media_type: str = Form('rfid'), db: Session = Depends(get_db)):
    user, redirect = require_admin_response(request, db)
    if redirect:
        return redirect
    plugin_key = MEDIA_PLUGIN.get(media_type, 'rfid')
    if plugin_key != 'rfid':
        message = 'Handy und Smartwatch dürfen nicht als RFID-UID gespeichert werden. Bitte das Geräte-Pairing des passenden Plugins verwenden.'
        return RedirectResponse(f'/admin/employees/{employee_id}/rfid-media?message={quote(message)}', status_code=303)
    try:
        medium = add_rfid_medium(db, employee_id, uid, name, media_type)
        db.commit()
        log_action(db, user.employee_number, 'rfid_medium_added', 'employees', str(employee_id), f'{medium.name}: {medium.uid}')
        message = 'Medium wurde gespeichert.'
    except ValueError as exc:
        db.rollback()
        message = str(exc)
    return RedirectResponse(f'/admin/employees/{employee_id}/rfid-media?message={quote(message)}', status_code=303)


@router.post('/admin/employees/{employee_id}/rfid-media/scan/start')
def start_remote_scan(employee_id: int, request: Request, client_id: int = Form(...), media_type: str = Form('rfid'), db: Session = Depends(get_db)):
    user, redirect = require_admin_response(request, db)
    if redirect:
        return JSONResponse({'message': 'Anmeldung erforderlich'}, status_code=401)
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        return JSONResponse({'message': 'Mitarbeiter nicht gefunden'}, status_code=404)
    client = db.query(RaspberryClient).filter(RaspberryClient.id == client_id).first()
    if not client:
        return JSONResponse({'message': 'Raspberry-Terminal nicht gefunden'}, status_code=404)
    if not _online(client):
        return JSONResponse({'message': 'Raspberry-Terminal ist nicht online'}, status_code=409)

    plugin_key = MEDIA_PLUGIN.get(media_type)
    if not plugin_key:
        return JSONResponse({'message': 'Für diesen Medientyp ist kein Anmelde-Plugin definiert'}, status_code=400)
    plugin = installed_plugin(plugin_key)
    if not plugin:
        return JSONResponse({'message': f'Anmelde-Plugin {plugin_key} ist nicht installiert'}, status_code=409)
    try:
        enrollment = plugin.start_enrollment(db, employee_id, client.id)
    except NotImplementedError:
        return JSONResponse({'message': f'Plugin {plugin_key} unterstützt kein Anlernen'}, status_code=409)

    token = secrets.token_urlsafe(12)
    command = f'auth_enroll:{plugin_key}:{employee_id}:{token}'
    client.pending_command = command
    client.command_requested_at = datetime.now()
    client.command_result = json.dumps({'status': 'waiting', 'token': token, 'provider': plugin_key})
    client.updated_at = datetime.now()
    db.commit()
    log_action(db, user.employee_number, 'auth_enrollment_started', 'raspberry_clients', str(client.id), f'employee={employee_id}; plugin={plugin_key}; type={media_type}')

    message = enrollment.get('message') or 'Anlernmodus gestartet.'
    if plugin_key == 'rfid':
        message = 'RFID-Plugin gestartet: Medium jetzt an den Leser halten. Am Terminal erscheint der Anlern-Bildschirm.'
    else:
        message = f'{message} Am Terminal wird der Plugin-Hinweis angezeigt.'
    return {'status': 'waiting', 'token': token, 'client': client.hostname, 'plugin': plugin_key, 'message': message}


@router.get('/admin/employees/{employee_id}/rfid-media/scan/status')
def remote_scan_status(employee_id: int, client_id: int, token: str, request: Request, db: Session = Depends(get_db)):
    user, redirect = require_admin_response(request, db)
    if redirect:
        return JSONResponse({'status': 'error', 'message': 'Anmeldung erforderlich'}, status_code=401)
    client = db.query(RaspberryClient).filter(RaspberryClient.id == client_id).first()
    if not client:
        return JSONResponse({'status': 'error', 'message': 'Terminal nicht gefunden'}, status_code=404)
    if client.command_requested_at and client.command_requested_at < datetime.now() - timedelta(seconds=45):
        if client.pending_command and token in client.pending_command:
            client.pending_command = None
            client.command_result = json.dumps({'status': 'timeout', 'token': token})
            db.commit()
        return {'status': 'timeout', 'message': 'Zeitüberschreitung: Bitte Anlernen erneut starten.'}
    try:
        result = json.loads(client.command_result or '{}')
    except Exception:
        result = {}
    if result.get('token') != token:
        return {'status': 'waiting'}
    if result.get('status') == 'complete' and result.get('uid'):
        return {'status': 'complete', 'uid': str(result['uid']), 'reader': result.get('reader', ''), 'plugin': result.get('provider', 'rfid')}
    if result.get('status') == 'pairing_required':
        return {'status': 'pairing_required', 'plugin': result.get('provider'), 'message': result.get('message', 'Geräte-Pairing erforderlich')}
    if result.get('status') == 'error':
        return {'status': 'error', 'message': result.get('message', 'Anlernen fehlgeschlagen')}
    return {'status': 'waiting'}


@router.get('/admin/employees/{employee_id}/rfid-media/terminal/{client_id}')
def terminal_status(employee_id: int, client_id: int, request: Request, db: Session = Depends(get_db)):
    user, redirect = require_admin_response(request, db)
    if redirect:
        return JSONResponse({'online': False, 'message': 'Anmeldung erforderlich'}, status_code=401)
    client = db.query(RaspberryClient).filter(RaspberryClient.id == client_id).first()
    if not client:
        return JSONResponse({'online': False, 'message': 'Terminal nicht gefunden'}, status_code=404)
    online = _online(client)
    return {'online': online, 'message': f"{client.hostname} ist {'online und bereit' if online else 'offline'} (letzter Kontakt: {client.last_seen.strftime('%d.%m.%Y %H:%M:%S') if client.last_seen else 'nie'})"}


@router.post('/admin/employees/{employee_id}/rfid-media/{medium_id}/delete')
def delete_medium(employee_id: int, medium_id: int, request: Request, db: Session = Depends(get_db)):
    user, redirect = require_admin_response(request, db)
    if redirect:
        return redirect
    medium = db.query(EmployeeRfidMedia).filter(EmployeeRfidMedia.id == medium_id, EmployeeRfidMedia.employee_id == employee_id).first()
    if medium:
        details = f'{medium.name}: {medium.uid}'
        db.delete(medium)
        db.commit()
        log_action(db, user.employee_number, 'rfid_medium_deleted', 'employees', str(employee_id), details)
    return RedirectResponse(f'/admin/employees/{employee_id}/rfid-media', status_code=303)
