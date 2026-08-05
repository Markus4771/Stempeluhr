from html import escape

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Employee
from app.services.rfid_media import EmployeeRfidMedia, add_rfid_medium
from .common import require_admin_response, log_action

router = APIRouter()


def _page(employee: Employee, media: list[EmployeeRfidMedia], message: str = "") -> str:
    rows = "".join(
        f"<tr><td>{escape(m.name)}</td><td><code>{escape(m.uid_raw or m.uid)}</code></td>"
        f"<td>{escape(m.media_type)}</td><td>{'aktiv' if m.active else 'inaktiv'}</td>"
        f"<td><form method='post' action='/admin/employees/{employee.id}/rfid-media/{m.id}/delete' "
        f"onsubmit=\"return confirm('Medium wirklich löschen?')\"><button type='submit'>Löschen</button></form></td></tr>"
        for m in media
    ) or "<tr><td colspan='5'>Noch keine zusätzlichen Medien vorhanden.</td></tr>"

    return f"""<!doctype html>
<html lang='de'><head><meta charset='utf-8'><title>RFID/NFC-Medien</title>
<style>body{{font-family:sans-serif;max-width:1000px;margin:2rem auto;padding:0 1rem}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ccc;padding:.6rem;text-align:left}}label{{display:block;margin:.8rem 0}}input,select{{padding:.5rem;min-width:22rem}}button{{padding:.55rem 1rem}}.msg{{padding:.7rem;background:#eef;margin:1rem 0}}</style></head>
<body><p><a href='/admin/employees/{employee.id}/edit'>← Zurück zum Mitarbeiter</a></p>
<h1>RFID/NFC-Medien: {escape(employee.first_name)} {escape(employee.last_name)}</h1>
{f"<div class='msg'>{escape(message)}</div>" if message else ''}
<table><thead><tr><th>Bezeichnung</th><th>UID</th><th>Typ</th><th>Status</th><th>Aktion</th></tr></thead><tbody>{rows}</tbody></table>
<h2>Neues Medium anlernen</h2>
<p>In das UID-Feld klicken und Karte, Handy oder Smartwatch an den Leser halten.</p>
<form method='post'>
<label>Bezeichnung <input name='name' placeholder='z. B. Smartwatch' required></label>
<label>Typ <select name='media_type'><option value='rfid'>RFID-Karte</option><option value='nfc_phone'>Handy</option><option value='nfc_watch'>Smartwatch</option><option value='nfc_ring'>NFC-Ring</option><option value='other'>Sonstiges</option></select></label>
<label>UID <input name='uid' autocomplete='off' autofocus required></label>
<button type='submit'>Medium speichern</button>
</form></body></html>"""


@router.get('/admin/employees/{employee_id}/rfid-media', response_class=HTMLResponse)
def list_media(employee_id: int, request: Request, message: str = '', db: Session = Depends(get_db)):
    user, redirect = require_admin_response(request, db)
    if redirect:
        return redirect
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        return HTMLResponse('<h1>Mitarbeiter nicht gefunden</h1>', status_code=404)
    media = db.query(EmployeeRfidMedia).filter(EmployeeRfidMedia.employee_id == employee_id).order_by(EmployeeRfidMedia.id).all()
    return HTMLResponse(_page(employee, media, message))


@router.post('/admin/employees/{employee_id}/rfid-media')
def create_medium(
    employee_id: int,
    request: Request,
    uid: str = Form(...),
    name: str = Form('RFID/NFC-Medium'),
    media_type: str = Form('rfid'),
    db: Session = Depends(get_db),
):
    user, redirect = require_admin_response(request, db)
    if redirect:
        return redirect
    try:
        medium = add_rfid_medium(db, employee_id, uid, name, media_type)
        db.commit()
        log_action(db, user.employee_number, 'rfid_medium_added', 'employees', str(employee_id), f'{medium.name}: {medium.uid}')
        message = 'Medium wurde gespeichert.'
    except ValueError as exc:
        db.rollback()
        message = str(exc)
    from urllib.parse import quote
    return RedirectResponse(f'/admin/employees/{employee_id}/rfid-media?message={quote(message)}', status_code=303)


@router.post('/admin/employees/{employee_id}/rfid-media/{medium_id}/delete')
def delete_medium(employee_id: int, medium_id: int, request: Request, db: Session = Depends(get_db)):
    user, redirect = require_admin_response(request, db)
    if redirect:
        return redirect
    medium = db.query(EmployeeRfidMedia).filter(
        EmployeeRfidMedia.id == medium_id,
        EmployeeRfidMedia.employee_id == employee_id,
    ).first()
    if medium:
        details = f'{medium.name}: {medium.uid}'
        db.delete(medium)
        db.commit()
        log_action(db, user.employee_number, 'rfid_medium_deleted', 'employees', str(employee_id), details)
    return RedirectResponse(f'/admin/employees/{employee_id}/rfid-media', status_code=303)
