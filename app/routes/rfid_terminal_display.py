from __future__ import annotations

from html import escape

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Employee

router = APIRouter()


def _page(title: str, employee_name: str, seconds: int, uid: str = "") -> str:
    success = bool(uid)
    accent = "#22c55e" if success else "#2384ff"
    heading = "ERFOLGREICH" if success else "RFID / NFC ANLERNEN"
    body = (
        f"<div class='check'>✓</div><h2>Medium erkannt</h2><p class='uid'>UID: {escape(uid)}</p>"
        if success
        else "<div class='waves'>)))</div><h2>Bitte Karte, Handy oder Smartwatch an den Leser halten.</h2>"
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
<meta name='viewport' content='width=device-width,initial-scale=1'><title>{escape(title)}</title>
<style>
*{{box-sizing:border-box}}html,body{{width:100%;height:100%;margin:0;overflow:hidden}}
body{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;background:#06080d;color:white;display:flex;align-items:center;justify-content:center}}
.panel{{width:100vw;height:100vh;padding:7vh 8vw;display:flex;flex-direction:column;background:radial-gradient(circle at 20% 20%,#17233b,#06080d 58%)}}
.top{{display:flex;justify-content:space-between;align-items:center}}.heading{{font-size:4.2vw;color:{accent};font-weight:800;letter-spacing:.04em}}.clock{{font-size:3vw}}
.main{{flex:1;display:grid;grid-template-columns:30% 1fr;align-items:center;gap:5vw}}h2{{font-size:5vw;line-height:1.16;margin:.4em 0}}p{{font-size:3vw;margin:.35em 0;color:#d8e0ec}}
.name{{color:{accent};font-weight:750}}.waves{{font-size:10vw;color:{accent};font-weight:900;transform:rotate(180deg)}}.check{{font-size:12vw;color:{accent};font-weight:900}}
.uid{{font-family:ui-monospace,monospace;font-size:3.2vw}}.footer{{background:{accent};padding:2.4vh 3vw;font-size:3vw;font-weight:750;border-radius:1.2vw;display:flex;justify-content:space-between}}
</style></head><body><main class='panel'><div class='top'><div class='heading'>{heading}</div><div class='clock' id='clock'></div></div>
<div class='main'><div>{body}</div><div><p>Mitarbeiter</p><h2 class='name'>{escape(employee_name)}</h2></div></div>
<div class='footer'><span>{footer}</span><span>{'✓' if success else ''}</span></div></main>
<script>function clock(){{document.getElementById('clock').textContent=new Date().toLocaleTimeString('de-DE',{{hour:'2-digit',minute:'2-digit'}})}}clock();setInterval(clock,1000);</script>{script}</body></html>"""


@router.get('/terminal/rfid-enrollment/{employee_id}', response_class=HTMLResponse)
def enrollment_display(
    employee_id: int,
    seconds: int = Query(35, ge=5, le=300),
    uid: str = Query(''),
    db: Session = Depends(get_db),
):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    employee_name = f"{employee.first_name} {employee.last_name}" if employee else f"Mitarbeiter {employee_id}"
    return HTMLResponse(_page('RFID/NFC anlernen', employee_name, seconds, uid))
