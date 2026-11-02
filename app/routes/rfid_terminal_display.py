from __future__ import annotations

import json
import socket
from datetime import datetime
from html import escape

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Employee, RaspberryClient
from app.routes.mobile_pairing import get_pairing_session

router = APIRouter()

PLUGIN_UI = {
    "rfid": {"title":"RFID ANLERNEN","instruction":"Bitte RFID-Karte oder RFID-Schlüsselanhänger an den Leser halten.","symbol":"RFID","success":"RFID-Medium erkannt","identifier_label":"UID"},
    "nfc": {"title":"NFC ANLERNEN","instruction":"Bitte NFC-Tag oder NFC-Ring an den Leser halten.","symbol":"NFC","success":"NFC-Medium erkannt","identifier_label":"UID"},
    "mobile_app": {"title":"HANDY KOPPELN","instruction":"Handy an den NFC-Leser halten. Die mobile App übernimmt die sichere Identifikation.","symbol":"PHONE","success":"Handy gekoppelt","identifier_label":"Gerät"},
    "smartwatch": {"title":"SMARTWATCH KOPPELN","instruction":"Smartwatch an den vorgesehenen Leser halten bzw. das konfigurierte Smartwatch-Verfahren starten.","symbol":"WATCH","success":"Smartwatch gekoppelt","identifier_label":"Gerät"},
}

PAGE_CSS = """*{box-sizing:border-box}html,body{width:100%;height:100%;margin:0;overflow:hidden}body{font-family:system-ui;background:#06080d;color:white;display:flex;align-items:center;justify-content:center}.panel{width:100vw;height:100vh;padding:5vh 6vw;display:flex;flex-direction:column;background:radial-gradient(circle at 20% 20%,#17233b,#06080d 58%)}.top{display:flex;justify-content:space-between}.heading{font-size:4vw;font-weight:800}.clock{font-size:3vw}.main{flex:1;display:flex;align-items:center;justify-content:center;gap:5vw}h2{font-size:3.8vw}p{font-size:2.2vw;color:#d8e0ec}.name{font-weight:750}.waves{font-size:7vw;font-weight:900}.check{font-size:12vw}.small{font-size:1.2vw;max-width:45vw;word-break:break-all}.footer{padding:2vh 3vw;font-size:2.5vw;font-weight:750;border-radius:1vw;display:flex;justify-content:space-between}"""


def _return_url(terminal_code: str) -> str:
    if terminal_code:
        from urllib.parse import quote
        return f"/raspberry?terminal_code={quote(terminal_code)}"
    return "/raspberry"


def _page(plugin_key: str, employee_name: str, seconds: int, identifier: str = "", message: str = "", terminal_code: str = "", token: str = "") -> str:
    config = PLUGIN_UI.get(plugin_key, PLUGIN_UI["rfid"])
    success = bool(identifier)
    accent = "#22c55e" if success else "#2384ff"
    heading = "ERFOLGREICH" if success else config["title"]
    if success:
        body = f"<div class='check'>✓</div><h2>{escape(config['success'])}</h2><p class='uid'>{escape(config['identifier_label'])}: {escape(identifier)}</p>"
    else:
        body = f"<div class='waves'>{escape(config['symbol'])}</div><h2 id='status-message'>{escape(message or config['instruction'])}</h2>"
    footer = "Anlernmodus beendet" if success else "Verbleibende Zeit: <span id='countdown'></span>"
    return_url = _return_url(terminal_code)
    if success:
        state_script = "<script>setTimeout(function(){location.replace(" + json.dumps(return_url) + ")},3000);</script>"
    else:
        state_script = """<script>
let remaining=SECONDS,finished=false;const countdown=document.getElementById('countdown');const statusMessage=document.getElementById('status-message');const terminalCode=TERMINAL_CODE;const enrollmentToken=TOKEN;const returnUrl=RETURN_URL;
function tick(){countdown.textContent=Math.floor(remaining/60)+':'+String(Math.max(0,remaining%60)).padStart(2,'0');remaining=Math.max(0,remaining-1)}tick();setInterval(tick,1000);
async function pollEnrollment(){if(finished||!enrollmentToken)return;try{const q=new URLSearchParams({terminal_code:terminalCode,token:enrollmentToken});const res=await fetch('/terminal/enrollment-state?'+q.toString(),{cache:'no-store'});if(!res.ok)return;const data=await res.json();if(data.status==='complete'){finished=true;const p=new URLSearchParams(location.search);p.set('identifier',data.identifier||'Gerät');location.replace(location.pathname+'?'+p.toString());return}if(data.status==='error'||data.status==='timeout'||data.status==='expired'){finished=true;if(statusMessage)statusMessage.textContent=data.message||'Anlernmodus beendet.';countdown.textContent='--:--';setTimeout(function(){location.replace(returnUrl)},4000)}}catch(e){}}
setInterval(pollEnrollment,750);pollEnrollment();</script>"""
        state_script = state_script.replace("SECONDS", str(seconds), 1).replace("TERMINAL_CODE", json.dumps(terminal_code), 1).replace("TOKEN", json.dumps(token), 1).replace("RETURN_URL", json.dumps(return_url), 1)
    success_mark = "✓" if success else ""
    clock_script = "<script>function clock(){document.getElementById('clock').textContent=new Date().toLocaleTimeString('de-DE',{hour:'2-digit',minute:'2-digit'})}clock();setInterval(clock,1000);</script>"
    dynamic_css = f".heading,.name,.waves,.check{{color:{accent}}}.footer{{background:{accent}}}"
    return (
        "<!doctype html><html lang='de'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{escape(config['title'])}</title><style>{PAGE_CSS}{dynamic_css}</style></head><body>"
        "<main class='panel'><div class='top'>"
        f"<div class='heading'>{escape(heading)}</div><div class='clock' id='clock'></div></div>"
        f"<div class='main'><div>{body}</div><div><p>Mitarbeiter</p><h2 class='name'>{escape(employee_name)}</h2></div></div>"
        f"<div class='footer'><span>{footer}</span><span>{success_mark}</span></div></main>{clock_script}{state_script}</body></html>"
    )


def _employee_name(db: Session, employee_id: int) -> str:
    employee=db.query(Employee).filter(Employee.id==employee_id).first();return f"{employee.first_name} {employee.last_name}" if employee else f"Mitarbeiter {employee_id}"


def _client_for_request(db: Session, request: Request, terminal_code: str):
    code=(terminal_code or '').strip()
    if code:return db.query(RaspberryClient).filter(RaspberryClient.hostname==code).first()
    remote_ip=request.client.host if request.client else ''
    if remote_ip:
        matches=db.query(RaspberryClient).filter(RaspberryClient.ip_address==remote_ip).all()
        if len(matches)==1:return matches[0]
    if remote_ip in {'127.0.0.1','::1','localhost'}:
        client=db.query(RaspberryClient).filter(RaspberryClient.hostname==socket.gethostname().strip()).first()
        if client:return client
    return None


def _parse_pending_command(command: str):
    command=str(command or '')
    if command.startswith('auth_enroll:'):
        parts=command.split(':',3)
        if len(parts)==4:
            try:return {'plugin':parts[1],'employee_id':int(parts[2]),'token':parts[3]}
            except ValueError:return None
    if command.startswith('rfid_scan:'):
        parts=command.split(':',2)
        if len(parts)==3:
            try:return {'plugin':'rfid','employee_id':int(parts[1]),'token':parts[2]}
            except ValueError:return None
    return None


@router.get('/terminal/enrollment-state')
def enrollment_state(request: Request, terminal_code: str=Query(''), token: str=Query(''), db: Session=Depends(get_db)):
    client=_client_for_request(db,request,terminal_code)
    if not client:return JSONResponse({'status':'idle'})
    pending=_parse_pending_command(client.pending_command or '')
    if token:
        session=get_pairing_session(db,token)
        if session:
            if session.completed:return {'status':'complete','plugin':session.provider,'identifier':'Gerät','terminal_code':client.hostname}
            if session.expires_at<datetime.now():return {'status':'expired','message':'Pairing-Zeit abgelaufen.','terminal_code':client.hostname}
    if pending and (not token or pending['token']==token):
        seconds=300 if pending['plugin'] in {'mobile_app','smartwatch'} else 45
        if client.command_requested_at:
            elapsed=int(max(0,(datetime.now()-client.command_requested_at).total_seconds()));seconds=max(1,seconds-elapsed)
        return {'status':'active','plugin':pending['plugin'],'employee_id':pending['employee_id'],'token':pending['token'],'seconds':seconds,'terminal_code':client.hostname}
    if token:
        try:result=json.loads(client.command_result or '{}')
        except Exception:result={}
        if result.get('token')==token:
            identifier=result.get('uid') or result.get('identifier') or ''
            return {'status':str(result.get('status') or 'waiting'),'plugin':result.get('provider') or 'rfid','identifier':str(identifier) if identifier else '','message':result.get('message') or '','terminal_code':client.hostname}
    return {'status':'idle','terminal_code':client.hostname}


@router.get('/terminal/auth-enrollment/{plugin_key}/{employee_id}',response_class=HTMLResponse)
def auth_enrollment_display(plugin_key:str,employee_id:int,request:Request,seconds:int=Query(35,ge=5,le=300),identifier:str=Query(''),message:str=Query(''),terminal_code:str=Query(''),token:str=Query(''),db:Session=Depends(get_db)):
    if plugin_key in {'mobile_app','smartwatch'}:
        seconds=300
    return HTMLResponse(_page(plugin_key,_employee_name(db,employee_id),seconds,identifier,message,terminal_code,token))


@router.get('/terminal/rfid-enrollment/{employee_id}',response_class=HTMLResponse)
def enrollment_display(employee_id:int,seconds:int=Query(35,ge=5,le=300),uid:str=Query(''),terminal_code:str=Query(''),token:str=Query(''),db:Session=Depends(get_db)):
    return HTMLResponse(_page('rfid',_employee_name(db,employee_id),seconds,uid,'',terminal_code,token))
