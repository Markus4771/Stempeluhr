from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc

from .common import templates, require_system_admin_response
from app.database import get_db
from app.models import RaspberryClient
from app.services.monitoring import system_status
from app.services.rollback import list_rollback_backups, create_manual_restore_point

router = APIRouter()


def raspberry_online(client: RaspberryClient) -> bool:
    try:
        return bool(client.last_seen and client.last_seen > datetime.now() - timedelta(seconds=90))
    except Exception:
        return False


@router.get('/system/monitoring', response_class=HTMLResponse)
def monitoring_page(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    clients = db.query(RaspberryClient).order_by(desc(RaspberryClient.last_seen)).all()
    return templates.TemplateResponse('system_monitoring.html', {
        'request': request,
        'user': user,
        'status': system_status(db),
        'raspberry_clients': clients,
        'raspberry_online': raspberry_online,
    })


@router.get('/api/v1/monitoring')
def monitoring_api(db: Session = Depends(get_db)):
    status = system_status(db)
    clients = db.query(RaspberryClient).order_by(desc(RaspberryClient.last_seen)).all()
    status['raspberry_clients'] = [{
        'id': c.id,
        'hostname': c.hostname,
        'ip_address': c.ip_address,
        'online': raspberry_online(c),
        'chromium_running': bool(c.chromium_running),
        'kiosk_url': c.kiosk_url,
        'fullscreen': bool(c.fullscreen),
        'last_seen': c.last_seen.isoformat() if c.last_seen else None,
        'cpu_percent': c.cpu_percent,
        'ram_percent': c.ram_percent,
        'temperature': c.temperature,
        'uptime': c.uptime,
        'agent_version': c.agent_version,
        'pending_command': c.pending_command,
        'command_result': c.command_result,
    } for c in clients]
    return status


@router.get('/system/rollback', response_class=HTMLResponse)
def rollback_page(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    return templates.TemplateResponse('system_rollback.html', {'request': request, 'user': user, 'backups': list_rollback_backups(), 'message': None})


@router.post('/system/rollback/restore-point', response_class=HTMLResponse)
def rollback_restore_point(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    result = create_manual_restore_point('Manueller Wiederherstellungspunkt aus GUI')
    return templates.TemplateResponse('system_rollback.html', {'request': request, 'user': user, 'backups': list_rollback_backups(), 'message': result})
