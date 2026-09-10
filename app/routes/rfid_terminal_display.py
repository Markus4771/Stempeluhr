from __future__ import annotations

from html import escape

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Employee

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


def _page(plugin_key: str, employee_name: str, seconds: int, identifier: str = "", message: str = "") -> str:
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
            f"<h2>{escape(message or config['instruction'])}</h2>"
        )
    footer = "Anlernmodus beendet" if success else "Verbleibende Zeit: <span id='countdown'></span>"
    script = "" if success else f"""
<script>
let remaining={seconds};
const el=document.getElementById('countdown');
function tick(){{el.textContent='00:'+String(Math.max(0,remaining)).padStart(2,'0');if(remaining--<=0)clearInterval(timer)}}
tick();const timer=setInterval(tick,1000);
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
<script>function clock(){{document.getElementById('clock').textContent=new Date().toLocaleTimeString('de-DE',{{hour:'2-digit',minute:'2-digit'}})}}clock();setInterval(clock,1000);</script>{script}</body></html>"""


def _employee_name(db: Session, employee_id: int) -> str:
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    return f"{employee.first_name} {employee.last_name}" if employee else f"Mitarbeiter {employee_id}"


@router.get('/terminal/auth-enrollment/{plugin_key}/{employee_id}', response_class=HTMLResponse)
def auth_enrollment_display(
    plugin_key: str,
    employee_id: int,
    seconds: int = Query(35, ge=5, le=300),
    identifier: str = Query(''),
    message: str = Query(''),
    db: Session = Depends(get_db),
):
    return HTMLResponse(_page(plugin_key, _employee_name(db, employee_id), seconds, identifier, message))


# Kompatibilitätsroute für bereits installierte 6.0.0-Terminal-Agenten.
@router.get('/terminal/rfid-enrollment/{employee_id}', response_class=HTMLResponse)
def enrollment_display(
    employee_id: int,
    seconds: int = Query(35, ge=5, le=300),
    uid: str = Query(''),
    db: Session = Depends(get_db),
):
    return HTMLResponse(_page('rfid', _employee_name(db, employee_id), seconds, uid))
