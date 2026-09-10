from __future__ import annotations

import base64
import hashlib
import io
import json
import secrets
from datetime import datetime, timedelta
from html import escape

import qrcode
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Session

from app.auth_plugins.registry import installed_plugin
from app.database import Base, engine, get_db
from app.models import Employee
from app.services.auth_credentials import add_auth_credential
from .common import create_time_entry, determine_auto_entry_type

router = APIRouter()


class MobilePairingSession(Base):
    __tablename__ = "mobile_pairing_sessions"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(50), nullable=False, default="mobile_app")
    pairing_hash = Column(String(64), nullable=False, unique=True, index=True)
    pairing_hint = Column(String(20), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    completed = Column(Boolean, nullable=False, default=False)
    credential_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    completed_at = Column(DateTime, nullable=True)


def ensure_mobile_pairing_schema() -> None:
    Base.metadata.create_all(bind=engine, tables=[MobilePairingSession.__table__])


def _hash(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def create_pairing_session(db: Session, employee_id: int, provider: str = "mobile_app", token: str | None = None) -> tuple[MobilePairingSession, str]:
    employee = db.query(Employee).filter(Employee.id == employee_id, Employee.active.is_(True)).first()
    if not employee:
        raise ValueError("Mitarbeiter nicht gefunden")
    raw = token or secrets.token_urlsafe(24)
    existing = db.query(MobilePairingSession).filter(MobilePairingSession.pairing_hash == _hash(raw)).first()
    if existing:
        return existing, raw
    row = MobilePairingSession(employee_id=employee_id, provider=provider, pairing_hash=_hash(raw), pairing_hint=raw[:6].upper(), expires_at=datetime.now() + timedelta(minutes=5))
    db.add(row); db.commit(); db.refresh(row)
    return row, raw


def get_pairing_session(db: Session, token: str) -> MobilePairingSession | None:
    return db.query(MobilePairingSession).filter(MobilePairingSession.pairing_hash == _hash(token)).first()


def pairing_qr_data_uri(url: str) -> str:
    image = qrcode.make(url); output = io.BytesIO(); image.save(output, format="PNG")
    return "data:image/png;base64," + base64.b64encode(output.getvalue()).decode("ascii")


def _pairing_page(token: str, error: str = "") -> str:
    failure = f"<p class='error'>{escape(error)}</p>" if error else ""
    return f"""<!doctype html><html lang='de'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Handy koppeln</title><style>body{{font-family:system-ui;margin:0;background:#f3f6fa;color:#172033}}main{{max-width:520px;margin:8vh auto;background:white;padding:28px;border-radius:16px;box-shadow:0 8px 30px #0001}}input,button{{width:100%;padding:13px;margin-top:10px;font:inherit;box-sizing:border-box}}button{{background:#1769e0;color:white;border:0;border-radius:8px;font-weight:700}}.error{{color:#b42318}}</style></head><body><main><h1>Handy mit Stempeluhr koppeln</h1><p>Gib diesem Gerät einen Namen. Die wechselnde NFC-UID wird nicht verwendet.</p>{failure}<form method='post' action='/mobile/pair/{escape(token)}'><label>Gerätename</label><input name='device_name' value='Mein Handy' maxlength='100' required><button type='submit'>Dieses Handy koppeln</button></form></main></body></html>"""


def _mobile_clock_page(message: str = "", error: str = "") -> str:
    return f"""<!doctype html><html lang='de'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Mobile Stempeluhr</title><style>body{{font-family:system-ui;margin:0;background:#f3f6fa;color:#172033}}main{{max-width:520px;margin:6vh auto;background:white;padding:28px;border-radius:16px;box-shadow:0 8px 30px #0001}}button{{width:100%;padding:16px;margin-top:12px;border:0;border-radius:10px;background:#1769e0;color:white;font:700 1.05rem system-ui}}.secondary{{background:#475467}}.ok{{padding:12px;background:#ecfdf3;color:#116a3b;border-radius:8px}}.error{{padding:12px;background:#fff1f1;color:#9f2424;border-radius:8px}}</style></head><body><main><h1>Mobile Stempeluhr</h1>{f'<p class="ok">{escape(message)}</p>' if message else ''}{f'<p class="error">{escape(error)}</p>' if error else ''}<p id='state'>Gekoppeltes Handy wird geprüft …</p><button onclick="stamp('auto')">Automatisch Kommen / Gehen</button><button class='secondary' onclick="stamp('kommen')">Kommen</button><button class='secondary' onclick="stamp('gehen')">Gehen</button><script>
const token=localStorage.getItem('stempeluhr_mobile_token')||'';const state=document.getElementById('state');if(!token)state.textContent='Dieses Handy ist noch nicht gekoppelt.';else state.textContent='Handy gekoppelt und bereit.';
async function stamp(action){{if(!token){{state.textContent='Dieses Handy ist nicht gekoppelt.';return}}state.textContent='Buchung wird gesendet …';try{{const r=await fetch('/mobile/clock',{{method:'POST',headers:{{'Content-Type':'application/x-www-form-urlencoded'}},body:new URLSearchParams({{device_token:token,action}})}});const d=await r.json();state.textContent=d.message||'Antwort erhalten.';if(!r.ok)state.className='error';else state.className='ok';}}catch(e){{state.textContent='Server nicht erreichbar.';state.className='error';}}}}
</script></main></body></html>"""


@router.get('/mobile/pair/{token}', response_class=HTMLResponse, name="pairing_form")
def pairing_form(token: str, db: Session = Depends(get_db)):
    row = get_pairing_session(db, token)
    if not row or row.completed or row.expires_at < datetime.now():
        return HTMLResponse(_pairing_page('', 'Dieser Pairing-Link ist ungültig oder abgelaufen.'), status_code=410)
    return HTMLResponse(_pairing_page(token))


@router.post('/mobile/pair/{token}', response_class=HTMLResponse)
def pairing_complete(token: str, device_name: str = Form('Mein Handy'), db: Session = Depends(get_db)):
    row = get_pairing_session(db, token)
    if not row or row.completed or row.expires_at < datetime.now():
        return HTMLResponse(_pairing_page('', 'Dieser Pairing-Link ist ungültig oder abgelaufen.'), status_code=410)
    device_token = secrets.token_urlsafe(48)
    credential = add_auth_credential(db, employee_id=row.employee_id, provider=row.provider, credential_type='mobile_device', identifier=device_token, display_name=(device_name or 'Mein Handy').strip(), metadata={'paired_at': datetime.now().isoformat(timespec='seconds')})
    db.flush(); row.completed = True; row.credential_id = credential.id; row.completed_at = datetime.now(); db.commit()
    token_js = json.dumps(device_token); credential_js = json.dumps(str(credential.id))
    return HTMLResponse(f"""<!doctype html><html lang='de'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Handy gekoppelt</title><style>body{{font-family:system-ui;background:#f3f6fa;color:#172033}}main{{max-width:520px;margin:8vh auto;background:white;padding:28px;border-radius:16px}}a{{display:block;padding:14px;background:#1769e0;color:white;text-align:center;text-decoration:none;border-radius:9px}}</style></head><body><main><h1>Handy gekoppelt</h1><p>Dieses Gerät ist jetzt mit der Stempeluhr verbunden.</p><a href='/mobile/clock'>Mobile Stempeluhr öffnen</a><script>localStorage.setItem('stempeluhr_mobile_token',{token_js});localStorage.setItem('stempeluhr_mobile_credential_id',{credential_js});</script></main></body></html>""")


@router.get('/mobile/clock', response_class=HTMLResponse)
def mobile_clock_page():
    return HTMLResponse(_mobile_clock_page())


@router.post('/mobile/clock')
def mobile_clock(device_token: str = Form(...), action: str = Form('auto'), db: Session = Depends(get_db)):
    plugin = installed_plugin('mobile_app')
    if not plugin:
        return JSONResponse({'status': 'error', 'message': 'Handy-Plugin ist nicht installiert.'}, status_code=503)
    result = plugin.authenticate(db, device_token, {'source': 'mobile_web'})
    if not result.success or not result.employee_id:
        db.rollback()
        return JSONResponse({'status': 'error', 'message': result.message or 'Handy nicht erkannt.'}, status_code=401)
    employee = db.query(Employee).filter(Employee.id == result.employee_id, Employee.active.is_(True)).first()
    if not employee:
        db.rollback(); return JSONResponse({'status': 'error', 'message': 'Mitarbeiter ist nicht aktiv.'}, status_code=403)
    if action == 'auto':
        entry_type = determine_auto_entry_type(db, employee.id)
    elif action in {'kommen', 'gehen'}:
        entry_type = action
    else:
        db.rollback(); return JSONResponse({'status': 'error', 'message': 'Ungültige Buchungsart.'}, status_code=400)
    entry, duplicate_last = create_time_entry(db, employee, entry_type, 'mobile_app', 'mobile_web', 'Buchung über gekoppeltes Handy', duplicate_seconds=8)
    if duplicate_last:
        db.rollback(); return JSONResponse({'status': 'duplicate', 'message': 'Diese Buchung wurde gerade bereits erfasst.'}, status_code=409)
    db.commit()
    label = 'Kommen' if entry_type == 'kommen' else 'Gehen'
    return {'status': 'ok', 'entry_type': entry_type, 'employee_id': employee.id, 'message': f'{label} für {employee.first_name} {employee.last_name} gebucht.'}


@router.get('/mobile/pair/status/{session_id}')
def pairing_status(session_id: int, db: Session = Depends(get_db)):
    row = db.query(MobilePairingSession).filter(MobilePairingSession.id == session_id).first()
    if not row:
        return JSONResponse({'status': 'not_found'}, status_code=404)
    if row.completed:
        return {'status': 'complete', 'credential_id': row.credential_id}
    if row.expires_at < datetime.now():
        return {'status': 'expired'}
    return {'status': 'waiting', 'pairing_code': row.pairing_hint, 'expires_at': row.expires_at.isoformat(timespec='seconds')}
