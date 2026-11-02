from __future__ import annotations

from html import escape
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Employee
from app.services.auth_credentials import (
    activate_auth_credential,
    add_auth_credential,
    list_employee_credentials,
    revoke_auth_credential,
)
from .common import require_admin_response

router = APIRouter()


PROVIDER_LABELS = {
    "rfid": "RFID / NFC-Tag",
    "qr": "QR-Code",
    "pin": "PIN",
    "fingerprint": "Fingerabdruck",
    "mobile_app": "Handy-App",
    "smartwatch": "Smartwatch",
    "fido2": "FIDO2 / Passkey",
    "bluetooth": "Bluetooth",
}


def _page(employee: Employee, credentials, message: str = "") -> str:
    cards = "".join(
        f"""
        <article class='credential {'inactive' if not item.active else ''}'>
          <div>
            <span class='provider'>{escape(PROVIDER_LABELS.get(item.provider, item.provider))}</span>
            <h3>{escape(item.display_name)}</h3>
            <p>{escape(item.credential_type)} · {escape(item.identifier_hint or 'Kennung geschützt')}</p>
            <small>Letzte Nutzung: {item.last_used_at.strftime('%d.%m.%Y %H:%M:%S') if item.last_used_at else 'Noch nie'}</small>
          </div>
          <div class='right'>
            <span class='state {'ok' if item.active else 'off'}'>{'Aktiv' if item.active else 'Gesperrt'}</span>
            <form method='post' action='/admin/employees/{employee.id}/auth-credentials/{item.id}/{'revoke' if item.active else 'activate'}'>
              <button class='{'danger' if item.active else 'secondary'}' type='submit'>{'Sperren' if item.active else 'Aktivieren'}</button>
            </form>
          </div>
        </article>
        """
        for item in credentials
    ) or "<div class='empty'>Noch keine allgemeinen Anmeldemedien vorhanden.</div>"

    return f"""<!doctype html>
<html lang='de'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Anmeldemedien</title>
<style>
:root{{--bg:#f3f6fb;--card:#fff;--text:#172033;--muted:#667085;--line:#d9e2ee;--blue:#1769e0;--red:#c93434;--green:#18864b}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);font-family:system-ui,-apple-system,Segoe UI,sans-serif;color:var(--text)}}
main{{max-width:1150px;margin:0 auto;padding:28px}}a{{color:var(--blue)}}h1{{margin-bottom:5px}}.sub{{color:var(--muted);margin-top:0}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:15px;padding:22px;margin-top:18px;box-shadow:0 4px 18px rgba(20,30,50,.06)}}
.credential{{display:flex;justify-content:space-between;gap:20px;padding:17px;border:1px solid var(--line);border-radius:12px;margin:12px 0;background:white}}
.credential.inactive{{opacity:.72;background:#f8fafc}}.credential h3{{margin:7px 0 4px}}.credential p,.credential small{{color:var(--muted)}}
.provider{{display:inline-block;background:#eaf2ff;color:#1658a8;padding:4px 9px;border-radius:999px;font-size:.82rem;font-weight:700}}
.right{{display:flex;align-items:center;gap:12px}}.state{{font-weight:700}}.state.ok{{color:var(--green)}}.state.off{{color:var(--red)}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:15px}}label{{display:block;font-weight:650;margin-bottom:6px}}input,select{{width:100%;padding:11px;border:1px solid #bbc7d6;border-radius:9px;font:inherit}}
button{{border:0;border-radius:9px;padding:10px 15px;background:var(--blue);color:white;font-weight:700;cursor:pointer}}button.danger{{background:white;color:var(--red);border:1px solid #e5a1a1}}button.secondary{{background:white;color:var(--blue);border:1px solid var(--blue)}}
.msg{{padding:12px 15px;border-radius:10px;background:#ecfdf3;border:1px solid #a8e0bd;margin-top:15px}}.empty{{color:var(--muted);text-align:center;padding:28px}}
@media(max-width:760px){{.grid{{grid-template-columns:1fr}}.credential{{display:block}}.right{{margin-top:14px;justify-content:space-between}}main{{padding:15px}}}}
</style></head><body><main>
<a href='/admin/employees/{employee.id}/edit'>← Zurück zum Mitarbeiter</a>
<h1>Anmeldemedien: {escape(employee.first_name)} {escape(employee.last_name)}</h1>
<p class='sub'>Alle Anmeldeverfahren dieses Mitarbeiters zentral verwalten.</p>
{f"<div class='msg'>{escape(message)}</div>" if message else ''}
<section class='card'><h2>Vorhandene Medien ({len(credentials)})</h2>{cards}</section>
<section class='card'><h2>Medium manuell hinzufügen</h2>
<form method='post'>
<div class='grid'>
<div><label>Provider</label><select name='provider'><option value='rfid'>RFID / NFC-Tag</option><option value='qr'>QR-Code</option><option value='pin'>PIN</option><option value='fingerprint'>Fingerabdruck</option><option value='mobile_app'>Handy-App</option><option value='smartwatch'>Smartwatch</option><option value='fido2'>FIDO2 / Passkey</option><option value='bluetooth'>Bluetooth</option></select></div>
<div><label>Typ</label><input name='credential_type' placeholder='z. B. Firmenkarte, Galaxy Watch' required></div>
<div><label>Bezeichnung</label><input name='display_name' placeholder='z. B. Firmenausweis' required></div>
<div><label>Kennung</label><input name='identifier' placeholder='UID, Token oder Gerätekennung' required></div>
</div><p><button type='submit'>Anmeldemedium speichern</button></p>
</form></section>
</main></body></html>"""


@router.get('/admin/employees/{employee_id}/auth-credentials', response_class=HTMLResponse)
def list_credentials(employee_id: int, request: Request, message: str = '', db: Session = Depends(get_db)):
    user, redirect = require_admin_response(request, db)
    if redirect:
        return redirect
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        return HTMLResponse('<h1>Mitarbeiter nicht gefunden</h1>', status_code=404)
    return HTMLResponse(_page(employee, list_employee_credentials(db, employee_id), message))


@router.post('/admin/employees/{employee_id}/auth-credentials')
def create_credential(
    employee_id: int,
    request: Request,
    provider: str = Form(...),
    credential_type: str = Form(...),
    display_name: str = Form(...),
    identifier: str = Form(...),
    db: Session = Depends(get_db),
):
    user, redirect = require_admin_response(request, db)
    if redirect:
        return redirect
    try:
        add_auth_credential(
            db,
            employee_id=employee_id,
            provider=provider,
            credential_type=credential_type,
            identifier=identifier,
            display_name=display_name,
        )
        db.commit()
        message = 'Anmeldemedium wurde gespeichert.'
    except ValueError as exc:
        db.rollback()
        message = str(exc)
    return RedirectResponse(f'/admin/employees/{employee_id}/auth-credentials?message={quote(message)}', status_code=303)


@router.post('/admin/employees/{employee_id}/auth-credentials/{credential_id}/revoke')
def revoke_credential(employee_id: int, credential_id: int, request: Request, db: Session = Depends(get_db)):
    user, redirect = require_admin_response(request, db)
    if redirect:
        return redirect
    try:
        revoke_auth_credential(db, credential_id)
        db.commit()
        message = 'Anmeldemedium wurde gesperrt.'
    except ValueError as exc:
        db.rollback()
        message = str(exc)
    return RedirectResponse(f'/admin/employees/{employee_id}/auth-credentials?message={quote(message)}', status_code=303)


@router.post('/admin/employees/{employee_id}/auth-credentials/{credential_id}/activate')
def activate_credential(employee_id: int, credential_id: int, request: Request, db: Session = Depends(get_db)):
    user, redirect = require_admin_response(request, db)
    if redirect:
        return redirect
    try:
        activate_auth_credential(db, credential_id)
        db.commit()
        message = 'Anmeldemedium wurde aktiviert.'
    except ValueError as exc:
        db.rollback()
        message = str(exc)
    return RedirectResponse(f'/admin/employees/{employee_id}/auth-credentials?message={quote(message)}', status_code=303)
