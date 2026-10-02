"""Admin-Verwaltung für gekoppelte Smartphones.

Smartphones verwenden provider='mobile_app' und einen stabilen Geräte-Token.
RFID-/NFC-UID-Medien bleiben vollständig in employee_rfid_media.
"""
from __future__ import annotations

import json
from html import escape

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Employee
from app.services.auth_credentials import EmployeeAuthCredential, activate_auth_credential, revoke_auth_credential
from .common import log_action, require_admin_response
from .mobile_pairing import create_pairing_session, pairing_qr_data_uri

router = APIRouter()
PROVIDER = "mobile_app"


def _authorized(request: Request, db: Session):
    user, redirect = require_admin_response(request, db)
    if redirect:
        return None, JSONResponse({"status": "error", "message": "Admin-Anmeldung erforderlich"}, status_code=401)
    return user, None


def _row_json(row: EmployeeAuthCredential) -> dict:
    try:
        metadata = json.loads(row.metadata_json or "{}")
    except Exception:
        metadata = {}
    return {
        "id": row.id, "employee_id": row.employee_id, "provider": row.provider,
        "credential_type": row.credential_type, "display_name": row.display_name,
        "active": bool(row.active), "identifier_hint": row.identifier_hint,
        "created_at": row.created_at.isoformat(timespec="seconds") if row.created_at else None,
        "updated_at": row.updated_at.isoformat(timespec="seconds") if row.updated_at else None,
        "last_used_at": row.last_used_at.isoformat(timespec="seconds") if row.last_used_at else None,
        "revoked_at": row.revoked_at.isoformat(timespec="seconds") if row.revoked_at else None,
        "revoked_reason": row.revoked_reason, "metadata": metadata,
    }


def _devices(db: Session, employee_id: int):
    return db.query(EmployeeAuthCredential).filter(
        EmployeeAuthCredential.employee_id == employee_id,
        EmployeeAuthCredential.provider == PROVIDER,
    ).order_by(EmployeeAuthCredential.id.desc()).all()


def _page(employee: Employee, rows, pairing_url: str = "", qr_data: str = "") -> str:
    cards = "".join(f"""<article class='device'><div><h3>{escape(row.display_name or 'Smartphone')}</h3><p>{'Aktiv' if row.active else 'Gesperrt'} · Letzte Nutzung: {row.last_used_at.strftime('%d.%m.%Y %H:%M:%S') if row.last_used_at else 'Noch nie'}</p></div><div class='actions'><form method='post' action='/admin/employees/{employee.id}/mobile-devices/{row.id}/{'revoke' if row.active else 'activate'}'><button class='{'danger' if row.active else ''}'>{'Sperren' if row.active else 'Aktivieren'}</button></form><form method='post' action='/admin/employees/{employee.id}/mobile-devices/{row.id}/delete' onsubmit="return confirm('Smartphone wirklich löschen?')"><button class='danger'>Löschen</button></form></div></article>""" for row in rows) or "<p>Noch kein Smartphone gekoppelt.</p>"
    pairing = f"""<section><h2>Neues Smartphone koppeln</h2><p>QR-Code mit dem Smartphone öffnen. Der Link ist nur wenige Minuten gültig.</p><img class='qr' src='{qr_data}' alt='Pairing QR-Code'><p><a class='link' href='{escape(pairing_url)}'>Pairing-Link auf diesem Gerät öffnen</a></p></section>""" if pairing_url else """<section><h2>Neues Smartphone koppeln</h2><form method='post' action='/admin/employees/{employee.id}/mobile-devices/pair'><button>Pairing starten</button></form><p>Die wechselnde NFC-UID des Smartphones wird nicht gespeichert.</p></section>"""
    return f"""<!doctype html><html lang='de'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Smartphones</title><style>body{{font-family:system-ui;background:#f3f6fa;color:#172033;margin:0}}main{{max-width:950px;margin:auto;padding:28px}}section,.device{{background:white;border:1px solid #dbe3ee;border-radius:13px;padding:20px;margin:16px 0}}.device{{display:flex;justify-content:space-between;align-items:center;gap:18px}}.actions{{display:flex;gap:8px}}form{{margin:0}}button,.link{{display:inline-block;border:0;border-radius:8px;padding:11px 15px;background:#1769e0;color:white;font-weight:700;text-decoration:none;cursor:pointer}}button.danger{{background:#b42318}}.qr{{width:260px;max-width:100%;height:auto}}p{{color:#667085}}@media(max-width:650px){{.device{{display:block}}.actions{{margin-top:12px;flex-wrap:wrap}}}}</style></head><body><main><a href='/admin/employees/{employee.id}/edit'>← Zurück zum Mitarbeiter</a><h1>Smartphones: {escape(employee.first_name)} {escape(employee.last_name)}</h1><p>Hier werden ausschließlich gekoppelte Smartphones verwaltet. RFID-Karten und feste NFC-Tags bleiben getrennt.</p><section><h2>Gekoppelte Geräte ({len(rows)})</h2>{cards}</section>{pairing}</main></body></html>"""


@router.get('/admin/employees/{employee_id}/mobile-devices', response_class=HTMLResponse)
def mobile_devices_page(employee_id: int, request: Request, db: Session = Depends(get_db)):
    user, redirect = require_admin_response(request, db)
    if redirect: return redirect
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee: return HTMLResponse('<h1>Mitarbeiter nicht gefunden</h1>', status_code=404)
    return HTMLResponse(_page(employee, _devices(db, employee_id)))


@router.post('/admin/employees/{employee_id}/mobile-devices/pair', response_class=HTMLResponse)
def start_mobile_pairing(employee_id: int, request: Request, db: Session = Depends(get_db)):
    user, redirect = require_admin_response(request, db)
    if redirect: return redirect
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee: return HTMLResponse('<h1>Mitarbeiter nicht gefunden</h1>', status_code=404)
    try:
        session, token = create_pairing_session(db, employee_id, PROVIDER)
    except ValueError as exc:
        return HTMLResponse(f'<h1>Pairing fehlgeschlagen</h1><p>{escape(str(exc))}</p>', status_code=400)
    pairing_url = str(request.base_url).rstrip('/') + f'/mobile/pair/{token}'
    log_action(db, user.employee_number, 'mobile_pairing_created', 'employees', str(employee_id), f'session={session.id}')
    return HTMLResponse(_page(employee, _devices(db, employee_id), pairing_url, pairing_qr_data_uri(pairing_url)))


def _device_action(employee_id: int, credential_id: int, request: Request, db: Session, action: str):
    user, redirect = require_admin_response(request, db)
    if redirect: return redirect
    row = db.query(EmployeeAuthCredential).filter(EmployeeAuthCredential.id == credential_id, EmployeeAuthCredential.employee_id == employee_id, EmployeeAuthCredential.provider == PROVIDER).first()
    if not row: return HTMLResponse('<h1>Smartphone nicht gefunden</h1>', status_code=404)
    if action == 'revoke': revoke_auth_credential(db, row.id, 'Smartphone durch Administrator gesperrt')
    elif action == 'activate': activate_auth_credential(db, row.id)
    elif action == 'delete': db.delete(row)
    db.commit(); log_action(db, user.employee_number, f'mobile_device_{action}', 'employee_auth_credentials', str(credential_id), f'employee={employee_id}')
    return RedirectResponse(f'/admin/employees/{employee_id}/mobile-devices', status_code=303)


@router.post('/admin/employees/{employee_id}/mobile-devices/{credential_id}/revoke')
def revoke_device_page(employee_id:int, credential_id:int, request:Request, db:Session=Depends(get_db)): return _device_action(employee_id,credential_id,request,db,'revoke')

@router.post('/admin/employees/{employee_id}/mobile-devices/{credential_id}/activate')
def activate_device_page(employee_id:int, credential_id:int, request:Request, db:Session=Depends(get_db)): return _device_action(employee_id,credential_id,request,db,'activate')

@router.post('/admin/employees/{employee_id}/mobile-devices/{credential_id}/delete')
def delete_device_page(employee_id:int, credential_id:int, request:Request, db:Session=Depends(get_db)): return _device_action(employee_id,credential_id,request,db,'delete')


@router.get('/api/admin/mobile-devices/employees/{employee_id}')
def list_mobile_devices(employee_id:int, request:Request, db:Session=Depends(get_db)):
    user,error=_authorized(request,db)
    if error:return error
    employee=db.query(Employee).filter(Employee.id==employee_id).first()
    if not employee:return JSONResponse({'status':'error','message':'Mitarbeiter nicht gefunden'},status_code=404)
    return {'status':'ok','employee_id':employee.id,'employee':f'{employee.first_name} {employee.last_name}','devices':[_row_json(row) for row in _devices(db,employee_id)]}

@router.post('/api/admin/mobile-devices/{credential_id}/revoke')
def revoke_mobile_device(credential_id:int,request:Request,db:Session=Depends(get_db)):
    user,error=_authorized(request,db)
    if error:return error
    row=db.query(EmployeeAuthCredential).filter(EmployeeAuthCredential.id==credential_id,EmployeeAuthCredential.provider==PROVIDER).first()
    if not row:return JSONResponse({'status':'error','message':'Smartphone nicht gefunden'},status_code=404)
    revoke_auth_credential(db,row.id,'Smartphone durch Administrator gesperrt');db.commit();log_action(db,user.employee_number,'mobile_device_revoked','employee_auth_credentials',str(row.id),f'employee={row.employee_id}');return {'status':'ok','device':_row_json(row)}

@router.post('/api/admin/mobile-devices/{credential_id}/activate')
def activate_mobile_device(credential_id:int,request:Request,db:Session=Depends(get_db)):
    user,error=_authorized(request,db)
    if error:return error
    row=db.query(EmployeeAuthCredential).filter(EmployeeAuthCredential.id==credential_id,EmployeeAuthCredential.provider==PROVIDER).first()
    if not row:return JSONResponse({'status':'error','message':'Smartphone nicht gefunden'},status_code=404)
    activate_auth_credential(db,row.id);db.commit();log_action(db,user.employee_number,'mobile_device_activated','employee_auth_credentials',str(row.id),f'employee={row.employee_id}');return {'status':'ok','device':_row_json(row)}

@router.delete('/api/admin/mobile-devices/{credential_id}')
def delete_mobile_device(credential_id:int,request:Request,db:Session=Depends(get_db)):
    user,error=_authorized(request,db)
    if error:return error
    row=db.query(EmployeeAuthCredential).filter(EmployeeAuthCredential.id==credential_id,EmployeeAuthCredential.provider==PROVIDER).first()
    if not row:return JSONResponse({'status':'error','message':'Smartphone nicht gefunden'},status_code=404)
    employee_id=row.employee_id;db.delete(row);db.commit();log_action(db,user.employee_number,'mobile_device_deleted','employee_auth_credentials',str(credential_id),f'employee={employee_id}');return {'status':'ok','credential_id':credential_id}
