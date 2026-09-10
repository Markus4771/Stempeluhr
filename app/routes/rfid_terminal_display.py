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

router = APIRouter()


PLUGIN_UI = {
    "rfid": {
        "title": "RFID / NFC ANLERNEN",
        "instruction": "Bitte RFID-Karte, NFC-Tag oder NFC-Ring an den Leser halten.",
        "symbol": ")))",
        "success": "Medium erkannt",
        "identifier_label": "UID",
    },
    "mobile_app": {
        "title": "HANDY KOPPELN",
        "instruction": "Handys werden über ein sicheres Geräte-Pairing gekoppelt. Die wechselnde NFC-UID wird nicht gespeichert.",
        "symbol": "PHONE",
        "success": "Handy gekoppelt",
        "identifier_label": "Gerät",
    },
    "smartwatch": {
        "title": "SMARTWATCH KOPPELN",
        "instruction": "Smartwatches werden über ein sicheres Geräte-Pairing gekoppelt. Die NFC-UID wird nicht als Identität verwendet.",
        "symbol": "WATCH",
        "success": "Smartwatch gekoppelt",
        "identifier_label": "Gerät",
    },
}


def _return_url(terminal_code: str) -> str:
    if terminal_code:
        from urllib.parse import quote
        return f"/raspberry?terminal_code={quote(terminal_code)}"
    return "/raspberry"


def _page(
    plugin_key: str,
    employee_name: str,
    seconds: int,
    identifier: str = "",
    message: str = "",
    terminal_code: str = "",
    token: str = "",
) -> str:
    config = PLUGIN_UI.get(plugin_key, PLUGIN_UI["rfid"])
    success = bool(identifier)
    accent = "#22c55e" if success else "#2384ff"
    heading = "ERFOLGREICH" if success else config["title"]
    if success:
        body = (
            f"<div class='check'>✓</div><h2>{escape(config['success'])}</h2>"
            f"<p class='uid'>{escape(config['identifier_label'])}: {escape(identifier)}</p>"
        )
    else:
        body = (
            f"<div class='waves'>{escape(config['symbol'])}</div>"
            f"<h2 id='status-message'>{escape(message or config['instruction'])}</h2>"
        )
    footer = "Anlernmodus beendet" if success else "Verbleibende Zeit: <span id='countdown'></span>"
    return_url = _return_url(terminal_code)

    if success:
        state_script = f"<script>setTimeout(()=>location.replace({json.dumps(return_url)}),3000);</script>"
    else:
        state_script = f"""
<script>
let remaining={seconds};
const countdown=document.getElementById('countdown');
const statusMessage=document.getElementById('status-message');
const terminalCode={json.dumps(terminal_code)};
const enrollmentToken={json.dumps(token)};
const returnUrl={json.dumps(return_url)};
let finished=false;
function tick(){{
  countdown.textContent='00:'+String(Math.max(0,remaining)).padStart(2,'0');
  remaining=Math.max(0,remaining-1);
}}
tick();setInterval(tick,1000);
async function pollEnrollment(){{
  if(finished || !enrollmentToken) return;
  try{{
    const q=new URLSearchParams({{terminal_code:terminalCode,token:enrollmentToken}});
    const res=await fetch('/terminal/enrollment-state?'+q.toString(),{{cache:'no-store'}});
    if(!res.ok) return;
    const data=await res.json();
    if(data.status==='complete' && data.identifier){{
      finished=true;
      const p=new URLSearchParams(location.search);
      p.set('identifier',data.identifier);
      location.replace(location.pathname+'?'+p.toString());
      return;
    }}
    if(data.status==='pairing_required'||data.status==='error'||data.status==='timeout'){{
      finished=true;
      statusMessage.textContent=data.message||'Anlernmodus beendet.';
      countdown.textContent='--:--';
      setTimeout(()=>location.replace(returnUrl),4000);
    }}
  }}catch(e){{}}
}}
setInterval(pollEnrollment,750);pollEnrollment();
</script>"""

    return f"""<!doctype html><html lang='de'><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'><title>{escape(config['title'])}</title>
<style>
*{{box-sizing:border-box}}html,body{{width:100%;height:100%;margin:0;overflow:hidden}}
body{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;background:#06080d;color:white;display:flex;align-items:center;justify-content:center}}
.panel{{width:100vw;height:100vh;padding:7vh 8vw;display:flex;flex-direction:column;background:radial-gradient(circle at 20% 20%,#17233b,#06080d 58%)}}
.top{{display:flex;justify-content:space-between;align-items:center}}.heading{{font-size:4.2vw;color:{accent};font-weight:800;letter-spacing:.04em}}.clock{{font-size:3vw}}
.main{{flex:1;display:grid;grid-template-columns:30% 1fr;align-items:center;gap:5vw}}h2{{font-size:4.5vw;line-height:1.16;margin:.4em 0}}p{{font-size:3vw;margin:.35em 0;color:#d8e0ec}}
.name{{color:{accent};font-weight:750}}.waves{{font-size:7vw;color:{accent};font-weight:900}}.check{{font-size:12vw;color:{accent};font-weight:900}}
.uid{{font-family:ui-monospace,monospace;font-size:3.2vw}}.footer{{background:{accent};padding:2.4vh 3vw;font-size:3vw;font-weight:750;border-radius:1.2vw;display:flex;justify-content:space-between}}
</style></head><body><main class='panel'><div class='top'><div class='heading'>{escape(heading)}</div><div class='clock' id='clock'></div></div>
<div class='main'><div>{body}</div><div><p>Mitarbeiter</p><h2 class='name'>{escape(employee_name)}</h2></div></div>
<div class='footer'><span>{footer}</span><span>{'✓' if success else ''}</span></div></main>
<script>function clock(){{document.getElementById('clock').textContent=new Date().toLocaleTimeString('de-DE',{{hour:'2-digit',minute:'2-digit'}})}}clock();setInterval(clock,1000);</script>{state_script}</body></html>"""


def _employee_name(db: Session, employee_id: int) -> str:
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    return f"{employee.first_name} {employee.last_name}" if employee else f"Mitarbeiter {employee_id}"


def _client_for_request(db: Session, request: Request, terminal_code: str) -> RaspberryClient | None:
    code = (terminal_code or "").strip()
    if code:
        return db.query(RaspberryClient).filter(RaspberryClient.hostname == code).first()

    remote_ip = request.client.host if request.client else ""
    if remote_ip:
        matches = db.query(RaspberryClient).filter(RaspberryClient.ip_address == remote_ip).all()
        if len(matches) == 1:
            return matches[0]

    # All-in-One-Terminal: Der Kiosk ruft den lokalen Server über 127.0.0.1 auf.
    # In diesem Fall entspricht der registrierte Raspberry-Hostname dem Hostnamen
    # des Servers. So funktioniert die Bildschirmumschaltung auch ohne
    # terminal_code-Parameter in einer bestehenden Kiosk-Autostart-Konfiguration.
    if remote_ip in {"127.0.0.1", "::1", "localhost"}:
        local_hostname = socket.gethostname().strip()
        if local_hostname:
            client = db.query(RaspberryClient).filter(RaspberryClient.hostname == local_hostname).first()
            if client:
                return client

    return None


def _parse_pending_command(command: str) -> dict | None:
    command = str(command or "")
    if command.startswith("auth_enroll:"):
        parts = command.split(":", 3)
        if len(parts) == 4:
            try:
                employee_id = int(parts[2])
            except ValueError:
                return None
            return {"plugin": parts[1], "employee_id": employee_id, "token": parts[3]}
    if command.startswith("rfid_scan:"):
        parts = command.split(":", 2)
        if len(parts) == 3:
            try:
                employee_id = int(parts[1])
            except ValueError:
                return None
            return {"plugin": "rfid", "employee_id": employee_id, "token": parts[2]}
    return None


@router.get('/terminal/enrollment-state')
def enrollment_state(
    request: Request,
    terminal_code: str = Query(''),
    token: str = Query(''),
    db: Session = Depends(get_db),
):
    client = _client_for_request(db, request, terminal_code)
    if not client:
        return JSONResponse({"status": "idle"})

    pending = _parse_pending_command(client.pending_command or "")
    if pending and (not token or pending["token"] == token):
        seconds = 45
        if client.command_requested_at:
            elapsed = int(max(0, (datetime.now() - client.command_requested_at).total_seconds()))
            seconds = max(1, 45 - elapsed)
        return {
            "status": "active",
            "plugin": pending["plugin"],
            "employee_id": pending["employee_id"],
            "token": pending["token"],
            "seconds": seconds,
            "terminal_code": client.hostname,
        }

    if token:
        try:
            result = json.loads(client.command_result or "{}")
        except Exception:
            result = {}
        if result.get("token") == token:
            status = str(result.get("status") or "waiting")
            identifier = result.get("uid") or result.get("identifier") or ""
            return {
                "status": status,
                "plugin": result.get("provider") or "rfid",
                "identifier": str(identifier) if identifier else "",
                "message": result.get("message") or "",
                "terminal_code": client.hostname,
            }
    return {"status": "idle", "terminal_code": client.hostname}


@router.get('/terminal/auth-enrollment/{plugin_key}/{employee_id}', response_class=HTMLResponse)
def auth_enrollment_display(
    plugin_key: str,
    employee_id: int,
    seconds: int = Query(35, ge=5, le=300),
    identifier: str = Query(''),
    message: str = Query(''),
    terminal_code: str = Query(''),
    token: str = Query(''),
    db: Session = Depends(get_db),
):
    return HTMLResponse(_page(
        plugin_key,
        _employee_name(db, employee_id),
        seconds,
        identifier,
        message,
        terminal_code,
        token,
    ))


@router.get('/terminal/rfid-enrollment/{employee_id}', response_class=HTMLResponse)
def enrollment_display(
    employee_id: int,
    seconds: int = Query(35, ge=5, le=300),
    uid: str = Query(''),
    terminal_code: str = Query(''),
    token: str = Query(''),
    db: Session = Depends(get_db),
):
    return HTMLResponse(_page('rfid', _employee_name(db, employee_id), seconds, uid, '', terminal_code, token))
