from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta
from html import escape

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import Employee
from app.services.auth_credentials import add_auth_credential

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


def create_pairing_session(db: Session, employee_id: int, provider: str = "mobile_app") -> tuple[MobilePairingSession, str]:
    employee = db.query(Employee).filter(Employee.id == employee_id, Employee.active.is_(True)).first()
    if not employee:
        raise ValueError("Mitarbeiter nicht gefunden")
    raw = secrets.token_urlsafe(24)
    row = MobilePairingSession(
        employee_id=employee_id,
        provider=provider,
        pairing_hash=_hash(raw),
        pairing_hint=raw[:6].upper(),
        expires_at=datetime.now() + timedelta(minutes=5),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row, raw


def _pairing_page(token: str, message: str = "", error: str = "") -> str:
    notice = f"<p style='color:#167344'>{escape(message)}</p>" if message else ""
    failure = f"<p style='color:#b42318'>{escape(error)}</p>" if error else ""
    return f"""<!doctype html><html lang='de'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Handy koppeln</title><style>body{{font-family:system-ui;margin:0;background:#f3f6fa;color:#172033}}main{{max-width:520px;margin:8vh auto;background:white;padding:28px;border-radius:16px}}input,button{{width:100%;padding:13px;margin-top:10px;font:inherit;box-sizing:border-box}}button{{background:#1769e0;color:white;border:0;border-radius:8px;font-weight:700}}</style></head><body><main>
<h1>Handy mit Stempeluhr koppeln</h1><p>Gib diesem Gerät einen Namen. Danach wird auf diesem Handy ein stabiler, zufälliger Geräte-Token erzeugt und sicher im Browser gespeichert. Die wechselnde NFC-UID wird nicht verwendet.</p>{notice}{failure}
<form method='post' action='/mobile/pair/{escape(token)}'><label>Gerätename</label><input name='device_name' value='Mein Handy' maxlength='100' required><button type='submit'>Dieses Handy koppeln</button></form>
</main></body></html>"""


@router.get('/mobile/pair/{token}', response_class=HTMLResponse)
def pairing_form(token: str, db: Session = Depends(get_db)):
    row = db.query(MobilePairingSession).filter(MobilePairingSession.pairing_hash == _hash(token)).first()
    if not row or row.completed or row.expires_at < datetime.now():
        return HTMLResponse(_pairing_page('', error='Dieser Pairing-Link ist ungültig oder abgelaufen.'), status_code=410)
    return HTMLResponse(_pairing_page(token))


@router.post('/mobile/pair/{token}', response_class=HTMLResponse)
def pairing_complete(token: str, device_name: str = Form('Mein Handy'), db: Session = Depends(get_db)):
    row = db.query(MobilePairingSession).filter(MobilePairingSession.pairing_hash == _hash(token)).first()
    if not row or row.completed or row.expires_at < datetime.now():
        return HTMLResponse(_pairing_page('', error='Dieser Pairing-Link ist ungültig oder abgelaufen.'), status_code=410)

    device_token = secrets.token_urlsafe(48)
    credential = add_auth_credential(
        db,
        employee_id=row.employee_id,
        provider=row.provider,
        credential_type='mobile_device',
        identifier=device_token,
        display_name=(device_name or 'Mein Handy').strip(),
        metadata={'paired_at': datetime.now().isoformat(timespec='seconds')},
    )
    db.flush()
    row.completed = True
    row.credential_id = credential.id
    row.completed_at = datetime.now()
    db.commit()

    # Der Klartext-Token wird nur einmal an dieses Gerät ausgeliefert und bleibt nicht in der DB.
    html = f"""<!doctype html><html lang='de'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Handy gekoppelt</title></head><body><main style='font-family:system-ui;max-width:520px;margin:8vh auto'><h1>Handy gekoppelt</h1><p>Dieses Gerät ist jetzt mit der Stempeluhr verbunden.</p><script>localStorage.setItem('stempeluhr_mobile_token',{device_token!r});</script></main></body></html>"""
    return HTMLResponse(html)


@router.get('/mobile/pair/status/{session_id}')
def pairing_status(session_id: int, db: Session = Depends(get_db)):
    row = db.query(MobilePairingSession).filter(MobilePairingSession.id == session_id).first()
    if not row:
        return JSONResponse({'status': 'not_found'}, status_code=404)
    if row.completed:
        return {'status': 'complete', 'credential_id': row.credential_id}
    if row.expires_at < datetime.now():
        return {'status': 'expired'}
    return {'status': 'waiting', 'expires_at': row.expires_at.isoformat(timespec='seconds')}
