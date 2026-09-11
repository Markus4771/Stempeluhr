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
    "nfc_tag": "nfc",
    "nfc_ring": "nfc",
    "other": "rfid",
    "nfc_phone": "mobile_app",
    "nfc_watch": "smartwatch",
}
UID_PLUGINS = {"rfid", "nfc"}


def _online(client: RaspberryClient) -> bool:
    return bool(client.last_seen and client.last_seen > datetime.now() - timedelta(seconds=90))


def _type_label(value: str) -> str:
    return {"rfid":"RFID-Karte","nfc_tag":"NFC-Tag","nfc_ring":"NFC-Ring","nfc_phone":"Handy","nfc_watch":"Smartwatch","other":"Sonstiges RFID"}.get(value, value or "Anmeldemedium")


def _page(employee: Employee, media: list[EmployeeRfidMedia], clients: list[RaspberryClient], message: str = "") -> str:
    rows = "".join(
        f"<tr><td>{escape(m.name)}</td><td>{escape(_type_label(m.media_type))}</td><td><code>{escape(m.uid_raw or m.uid)}</code></td>"
        f"<td>{'Aktiv' if m.active else 'Inaktiv'}</td><td>{m.last_used_at.strftime('%d.%m.%Y %H:%M:%S') if m.last_used_at else 'Noch nie'}</td>"
        f"<td><form method='post' action='/admin/employees/{employee.id}/rfid-media/{m.id}/delete'><button>Löschen</button></form></td></tr>" for m in media
    ) or "<tr><td colspan='6'>Noch keine RFID-/NFC-Medien vorhanden.</td></tr>"
    options = "".join(f"<option value='{c.id}'>{escape(c.hostname)} ({'online' if _online(c) else 'offline'})</option>" for c in sorted(clients, key=lambda x:(not _online(x), x.hostname.lower()))) or "<option value=''>Kein Terminal</option>"
    msg = f"<p class='msg'>{escape(message)}</p>" if message else ""
    return f"""<!doctype html><html lang='de'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Anmeldemedien</title>
<style>body{{font-family:system-ui;background:#f3f6fa;color:#172033;margin:0}}main{{max-width:1200px;margin:auto;padding:28px}}section{{background:white;border:1px solid #dbe3ee;border-radius:12px;padding:20px;margin:18px 0}}table{{width:100%;border-collapse:collapse}}th,td{{padding:11px;border-bottom:1px solid #ddd;text-align:left}}label{{display:block;font-weight:650;margin:8px 0}}input,select,button{{padding:10px;font:inherit}}input,select{{width:100%;box-sizing:border-box}}button{{cursor:pointer}}.grid{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px}}.scan{{display:flex;gap:12px;align-items:end;margin-top:14px}}.scan>div{{flex:1}}.msg{{background:#ecfdf3;padding:10px}}#status{{margin-top:12px;padding:10px;background:#eef2f6}}@media(max-width:800px){{.grid{{grid-template-columns:1fr}}.scan{{display:block}}}}</style></head><body><main>
<a href='/admin/employees/{employee.id}/edit'>← Zurück zum Mitarbeiter</a><h1>Anmeldemedien: {escape(employee.first_name)} {escape(employee.last_name)}</h1>{msg}
<section><strong>Getrennte Anmelde-Plugins</strong><p>RFID-Karte → RFID-Plugin · NFC-Tag/Ring → NFC-Plugin · Handy → mobile_app · Smartwatch → smartwatch.</p></section>
<section><h2>Vorhandene Medien</h2><table><thead><tr><th>Name</th><th>Typ</th><th>UID</th><th>Status</th><th>Letzte Nutzung</th><th></th></tr></thead><tbody>{rows}</tbody></table></section>
<section><h2>Neues Anmeldemedium</h2><form method='post'><div class='grid'>
<div><label>Bezeichnung</label><input name='name' required placeholder='z. B. Mitarbeiterkarte'></div>
<div><label>Typ</label><select name='media_type' id='media-type' onchange='mediaTypeChanged()'><option value='rfid'>RFID-Karte</option><option value='nfc_tag'>NFC-Tag</option><option value='nfc_ring'>NFC-Ring</option><option value='nfc_phone'>Handy</option><option value='nfc_watch'>Smartwatch</option><option value='other'>Sonstiges RFID</option></select></div>
<div><label>Terminal</label><select id='client-id'>{options}</select></div></div>
<div class='scan'><div><label id='identifier-label'>UID</label><input id='uid' name='uid' readonly required></div><button type='button' id='scan-button' onclick='startScan()'>Scan starten</button></div><div id='status'>Terminal auswählen und Scan starten.</div><p><button id='save-button' type='submit'>Medium speichern</button></p></form></section></main>
<script>
let pollTimer=null,scanToken=null;const employeeId={employee.id};
function pluginForType(t){{if(t==='nfc_tag'||t==='nfc_ring')return'nfc';if(t==='nfc_phone')return'mobile_app';if(t==='nfc_watch')return'smartwatch';return'rfid'}}
function setStatus(t){{document.getElementById('status').textContent=t}}
function mediaTypeChanged(){{const p=pluginForType(document.getElementById('media-type').value),device=!['rfid','nfc'].includes(p),u=document.getElementById('uid');document.getElementById('identifier-label').textContent=device?'Geräte-Kopplung':'UID';u.required=!device;u.placeholder=device?'Keine Hardware-UID speichern':'Noch nicht erfasst';document.getElementById('save-button').style.display=device?'none':'';document.getElementById('scan-button').textContent=device?'Kopplung starten':(p==='nfc'?'NFC-Scan starten':'RFID-Scan starten');setStatus(device?'Handy/Smartwatch werden über ihr eigenes Geräte-Plugin gekoppelt.':(p==='nfc'?'NFC-Medium an den Leser halten.':'RFID-Medium an den Leser halten.'))}}
async function startScan(){{const clientId=document.getElementById('client-id').value,mediaType=document.getElementById('media-type').value,b=document.getElementById('scan-button');if(!clientId){{setStatus('Kein Terminal ausgewählt.');return}}b.disabled=true;document.getElementById('uid').value='';try{{const r=await fetch(`/admin/employees/${{employeeId}}/rfid-media/scan/start`,{{method:'POST',headers:{{'Content-Type':'application/x-www-form-urlencoded'}},body:new URLSearchParams({{client_id:clientId,media_type:mediaType}})}}),d=await r.json();if(!r.ok)throw new Error(d.message||'Start fehlgeschlagen');scanToken=d.token;setStatus(d.message||'Anlernmodus gestartet.');pollTimer=setInterval(()=>pollScan(clientId),1000)}}catch(e){{setStatus(e.message);b.disabled=false}}}}
async function pollScan(clientId){{try{{const r=await fetch(`/admin/employees/${{employeeId}}/rfid-media/scan/status?client_id=${{clientId}}&token=${{encodeURIComponent(scanToken)}}`),d=await r.json();if(d.status==='complete'){{clearInterval(pollTimer);document.getElementById('uid').value=d.uid||'';setStatus(`${{(d.plugin||'').toUpperCase()}} UID ${{d.uid}} erfasst. Medium jetzt speichern.`);document.getElementById('scan-button').disabled=false}}else if(d.status==='pairing_required'||d.status==='error'||d.status==='timeout'){{clearInterval(pollTimer);setStatus(d.message||d.status);document.getElementById('scan-button').disabled=false}}}}catch(e){{clearInterval(pollTimer);setStatus('Verbindung zum Server unterbrochen.');document.getElementById('scan-button').disabled=false}}}}
mediaTypeChanged();
</script></body></html>"""


@router.get('/admin/employees/{employee_id}/rfid-media', response_class=HTMLResponse)
def list_media(employee_id:int, request:Request, message:str='', db:Session=Depends(get_db)):
    user, redirect=require_admin_response(request,db)
    if redirect:return redirect
    employee=db.query(Employee).filter(Employee.id==employee_id).first()
    if not employee:return HTMLResponse('<h1>Mitarbeiter nicht gefunden</h1>',status_code=404)
    media=db.query(EmployeeRfidMedia).filter(EmployeeRfidMedia.employee_id==employee_id).order_by(EmployeeRfidMedia.id).all();clients=db.query(RaspberryClient).order_by(RaspberryClient.hostname).all()
    return HTMLResponse(_page(employee,media,clients,message))


@router.post('/admin/employees/{employee_id}/rfid-media')
def create_medium(employee_id:int, request:Request, uid:str=Form(''), name:str=Form('RFID/NFC-Medium'), media_type:str=Form('rfid'), db:Session=Depends(get_db)):
    user,redirect=require_admin_response(request,db)
    if redirect:return redirect
    plugin_key=MEDIA_PLUGIN.get(media_type,'rfid')
    if plugin_key not in UID_PLUGINS:
        message='Handy und Smartwatch werden über ihr eigenes Geräte-Plugin gekoppelt und nicht als UID-Medium gespeichert.'
        return RedirectResponse(f'/admin/employees/{employee_id}/rfid-media?message={quote(message)}',status_code=303)
    try:
        medium=add_rfid_medium(db,employee_id,uid,name,media_type);db.commit();log_action(db,user.employee_number,f'{plugin_key}_medium_added','employees',str(employee_id),f'{medium.name}: {medium.uid}');message=f'{plugin_key.upper()}-Medium wurde gespeichert.'
    except ValueError as exc:
        db.rollback();message=str(exc)
    return RedirectResponse(f'/admin/employees/{employee_id}/rfid-media?message={quote(message)}',status_code=303)


@router.post('/admin/employees/{employee_id}/rfid-media/scan/start')
def start_remote_scan(employee_id:int, request:Request, client_id:int=Form(...), media_type:str=Form('rfid'), db:Session=Depends(get_db)):
    user,redirect=require_admin_response(request,db)
    if redirect:return JSONResponse({'message':'Anmeldung erforderlich'},status_code=401)
    employee=db.query(Employee).filter(Employee.id==employee_id).first();client=db.query(RaspberryClient).filter(RaspberryClient.id==client_id).first()
    if not employee:return JSONResponse({'message':'Mitarbeiter nicht gefunden'},status_code=404)
    if not client:return JSONResponse({'message':'Raspberry-Terminal nicht gefunden'},status_code=404)
    if not _online(client):return JSONResponse({'message':'Raspberry-Terminal ist nicht online'},status_code=409)
    plugin_key=MEDIA_PLUGIN.get(media_type)
    if not plugin_key:return JSONResponse({'message':'Für diesen Medientyp ist kein Anmelde-Plugin definiert'},status_code=400)
    plugin=installed_plugin(plugin_key)
    if not plugin:return JSONResponse({'message':f'Anmelde-Plugin {plugin_key} ist nicht installiert'},status_code=409)
    try:enrollment=plugin.start_enrollment(db,employee_id,client.id)
    except NotImplementedError:return JSONResponse({'message':f'Plugin {plugin_key} unterstützt kein Anlernen'},status_code=409)
    token=secrets.token_urlsafe(12);command=f'auth_enroll:{plugin_key}:{employee_id}:{token}';client.pending_command=command;client.command_requested_at=datetime.now();client.command_result=json.dumps({'status':'waiting','token':token,'provider':plugin_key});client.updated_at=datetime.now();db.commit()
    log_action(db,user.employee_number,'auth_enrollment_started','raspberry_clients',str(client.id),f'employee={employee_id}; plugin={plugin_key}; type={media_type}')
    if plugin_key in UID_PLUGINS:message=f'{plugin_key.upper()}-Plugin gestartet: Medium jetzt an den Leser halten.'
    else:message=(enrollment.get('message') or 'Geräte-Kopplung gestartet.')+' Am Terminal wird der Plugin-Hinweis angezeigt.'
    return {'status':'waiting','token':token,'client':client.hostname,'plugin':plugin_key,'message':message}


@router.get('/admin/employees/{employee_id}/rfid-media/scan/status')
def remote_scan_status(employee_id:int, client_id:int, token:str, request:Request, db:Session=Depends(get_db)):
    user,redirect=require_admin_response(request,db)
    if redirect:return JSONResponse({'status':'error','message':'Anmeldung erforderlich'},status_code=401)
    client=db.query(RaspberryClient).filter(RaspberryClient.id==client_id).first()
    if not client:return JSONResponse({'status':'error','message':'Terminal nicht gefunden'},status_code=404)
    try:result=json.loads(client.command_result or '{}')
    except Exception:result={}
    provider=result.get('provider','rfid');timeout=300 if provider in {'mobile_app','smartwatch'} else 45
    if client.command_requested_at and client.command_requested_at<datetime.now()-timedelta(seconds=timeout):
        if client.pending_command and token in client.pending_command:client.pending_command=None;client.command_result=json.dumps({'status':'timeout','token':token,'provider':provider});db.commit()
        return {'status':'timeout','message':'Zeitüberschreitung: Bitte Anlernen erneut starten.'}
    if result.get('token')!=token:return {'status':'waiting'}
    if result.get('status')=='complete' and result.get('uid'):return {'status':'complete','uid':str(result['uid']),'reader':result.get('reader',''),'plugin':provider}
    if result.get('status')=='pairing_required':return {'status':'pairing_required','plugin':provider,'message':result.get('message','Geräte-Pairing erforderlich')}
    if result.get('status')=='error':return {'status':'error','message':result.get('message','Anlernen fehlgeschlagen')}
    return {'status':'waiting'}


@router.get('/admin/employees/{employee_id}/rfid-media/terminal/{client_id}')
def terminal_status(employee_id:int, client_id:int, request:Request, db:Session=Depends(get_db)):
    user,redirect=require_admin_response(request,db)
    if redirect:return JSONResponse({'online':False,'message':'Anmeldung erforderlich'},status_code=401)
    client=db.query(RaspberryClient).filter(RaspberryClient.id==client_id).first()
    if not client:return JSONResponse({'online':False,'message':'Terminal nicht gefunden'},status_code=404)
    online=_online(client);return {'online':online,'message':f"{client.hostname} ist {'online und bereit' if online else 'offline'}"}


@router.post('/admin/employees/{employee_id}/rfid-media/{medium_id}/delete')
def delete_medium(employee_id:int, medium_id:int, request:Request, db:Session=Depends(get_db)):
    user,redirect=require_admin_response(request,db)
    if redirect:return redirect
    medium=db.query(EmployeeRfidMedia).filter(EmployeeRfidMedia.id==medium_id,EmployeeRfidMedia.employee_id==employee_id).first()
    if medium:
        details=f'{medium.name}: {medium.uid}';db.delete(medium);db.commit();log_action(db,user.employee_number,'auth_medium_deleted','employees',str(employee_id),details)
    return RedirectResponse(f'/admin/employees/{employee_id}/rfid-media',status_code=303)
